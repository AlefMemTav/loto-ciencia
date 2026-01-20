from typing import Dict

from .models import GameConfig, BoardLayout


def _layout(r, c, n):
    return BoardLayout(rows=r, cols=c, n_numbers=n)


MEGASENA = GameConfig(
    slug="mega_sena_sorteio",
    name="Mega-Sena",
    n_numbers=60,
    k=6,
    layout=_layout(6, 10, 60),
    start_year=1996,
    odds_text="1 em 50.063.860",
    game_price=6.00,
    how_to_play=(
        "O volante tem 60 números (01 a 60). "
        "Você marca de 6 a 20 números. Ganha quem acertar 6 (Sena), "
        "5 (Quina) ou 4 (Quadra) números sorteados."
    ),
    gauss_range="140-240",
    theme_color="#16a34a",
)

QUINA = GameConfig(
    slug="quina_sorteio",
    name="Quina",
    n_numbers=80,
    k=5,
    layout=_layout(8, 10, 80),
    start_year=1994,
    odds_text="1 em 24.040.016",
    game_price=3.00,
    how_to_play=(
        "O volante tem 80 números (01 a 80). "
        "Você aposta de 5 a 15 números. Ganha quem acerta 5 (Quina), "
        "4 (Quadra), 3 (Terno) ou 2 (Duque)."
    ),
    gauss_range="120-200",
    theme_color="#7c3aed",
)

LOTOFACIL = GameConfig(
    slug="loto_facil_sorteio",
    name="Lotofácil",
    n_numbers=25,
    k=15,
    layout=_layout(5, 5, 25),
    start_year=2003,
    odds_text="1 em 3.268.760",
    game_price=3.50,
    how_to_play=(
        "O volante tem 25 números (01 a 25)."
        "Você marca entre 15 e 20 números. Fatura prêmio se acertar "
        "11, 12, 13, 14 ou 15 números."
    ),
    gauss_range="180-220",
    theme_color="#db2777",
    target_score_excellent=70,
    target_score_accept=60,
    final_digit_alert=4,
    final_digit_error=5,
)

LOTOMANIA = GameConfig(
    slug="loto_mania_sorteio",
    name="Lotomania",
    n_numbers=100,
    k=20,
    bet_k=50,  # Joga 50, sorteia 20
    layout=_layout(10, 10, 100),
    start_year=1999,
    odds_text="1 em 11.372.635",
    game_price=3.00,
    how_to_play=(
        "Você escolhe 50 números entre os 100 disponíveis (01 a 00). "
        "São sorteados 20 números. Ganha quem acerta 20, 19, 18, 17, 16, 15 ou "
        "nenhum número (0 acertos)."
    ),
    gauss_range="2000-3000",
    theme_color="#f59e0b",
    target_score_excellent=80,
    target_score_accept=65,
    final_digit_alert=6,
    final_digit_error=8,
)

GAMES_REGISTRY: Dict[str, GameConfig] = {
    g.slug: g for g in [MEGASENA, LOTOFACIL, QUINA, LOTOMANIA]
}
