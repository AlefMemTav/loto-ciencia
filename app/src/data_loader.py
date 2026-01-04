import pandas as pd
import streamlit as st
from .constants import IDS_VIRADA


@st.cache_data
def carregar_dados_mega_sena(caminho_arquivo="data/mega_sena_sorteio.xlsx"):
    try:
        # Carrega o Excel
        df = pd.read_excel(caminho_arquivo)

        # Ajuste de colunas
        # Tenta detectar uma coluna de identificação do concurso (Ex.: 'Concurso')
        contest_col = None
        possible_names = [
            "Concurso",
            "CONCURSO",
            "concurso",
            "Nº Concurso",
            "numero_concurso",
            "Número",
            "Número do Concurso",
        ]
        for name in possible_names:
            if name in df.columns:
                contest_col = name
                break

        # Se não achar pelo nome, tenta pela primeira coluna se for inteira e única
        if contest_col is None:
            first_col = df.iloc[:, 0]
            try:
                as_int = pd.to_numeric(first_col, errors="coerce")
                if as_int.notna().all() and as_int.is_unique:
                    contest_col = df.columns[0]
            except Exception:
                contest_col = None

        df_limpo = df.iloc[:, 2:8].copy()
        df_limpo.columns = ["D1", "D2", "D3", "D4", "D5", "D6"]

        # Preserva o índice original do concurso se detectado
        if contest_col is not None and contest_col in df.columns:
            try:
                idx_vals = pd.to_numeric(df[contest_col], errors="coerce")
                # só aplica se os índices são válidos
                if idx_vals.notna().any():
                    # usa os valores convertidos (inteiros quando possível)
                    df_limpo.index = idx_vals.astype(int).values
            except Exception:
                pass

        for col in df_limpo.columns:
            df_limpo[col] = pd.to_numeric(df_limpo[col], errors="coerce")

        return df_limpo.dropna()
    except FileNotFoundError:
        st.error("Erro: Arquivo Excel não encontrado na pasta data/.")
        return pd.DataFrame()

    except Exception as e:
        st.error(f"Erro ao carregar dados da Mega Sena: {e}")
        return pd.DataFrame()


@st.cache_data
def filtrar_mega_virada(df):
    """Retorna apenas os jogos da Mega da Virada"""
    if df.empty:
        return pd.Series(), pd.DataFrame()

    df_virada = df[df.index.isin(IDS_VIRADA)]

    if df_virada.empty:
        return pd.Series(), pd.DataFrame()

    todos_virada = df_virada.values.flatten()
    freq_virada = pd.Series(todos_virada).value_counts().sort_values(ascending=False)

    return freq_virada, df_virada
