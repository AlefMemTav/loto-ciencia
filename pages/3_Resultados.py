# pages/3_Resultados.py
from app.ui.page_config import apply_page_config
from app.ui.core.styles import apply_custom_css
from app.ui.core.state import init_game_state, load_context
from app.ui.views.validador_em_acao import render_validador_em_acao
from app.ui.services.auth_client import AUTHClient

AUTHClient.init()

apply_page_config(title="Últimos Resultados Lotofácil e Mega-Sena | LotoScience")
apply_custom_css()

init_game_state()

ctx, svc = load_context()
render_validador_em_acao()
