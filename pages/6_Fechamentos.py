# pages/6_Fechamentos.py
from app.ui.core.shell import init_page
from app.ui.views.closures import render_closures

ctx, svc = init_page(title="Fechamentos e Desdobramentos (Lotofácil/Mega)")

render_closures(ctx, svc)
