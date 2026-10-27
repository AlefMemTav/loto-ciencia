"""Financial diagnostics for lottery backtests.

The historical spreadsheets bundled with the project only contain drawn
numbers, not paid prizes per contest.  This module therefore works with an
explicit prize table: fixed tiers are provided where they are stable enough to
be useful, and variable tiers can be supplied by CLI overrides.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from app.core.lottery import GameConfig


DEFAULT_PRIZE_TABLES: dict[str, dict[int, float]] = {
    # Conservative fixed-tier defaults for the current Lotofacil base game.
    # The 14/15 tiers are variable and intentionally left out unless supplied.
    "loto_facil_sorteio": {11: 6.0, 12: 12.0, 13: 30.0},
}


@dataclass(frozen=True)
class FinancialDiagnostics:
    cost: float
    gross_return: float
    net_return: float
    roi: float
    profit_factor: float
    prize_table: dict[str, float]
    paid_hits: dict[str, int]
    n_bets: int
    n_draws: int
    stake_per_bet: float
    mode: str


def parse_prize_table(values: list[str] | None) -> dict[int, float]:
    table: dict[int, float] = {}
    for raw in values or []:
        if "=" not in raw:
            raise ValueError(f"Premio invalido '{raw}'. Use acertos=valor, ex: 14=1500.")
        key, value = raw.split("=", 1)
        try:
            hits = int(key.strip())
            amount = float(value.strip().replace(",", "."))
        except ValueError as exc:
            raise ValueError(f"Premio invalido '{raw}'. Use acertos=valor.") from exc
        if hits < 0 or amount < 0:
            raise ValueError(f"Premio invalido '{raw}'. Acertos/valor devem ser positivos.")
        table[hits] = amount
    return table


def resolve_prize_table(
    config: GameConfig,
    overrides: dict[int, float] | None = None,
    include_defaults: bool = True,
) -> dict[int, float]:
    table: dict[int, float] = {}
    if include_defaults:
        table.update(DEFAULT_PRIZE_TABLES.get(config.slug, {}))
    table.update(overrides or {})
    return {int(k): float(v) for k, v in sorted(table.items()) if float(v) > 0}


def financial_diagnostics(
    games: list[list[int]] | np.ndarray,
    gabarito: np.ndarray,
    config: GameConfig,
    prize_table: dict[int, float] | None = None,
) -> FinancialDiagnostics:
    arr = np.asarray(games, dtype=int)
    draws = np.asarray(gabarito, dtype=int)
    if arr.size == 0 or draws.size == 0:
        n_bets = int(len(arr)) if arr.ndim > 1 else 0
        n_draws = int(len(draws)) if draws.ndim > 1 else 0
        cost = n_bets * n_draws * float(config.game_price)
        return FinancialDiagnostics(
            cost=round(float(cost), 2),
            gross_return=0.0,
            net_return=round(float(-cost), 2),
            roi=0.0,
            profit_factor=0.0,
            prize_table={str(k): v for k, v in sorted((prize_table or {}).items())},
            paid_hits={},
            n_bets=n_bets,
            n_draws=n_draws,
            stake_per_bet=float(config.game_price),
            mode="prize_table",
        )

    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    if draws.ndim == 1:
        draws = draws.reshape(1, -1)

    table = {int(k): float(v) for k, v in (prize_table or {}).items()}
    paid_hits = {int(k): 0 for k in table}
    gross = 0.0
    for game in arr:
        game_set = set(int(n) for n in game.tolist())
        for draw in draws:
            hits = len(game_set.intersection(int(n) for n in draw.tolist()))
            prize = table.get(hits, 0.0)
            if prize > 0:
                paid_hits[hits] = paid_hits.get(hits, 0) + 1
                gross += prize

    n_bets = int(len(arr))
    n_draws = int(len(draws))
    cost = float(n_bets * n_draws * config.game_price)
    net = gross - cost
    profit_factor = gross / cost if cost > 0 else 0.0
    roi = net / cost if cost > 0 else 0.0
    return FinancialDiagnostics(
        cost=round(cost, 2),
        gross_return=round(float(gross), 2),
        net_return=round(float(net), 2),
        roi=round(float(roi), 6),
        profit_factor=round(float(profit_factor), 6),
        prize_table={str(k): round(float(v), 2) for k, v in sorted(table.items())},
        paid_hits={str(k): int(v) for k, v in sorted(paid_hits.items()) if v > 0},
        n_bets=n_bets,
        n_draws=n_draws,
        stake_per_bet=round(float(config.game_price), 2),
        mode="prize_table",
    )


def diagnostics_to_dict(diag: FinancialDiagnostics) -> dict[str, Any]:
    return {
        "custo_total": diag.cost,
        "receita_bruta": diag.gross_return,
        "lucro_liquido": diag.net_return,
        "roi": diag.roi,
        "fator_retorno": diag.profit_factor,
        "tabela_premios": diag.prize_table,
        "hits_pagos": diag.paid_hits,
        "n_jogos": diag.n_bets,
        "n_concursos": diag.n_draws,
        "preco_aposta": diag.stake_per_bet,
        "modo": diag.mode,
    }
