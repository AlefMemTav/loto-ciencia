# pages/1_Painel.py
from app.ui.components.header import render_app_header
from app.ui.components.nav import top_nav
from app.ui.page_config import apply_page_config
from app.ui.core.styles import apply_custom_css
from app.ui.components.sidebar import render_game_selector
from app.ui.core.state import init_game_state, load_context
from app.ui.views.dashboard import render_dashboard
from app.ui.services.auth_client import AUTHClient

AUTHClient.init()

apply_page_config()
apply_custom_css()

init_game_state()

ctx, svc = load_context()
render_app_header(ctx.config, ctx.df)
top_nav()
render_game_selector()
render_dashboard(ctx, svc)
