# app/core/statistics/backtest.py
"""
Backtest Científico & Validação Temporal (Forward Testing)
VERSÃO FINAL: Walk-Forward + Monte Carlo (hipótese nula) + p-valor empírico.
Pontuação adaptativa por jogo (Lotomania, Quina, etc).
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple

from app.core.lottery import GameConfig
from app.core.logger import logger


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
    lista_jogos: List[List[int]], gabarito: np.ndarray, config: GameConfig
) -> Tuple[int, Dict[str, int]]:
    """
    Score adaptativo por jogo.
    Retorna Score Total (para cálculo do Delta) e Hits Absolutos.
    """
    score_total = 0
    # Inicializa hits genéricos estendidos
    hits = {
        "0": 0,
        "2": 0,
        "3": 0,
        "4": 0,
        "5": 0,
        "6": 0,
        "11": 0,
        "12": 0,
        "13": 0,
        "14": 0,
        "15": 0,
        "16": 0,
        "17": 0,
        "18": 0,
        "19": 0,
        "20": 0,
    }

    g_sets = [set(row.tolist()) for row in gabarito]
    slug = config.slug

    is_lotomania = "loto_mania_sorteio" in slug
    is_lotofacil = "loto_facil_sorteio" in slug
    is_quina = "quina_sorteio" in slug

    for jogo in lista_jogos:
        s_jogo = set(jogo)
        for s_real in g_sets:
            acertos = len(s_jogo.intersection(s_real))

            if is_lotomania:
                # Lotomania: Paga 20, 19, 18, 17, 16, 15 e 0
                if acertos == 20:
                    hits["20"] += 1
                    score_total += 1000000
                elif acertos == 19:
                    hits["19"] += 1
                    score_total += 50000
                elif acertos == 18:
                    hits["18"] += 1
                    score_total += 2000
                elif acertos == 17:
                    hits["17"] += 1
                    score_total += 200
                elif acertos == 16:
                    hits["16"] += 1
                    score_total += 50
                elif acertos == 15:
                    hits["15"] += 1
                    score_total += 10
                elif acertos == 0:
                    hits["0"] += 1
                    score_total += 200000  # Espelho vale muito

                # Mapeamento para visualização simples (compatibilidade)
                if acertos >= 15 or acertos == 0:
                    hits["6"] += 1  # Marca como "Hit relevante" no bucket genérico

            elif is_lotofacil:
                # Lotofácil: 11 a 15
                if acertos == 15:
                    hits["15"] += 1
                    hits["6"] += 1  # Bucket 6 = Maximo
                    score_total += 1000000
                elif acertos == 14:
                    hits["14"] += 1
                    hits["5"] += 1
                    score_total += 2000
                elif acertos == 13:
                    hits["13"] += 1
                    hits["4"] += 1
                    score_total += 25
                elif acertos == 12:
                    hits["12"] += 1
                    score_total += 10
                elif acertos == 11:
                    hits["11"] += 1
                    score_total += 5

            elif is_quina:
                # Quina: 2, 3, 4, 5
                if acertos == 5:
                    hits["5"] += 1
                    hits["6"] += 1
                    score_total += 1000000
                elif acertos == 4:
                    hits["4"] += 1
                    score_total += 10000
                elif acertos == 3:
                    hits["3"] += 1
                    score_total += 200
                elif acertos == 2:
                    hits["2"] += 1
                    score_total += 10

            else:
                # Mega-Sena e Padrão (6 números)
                if acertos >= 6:
                    hits["6"] += 1
                    score_total += 1000000
                elif acertos == 5:
                    hits["5"] += 1
                    score_total += 5000
                elif acertos == 4:
                    hits["4"] += 1
                    score_total += 100

    return score_total, hits


def _mc_gerar_jogos_numpy(
    rng: np.random.Generator, n_jogos: int, n_numbers: int, k: int
) -> List[List[int]]:
    jogos = []
    for _ in range(n_jogos):
        arr = rng.choice(np.arange(1, n_numbers + 1), size=k, replace=False)
        arr.sort()
        jogos.append(arr.tolist())
    return jogos


def _p_empirico_supera_ou_iguala(mc_scores: np.ndarray, score_obs: float) -> float:
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
    from app.services.lottery_service import LotteryService

    logger.info(
        f"⏳ Backtest Científico ({config.name}) - Janelas: {n_janelas}, MC: {n_simulacoes_monte_carlo}"
    )

    total_sorteios = len(df_completo)
    if total_sorteios < 200:
        return {"erro": "Histórico insuficiente (mínimo 200 sorteios)."}

    inicio = max(100, total_sorteios - (n_janelas * step) - tamanho_teste)
    pontos_corte = list(range(inicio, total_sorteios - tamanho_teste, step))

    if not pontos_corte:
        return {"erro": "Não foi possível gerar janelas de teste."}

    rng_global = np.random.default_rng(seed)

    deltas_gen = []
    deltas_vet = []
    pvals_gen = []
    pvals_vet = []
    wins_gen = 0
    wins_vet = 0
    n_janelas_validas = 0

    # Inicializa acumuladores de hits (chaves relevantes)
    keys_hits = [
        "0",
        "2",
        "3",
        "4",
        "5",
        "6",
        "11",
        "12",
        "13",
        "14",
        "15",
        "16",
        "17",
        "18",
        "19",
        "20",
    ]
    hits_reais = {
        "Genetico": {k: 0 for k in keys_hits},
        "Vetorial": {k: 0 for k in keys_hits},
    }
    hits_esperado_mc = {k: 0.0 for k in keys_hits}

    detalhes = []

    service = LotteryService()

    for corte in pontos_corte:
        df_treino = df_completo.iloc[:corte].copy()
        df_futuro = df_completo.iloc[corte : corte + tamanho_teste].copy()

        draw_cols = _extrair_draw_cols(df_futuro, config)
        gabarito = df_futuro[draw_cols].values

        try:
            ctx_janela = service.build_context_from_df(config, df_treino)
            payload = {"quantidade": jogos_por_janela, "estrategia": estrategia}
            jogos_gen = service.generate_genetic(config.slug, payload, ctx=ctx_janela)
            jogos_vet = service.generate(config.slug, payload, ctx=ctx_janela)

            score_gen, hits_gen = _contar_hits_e_score(jogos_gen, gabarito, config)
            score_vet, hits_vet = _contar_hits_e_score(jogos_vet, gabarito, config)

            for k in keys_hits:
                hits_reais["Genetico"][k] += hits_gen.get(k, 0)
                hits_reais["Vetorial"][k] += hits_vet.get(k, 0)

        except Exception as e:
            logger.error(f"[Backtest] Erro no corte {corte}: {e}")
            continue

        # Monte Carlo
        rng_janela = np.random.default_rng(seed + int(corte))
        mc_scores = np.zeros(n_simulacoes_monte_carlo, dtype=float)

        # Buffer temporário para hits MC desta janela
        mc_hits_janela = {k: 0 for k in keys_hits}

        for i in range(n_simulacoes_monte_carlo):
            jogos_mc = _mc_gerar_jogos_numpy(
                rng=rng_janela,
                n_jogos=jogos_por_janela,
                n_numbers=config.n_numbers,
                k=config.bet_size,
            )
            s_mc, h_mc = _contar_hits_e_score(jogos_mc, gabarito, config)
            mc_scores[i] = s_mc

            for k in keys_hits:
                mc_hits_janela[k] += h_mc.get(k, 0)

        media_mc = float(np.mean(mc_scores))

        # Atualiza esperança matemática global
        for k in keys_hits:
            hits_esperado_mc[k] += mc_hits_janela[k] / n_simulacoes_monte_carlo

        delta_gen = float(score_gen - media_mc)
        delta_vet = float(score_vet - media_mc)

        p_gen = _p_empirico_supera_ou_iguala(mc_scores, score_gen)
        p_vet = _p_empirico_supera_ou_iguala(mc_scores, score_vet)

        wins_gen += int(score_gen > media_mc)
        wins_vet += int(score_vet > media_mc)

        deltas_gen.append(delta_gen)
        deltas_vet.append(delta_vet)
        pvals_gen.append(p_gen)
        pvals_vet.append(p_vet)

        n_janelas_validas += 1

        detalhes.append(
            {
                "corte": int(corte),
                "janela_futura": f"{int(corte)+1} a {int(corte)+tamanho_teste}",
                "score_gen": int(score_gen),
                "score_vet": int(score_vet),
                "mc_media": round(media_mc, 2),
                "delta_gen": round(delta_gen, 2),
                "delta_vet": round(delta_vet, 2),
                "p_emp_gen": round(p_gen, 4),
                "p_emp_vet": round(p_vet, 4),
            }
        )

    if n_janelas_validas == 0:
        return {"erro": "Nenhuma janela válida processada."}

    deltas_gen = np.array(deltas_gen)
    deltas_vet = np.array(deltas_vet)

    ic_gen = _bootstrap_ic95_media(deltas_gen, n_boot=n_bootstrap, rng=rng_global)
    ic_vet = _bootstrap_ic95_media(deltas_vet, n_boot=n_bootstrap, rng=rng_global)

    # Limpa keys zeradas do relatório final para não poluir
    def limpar_zeros(d):
        # Lista de chaves que queremos ver sempre, mesmo que sejam zero
        whitelist = [
            "0",
            "2",
            "3",
            "4",
            "5",
            "6",  # Mega, Quina, Mania(0)
            "11",
            "12",
            "13",
            "14",
            "15",  # Lotofácil, Mania
            "16",
            "17",
            "18",
            "19",
            "20",  # Mania
        ]
        return {k: v for k, v in d.items() if v > 0 or k in whitelist}

    return {
        "meta": {
            "jogo": config.name,
            "n_janelas_validas": n_janelas_validas,
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
            "simulacoes_mc": n_simulacoes_monte_carlo,
        },
        "analise_estatistica": {
            "Genetico": {
                "delta_medio_vs_acaso": round(float(np.mean(deltas_gen)), 4),
                "ic95_delta_medio": ic_gen,
                "mediana_p_emp": round(float(np.median(np.array(pvals_gen))), 6),
                "win_rate_vs_media_mc": round(wins_gen / n_janelas_validas, 4),
            },
            "Vetorial": {
                "delta_medio_vs_acaso": round(float(np.mean(deltas_vet)), 4),
                "ic95_delta_medio": ic_vet,
                "mediana_p_emp": round(float(np.median(np.array(pvals_vet))), 6),
                "win_rate_vs_media_mc": round(wins_vet / n_janelas_validas, 4),
            },
        },
        "hits_absolutos_reais": {
            "Genetico": limpar_zeros(hits_reais["Genetico"]),
            "Vetorial": limpar_zeros(hits_reais["Vetorial"]),
        },
        "hits_esperados_mc_media": limpar_zeros(
            {k: round(v, 2) for k, v in hits_esperado_mc.items()}
        ),
        "detalhes_janelas": detalhes,
    }
