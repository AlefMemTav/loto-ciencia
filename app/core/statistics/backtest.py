# app/core/statistics/backtest.py
"""
Backtest Científico & Validação Temporal (Forward Testing)
VERSÃO FINAL: Walk-Forward + Monte Carlo (hipótese nula) + p-valor empírico.

O que esta função mede:
- Se o método (Genético/Vetorial) tem performance acima do acaso em um teste fora-da-amostra,
  com baseline estocástico robusto (Monte Carlo) em cada janela temporal.

O que ela NÃO promete:
- "prever" sorteios. Ela apenas testa se existe ganho estatístico vs aleatório.
"""

import numpy as np
import pandas as pd
import random
from typing import List, Dict, Optional, Tuple

from app.core.lottery import GameConfig
from app.core.statistics import get_tabela_inteligencia, analise_intervalo_confianca
from app.core.logger import logger

from app.core.generator_fast import gerar_jogos_vetorizado
from app.core.generator_genetic import gerar_jogos_geneticos


# ----------------------------------------------------------------------
# Mock Context mínimo para os geradores (igual ao seu)
# ----------------------------------------------------------------------
class MockContext:
    def __init__(self, df, config, tabela, ic_info):
        self.df = df
        self.config = config
        self.tabela = tabela
        self.ic_info = ic_info

        draw_cols = [c for c in df.columns if c.startswith("D")]
        if not draw_cols:
            draw_cols = config.draw_cols

        self.historico_set = set(tuple(sorted(x)) for x in df[draw_cols].values)
        self.pesos_dinamicos = {"w_freq": 0.5, "w_gap": 0.5}


# ----------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------
def _extrair_draw_cols(df: pd.DataFrame, config: GameConfig) -> List[str]:
    cols = [c for c in df.columns if c.startswith("D")]
    return cols if cols else list(config.draw_cols)


def _contar_hits_e_score(
    lista_jogos: List[List[int]], gabarito: np.ndarray
) -> Tuple[int, Dict[str, int]]:
    """
    Score operacional (apenas para comparação): quadra=1, quina=50, sena=1000.
    Também retorna contagens absolutas de hits 4/5/6+.
    """
    score_total = 0
    hits = {"4": 0, "5": 0, "6": 0}

    # Converte gabarito em sets uma vez (velocidade)
    g_sets = [set(row.tolist()) for row in gabarito]

    for jogo in lista_jogos:
        s_jogo = set(jogo)
        for s_real in g_sets:
            acertos = len(s_jogo.intersection(s_real))
            if acertos == 4:
                hits["4"] += 1
                score_total += 1
            elif acertos == 5:
                hits["5"] += 1
                score_total += 50
            elif acertos >= 6:
                hits["6"] += 1
                score_total += 1000

    return score_total, hits


def _mc_gerar_jogos_numpy(
    rng: np.random.Generator, n_jogos: int, n_numbers: int, k: int
) -> List[List[int]]:
    """
    Gera n_jogos jogos aleatórios (sem repetição) usando numpy.
    Retorna lista de listas ordenadas.
    """
    jogos = []
    # Para simplicidade/compatibilidade: loop por jogo, mas usando RNG do numpy
    # (Mais rápido que random.sample e reprodutível via rng)
    for _ in range(n_jogos):
        arr = rng.choice(np.arange(1, n_numbers + 1), size=k, replace=False)
        arr.sort()
        jogos.append(arr.tolist())
    return jogos


def _p_empirico_supera_ou_iguala(mc_scores: np.ndarray, score_obs: float) -> float:
    """
    p-valor empírico unilateral (conservador):
    p = P_MC(score >= score_obs). Usa correção +1/(N+1) para nunca dar 0.
    """
    n = len(mc_scores)
    if n <= 0:
        return 1.0
    return (np.sum(mc_scores >= score_obs) + 1.0) / (n + 1.0)


def _bootstrap_ic95_media(
    deltas: np.ndarray, n_boot: int, rng: np.random.Generator
) -> Tuple[float, float]:
    if len(deltas) == 0:
        return (0.0, 0.0)
    means = []
    for _ in range(n_boot):
        sample = rng.choice(deltas, size=len(deltas), replace=True)
        means.append(float(np.mean(sample)))
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(lo), float(hi)


