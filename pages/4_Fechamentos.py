# pages/4_Fechamentos.py
from app.ui.core.shell import init_page
from app.ui.views.closures import render_closures

ctx, svc = init_page(title="Fechamentos Matemáticos")

render_closures(ctx, svc)
