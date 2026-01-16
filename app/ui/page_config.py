# app/ui/page_config.py
import streamlit as st


def apply_page_config(title=None):
    # Título Padrão (Global)
    default_title = "LotoScience | Inteligência Estatística para Loterias"

    # Se passar um título específico, usa ele. Senão, usa o padrão.
    final_title = title if title else default_title
    st.set_page_config(
        page_title=final_title,
        page_icon="🧬",
        layout="wide",
        initial_sidebar_state="collapsed",
        menu_items={
            "Get Help": None,
            "Report a bug": None,
            "About": "# LotoScience\nInteligência Estatística para Loterias.",
        },
    )
