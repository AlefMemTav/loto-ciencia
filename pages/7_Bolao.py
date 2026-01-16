# pages/7_Bolao.py
from app.ui.core.shell import init_page
from app.ui.views.bolao import render_bolao

ctx, svc = init_page(title="Auditor e Organizador de Bolões")

render_bolao(ctx, svc)
