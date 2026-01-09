# pages/5_Bolao.py
from app.ui.core.shell import init_page
from app.ui.views.bolao import render_bolao

ctx, svc = init_page(title="Gerenciador de Bolão", require_pro=True)

render_bolao(ctx, svc)
