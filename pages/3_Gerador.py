# pages/3_Gerador.py
from app.ui.core.shell import init_page
from app.ui.views.generator import render_generator

ctx, svc = init_page(title="Gerador Inteligente")
render_generator(ctx, svc)
