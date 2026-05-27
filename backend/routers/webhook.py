"""
Router de webhook do Z-API (Story 2.2).

Recebe eventos POST do Z-API em /webhook/whatsapp,
faz parse do payload e delega ao webhook_service.
O router não contém lógica de negócio.
"""
from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from core.config import Settings
from schemas.webhook import ZApiWebhookPayload
from services.webhook_service import process_inbound_message

router = APIRouter()


@lru_cache(maxsize=1)
def _get_settings() -> Settings:
    """Retorna o singleton de configuração (instanciado uma única vez no primeiro uso)."""
    return Settings()


def _get_expected_token() -> str:
    """Retorna o token Z-API esperado, lido do singleton de configuração."""
    return _get_settings().zapi_token


@router.post("/webhook/whatsapp")
async def receive_whatsapp_webhook(
    request: Request,
    x_zapi_token: str | None = Header(default=None),
) -> JSONResponse:
    """Recebe eventos de webhook do Z-API.

    Valida o token de autenticação e delega o processamento ao service.
    Retorna 200 para payloads válidos (mesmo que ignorados por tipo).
    Retorna 401 para token ausente ou inválido.
    """
    body = await request.json()
    payload = ZApiWebhookPayload.model_validate(body)
    expected_token = _get_expected_token()

    try:
        service_response = await process_inbound_message(payload, x_zapi_token, expected_token)
    except PermissionError:
        raise HTTPException(status_code=401, detail="Token inválido ou ausente")

    return JSONResponse(content=service_response)
