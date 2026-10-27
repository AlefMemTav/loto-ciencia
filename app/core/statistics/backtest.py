# app/core/statistics/backtest.py
"""
Backtest Científico & Validação Temporal (Forward Testing)
VERSÃO FINAL: Walk-Forward + Monte Carlo (hipótese nula) + p-valor empírico.
Pontuação adaptativa por jogo (Lotomania, Quina, etc).
"""

import numpy as np
import pandas as pd
from typing import Any, List, Dict, Tuple

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
) -> Tuple[int, Dict[str, int], Dict[str, Any]]:
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
    match_distribution = {str(i): 0 for i in range(config.bet_size + 1)}
    max_acertos = 0

    is_lotomania = "loto_mania_sorteio" in slug
    is_lotofacil = "loto_facil_sorteio" in slug
    is_quina = "quina_sorteio" in slug

    for jogo in lista_jogos:
        s_jogo = set(jogo)
        for s_real in g_sets:
            acertos = len(s_jogo.intersection(s_real))
            match_distribution[str(acertos)] = (
                match_distribution.get(str(acertos), 0) + 1
            )
            max_acertos = max(max_acertos, acertos)

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

    total_comparacoes = max(1, len(lista_jogos) * len(g_sets))
    soma_acertos = sum(int(k) * v for k, v in match_distribution.items())
    match_stats = {
        "distribuicao": match_distribution,
        "media_acertos": float(soma_acertos / total_comparacoes),
        "max_acertos": int(max_acertos),
        "comparacoes": int(total_comparacoes),
    }

    return score_total, hits, match_stats


def _nova_dist_acertos(config: GameConfig) -> Dict[str, float]:
    return {str(i): 0.0 for i in range(config.bet_size + 1)}


def _somar_dist_acertos(destino: Dict[str, float], origem: Dict[str, Any]) -> None:
    for k, v in origem.items():
        destino[str(k)] = destino.get(str(k), 0.0) + float(v)


def _resumir_dist_acertos(dist: Dict[str, float]) -> Dict[str, Any]:
    total = float(sum(dist.values()))
    if total <= 0:
        return {
            "distribuicao": {
                k: round(v, 4)
                for k, v in sorted(dist.items(), key=lambda x: int(x[0]))
            },
            "media_acertos": 0.0,
            "max_acertos_observado": 0,
            "comparacoes": 0,
        }

    soma_acertos = sum(int(k) * float(v) for k, v in dist.items())
    max_obs = max((int(k) for k, v in dist.items() if float(v) > 0), default=0)
    return {
        "distribuicao": {
            k: round(float(v), 4)
            for k, v in sorted(dist.items(), key=lambda x: int(x[0]))
        },
        "media_acertos": round(float(soma_acertos / total), 6),
        "max_acertos_observado": int(max_obs),
        "comparacoes": round(total, 4),
    }


def _novo_acumulador_portfolio(config: GameConfig) -> Dict[str, Any]:
    return {
        "n": 0,
        "numeric": {},
        "exposicao_dezenas": {str(n): 0.0 for n in range(1, config.n_numbers + 1)},
    }


def _flatten_numeric(prefix: str, data: Dict[str, Any], out: Dict[str, float]) -> None:
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else str(key)
        if key in {"exposicao_dezenas", "top_dezenas"}:
            continue
        if isinstance(value, dict):
            _flatten_numeric(full_key, value, out)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            out[full_key] = float(value)


def _somar_diagnostico_portfolio(
    acc: Dict[str, Any], diag: Dict[str, Any], peso: float = 1.0
) -> None:
    if not diag:
        return

    acc["n"] += float(peso)
    numeric: Dict[str, float] = {}
    _flatten_numeric("", diag, numeric)
    for key, value in numeric.items():
        acc["numeric"][key] = acc["numeric"].get(key, 0.0) + (value * peso)

    for dezena, count in diag.get("exposicao_dezenas", {}).items():
        acc["exposicao_dezenas"][str(dezena)] = (
            acc["exposicao_dezenas"].get(str(dezena), 0.0) + (float(count) * peso)
        )