# ----------------------------------------------------------------------
# Função principal
# ----------------------------------------------------------------------
def executar_backtest_temporal(
    df_completo: pd.DataFrame,
    config: GameConfig,
    n_janelas: int = 12,
    jogos_por_janela: int = 10,
    n_simulacoes_monte_carlo: int = 500,
    tamanho_teste: int = 10,
    step: int = 20,
    seed: int = 42,
    n_bootstrap: int = 2000,
    estrategia: str = "balanceada",
) -> Dict:
    """
    Walk-Forward + Monte Carlo:
    - Para cada corte temporal:
      - Treina no passado (df_treino)
      - Testa nos próximos 'tamanho_teste' sorteios reais
      - Compara método vs distribuição aleatória gerada por Monte Carlo
    - Retorna p-valor empírico por janela + agregações globais.

    Métrica primária operacional: score ponderado (1/50/1000) por janela.
    Métricas secundárias: hits 4/5/6+ absolutos.
    """
    logger.info(
        f"⏳ Backtest Científico (Walk-Forward + Monte Carlo N={n_simulacoes_monte_carlo}) para {config.name}"
    )

    total_sorteios = len(df_completo)
    if total_sorteios < 200:
        return {
            "erro": "Histórico insuficiente para backtest temporal (mínimo 200 sorteios)."
        }

    inicio = max(100, total_sorteios - (n_janelas * step) - tamanho_teste)
    pontos_corte = list(range(inicio, total_sorteios - tamanho_teste, step))
    if len(pontos_corte) == 0:
        return {
            "erro": "Não foi possível montar pontos de corte com os parâmetros atuais."
        }

    # RNGs reprodutíveis
    rng_global = np.random.default_rng(seed)

    # Acumuladores por janela (para inferência)
    deltas_gen = []
    deltas_vet = []
    pvals_gen = []
    pvals_vet = []
    wins_gen = 0
    wins_vet = 0
    n_janelas_validas = 0

    # Acumuladores de hits absolutos (reais) e baseline esperado (média MC)
    hits_reais = {
        "Genetico": {"4": 0, "5": 0, "6": 0},
        "Vetorial": {"4": 0, "5": 0, "6": 0},
    }
    hits_esperado_mc = {"4": 0.0, "5": 0.0, "6": 0.0}

    detalhes = []

    for corte in pontos_corte:
        df_treino = df_completo.iloc[:corte].copy()
        df_futuro = df_completo.iloc[corte : corte + tamanho_teste].copy()

        draw_cols = _extrair_draw_cols(df_futuro, config)
        gabarito = df_futuro[draw_cols].values

        try:
            tabela = get_tabela_inteligencia(df_treino, config)
            ic_info = analise_intervalo_confianca(df_treino, config)
            ctx = MockContext(df_treino, config, tabela, ic_info)

            jogos_gen = gerar_jogos_geneticos(
                ctx, quantidade=jogos_por_janela, estrategia=estrategia
            )
            jogos_vet = gerar_jogos_vetorizado(
                ctx, quantidade=jogos_por_janela, estrategia=estrategia
            )

            score_gen, hits_gen = _contar_hits_e_score(jogos_gen, gabarito)
            score_vet, hits_vet = _contar_hits_e_score(jogos_vet, gabarito)

            for kk in ["4", "5", "6"]:
                hits_reais["Genetico"][kk] += int(hits_gen[kk])
                hits_reais["Vetorial"][kk] += int(hits_vet[kk])

        except Exception as e:
            logger.error(f"[Backtest] Erro no corte {corte}: {e}")
            continue

        # Monte Carlo por janela (hipótese nula)
        # Usa seed derivada do corte para independência reprodutível por janela
        rng_janela = np.random.default_rng(seed + int(corte))

        mc_scores = np.zeros(n_simulacoes_monte_carlo, dtype=float)
        mc_hits = {"4": 0, "5": 0, "6": 0}

        for i in range(n_simulacoes_monte_carlo):
            jogos_mc = _mc_gerar_jogos_numpy(
                rng=rng_janela,
                n_jogos=jogos_por_janela,
                n_numbers=config.n_numbers,
                k=config.bet_size,
            )
            s_mc, h_mc = _contar_hits_e_score(jogos_mc, gabarito)
            mc_scores[i] = s_mc
            for kk in ["4", "5", "6"]:
                mc_hits[kk] += int(h_mc[kk])

        media_mc = float(np.mean(mc_scores))
        # delta = ganho absoluto vs esperança do acaso (por janela)
        delta_gen = float(score_gen - media_mc)
        delta_vet = float(score_vet - media_mc)

        # p-valores empíricos por janela (unilateral: "melhor que acaso")
        p_gen = _p_empirico_supera_ou_iguala(mc_scores, score_gen)
        p_vet = _p_empirico_supera_ou_iguala(mc_scores, score_vet)

        # win/loss por janela (métrica simples, robusta)
        wins_gen += int(score_gen > media_mc)
        wins_vet += int(score_vet > media_mc)

        deltas_gen.append(delta_gen)
        deltas_vet.append(delta_vet)
        pvals_gen.append(p_gen)
        pvals_vet.append(p_vet)

        # baseline esperado (média de hits MC por janela)
        for kk in ["4", "5", "6"]:
            hits_esperado_mc[kk] += mc_hits[kk] / n_simulacoes_monte_carlo

        n_janelas_validas += 1

        detalhes.append(
            {
                "corte": int(corte),
                "janela_futura": f"{int(corte)+1} a {int(corte)+tamanho_teste}",
                "score_gen": int(score_gen),
                "score_vet": int(score_vet),
                "mc_media": round(media_mc, 4),
                "delta_gen": round(delta_gen, 4),
                "delta_vet": round(delta_vet, 4),
                "p_emp_gen": round(p_gen, 6),
                "p_emp_vet": round(p_vet, 6),
            }
        )

    if n_janelas_validas == 0:
        return {
            "erro": "Nenhuma janela válida foi processada (todos os cortes falharam)."
        }

    deltas_gen = np.array(deltas_gen, dtype=float)
    deltas_vet = np.array(deltas_vet, dtype=float)

    # IC95% do ganho médio via bootstrap nas janelas (robusto e interpretável)
    ic_gen = _bootstrap_ic95_media(deltas_gen, n_boot=n_bootstrap, rng=rng_global)
    ic_vet = _bootstrap_ic95_media(deltas_vet, n_boot=n_bootstrap, rng=rng_global)

    # Estatística global simples: taxa de vitórias vs acaso (não é “p-value”, mas é robusto)
    win_rate_gen = wins_gen / n_janelas_validas
    win_rate_vet = wins_vet / n_janelas_validas

    # Relatório final
    return {
        "meta": {
            "jogo": config.name,
            "n_janelas_validas": int(n_janelas_validas),
            "parametros": {
                "n_janelas_solicitadas": int(n_janelas),
                "jogos_por_janela": int(jogos_por_janela),
                "tamanho_teste": int(tamanho_teste),
                "step": int(step),
                "simulacoes_mc_por_janela": int(n_simulacoes_monte_carlo),
                "seed": int(seed),
                "bootstrap_reps": int(n_bootstrap),
                "estrategia": estrategia,
            },
        },
        "analise_estatistica": {
            "Genetico": {
                "delta_medio_vs_acaso": round(float(np.mean(deltas_gen)), 4),
                "ic95_delta_medio": [round(ic_gen[0], 4), round(ic_gen[1], 4)],
                "mediana_p_emp": round(float(np.median(np.array(pvals_gen))), 6),
                "win_rate_vs_media_mc": round(float(win_rate_gen), 4),
            },
            "Vetorial": {
                "delta_medio_vs_acaso": round(float(np.mean(deltas_vet)), 4),
                "ic95_delta_medio": [round(ic_vet[0], 4), round(ic_vet[1], 4)],
                "mediana_p_emp": round(float(np.median(np.array(pvals_vet))), 6),
                "win_rate_vs_media_mc": round(float(win_rate_vet), 4),
            },
        },
        "hits_absolutos_reais": {
            "Genetico": hits_reais["Genetico"],
            "Vetorial": hits_reais["Vetorial"],
        },
        "hits_esperados_mc_media": {
            k: round(v, 3) for k, v in hits_esperado_mc.items()
        },
        "detalhes_janelas": detalhes,
    }


# Mantida por compatibilidade (não confundir com prova de performance preditiva)
def backtest_validator(df, config, n_amostras=1000, random_state=42):
    return {
        "status": "deprecated",
        "msg": "Use executar_backtest_temporal (walk-forward + monte carlo).",
    }
