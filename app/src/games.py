# app/src/games.py
from dataclasses import dataclass
from typing import List, Dict, Tuple


@dataclass(frozen=True)
class BoardLayout:
    rows: int
    cols: int
    n_numbers: int

    def pos(self, n: int) -> Tuple[int, int]:
        # (row, col) zero-based
        idx = n - 1
        return idx // self.cols, idx % self.cols

    def numbers(self) -> List[int]:
        return list(range(1, self.n_numbers + 1))

    def quadrant_numbers(self, q: int) -> List[int]:
        """
        Quadrantes geométricos (4 regiões) derivados do grid.
        Para grids ímpares (ex 5x5), fica assimétrico (2x2,2x3,3x2,3x3), mas consistente.
        q: 1..4
        """
        split_r = self.rows // 2
        split_c = self.cols // 2

        if q == 1:  # sup esq
            r0, r1 = 0, split_r
            c0, c1 = 0, split_c
        elif q == 2:  # sup dir
            r0, r1 = 0, split_r
            c0, c1 = split_c, self.cols
        elif q == 3:  # inf esq
            r0, r1 = split_r, self.rows
            c0, c1 = 0, split_c
        elif q == 4:  # inf dir
            r0, r1 = split_r, self.rows
            c0, c1 = split_c, self.cols
        else:
            raise ValueError("Quadrante inválido. Use 1..4")

        nums = []
        for n in self.numbers():
            r, c = self.pos(n)
            if r0 <= r < r1 and c0 <= c < c1:
                nums.append(n)
        return nums


@dataclass(frozen=True)
class GameConfig:
    slug: str
    name: str
    n_numbers: int
    k: int
    draw_cols: List[str]
    layout: BoardLayout
    start_year: int = 1996
    gauss_range: str = "140-240"
    odds_text: str = "1 em 50 milhões"


def _draw_cols(k: int) -> List[str]:
    return [f"D{i}" for i in range(1, k + 1)]


MEGASENA = GameConfig(
    slug="mega_sena_sorteio",
    name="Mega-Sena",
    n_numbers=60,
    k=6,
    draw_cols=_draw_cols(6),
    layout=BoardLayout(rows=6, cols=10, n_numbers=60),
    start_year=1996,
    gauss_range="140-240",
    odds_text="1 em 50.063.860",
)

QUINA = GameConfig(
    slug="quina_sorteio",
    name="Quina",
    n_numbers=80,
    k=5,
    draw_cols=_draw_cols(5),
    layout=BoardLayout(rows=8, cols=10, n_numbers=80),
    start_year=1994,
    gauss_range="120-200",
    odds_text="1 em 24.040.016",
)

LOTOFACIL = GameConfig(
    slug="loto_facil_sorteio",
    name="Lotofácil",
    n_numbers=25,
    k=15,
    draw_cols=_draw_cols(15),
    layout=BoardLayout(rows=5, cols=5, n_numbers=25),
    start_year=2003,
    gauss_range="180-220",
    odds_text="1 em 3.268.760",
)

GAMES: Dict[str, GameConfig] = {
    MEGASENA.slug: MEGASENA,
    QUINA.slug: QUINA,
    LOTOFACIL.slug: LOTOFACIL,
}
