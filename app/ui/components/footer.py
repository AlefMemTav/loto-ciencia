import streamlit as st


def render_footer():
    st.markdown(
        """
        <div class="footer-container">
            <div class="footer-text">
                © 2026 LotoCiencia • Feito com Rigor Estatístico.<br>
                <em>Loterias são jogos de azar. Jogue com responsabilidade. Probabilidades baseadas na matemática oficial.</em>
            </div>
        </div>
    """,
        unsafe_allow_html=True,
    )
