from app.core.games import GameConfig


from typing import Dict, List
from app.core.games import GameConfig


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


def _xis_proporcional(layout) -> List[int]:
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


def _xis(layout) -> List[int]:
    """
    Retorna as DUAS diagonais principais do volante (forma um X).

    Para grids retangulares (ex: 6x10 da Mega-Sena):
    - Diagonal principal: onde row == col (até min(rows, cols))
    - Diagonal secundária: onde row + col == cols - 1

    Para grids quadrados (ex: 5x5 da Quina): diagonais completas.
    """
    pos = set()
    rows, cols = layout.rows, layout.cols

    # Diagonal principal: linha == coluna
    for i in range(min(rows, cols)):
        pos.add((i, i))

    # Diagonal secundária: linha + coluna == cols - 1
    for r in range(rows):
        c = cols - 1 - r
        if 0 <= c < cols:
            pos.add((r, c))

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


def get_colunas(config: GameConfig) -> dict:
    """
    Gera colunas verticais baseado no layout do volante.

    Exemplo Mega-Sena (10 colunas):
        Col 1: [1, 11, 21, 31, 41, 51]
        Col 2: [2, 12, 22, 32, 42, 52]
        ...
    """
    colunas = {}
    for col_idx in range(config.layout.cols):
        numeros_col = [
            num
            for num in range(1, config.n_numbers + 1)
            if (num - 1) % config.layout.cols == col_idx
        ]
        colunas[f"Coluna {col_idx + 1}"] = numeros_col
    return colunas


def get_linhas(config: GameConfig) -> dict:
    """
    Gera linhas horizontais baseado no layout.

    Exemplo Mega-Sena (6 linhas):
        Linha 1: [1, 2, 3, ..., 10]
        Linha 2: [11, 12, ..., 20]
        ...
    """
    linhas = {}
    for row_idx in range(config.layout.rows):
        inicio = row_idx * config.layout.cols + 1
        fim = min((row_idx + 1) * config.layout.cols, config.n_numbers)
        numeros_linha = list(range(inicio, fim + 1))
        linhas[f"Linha {row_idx + 1}"] = numeros_linha
    return linhas


def get_metades_espaciais(config: GameConfig) -> dict:
    """
    Metades: Superior/Inferior e Esquerda/Direita.

    Retorna:
        {
            "Superior": [1-30],
            "Inferior": [31-60],
            "Esquerda": [números nas colunas 1-5],
            "Direita": [números nas colunas 6-10]
        }
    """
    meio_numerico = config.n_numbers // 2
    meio_col = config.layout.cols // 2

    metades = {
        "Superior": list(range(1, meio_numerico + 1)),
        "Inferior": list(range(meio_numerico + 1, config.n_numbers + 1)),
        "Esquerda": [
            n
            for n in range(1, config.n_numbers + 1)
            if (n - 1) % config.layout.cols < meio_col
        ],
        "Direita": [
            n
            for n in range(1, config.n_numbers + 1)
            if (n - 1) % config.layout.cols >= meio_col
        ],
    }
    return metades


def get_aneis_concentricos(config: GameConfig) -> dict:
    """
    Anéis concêntricos (externo → médio → interno).
    Baseado na distância Manhattan ao centro do volante.

    Exemplo:
        Externo: bordas do volante
        Médio: camada intermediária
        Interno: região central
    """
    rows, cols = config.layout.rows, config.layout.cols
    centro_row, centro_col = rows / 2, cols / 2

    aneis = {"Externo": [], "Médio": [], "Interno": []}

    for num in range(1, config.n_numbers + 1):
        row = (num - 1) // cols
        col = (num - 1) % cols

        # Distância Manhattan ao centro
        dist = abs(row - centro_row) + abs(col - centro_col)
        max_dist = rows / 2 + cols / 2

        # Classifica por distância relativa
        if dist >= max_dist * 0.66:
            aneis["Externo"].append(num)
        elif dist >= max_dist * 0.33:
            aneis["Médio"].append(num)
        else:
            aneis["Interno"].append(num)

    return aneis


def get_padrao_xadrez(config: GameConfig) -> dict:
    """
    Padrão xadrez: casas brancas vs pretas.
    Baseado na paridade da soma (linha + coluna).

    Exemplo Mega-Sena:
        Brancas: [1, 3, 5, 7, 9, 12, 14, ...]
        Pretas: [2, 4, 6, 8, 10, 11, 13, ...]
    """
    brancas = []
    pretas = []

    for num in range(1, config.n_numbers + 1):
        row = (num - 1) // config.layout.cols
        col = (num - 1) % config.layout.cols

        if (row + col) % 2 == 0:
            brancas.append(num)
        else:
            pretas.append(num)

    return {
        "Xadrez Branco": brancas,
        "Xadrez Preto": pretas,
    }


