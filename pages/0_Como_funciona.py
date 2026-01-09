from app.ui.views.landing import render_como_funciona
from app.ui.page_config import apply_page_config
from app.auth.api_client import APIClient

apply_page_config()
APIClient.init()
render_como_funciona()
