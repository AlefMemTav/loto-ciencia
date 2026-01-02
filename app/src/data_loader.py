import pandas as pd
import streamlit as st
from .constants import IDS_VIRADA


@st.cache_data
def carregar_dados_mega_sena(caminho_arquivo="data/mega_sena_sorteio.xlsx"):
    try:
        # Carrega o Excel
        df = pd.read_excel(caminho_arquivo)

        # Ajuste de colunas
        df_limpo = df.iloc[:, 2:8].copy()
        df_limpo.columns = ["D1", "D2", "D3", "D4", "D5", "D6"]

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
