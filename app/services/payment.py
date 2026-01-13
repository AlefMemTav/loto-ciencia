# app/services/payment.py
import logging
import stripe
import streamlit as st

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configura a chave uma única vez
if "stripe" in st.secrets:
    stripe.api_key = st.secrets["stripe"]["api_key"]
    logger.info("Stripe API key configurada a partir de st.secrets")


def get_checkout_url(user_email: str):
    """
    Gera uma URL de Checkout do Stripe para o plano PRO.
    """
    try:
        # Configurações vindas do secrets
        domain_url = st.secrets["stripe"]["domain_url"]
        price_id = st.secrets["stripe"]["price_id"]
        logger.info(
            "Iniciando criação de sessão de checkout | email=%s price_id=%s",
            user_email,
            price_id,
        )

        # Cria a sessão no Stripe
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                },
            ],
            mode="subscription",  # Importante: é uma assinatura (SaaS)
            success_url=f"{domain_url}/Painel?paid=true",
            cancel_url=f"{domain_url}/Planos",
            customer_email=user_email,  # Preenche automático para o usuário
            # client_reference_id ajuda a rastrear quem pagou no webhook depois
            client_reference_id=user_email,
        )

        logger.info(
            "Sessão de checkout criada com sucesso | session_id=%s",
            getattr(checkout_session, "id", "unknown"),
        )
        logger.debug("Checkout URL: %s", getattr(checkout_session, "url", "none"))
        return checkout_session.url

    except Exception as e:
        logger.exception("Erro ao gerar sessão de pagamento para email=%s", user_email)
        st.error(f"Erro ao gerar pagamento: {e}")
        return None