def get_diagonais_separadas(config: GameConfig) -> dict:
    """
    Diagonais principal e secundária SEPARADAS.

    Diagonal Principal: [1, 12, 23, 34, 45, 56]
    Diagonal Secundária: [10, 19, 28, 37, 46, 55]
    """
    rows, cols = config.layout.rows, config.layout.cols
    principal = []
    secundaria = []

    for num in range(1, config.n_numbers + 1):
        row = (num - 1) // cols
        col = (num - 1) % cols

        # Diagonal principal: row == col
        if row == col:
            principal.append(num)

        # Diagonal secundária: row + col == cols - 1
        if row + col == cols - 1:
            secundaria.append(num)

    return {
        "Diagonal Principal": principal,
        "Diagonal Secundária": secundaria,
    }


def get_all_grupos_geometricos(config: GameConfig) -> dict:
    """
    Retorna TODOS os grupos geométricos (estáticos + dinâmicos).

    Para fins acadêmicos: análise completa de padrões espaciais.

    Returns:
        Dict com ~25-35 grupos dependendo do jogo:
        - 5 estáticos: moldura, miolo, cruz, xis, cantos
        - 1 xis proporcional
        - N colunas (10 para Mega-Sena)
        - N linhas (6 para Mega-Sena)
        - 4 metades (superior, inferior, esquerda, direita)
        - 3 anéis (externo, médio, interno)
        - 2 xadrez (branco, preto)
        - 2 diagonais (principal, secundária)
        - 4 quadrantes (já existem via layout)
    """
    constants = get_constants_for_game(config)

    grupos_completos = {
        # Estáticos (do constants)
        "Moldura (Borda)": constants["moldura"],
        "Miolo (Centro)": constants["miolo"],
        "Cruz": constants["cruz"],
        "Xis (Diagonais)": constants["xis"],
        "Cantos": constants["cantos"],
    }
    grupos_completos["Quadrante 1 (Sup. Esq)"] = list(config.layout.quadrant_numbers(1))
    grupos_completos["Quadrante 2 (Sup. Dir)"] = list(config.layout.quadrant_numbers(2))
    grupos_completos["Quadrante 3 (Inf. Esq)"] = list(config.layout.quadrant_numbers(3))
    grupos_completos["Quadrante 4 (Inf. Dir)"] = list(config.layout.quadrant_numbers(4))
    # Dinâmicos (gerados)
    grupos_completos.update(get_colunas(config))
    grupos_completos.update(get_linhas(config))
    grupos_completos.update(get_metades_espaciais(config))
    grupos_completos.update(get_aneis_concentricos(config))
    grupos_completos.update(get_padrao_xadrez(config))
    grupos_completos.update(get_diagonais_separadas(config))

    # Quadrantes (via layout)
    for q in range(1, 5):
        grupos_completos[f"Quadrante {q}"] = list(config.layout.quadrant_numbers(q))

    return grupos_completos


def get_grupos_geometricos_essenciais(config: GameConfig) -> dict:
    """
    Retorna apenas grupos geométricos ESSENCIAIS (não redundantes).

    Recomendado para produção: ~15 grupos mais relevantes.

    Exclui:
    - Linhas (já analisadas em _verificar_linhas)
    - Metades superior/inferior (já em _verificar_metades)
    - Anéis (redundante com moldura/miolo)
    - Diagonais separadas (redundante com xis)
    """
    constants = get_constants_for_game(config)

    grupos_essenciais = {
        "Moldura (Borda)": constants["moldura"],
        "Miolo (Centro)": constants["miolo"],
        "Cruz": constants["cruz"],
        "Xis (Diagonais)": constants["xis"],
        "Cantos": constants["cantos"],
    }

    # Adiciona colunas (complementa linhas)
    grupos_essenciais.update(get_colunas(config))

    # Adiciona apenas metades H (esquerda/direita)
    metades = get_metades_espaciais(config)
    grupos_essenciais["Esquerda"] = metades["Esquerda"]
    grupos_essenciais["Direita"] = metades["Direita"]

    # Adiciona xadrez (padrão único)
    grupos_essenciais.update(get_padrao_xadrez(config))

    return grupos_essenciais


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
