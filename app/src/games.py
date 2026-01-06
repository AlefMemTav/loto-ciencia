# app/src/games.py
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple


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
    k: int  # tamanho do sorteio
    draw_cols: List[str]
    layout: BoardLayout
    start_year: int = 1996
    gauss_range: str = "140-240"
    odds_text: str = "1 em 50 milhões"
    game_price: float = 5.00
    how_to_play: str = "Regras do jogo..."
    bet_k: Optional[int] = None  # tamanho da aposta

    # Alvos para o Gerador (Scores para considerar o jogo "Pronto")
    target_score_excellent: int = 85
    target_score_accept: int = 70

    # Limites para Validação (Quantos números podem terminar com mesmo dígito 0-9)
    final_digit_alert: int = 3
    final_digit_error: int = 4

    @property
    def bet_size(self) -> int:
        """Retorna o tamanho da aposta (50 para Mania, k para outros)."""
        return self.bet_k if self.bet_k is not None else self.k

    @property
    def density(self) -> float:
        """Calcula a densidade do jogo (Aposta / Universo)."""
        return self.bet_size / self.n_numbers

    @property
    def min_geom_score(self) -> int:
        """
        FÓRMULA AUTOMÁTICA DE SCORE GEOMÉTRICO
        Define a tolerância visual baseada na densidade do tabuleiro.
        Mega (10% ocupado) -> Exige Score 54+
        Loto (60% ocupado) -> Aceita Score 24+
        """
        # Fórmula: Base 60 - (Penalidade * Densidade)
        score = 60 - (60 * self.density)
        return max(15, int(score))

    @property
    def geo_weights(self) -> Dict[str, float]:
        """
        CALIBRAGEM AUTOMÁTICA DE PESOS
        Define a severidade da punição baseada na densidade.
        Jogos densos (Loto) têm pesos leves. Jogos vazios (Mega) têm pesos pesados.
        """
        base = max(0.5, 3.4 - (4.0 * self.density))

        return {
            "moldura": round(base * 1.0, 1),
            "miolo": round(base * 1.2, 1),
            "cruz": round(base * 1.0, 1),
            "xis": round(base * 1.0, 1),
            "cantos": round(base * 0.6, 1),  # Cantos valem menos (alta variância)
        }


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
    game_price=6.00,
    how_to_play=(
        "O volante tem 60 números (01 a 60). "
        "Você marca de 6 a 20 números. Ganha quem acertar 6 (Sena), "
        "5 (Quina) ou 4 (Quadra) números sorteados."
    ),
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
    game_price=3.00,
    how_to_play=(
        "O volante tem 80 números (01 a 80). "
        "Você aposta de 5 a 15 números. Ganha quem acerta 5 (Quina), "
        "4 (Quadra), 3 (Terno) ou 2 (Duque)."
    ),
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
    game_price=3.50,
    how_to_play=(
        "O volante tem 25 números (01 a 25)."
        "Você marca entre 15 e 20 números. Fatura prêmio se acertar "
        "11, 12, 13, 14 ou 15 números."
    ),
    target_score_excellent=70,
    target_score_accept=60,  # Aceitável para parar o gerador
    final_digit_alert=4,  # Normal ter até 3 finais iguais. Alerta em 4.
    final_digit_error=5,  # Erro em 5+
)

LOTOMANIA = GameConfig(
    slug="loto_mania_sorteio",
    name="Lotomania",
    n_numbers=100,  # Tratamos 00 como 100
    k=20,  # Sorteia 20
    bet_k=50,  # Joga-se 50
    draw_cols=_draw_cols(20),
    layout=BoardLayout(rows=10, cols=10, n_numbers=100),
    start_year=1999,
    gauss_range="2000-3000",  # Soma de 50 números é muito maior
    odds_text="1 em 11.372.635",
    game_price=3.00,
    how_to_play=(
        "Você escolhe 50 números entre os 100 disponíveis (01 a 00). "
        "São sorteados 20 números. Ganha quem acerta 20, 19, 18, 17, 16, 15 ou "
        "nenhum número (0 acertos)."
    ),
    # Ajustes de Regras para 50 números
    target_score_excellent=80,
    target_score_accept=65,
    # Em 50 números, finais se repetem muito (ex: cinco finais 1)
    final_digit_alert=6,
    final_digit_error=8,
)

GAMES: Dict[str, GameConfig] = {
    MEGASENA.slug: MEGASENA,
    QUINA.slug: QUINA,
    LOTOFACIL.slug: LOTOFACIL,
    LOTOMANIA.slug: LOTOMANIA,
}
