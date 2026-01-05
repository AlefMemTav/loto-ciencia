# app/ui/board_ui.py
import matplotlib.pyplot as plt
import streamlit as st
from app.src.games import GameConfig


def render_volante_marcado(nums, config: GameConfig, figsize=(6, 3)):
    layout = config.layout
    fig, ax = plt.subplots(figsize=figsize)

    ax.set_xlim(0, layout.cols)
    ax.set_ylim(0, layout.rows)
    ax.axis("off")

    s = set(nums)
    for n in range(1, config.n_numbers + 1):
        r, c = layout.pos(n)
        # desenha de cima para baixo (igual seu padrão atual)
        y = layout.rows - r - 0.5
        x = c + 0.5

        selected = n in s
        color = "#d97706" if selected else "#f1f5f9"
        txtcol = "white" if selected else "#94a3b8"
        fw = "bold" if selected else "normal"

        ax.text(
            x,
            y,
            str(n),
            ha="center",
            va="center",
            color=txtcol,
            fontweight=fw,
            bbox=dict(boxstyle="circle,pad=0.3", fc=color, ec="none"),
        )

    st.pyplot(fig)
