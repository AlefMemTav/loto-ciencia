import streamlit as st


def top_nav():
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.page_link("pages/1_Painel.py", label="🏠 Início")
    with c2:
        st.page_link("pages/2_Validador.py", label="✅ Validar Jogo")
    with c3:
        st.page_link("pages/3_Gerador.py", label="🤖 Gerador Inteligente")
    with c4:
        st.page_link("pages/4_Fechamentos.py", label="📦 Fechamentos")
    with c5:
        st.page_link("pages/5_Bolao.py", label="👥 Análise de Bolão")