def _resumir_diagnostico_portfolio(acc: Dict[str, Any]) -> Dict[str, Any]:
    n = float(acc.get("n", 0.0))
    if n <= 0:
        return {}

    exposure = {
        k: round(float(v), 4)
        for k, v in sorted(
            acc["exposicao_dezenas"].items(),
            key=lambda item: int(item[0]),
        )
        if float(v) > 0
    }
    top_dezenas = sorted(
        ((int(k), float(v)) for k, v in exposure.items()),
        key=lambda item: (-item[1], item[0]),
    )[:10]

    return {
        "medias": {
            key: round(value / n, 6)
            for key, value in sorted(acc.get("numeric", {}).items())
        },
        "exposicao_dezenas_total": exposure,
        "top_dezenas_total": [
            {"dezena": dezena, "vezes": round(vezes, 4)}
            for dezena, vezes in top_dezenas
        ],
    }


def _novo_acumulador_calibracao() -> Dict[str, Any]:
    return {"n": 0.0, "numeric": {}}


def _somar_diagnostico_calibracao(
    acc: Dict[str, Any], diag: Dict[str, Any], peso: float = 1.0
) -> None:
    if not diag:
        return
    acc["n"] += float(peso)
    for key in (
        "score_medio",
        "score_min",
        "score_max",
        "js_vs_alvo",
        "js_vs_historico",
        "js_vs_nulo",
        "chi_square_vs_alvo",
    ):
        value = diag.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            acc["numeric"][key] = acc["numeric"].get(key, 0.0) + (float(value) * peso)


def _resumir_diagnostico_calibracao(acc: Dict[str, Any]) -> Dict[str, Any]:
    n = float(acc.get("n", 0.0))
    if n <= 0:
        return {}
    return {
        "medias": {
            key: round(value / n, 6)
            for key, value in sorted(acc.get("numeric", {}).items())
        }
    }


def _novo_acumulador_financeiro() -> Dict[str, Any]:
    return {
        "n": 0.0,
        "custo_total": 0.0,
        "receita_bruta": 0.0,
        "lucro_liquido": 0.0,
        "paid_hits": {},
        "numeric": {},
        "tabela_premios": {},
    }


def _somar_diagnostico_financeiro(
    acc: Dict[str, Any], diag: Dict[str, Any], peso: float = 1.0
) -> None:
    if not diag:
        return
    acc["n"] += float(peso)
    acc["custo_total"] += float(diag.get("custo_total", 0.0)) * peso
    acc["receita_bruta"] += float(diag.get("receita_bruta", 0.0)) * peso
    acc["lucro_liquido"] += float(diag.get("lucro_liquido", 0.0)) * peso
    acc["tabela_premios"] = dict(diag.get("tabela_premios", {}) or acc["tabela_premios"])
    for hit, count in (diag.get("hits_pagos", {}) or {}).items():
        acc["paid_hits"][str(hit)] = acc["paid_hits"].get(str(hit), 0.0) + (
            float(count) * peso
        )
    for key in ("roi", "fator_retorno"):
        value = diag.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            acc["numeric"][key] = acc["numeric"].get(key, 0.0) + (float(value) * peso)


