# pages/1_Como_funciona.py
from app.ui.views.methodology import render_como_funciona
from app.ui.page_config import apply_page_config
from app.ui.services.auth_client import AUTHClient

AUTHClient.init()
apply_page_config(title="A Ciência e Matemática por trás das Loterias")
render_como_funciona()
