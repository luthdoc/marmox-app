"""
Envio de mensagens via Meta WhatsApp Cloud API.

Responsabilidades:
- Lookup de whatsapp_phone_number_id do tenant (com cache de 30s)
- Envio de mensagens via POST para a Graph API da Meta
- Retry exponencial: até 3 tentativas com backoff 1s, 2s, 4s
- Logging estruturado para cada tentativa e resultado final
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import TypedDict

import httpx

from db.client import get_client

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 30
_META_API_BASE = "https://graph.facebook.com/v21.0"

# Estrutura: { tenant_id: (whatsapp_phone_number_id, cached_at_monotonic) }
_tenant_credential_cache: dict[str, tuple[str, float]] = {}


class TenantCredentials(TypedDict):
    whatsapp_phone_number_id: str


def _lookup_cached_credentials(tenant_id: str, now: float) -> TenantCredentials | None:
    cached = _tenant_credential_cache.get(tenant_id)
    if cached is not None:
        phone_number_id, cached_at = cached
        if now - cached_at < _CACHE_TTL_SECONDS:
            return {"whatsapp_phone_number_id": phone_number_id}
    return None


def _fetch_and_cache_credentials(tenant_id: str, now: float) -> TenantCredentials | None:
    client = get_client()
    result = (
        client.table("tenants")
        .select("whatsapp_phone_number_id")
        .eq("id", tenant_id)
        .execute()
    )
    if not result.data:
        return None
    row = result.data[0]
    phone_number_id = row.get("whatsapp_phone_number_id")
    if not phone_number_id:
        raise ValueError("whatsapp_phone_number_id ausente no tenant")
    _tenant_credential_cache[tenant_id] = (phone_number_id, now)
    return {"whatsapp_phone_number_id": phone_number_id}


def _get_tenant_credentials(tenant_id: str) -> TenantCredentials | None:
    now = time.monotonic()
    cached = _lookup_cached_credentials(tenant_id, now)
    if cached is not None:
        return cached
    return _fetch_and_cache_credentials(tenant_id, now)


_MAX_ATTEMPTS = 3


@dataclass
class OutboundMessage:
    tenant_id: str
    phone: str
    text: str


@dataclass
class SendContext:
    url: str
    headers: dict
    payload: dict
    tenant_id: str
    phone: str
    text: str


def _log_send_success(ctx: SendContext, attempt: int) -> None:
    logger.info(
        "Mensagem enviada via Meta WhatsApp API",
        extra={
            "tenant_id": ctx.tenant_id,
            "phone": ctx.phone,
            "message_length": len(ctx.text),
            "attempt_number": attempt,
            "success": True,
        },
    )


def _log_send_failure(ctx: SendContext, attempt: int, error: str | None = None) -> None:
    extra: dict = {
        "tenant_id": ctx.tenant_id,
        "phone": ctx.phone,
        "message_length": len(ctx.text),
        "attempt_number": attempt,
        "success": False,
    }
    if error is not None:
        extra["error"] = error
    label = "Meta API — erro de rede" if error else "Meta API — resposta não-2xx"
    logger.warning(label, extra=extra)


async def _attempt_post(
    http_client: httpx.AsyncClient,
    ctx: SendContext,
    attempt: int,
) -> bool:
    try:
        response = await http_client.post(ctx.url, json=ctx.payload, headers=ctx.headers)
        success = response.status_code < 300
        if success:
            _log_send_success(ctx, attempt)
        else:
            _log_send_failure(ctx, attempt)
        return success
    except Exception as exc:
        _log_send_failure(ctx, attempt, error=str(exc))
        return False


async def _retry_send(http_client: httpx.AsyncClient, ctx: SendContext) -> bool:
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        success = await _attempt_post(http_client, ctx, attempt)
        if success:
            return True
        if attempt < _MAX_ATTEMPTS:
            await asyncio.sleep(2 ** (attempt - 1))  # backoff: 1s, 2s
    return False


def _build_send_context(credentials: TenantCredentials, msg: OutboundMessage) -> SendContext:
    phone_number_id = credentials["whatsapp_phone_number_id"]
    access_token = os.environ.get("META_WHATSAPP_ACCESS_TOKEN", "")
    url = f"{_META_API_BASE}/{phone_number_id}/messages"
    return SendContext(
        url=url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        payload={
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": msg.phone,
            "type": "text",
            "text": {"body": msg.text},
        },
        tenant_id=msg.tenant_id,
        phone=msg.phone,
        text=msg.text,
    )


async def send_message(tenant_id: str, phone: str, text: str) -> bool:
    """Envia mensagem WhatsApp via Meta Cloud API com retry exponencial.

    Args:
        tenant_id: UUID do tenant que envia a mensagem.
        phone: Número do destinatário no formato E.164 sem '+' (ex: 5511999999999).
        text: Texto da mensagem a ser enviada.

    Returns:
        True se a mensagem foi enviada com sucesso (HTTP 2xx), False caso contrário.
    """
    credentials = await asyncio.to_thread(_get_tenant_credentials, tenant_id)
    if credentials is None:
        logger.error(
            "Tenant não encontrado para envio de mensagem",
            extra={"tenant_id": tenant_id, "phone": phone},
        )
        return False

    msg = OutboundMessage(tenant_id=tenant_id, phone=phone, text=text)
    ctx = _build_send_context(credentials, msg)

    async with httpx.AsyncClient() as http_client:
        success = await _retry_send(http_client, ctx)

    if not success:
        logger.error(
            "Falha ao enviar mensagem via Meta API após todas as tentativas",
            extra={
                "tenant_id": tenant_id,
                "phone": phone,
                "error": f"HTTP não-2xx em {_MAX_ATTEMPTS} tentativas",
            },
        )
        return False

    return True
