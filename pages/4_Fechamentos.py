# pages/4_Fechamentos.py
from app.ui.core.shell import init_page
from app.ui.closures_ui import render_closures

ctx, svc = init_page(title="Fechamentos Matemáticos", require_pro=True)

render_closures(ctx, svc)
