# app/ui/nav.py
import streamlit as st


def top_nav():
    """Navbar principal com links das páginas"""

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.page_link("pages/2_Painel.py", label="🏠 Início")
    with col2:
        st.page_link("pages/4_Validador.py", label="✅ Validar Jogo")
    with col3:
        st.page_link("pages/5_Gerador.py", label="🤖 Gerador Inteligente")
    with col4:
        st.page_link("pages/6_Fechamentos.py", label="📦 Fechamentos")
    with col5:
        st.page_link("pages/7_Bolao.py", label="👥 Análise de Bolão")
