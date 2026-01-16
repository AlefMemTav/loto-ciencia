# pages/4_Validador.py

from app.ui.core.shell import init_page
from app.ui.views.validator import render_validator

ctx, svc = init_page(
    title="Conferidor e Validador de Jogos (Lotofácil/Mega)",
)
render_validator(ctx, svc)
