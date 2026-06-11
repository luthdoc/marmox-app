"""
Router de webhook da Meta WhatsApp Cloud API.

GET  /webhook/whatsapp — verificação inicial do webhook (hub.challenge)
POST /webhook/whatsapp — recebe eventos de mensagem e delega ao webhook_service
"""
from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from core.config import Settings
from schemas.webhook import MetaWebhookPayload
from services.webhook_service import process_inbound_message

router = APIRouter()


@lru_cache(maxsize=1)
def _get_settings() -> Settings:
    return Settings()


@router.get("/webhook/whatsapp")
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
) -> PlainTextResponse:
    """Verificação inicial do webhook exigida pela Meta.

    A Meta envia um GET com hub.mode=subscribe e hub.verify_token para confirmar
    que o endpoint é válido. Retorna hub.challenge em texto plano se o token bater.
    """
    settings = _get_settings()
    if hub_mode == "subscribe" and hub_verify_token == settings.meta_whatsapp_verify_token:
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Verify token inválido")


@router.post("/webhook/whatsapp")
async def receive_whatsapp_webhook(request: Request) -> JSONResponse:
    """Recebe eventos de mensagem da Meta WhatsApp Cloud API.

    Itera sobre todas as mensagens do payload e delega cada uma ao service.
    Retorna 200 imediatamente (a Meta exige resposta rápida).
    """
    body = await request.json()
    payload = MetaWebhookPayload.model_validate(body)

    for phone_number_id, message in payload.get_messages():
        await process_inbound_message(phone_number_id, message)

    return JSONResponse(content={"received": True})
