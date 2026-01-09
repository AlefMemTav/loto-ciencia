# pages/2_Validador.py

from app.ui.core.shell import init_page
from app.ui.validator_ui import render_validator

ctx, svc = init_page(
    title="Validador Inteligente", require_auth=True, resource_usage="validator"
)
render_validator(ctx, svc)
