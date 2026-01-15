# app/ui/nav.py
import streamlit as st


def top_nav():
    """Navbar principal com links das páginas"""

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.page_link("pages/1_Painel.py", label="🏠 Início")
    with col2:
        st.page_link("pages/8_Validador_em_acao.py", label="Últimos Sorteios")
    with col3:
        st.page_link("pages/2_Validador.py", label="✅ Validar Jogo")
    with col4:
        st.page_link("pages/3_Gerador.py", label="🤖 Gerador Inteligente")
    with col5:
        st.page_link("pages/4_Fechamentos.py", label="📦 Fechamentos")
    with col6:
        st.page_link("pages/5_Bolao.py", label="👥 Análise de Bolão")
