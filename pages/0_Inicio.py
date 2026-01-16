# pages/0_Inicio.py
from app.ui.views.landing import render_landing_page
from app.ui.page_config import apply_page_config
from app.ui.services.auth_client import AUTHClient

AUTHClient.init()
apply_page_config(title="LotoScience | IA para Lotofácil e Mega-Sena")
render_landing_page()
