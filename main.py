import streamlit as st

from app.ui.router import router

st.set_page_config(
    page_title="LotoScience - A Ciência da Loteria",
    page_icon="🧬",
    layout="wide",
)


def main():
    router()


if __name__ == "__main__":
    main()
