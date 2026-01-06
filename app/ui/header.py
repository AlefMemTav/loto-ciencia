import streamlit as st


def render_app_header(config, df):
    c1, c2 = st.columns([2, 4])
    with c1:
        st.write("**LotoScience**")
    with c2:
        st.caption(
            f"Base de Dados ({config.name}) Atualizada: {len(df)} concursos analisados."
        )
    st.markdown("---")
