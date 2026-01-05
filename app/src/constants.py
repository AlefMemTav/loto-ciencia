# src/constants.py

# ===== PADRÕES MATEMÁTICOS =====
PRIMOS = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59]
FIBONACCI = [1, 2, 3, 5, 8, 13, 21, 34, 55]
GEMEOS = [11, 22, 33, 44, 55]

# ===== ÁREAS DE RISCO =====
LOST_NUMBERS = {4, 8, 15, 16, 23, 42}
DATAS = list(range(1, 32))

# ===== LAYOUT REAL DO VOLANTE (6 LINHAS × 10 COLUNAS) =====
LINHA_1 = list(range(1, 11))  # [1-10]
LINHA_2 = list(range(11, 21))  # [11-20]
LINHA_3 = list(range(21, 31))  # [21-30]
LINHA_4 = list(range(31, 41))  # [31-40]
LINHA_5 = list(range(41, 51))  # [41-50]
LINHA_6 = list(range(51, 61))  # [51-60]

LINHAS = [LINHA_1, LINHA_2, LINHA_3, LINHA_4, LINHA_5, LINHA_6]

# ===== FAIXAS (4 blocos de 15 números) =====
FAIXA_1_15 = list(range(1, 16))
FAIXA_16_30 = list(range(16, 31))
FAIXA_31_45 = list(range(31, 46))
FAIXA_46_60 = list(range(46, 61))
FAIXAS_15 = [FAIXA_1_15, FAIXA_16_30, FAIXA_31_45, FAIXA_46_60]

# ===== QUADRANTES GEOMÉTRICOS (layout 6×10 => quadrantes 3×5) =====
# Superior: linhas 1-3 (1-30); Inferior: linhas 4-6 (31-60)
# Esquerda: colunas 1-5; Direita: colunas 6-10
QUAD_GEO_Q1 = [1, 2, 3, 4, 5, 11, 12, 13, 14, 15, 21, 22, 23, 24, 25]  # Sup. Esq
QUAD_GEO_Q2 = [6, 7, 8, 9, 10, 16, 17, 18, 19, 20, 26, 27, 28, 29, 30]  # Sup. Dir
QUAD_GEO_Q3 = [31, 32, 33, 34, 35, 41, 42, 43, 44, 45, 51, 52, 53, 54, 55]  # Inf. Esq
QUAD_GEO_Q4 = [36, 37, 38, 39, 40, 46, 47, 48, 49, 50, 56, 57, 58, 59, 60]  # Inf. Dir
QUADRANTES_GEO = [QUAD_GEO_Q1, QUAD_GEO_Q2, QUAD_GEO_Q3, QUAD_GEO_Q4]

# ===== PADRÕES GEOMÉTRICOS =====
# Moldura (Bordas do volante)
MOLDURA = (
    set(range(1, 11)) | set(range(51, 61)) | set([11, 21, 31, 41, 10, 20, 30, 40, 50])
)

# Miolo (Centro do volante - números que não estão na moldura)
MIOLO = [n for n in range(1, 61) if n not in MOLDURA]

# Cruz (Colunas centrais 5 e 6 + Linhas centrais 3 e 4)
_col_cruz = [n for n in range(1, 61) if n % 10 in [5, 6, 0]]  # Colunas 5, 6, 10
_lin_cruz = list(range(21, 41))  # Linhas 3 e 4
CRUZ = sorted(list(set(_col_cruz + _lin_cruz)))

# Xis (Diagonais principais)
_diag1 = [1, 12, 23, 34, 45, 56]  # Diagonal \
_diag2 = [10, 19, 28, 37, 46, 55]  # Diagonal /
XIS = sorted(list(set(_diag1 + _diag2)))

# Cantos (4 extremos do volante)
CANTOS = [1, 2, 9, 10, 51, 52, 59, 60]

# ===== COLUNAS DO VOLANTE =====
COLUNA_1 = [1, 11, 21, 31, 41, 51]
COLUNA_2 = [2, 12, 22, 32, 42, 52]
COLUNA_3 = [3, 13, 23, 33, 43, 53]
COLUNA_4 = [4, 14, 24, 34, 44, 54]
COLUNA_5 = [5, 15, 25, 35, 45, 55]
COLUNA_6 = [6, 16, 26, 36, 46, 56]
COLUNA_7 = [7, 17, 27, 37, 47, 57]
COLUNA_8 = [8, 18, 28, 38, 48, 58]
COLUNA_9 = [9, 19, 29, 39, 49, 59]
COLUNA_10 = [10, 20, 30, 40, 50, 60]

COLUNAS = [
    COLUNA_1,
    COLUNA_2,
    COLUNA_3,
    COLUNA_4,
    COLUNA_5,
    COLUNA_6,
    COLUNA_7,
    COLUNA_8,
    COLUNA_9,
    COLUNA_10,
]

# ===== METADES =====
SUPERIOR = list(range(1, 31))  # Linhas 1-3 (números 1-30)
INFERIOR = list(range(31, 61))  # Linhas 4-6 (números 31-60)

# ===== IDs DA MEGA DA VIRADA (Atualizar anualmente) =====
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
