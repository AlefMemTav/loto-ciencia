# pages/2_Validador.py

from app.ui.core.shell import init_page
from app.ui.views.validator import render_validator

ctx, svc = init_page(title="Validador Inteligente")
render_validator(ctx, svc)
