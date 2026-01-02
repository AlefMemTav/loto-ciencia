# src/constants.py

# Padrões Matemáticos
PRIMOS = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59]
FIBONACCI = [1, 2, 3, 5, 8, 13, 21, 34, 55]
GEMEOS = [11, 22, 33, 44, 55]

# Áreas de Risco
LOST_NUMBERS = {4, 8, 15, 16, 23, 42}
DATAS = list(range(1, 32))

# Padrões Geométricos (Sets para performance)
MOLDURA = (
    set(range(1, 11)) | set(range(51, 61)) | set([11, 21, 31, 41, 10, 20, 30, 40, 50])
)

# Miolo (Números que não estão na Moldura)
MIOLO = [n for n in range(1, 61) if n not in MOLDURA]

# Cruz (Colunas 5 e 6 + Linhas 3 e 4)
_col_cruz = [n for n in range(1, 61) if n % 10 in [5, 6]]
_lin_cruz = list(range(21, 41))
CRUZ = sorted(list(set(_col_cruz + _lin_cruz)))

# Xis (Diagonais)
_diag1 = [1, 12, 23, 34, 45, 56]
_diag2 = [10, 19, 28, 37, 46, 55]
XIS = sorted(list(set(_diag1 + _diag2)))

# Cantos (Extremos)
CANTOS = [1, 2, 9, 10, 51, 52, 59, 60]

# Quadrantes
Q1 = [1, 2, 3, 4, 5, 11, 12, 13, 14, 15, 21, 22, 23, 24, 25]
Q2 = [6, 7, 8, 9, 10, 16, 17, 18, 19, 20, 26, 27, 28, 29, 30]
Q3 = [31, 32, 33, 34, 35, 41, 42, 43, 44, 45, 51, 52, 53, 54, 55]
Q4 = [36, 37, 38, 39, 40, 46, 47, 48, 49, 50, 56, 57, 58, 59, 60]

# IDs da Mega da Virada (Atualizar anualmente)
IDS_VIRADA = [
    1140,
    1245,
    1350,
    1455,
    1560,
    1665,
    1772,
    1890,
    2000,
    2110,
    2220,
    2330,
    2440,
    2550,
    2670,
    2810,
]
