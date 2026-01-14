# app/api/routers/webhook.py
import os
import stripe
from fastapi import APIRouter, Request, Header, HTTPException
from app.core.logger import logger
from app.services.auth_service import auth_service

router = APIRouter()

# Essa chave vem do Dashboard do Stripe (Developers > Webhooks)
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    """
    Recebe eventos do Stripe de forma segura.
    Atualiza o plano do usuário APENAS se o pagamento for confirmado.
    """
    payload = await request.body()

    try:
        # 1. Verifica a assinatura (Garante que veio do Stripe e não de um hacker)
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Payload inválido
        logger.error(f"Webhook Payload Error: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        # Assinatura falsa
        logger.error(f"Webhook Signature Error: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 2. Processa o evento
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        if session.get("payment_status") != "paid":
            logger.warning(
                f"Checkout completado, mas pagamento não confirmado: {session.get('id')}"
            )
            return {"status": "ignored"}

        # Recupera o email que enviamos no payment.py
        user_email = session.get("client_reference_id")

        if user_email:
            logger.info(f"💰 Pagamento confirmado ($$) para: {user_email}")
            auth_service.upgrade_user(user_email)
        else:
            logger.warning("Pagamento recebido sem email de referência.")

        # Lembra do client_reference_id que colocamos no payment.py? Usamos ele agora!
        user_email = session.get("client_reference_id")

        if user_email:
            logger.info(f"💰 Pagamento confirmado para: {user_email}")
            auth_service.upgrade_user(user_email)
        else:
            logger.warning("Pagamento recebido sem email de referência.")

    # Retorna 200 OK para o Stripe saber que deu certo
    return {"status": "success"}