def _resumir_diagnostico_financeiro(acc: Dict[str, Any]) -> Dict[str, Any]:
    cost = float(acc.get("custo_total", 0.0))
    gross = float(acc.get("receita_bruta", 0.0))
    net = float(acc.get("lucro_liquido", gross - cost))
    return {
        "custo_total": round(cost, 2),
        "receita_bruta": round(gross, 2),
        "lucro_liquido": round(net, 2),
        "roi": round(net / cost, 6) if cost > 0 else 0.0,
        "fator_retorno": round(gross / cost, 6) if cost > 0 else 0.0,
        "hits_pagos": {
            k: round(float(v), 4)
            for k, v in sorted(acc.get("paid_hits", {}).items(), key=lambda item: int(item[0]))
            if float(v) > 0
        },
        "tabela_premios": acc.get("tabela_premios", {}),
        "medias_janela": {
            key: round(value / max(1.0, float(acc.get("n", 0.0))), 6)
            for key, value in sorted(acc.get("numeric", {}).items())
        },
    }
    top_dezenas = sorted(
        ((int(k), float(v)) for k, v in exposure.items()),
        key=lambda item: (-item[1], item[0]),
    )[:10]

    return {
        "medias": {
            key: round(value / n, 6)
            for key, value in sorted(acc.get("numeric", {}).items())
        },
        "exposicao_dezenas_total": exposure,
        "top_dezenas_total": [
            {"dezena": dezena, "vezes": round(vezes, 4)}
            for dezena, vezes in top_dezenas
        ],
        "n_portfolios": round(n, 4),
    }


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
    payload_overrides: Dict[str, Any] | None = None,
    prize_table: Dict[int, float] | None = None,
) -> Dict:
    from app.services.lottery_service import LotteryService
    from app.core.generator_objective import portfolio_diagnostics
    from app.core.statistics.score_calibration import score_calibration_diagnostics
    from app.core.statistics.prize_model import (
        diagnostics_to_dict,
        financial_diagnostics,
        resolve_prize_table,
    )

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
    payload_overrides = dict(payload_overrides or {})

    deltas_gen = []
    deltas_vet = []
    deltas_media_acertos_gen = []
    deltas_media_acertos_vet = []
    deltas_receita_gen = []
    deltas_receita_vet = []
    pvals_gen = []
    pvals_vet = []
    pvals_media_acertos_gen = []
    pvals_media_acertos_vet = []
    pvals_receita_gen = []
    pvals_receita_vet = []
    wins_gen = 0
    wins_vet = 0
    wins_media_acertos_gen = 0
    wins_media_acertos_vet = 0
    wins_receita_gen = 0
    wins_receita_vet = 0
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
    dist_acertos_reais = {
        "Genetico": _nova_dist_acertos(config),
        "Vetorial": _nova_dist_acertos(config),
    }
    dist_acertos_esperado_mc = _nova_dist_acertos(config)
    diag_portfolio = {
        "Genetico": _novo_acumulador_portfolio(config),
        "Vetorial": _novo_acumulador_portfolio(config),
        "EsperadoMC": _novo_acumulador_portfolio(config),
    }
    diag_calibracao = {
        "Genetico": _novo_acumulador_calibracao(),
        "Vetorial": _novo_acumulador_calibracao(),
        "EsperadoMC": _novo_acumulador_calibracao(),
    }
    resolved_prize_table = resolve_prize_table(config, prize_table)
    diag_financeiro = {
        "Genetico": _novo_acumulador_financeiro(),
        "Vetorial": _novo_acumulador_financeiro(),
        "EsperadoMC": _novo_acumulador_financeiro(),
    }

    detalhes = []

    service = LotteryService()

    for corte in pontos_corte:
        df_treino = df_completo.iloc[:corte].copy()
        df_futuro = df_completo.iloc[corte : corte + tamanho_teste].copy()

        draw_cols = _extrair_draw_cols(df_futuro, config)
        gabarito = df_futuro[draw_cols].values

        try:
            ctx_janela = service.build_context_from_df(config, df_treino)
            payload = {
                "quantidade": jogos_por_janela,
                "estrategia": estrategia,
                **payload_overrides,
            }
            jogos_gen = service.generate_genetic(config.slug, payload, ctx=ctx_janela)
            jogos_vet = service.generate(config.slug, payload, ctx=ctx_janela)

            score_gen, hits_gen, match_gen = _contar_hits_e_score(
                jogos_gen, gabarito, config
            )
            score_vet, hits_vet, match_vet = _contar_hits_e_score(
                jogos_vet, gabarito, config
            )

            for k in keys_hits:
                hits_reais["Genetico"][k] += hits_gen.get(k, 0)
                hits_reais["Vetorial"][k] += hits_vet.get(k, 0)
            _somar_dist_acertos(
                dist_acertos_reais["Genetico"], match_gen["distribuicao"]
            )
            _somar_dist_acertos(
                dist_acertos_reais["Vetorial"], match_vet["distribuicao"]
            )
            matriz_cooc = getattr(ctx_janela, "matriz_coocorrencia", None)
            diag_gen = portfolio_diagnostics(jogos_gen, config, matriz_cooc)
            diag_vet = portfolio_diagnostics(jogos_vet, config, matriz_cooc)
            _somar_diagnostico_portfolio(diag_portfolio["Genetico"], diag_gen)
            _somar_diagnostico_portfolio(diag_portfolio["Vetorial"], diag_vet)
            cal_target = payload_overrides.get("calibration_target", "historico_nulo")
            cal_samples = payload_overrides.get("null_model_samples")
            cal_gen = score_calibration_diagnostics(
                jogos_gen,
                config,
                df_historico=ctx_janela.df,
                n_samples=cal_samples,
                target=cal_target,
            )
            cal_vet = score_calibration_diagnostics(
                jogos_vet,
                config,
                df_historico=ctx_janela.df,
                n_samples=cal_samples,
                target=cal_target,
            )
            _somar_diagnostico_calibracao(diag_calibracao["Genetico"], cal_gen)
            _somar_diagnostico_calibracao(diag_calibracao["Vetorial"], cal_vet)
            fin_gen = diagnostics_to_dict(
                financial_diagnostics(
                    jogos_gen,
                    gabarito,
                    config,
                    prize_table=resolved_prize_table,
                )
            )
            fin_vet = diagnostics_to_dict(
                financial_diagnostics(
                    jogos_vet,
                    gabarito,
                    config,
                    prize_table=resolved_prize_table,
                )
            )
            _somar_diagnostico_financeiro(diag_financeiro["Genetico"], fin_gen)
            _somar_diagnostico_financeiro(diag_financeiro["Vetorial"], fin_vet)

        except Exception as e:
            logger.error(f"[Backtest] Erro no corte {corte}: {e}")
            continue

        # Monte Carlo
        rng_janela = np.random.default_rng(seed + int(corte))
        mc_scores = np.zeros(n_simulacoes_monte_carlo, dtype=float)
        mc_media_acertos = np.zeros(n_simulacoes_monte_carlo, dtype=float)
        mc_max_acertos = np.zeros(n_simulacoes_monte_carlo, dtype=float)
        mc_receitas = np.zeros(n_simulacoes_monte_carlo, dtype=float)

        # Buffer temporário para hits MC desta janela
        mc_hits_janela = {k: 0 for k in keys_hits}
        mc_dist_acertos_janela = _nova_dist_acertos(config)

        for i in range(n_simulacoes_monte_carlo):
            jogos_mc = _mc_gerar_jogos_numpy(
                rng=rng_janela,
                n_jogos=jogos_por_janela,
                n_numbers=config.n_numbers,
                k=config.bet_size,
            )
            s_mc, h_mc, match_mc = _contar_hits_e_score(jogos_mc, gabarito, config)
            mc_scores[i] = s_mc
            mc_media_acertos[i] = match_mc["media_acertos"]
            mc_max_acertos[i] = match_mc["max_acertos"]

            for k in keys_hits:
                mc_hits_janela[k] += h_mc.get(k, 0)
            _somar_dist_acertos(
                mc_dist_acertos_janela, match_mc["distribuicao"]
            )
            diag_mc = portfolio_diagnostics(
                jogos_mc,
                config,
                getattr(ctx_janela, "matriz_coocorrencia", None),
            )
            _somar_diagnostico_portfolio(
                diag_portfolio["EsperadoMC"],
                diag_mc,
                peso=1.0 / max(1, n_simulacoes_monte_carlo),
            )
            cal_mc = score_calibration_diagnostics(
                jogos_mc,
                config,
                df_historico=ctx_janela.df,
                n_samples=payload_overrides.get("null_model_samples"),
                target=payload_overrides.get("calibration_target", "historico_nulo"),
            )
            _somar_diagnostico_calibracao(
                diag_calibracao["EsperadoMC"],
                cal_mc,
                peso=1.0 / max(1, n_simulacoes_monte_carlo),
            )
            fin_mc = diagnostics_to_dict(
                financial_diagnostics(
                    jogos_mc,
                    gabarito,
                    config,
                    prize_table=resolved_prize_table,
                )
            )
            mc_receitas[i] = fin_mc["receita_bruta"]
            _somar_diagnostico_financeiro(
                diag_financeiro["EsperadoMC"],
                fin_mc,
                peso=1.0 / max(1, n_simulacoes_monte_carlo),
            )

        media_mc = float(np.mean(mc_scores))

        # Atualiza esperança matemática global
        for k in keys_hits:
            hits_esperado_mc[k] += mc_hits_janela[k] / n_simulacoes_monte_carlo
        for k in dist_acertos_esperado_mc:
            dist_acertos_esperado_mc[k] += (
                mc_dist_acertos_janela[k] / n_simulacoes_monte_carlo
            )

        delta_gen = float(score_gen - media_mc)
        delta_vet = float(score_vet - media_mc)
        media_acertos_mc = float(np.mean(mc_media_acertos))
        delta_media_acertos_gen = float(match_gen["media_acertos"] - media_acertos_mc)
        delta_media_acertos_vet = float(match_vet["media_acertos"] - media_acertos_mc)
        media_receita_mc = float(np.mean(mc_receitas))
        delta_receita_gen = float(fin_gen["receita_bruta"] - media_receita_mc)
        delta_receita_vet = float(fin_vet["receita_bruta"] - media_receita_mc)

        p_gen = _p_empirico_supera_ou_iguala(mc_scores, score_gen)
        p_vet = _p_empirico_supera_ou_iguala(mc_scores, score_vet)
        p_media_gen = _p_empirico_supera_ou_iguala(
            mc_media_acertos, match_gen["media_acertos"]
        )
        p_media_vet = _p_empirico_supera_ou_iguala(
            mc_media_acertos, match_vet["media_acertos"]
        )
        p_receita_gen = _p_empirico_supera_ou_iguala(
            mc_receitas,
            fin_gen["receita_bruta"],
        )
        p_receita_vet = _p_empirico_supera_ou_iguala(
            mc_receitas,
            fin_vet["receita_bruta"],
        )

        wins_gen += int(score_gen > media_mc)
        wins_vet += int(score_vet > media_mc)
        wins_media_acertos_gen += int(match_gen["media_acertos"] > media_acertos_mc)
        wins_media_acertos_vet += int(match_vet["media_acertos"] > media_acertos_mc)
        wins_receita_gen += int(fin_gen["receita_bruta"] > media_receita_mc)
        wins_receita_vet += int(fin_vet["receita_bruta"] > media_receita_mc)

        deltas_gen.append(delta_gen)
        deltas_vet.append(delta_vet)
        deltas_media_acertos_gen.append(delta_media_acertos_gen)
        deltas_media_acertos_vet.append(delta_media_acertos_vet)
        deltas_receita_gen.append(delta_receita_gen)
        deltas_receita_vet.append(delta_receita_vet)
        pvals_gen.append(p_gen)
        pvals_vet.append(p_vet)
        pvals_media_acertos_gen.append(p_media_gen)
        pvals_media_acertos_vet.append(p_media_vet)
        pvals_receita_gen.append(p_receita_gen)
        pvals_receita_vet.append(p_receita_vet)

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
                "media_acertos_gen": round(match_gen["media_acertos"], 4),
                "media_acertos_vet": round(match_vet["media_acertos"], 4),
                "media_acertos_mc": round(media_acertos_mc, 4),
                "delta_media_acertos_gen": round(delta_media_acertos_gen, 6),
                "delta_media_acertos_vet": round(delta_media_acertos_vet, 6),
                "max_acertos_gen": int(match_gen["max_acertos"]),
                "max_acertos_vet": int(match_vet["max_acertos"]),
                "max_acertos_mc_medio": round(float(np.mean(mc_max_acertos)), 4),
                "p_emp_media_acertos_gen": round(p_media_gen, 4),
                "p_emp_media_acertos_vet": round(p_media_vet, 4),
                "receita_gen": round(float(fin_gen["receita_bruta"]), 2),
                "receita_vet": round(float(fin_vet["receita_bruta"]), 2),
                "receita_mc_media": round(media_receita_mc, 2),
                "delta_receita_gen": round(delta_receita_gen, 2),
                "delta_receita_vet": round(delta_receita_vet, 2),
                "roi_gen": round(float(fin_gen["roi"]), 6),
                "roi_vet": round(float(fin_vet["roi"]), 6),
                "p_emp_receita_gen": round(p_receita_gen, 4),
                "p_emp_receita_vet": round(p_receita_vet, 4),
                "portfolio_gen": {
                    "max_exposicao": diag_gen.get("max_exposicao", 0),
                    "overlap_medio": diag_gen.get("overlap_medio", 0),
                    "overlap_max": diag_gen.get("overlap_max", 0),
                    "pares_repetidos": diag_gen.get("pares_repetidos", 0),
                    "pares_repetidos_acima_2": diag_gen.get(
                        "pares_repetidos_acima_2", 0
                    ),
                    "max_repeticao_par": diag_gen.get("max_repeticao_par", 0),
                    "trincas_repetidas": diag_gen.get("trincas_repetidas", 0),
                    "max_repeticao_trinca": diag_gen.get(
                        "max_repeticao_trinca", 0
                    ),
                    "quadras_repetidas": diag_gen.get("quadras_repetidas", 0),
                    "max_repeticao_quadra": diag_gen.get(
                        "max_repeticao_quadra", 0
                    ),
                },
                "calibracao_gen": {
                    "score_medio": cal_gen.get("score_medio", 0),
                    "js_vs_alvo": cal_gen.get("js_vs_alvo", 0),
                    "chi_square_vs_alvo": cal_gen.get("chi_square_vs_alvo", 0),
                },
                "portfolio_vet": {
                    "max_exposicao": diag_vet.get("max_exposicao", 0),
                    "overlap_medio": diag_vet.get("overlap_medio", 0),
                    "overlap_max": diag_vet.get("overlap_max", 0),
                    "pares_repetidos": diag_vet.get("pares_repetidos", 0),
                    "pares_repetidos_acima_2": diag_vet.get(
                        "pares_repetidos_acima_2", 0
                    ),
                    "max_repeticao_par": diag_vet.get("max_repeticao_par", 0),
                    "trincas_repetidas": diag_vet.get("trincas_repetidas", 0),
                    "max_repeticao_trinca": diag_vet.get(
                        "max_repeticao_trinca", 0
                    ),
                    "quadras_repetidas": diag_vet.get("quadras_repetidas", 0),
                    "max_repeticao_quadra": diag_vet.get(
                        "max_repeticao_quadra", 0
                    ),
                },
                "calibracao_vet": {
                    "score_medio": cal_vet.get("score_medio", 0),
                    "js_vs_alvo": cal_vet.get("js_vs_alvo", 0),
                    "chi_square_vs_alvo": cal_vet.get("chi_square_vs_alvo", 0),
                },
            }
        )

    if n_janelas_validas == 0:
        return {"erro": "Nenhuma janela válida processada."}

    deltas_gen = np.array(deltas_gen)
    deltas_vet = np.array(deltas_vet)
    deltas_media_acertos_gen = np.array(deltas_media_acertos_gen)
    deltas_media_acertos_vet = np.array(deltas_media_acertos_vet)
    deltas_receita_gen = np.array(deltas_receita_gen)
    deltas_receita_vet = np.array(deltas_receita_vet)

    ic_gen = _bootstrap_ic95_media(deltas_gen, n_boot=n_bootstrap, rng=rng_global)
    ic_vet = _bootstrap_ic95_media(deltas_vet, n_boot=n_bootstrap, rng=rng_global)
    ic_media_gen = _bootstrap_ic95_media(
        deltas_media_acertos_gen, n_boot=n_bootstrap, rng=rng_global
    )
    ic_media_vet = _bootstrap_ic95_media(
        deltas_media_acertos_vet, n_boot=n_bootstrap, rng=rng_global
    )
    ic_receita_gen = _bootstrap_ic95_media(
        deltas_receita_gen,
        n_boot=n_bootstrap,
        rng=rng_global,
    )
    ic_receita_vet = _bootstrap_ic95_media(
        deltas_receita_vet,
        n_boot=n_bootstrap,
        rng=rng_global,
    )

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
                "opcoes_gerador": payload_overrides,
                "tabela_premios": {
                    str(k): round(float(v), 2)
                    for k, v in sorted(resolved_prize_table.items())
                },
            },
            "simulacoes_mc": n_simulacoes_monte_carlo,
        },
        "analise_estatistica": {
            "Genetico": {
                "delta_medio_vs_acaso": round(float(np.mean(deltas_gen)), 4),
                "ic95_delta_medio": ic_gen,
                "mediana_p_emp": round(float(np.median(np.array(pvals_gen))), 6),
                "win_rate_vs_media_mc": round(wins_gen / n_janelas_validas, 4),
                "delta_medio_acertos_vs_mc": round(
                    float(np.mean(deltas_media_acertos_gen)), 6
                ),
                "ic95_delta_medio_acertos": ic_media_gen,
                "mediana_p_emp_media_acertos": round(
                    float(np.median(np.array(pvals_media_acertos_gen))), 6
                ),
                "win_rate_media_acertos_vs_mc": round(
                    wins_media_acertos_gen / n_janelas_validas, 4
                ),
                "delta_medio_receita_vs_mc": round(
                    float(np.mean(deltas_receita_gen)), 6
                ),
                "ic95_delta_medio_receita": ic_receita_gen,
                "mediana_p_emp_receita": round(
                    float(np.median(np.array(pvals_receita_gen))), 6
                ),
                "win_rate_receita_vs_mc": round(
                    wins_receita_gen / n_janelas_validas, 4
                ),
            },
            "Vetorial": {
                "delta_medio_vs_acaso": round(float(np.mean(deltas_vet)), 4),
                "ic95_delta_medio": ic_vet,
                "mediana_p_emp": round(float(np.median(np.array(pvals_vet))), 6),
                "win_rate_vs_media_mc": round(wins_vet / n_janelas_validas, 4),
                "delta_medio_acertos_vs_mc": round(
                    float(np.mean(deltas_media_acertos_vet)), 6
                ),
                "ic95_delta_medio_acertos": ic_media_vet,
                "mediana_p_emp_media_acertos": round(
                    float(np.median(np.array(pvals_media_acertos_vet))), 6
                ),
                "win_rate_media_acertos_vs_mc": round(
                    wins_media_acertos_vet / n_janelas_validas, 4
                ),
                "delta_medio_receita_vs_mc": round(
                    float(np.mean(deltas_receita_vet)), 6
                ),
                "ic95_delta_medio_receita": ic_receita_vet,
                "mediana_p_emp_receita": round(
                    float(np.median(np.array(pvals_receita_vet))), 6
                ),
                "win_rate_receita_vs_mc": round(
                    wins_receita_vet / n_janelas_validas, 4
                ),
            },
        },
        "hits_absolutos_reais": {
            "Genetico": limpar_zeros(hits_reais["Genetico"]),
            "Vetorial": limpar_zeros(hits_reais["Vetorial"]),
        },
        "hits_esperados_mc_media": limpar_zeros(
            {k: round(v, 2) for k, v in hits_esperado_mc.items()}
        ),
        "diagnostico_acertos": {
            "Genetico": _resumir_dist_acertos(dist_acertos_reais["Genetico"]),
            "Vetorial": _resumir_dist_acertos(dist_acertos_reais["Vetorial"]),
            "EsperadoMC": _resumir_dist_acertos(dist_acertos_esperado_mc),
        },
        "diagnostico_portfolio": {
            "Genetico": _resumir_diagnostico_portfolio(diag_portfolio["Genetico"]),
            "Vetorial": _resumir_diagnostico_portfolio(diag_portfolio["Vetorial"]),
            "EsperadoMC": _resumir_diagnostico_portfolio(diag_portfolio["EsperadoMC"]),
        },
        "diagnostico_calibracao_score": {
            "Genetico": _resumir_diagnostico_calibracao(diag_calibracao["Genetico"]),
            "Vetorial": _resumir_diagnostico_calibracao(diag_calibracao["Vetorial"]),
            "EsperadoMC": _resumir_diagnostico_calibracao(diag_calibracao["EsperadoMC"]),
        },
        "diagnostico_financeiro": {
            "Genetico": _resumir_diagnostico_financeiro(diag_financeiro["Genetico"]),
            "Vetorial": _resumir_diagnostico_financeiro(diag_financeiro["Vetorial"]),
            "EsperadoMC": _resumir_diagnostico_financeiro(diag_financeiro["EsperadoMC"]),
        },
        "detalhes_janelas": detalhes,
    }
