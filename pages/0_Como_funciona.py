from app.ui.views.landing import render_como_funciona
from app.ui.page_config import apply_page_config
from app.ui.services.auth_client import AUTHClient

apply_page_config()
AUTHClient.init()
render_como_funciona()
