import pandas as pd
import streamlit as st
from app.src.games import GameConfig


@st.cache_data
def carregar_dados_loteria_excel(
    config: GameConfig, caminho_arquivo: str
) -> pd.DataFrame:
    """
    Espera cabeçalho padrão:
    Concurso | Data | bola 1 | bola 2 | ... | bola k
    Retorna df com index=Concurso e colunas D1..Dk (inteiros).
    """
    try:
        df = pd.read_excel(caminho_arquivo)

        # Normaliza nomes para facilitar matching
        cols_norm = {c: str(c).strip().lower() for c in df.columns}

        # 1) acha "concurso"
        concurso_col = None
        for c, cn in cols_norm.items():
            if cn == "concurso":
                concurso_col = c
                break
        if concurso_col is None:
            st.error("Coluna 'Concurso' não encontrada.")
            return pd.DataFrame()

        # 2) monta lista "bola 1..bola k"
        bola_cols = []
        for i in range(1, config.k + 1):
            alvo = f"bola {i}"
            achou = None
            for c, cn in cols_norm.items():
                if cn == alvo:
                    achou = c
                    break
            if achou is None:
                st.error(f"Coluna '{alvo}' não encontrada (esperado k={config.k}).")
                return pd.DataFrame()
            bola_cols.append(achou)

        out = df[[concurso_col] + bola_cols].copy()
        out[concurso_col] = pd.to_numeric(out[concurso_col], errors="coerce")
        out = out.dropna(subset=[concurso_col])
        out[concurso_col] = out[concurso_col].astype(int)
        out = out.set_index(concurso_col)

        # Renomeia para padrão interno
        out.columns = config.draw_cols  # D1..Dk

        # Converte dezenas para inteiro e filtra faixa 1..N
        for c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
        out = out.dropna()

        out = out.astype(int)
        mask = (out >= 1) & (out <= config.n_numbers)
        out = out[mask.all(axis=1)]

        return out.sort_index()

    except FileNotFoundError:
        st.error("Arquivo Excel não encontrado.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()
