from app.src.games import GameConfig


from typing import Dict, List
from app.src.games import GameConfig


def _numbers_by_positions(layout, positions):
    """positions: iterable[(r,c)] zero-based"""
    out = []
    for n in range(1, layout.n_numbers + 1):
        r, c = layout.pos(n)
        if (r, c) in positions:
            out.append(n)
    return sorted(out)


def _moldura(layout) -> List[int]:
    pos = set()
    for r in range(layout.rows):
        for c in range(layout.cols):
            if r == 0 or r == layout.rows - 1 or c == 0 or c == layout.cols - 1:
                pos.add((r, c))
    return _numbers_by_positions(layout, pos)


def _miolo(layout) -> List[int]:
    pos = set()
    for r in range(1, layout.rows - 1):
        for c in range(1, layout.cols - 1):
            pos.add((r, c))
    return _numbers_by_positions(layout, pos)


def _cantos(layout) -> List[int]:
    pos = {
        (0, 0),
        (0, layout.cols - 1),
        (layout.rows - 1, 0),
        (layout.rows - 1, layout.cols - 1),
    }
    return _numbers_by_positions(layout, pos)


def _cruz(layout) -> List[int]:
    # Para grids ímpares: 1 linha e 1 coluna centrais
    # Para grids pares: 2 linhas e/ou 2 colunas centrais
    if layout.rows % 2 == 1:
        rows_center = {layout.rows // 2}
    else:
        rows_center = {layout.rows // 2 - 1, layout.rows // 2}

    if layout.cols % 2 == 1:
        cols_center = {layout.cols // 2}
    else:
        cols_center = {layout.cols // 2 - 1, layout.cols // 2}

    pos = set()
    for r in range(layout.rows):
        for c in range(layout.cols):
            if (r in rows_center) or (c in cols_center):
                pos.add((r, c))

    return _numbers_by_positions(layout, pos)


def _xis(layout) -> List[int]:
    # Diagonais para grids retangulares:
    # mapeia coluna proporcionalmente à linha para cobrir o grid.
    pos = set()
    for r in range(layout.rows):
        # diag principal
        c1 = round(r * (layout.cols - 1) / (layout.rows - 1)) if layout.rows > 1 else 0
        # diag secundária
        c2 = (layout.cols - 1) - c1
        pos.add((r, c1))
        pos.add((r, c2))
    return _numbers_by_positions(layout, pos)


def _primos_ate(n: int) -> List[int]:
    if n < 2:
        return []
    primos = []
    for x in range(2, n + 1):
        ok = True
        for p in range(2, int(x**0.5) + 1):
            if x % p == 0:
                ok = False
                break
        if ok:
            primos.append(x)
    return primos


def _fibonacci_ate(n: int) -> List[int]:
    fib = []
    a, b = (
        1,
        2,
    )  # começa em 1,2 para casar com “dezenas” usuais; ajuste se preferir incluir 0
    while a <= n:
        fib.append(a)
        a, b = b, a + b
    return fib


def get_constants_for_game(config: GameConfig) -> Dict[str, List[int]]:
    layout = config.layout
    n = config.n_numbers
    # --- Tema de cores por jogo ---
    if config.slug == "mega_sena_sorteio":
        heat_color = "#16a34a"  # verde (Mega)
    elif config.slug == "quina_sorteio":
        heat_color = "#7c3aed"  # roxo (Quina)
    elif config.slug == "loto_facil_sorteio":
        heat_color = "#db2777"  # rosa (Lotofácil)
    elif config.slug == "loto_mania_sorteio":
        heat_color = "#f59e0b"  # amarelo (Lotomania)
    else:
        heat_color = "#2563eb"  # azul (padrão)

    # Observação: Lost Numbers é um “easter egg” do Lost; faz sentido só até 60,
    # então aqui limita ao universo do jogo.
    lost_base = [4, 8, 15, 16, 23, 42]
    lost_numbers = [x for x in lost_base if 1 <= x <= n]

    # “Gêmeos” = repetição do dígito (11,22,33...) até N
    gemeos = [11 * k for k in range(1, 10) if 11 * k <= n]

    return {
        # Padrões geométricos (layout-driven)
        "moldura": _moldura(layout),
        "miolo": _miolo(layout),
        "cruz": _cruz(layout),
        "xis": _xis(layout),
        "cantos": _cantos(layout),
        # Padrões numéricos (N-driven)
        "primos": _primos_ate(n),
        "fibonacci": _fibonacci_ate(n),
        "lost_numbers": lost_numbers,
        "gemeos": gemeos,
        "heat_color": heat_color,
    }
