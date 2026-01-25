# app/api/routers/webhook.py
import os
import stripe
from fastapi import APIRouter, Request, Header, HTTPException
from app.core.logger import logger
from app.services.auth_service import auth_service

router = APIRouter()

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")


@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    """
    Recebe eventos do Stripe de forma segura.
    Atualiza o plano do usuário APENAS se o pagamento for confirmado.
    """
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Webhook Payload Error: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Webhook Signature Error: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]

        if session.get("payment_status") != "paid":
            logger.info(
                f"Sessão {session.get('id')} completada, aguardando pagamento (Boleto)."
            )
            return {"status": "ignored"}

        user_email = session.get("client_reference_id")
        if user_email:
            logger.info(f"💰 Pagamento Imediato confirmado (Cartão) para: {user_email}")
            auth_service.upgrade_user(user_email)

    elif event_type == "invoice.paid":
        invoice = event["data"]["object"]

        user_email = invoice.get("customer_email")

        if user_email:
            logger.info(
                f"💰 Boleto Compensado ou Renovação confirmada para: {user_email}"
            )
            auth_service.upgrade_user(user_email)
        else:
            logger.warning("Fatura paga recebida sem email do cliente.")

    return {"status": "success"}
