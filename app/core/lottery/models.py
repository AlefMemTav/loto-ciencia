# app/core/lottery/models.py
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Set


@dataclass(frozen=True)
class BoardLayout:
    """Define a geometria do volante (linhas x colunas)."""

    rows: int
    cols: int
    n_numbers: int

    def pos(self, n: int) -> Tuple[int, int]:
        """Retorna (linha, coluna) zero-based para o número n."""
        idx = n - 1
        return idx // self.cols, idx % self.cols

    @property
    def numbers(self) -> List[int]:
        return list(range(1, self.n_numbers + 1))

    # --- GEOMETRIA BÁSICA ---

    @property
    def moldura(self) -> List[int]:
        """Números na borda do volante."""
        return [
            n
            for n in self.numbers
            if self.pos(n)[0] in (0, self.rows - 1)
            or self.pos(n)[1] in (0, self.cols - 1)
        ]

    @property
    def miolo(self) -> List[int]:
        """Números no centro (excluindo moldura)."""
        moldura_set = set(self.moldura)
        return [n for n in self.numbers if n not in moldura_set]

    @property
    def cantos(self) -> List[int]:
        """Os 4 cantos do volante."""
        coords = {
            (0, 0),
            (0, self.cols - 1),
            (self.rows - 1, 0),
            (self.rows - 1, self.cols - 1),
        }
        return [n for n in self.numbers if self.pos(n) in coords]

    @property
    def cruz(self) -> List[int]:
        """Linha e Coluna centrais (lógica adaptada para par/ímpar)."""
        center_r = (
            {self.rows // 2}
            if self.rows % 2 != 0
            else {self.rows // 2 - 1, self.rows // 2}
        )
        center_c = (
            {self.cols // 2}
            if self.cols % 2 != 0
            else {self.cols // 2 - 1, self.cols // 2}
        )
        return [
            n
            for n in self.numbers
            if self.pos(n)[0] in center_r or self.pos(n)[1] in center_c
        ]

    @property
    def xis(self) -> List[int]:
        """Diagonais principais (reproduzindo lógica exata do game_constants)."""
        res = []
        for n in self.numbers:
            r, c = self.pos(n)
            # Diagonal Principal: r == c (até o limite do quadrado)
            if r == c and r < min(self.rows, self.cols):
                res.append(n)
            # Diagonal Secundária: r + c == cols - 1
            elif (r + c) == (self.cols - 1):
                res.append(n)
        return sorted(list(set(res)))

    def quadrant_numbers(self, q: int) -> List[int]:
        """Retorna números do quadrante 1, 2, 3 ou 4."""
        split_r = self.rows // 2
        split_c = self.cols // 2

        # Define ranges [min, max)
        r_min, r_max = (0, split_r) if q in [1, 2] else (split_r, self.rows)
        c_min, c_max = (0, split_c) if q in [1, 3] else (split_c, self.cols)

        return [
            n
            for n in self.numbers
            if r_min <= self.pos(n)[0] < r_max and c_min <= self.pos(n)[1] < c_max
        ]

    # --- GEOMETRIA AVANÇADA (Preservada do game_constants) ---

    @property
    def xadrez(self) -> Dict[str, List[int]]:
        """Casas brancas e pretas (tabuleiro de xadrez)."""
        brancas, pretas = [], []
        for n in self.numbers:
            r, c = self.pos(n)
            if (r + c) % 2 == 0:
                brancas.append(n)
            else:
                pretas.append(n)
        return {"Xadrez Branco": brancas, "Xadrez Preto": pretas}

    @property
    def aneis(self) -> Dict[str, List[int]]:
        """Anéis concêntricos baseados na Distância Manhattan ao centro."""
        centro_r, centro_c = self.rows / 2, self.cols / 2
        max_dist = self.rows / 2 + self.cols / 2
        grupos = {"Externo": [], "Médio": [], "Interno": []}

        for n in self.numbers:
            r, c = self.pos(n)
            dist = abs(r - centro_r) + abs(c - centro_c)

            if dist >= max_dist * 0.66:
                grupos["Externo"].append(n)
            elif dist >= max_dist * 0.33:
                grupos["Médio"].append(n)
            else:
                grupos["Interno"].append(n)
        return grupos

    def get_colunas(self) -> Dict[str, List[int]]:
        cols = {}
        for c in range(self.cols):
            cols[f"Coluna {c + 1}"] = [n for n in self.numbers if self.pos(n)[1] == c]
        return cols

    def get_linhas(self) -> Dict[str, List[int]]:
        lins = {}
        for r in range(self.rows):
            lins[f"Linha {r + 1}"] = [n for n in self.numbers if self.pos(n)[0] == r]
        return lins


@dataclass(frozen=True)
class GameConfig:
    """Configuração completa de uma Loteria."""

    slug: str
    name: str
    n_numbers: int
    k: int
    layout: BoardLayout
    start_year: int
    odds_text: str
    game_price: float
    how_to_play: str

    # Configurações visuais e estatísticas
    theme_color: str = "#2563eb"
    gauss_range: str = "140-240"
    bet_k: Optional[int] = None  # Se for None, assume k

    # Validações
    target_score_excellent: int = 85
    target_score_accept: int = 70
    final_digit_alert: int = 3
    final_digit_error: int = 4

    @property
    def bet_size(self) -> int:
        return self.bet_k if self.bet_k else self.k

    @property
    def draw_cols(self) -> List[str]:
        return [f"D{i}" for i in range(1, self.k + 1)]

    @property
    def density(self) -> float:
        return self.bet_size / self.n_numbers

    # --- PROPRIEDADES MATEMÁTICAS ---

    @property
    def primos(self) -> List[int]:
        """Números primos até N."""
        primes = []
        for num in range(2, self.n_numbers + 1):
            if all(num % i != 0 for i in range(2, int(num**0.5) + 1)):
                primes.append(num)
        return primes

    @property
    def fibonacci(self) -> List[int]:
        """Sequência de Fibonacci até N."""
        fib = [1, 2]
        while True:
            prox = fib[-1] + fib[-2]
            if prox > self.n_numbers:
                break
            fib.append(prox)
        return fib

    @property
    def gemeos(self) -> List[int]:
        """Números com dígitos iguais (11, 22...)"""
        return [i for i in range(11, self.n_numbers + 1, 11)]

    @property
    def lost_numbers(self) -> List[int]:
        """Easter egg: Números do seriado Lost."""
        base = [4, 8, 15, 16, 23, 42]
        return [n for n in base if n <= self.n_numbers]

    # --- HELPERS DE COMPATIBILIDADE ---

    def as_constants_dict(self) -> Dict[str, List[int]]:
        """
        Retorna dicionário compatível com o antigo game_constants.py.
        Usado para manter compatibilidade com validator e statistics.
        """
        return {
            "moldura": self.layout.moldura,
            "miolo": self.layout.miolo,
            "cruz": self.layout.cruz,
            "xis": self.layout.xis,
            "cantos": self.layout.cantos,
            "primos": self.primos,
            "fibonacci": self.fibonacci,
            "lost_numbers": self.lost_numbers,
            "gemeos": self.gemeos,
            "heat_color": self.theme_color,
        }

    def get_geometric_groups(self) -> Dict[str, List[int]]:
        """Retorna grupos essenciais para análise estatística."""
        groups = {
            "Moldura (Borda)": self.layout.moldura,
            "Miolo (Centro)": self.layout.miolo,
            "Cruz": self.layout.cruz,
            "Xis (Diagonais)": self.layout.xis,
            "Cantos": self.layout.cantos,
        }
        # Adiciona colunas
        groups.update(self.layout.get_colunas())
        # Adiciona xadrez
        groups.update(self.layout.xadrez)

        # Adiciona metades Esquerda/Direita
        meio_col = self.layout.cols // 2
        groups["Esquerda"] = [
            n for n in self.layout.numbers if self.layout.pos(n)[1] < meio_col
        ]
        groups["Direita"] = [
            n for n in self.layout.numbers if self.layout.pos(n)[1] >= meio_col
        ]

        return groups
