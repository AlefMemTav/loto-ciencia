# app/services/payment.py
import os
from dotenv import load_dotenv


load_dotenv()

import logging
import stripe
import streamlit as st

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")

if STRIPE_API_KEY:
    stripe.api_key = STRIPE_API_KEY
    logger.info("✅ Stripe API key configurada via ambiente.")
else:
    logger.warning("⚠️ STRIPE_API_KEY não encontrada nas variáveis de ambiente.")


def get_checkout_url(user_email: str):
    """
    Gera uma URL de Checkout do Stripe para o plano PRO.
    """
    try:
        # Busca configurações do ambiente
        domain_url = os.getenv("DOMAIN_URL")
        price_id = os.getenv("STRIPE_PRICE_ID")

        # Validação de Segurança
        if not STRIPE_API_KEY:
            logger.error("Tentativa de pagamento sem API Key configurada.")
            st.error("Erro interno: Pagamentos desativados temporariamente.")
            return None

        if not domain_url or not price_id:
            logger.error("Faltam configurações de DOMAIN_URL ou STRIPE_PRICE_ID.")
            st.error("Erro de configuração do sistema de pagamento.")
            return None

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
            mode="subscription",  # Assinatura Recorrente
            success_url=f"{domain_url}/Painel?paid=true",
            cancel_url=f"{domain_url}/Planos",
            customer_email=user_email,
            client_reference_id=user_email,
        )

        logger.info(
            "Sessão de checkout criada com sucesso | session_id=%s",
            getattr(checkout_session, "id", "unknown"),
        )
        return checkout_session.url

    except Exception as e:
        logger.exception("Erro ao gerar sessão de pagamento para email=%s", user_email)
        st.error("Ocorreu um erro ao conectar com o provedor de pagamentos.")
        return None
