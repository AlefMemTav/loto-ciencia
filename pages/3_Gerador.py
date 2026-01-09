# pages/3_Gerador.py
from app.ui.core.shell import init_page
from app.ui.generator_ui import render_generator

ctx, svc = init_page(
    title="Gerador Inteligente", require_auth=True, resource_usage="generator"
)
render_generator(ctx, svc)
