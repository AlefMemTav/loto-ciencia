# app/ui/components/header.py
import streamlit as st


def render_app_header(config, df):
    """Header principal com logo e informações do jogo."""

    col1, col2 = st.columns([2, 3])

    with col1:
        st.markdown("### 🧪 **LotoCiencia**")

    with col2:
        st.caption(f"{config.name} • {len(df)} concursos analisados")

    st.markdown("---")
