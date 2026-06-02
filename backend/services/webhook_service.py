"""Service de processamento de webhooks do Z-API."""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass

from db.client import get_client, set_tenant_context
from db.tenants import get_owner_phone
from schemas.webhook import ZApiWebhookPayload
from services.agent_dispatch import dispatch_agent
from services.onboarding_dispatch import dispatch_onboarding_agent

logger = logging.getLogger(__name__)

_ACTIVE_STATUS = "active"
_ONBOARDING_STATUS = "onboarding"
_PHONE_RE = re.compile(r"^\d{10,15}$")


def _is_valid_phone(phone: str | None) -> bool:
    """Retorna True se o phone está no formato numérico Z-API (10–15 dígitos, sem '+')."""
    return phone is not None and bool(_PHONE_RE.match(phone))


@dataclass
class InboundMessage:
    """Agrupa os dados de uma mensagem inbound para processamento interno."""

    tenant_id: str
    tenant_status: str
    tenant_name: str
    phone: str
    text: str
    instance_id: str
    image_url: str | None = None


def _validate_token(received_token: str | None, expected_token: str) -> None:
    """Lança PermissionError se o token for ausente ou inválido."""
    if not received_token or received_token != expected_token:
        raise PermissionError("Token Z-API inválido ou ausente")


def _resolve_tenant(instance_id: str) -> dict | None:
    """Busca o tenant pelo instanceId. Retorna row com id/status/name ou None."""
    client = get_client()
    tenant_query_result = (
        client.table("tenants")
        .select("id, status, name")
        .eq("zapi_instance_id", instance_id)
        .execute()
    )
    if not tenant_query_result.data:
        logger.warning(
            "Tenant não encontrado para instanceId",
            extra={"instance_id": instance_id},
        )
        return None
    return tenant_query_result.data[0]


def _persist_inbound_message(
    tenant_id: str,
    phone: str,
    content: str,
    *,
    media_url: str | None = None,
) -> None:
    set_tenant_context(tenant_id)
    client = get_client()
    row: dict = {
        "tenant_id": tenant_id,
        "direction": "inbound",
        "lead_id": None,
        "phone": phone,
        "content": content,
    }
    if media_url is not None:
        row["media_url"] = media_url
    client.table("messages").insert(row).execute()


async def _route_onboarding_message(msg: InboundMessage) -> None:
    """Valida owner_phone e agenda dispatch de onboarding para o dono."""
    owner_phone = await asyncio.to_thread(get_owner_phone, msg.tenant_id)
    if owner_phone is not None and msg.phone != owner_phone:
        logger.warning(
            "Mensagem de onboarding descartada — phone não é do owner",
            extra={"tenant_id": msg.tenant_id, "phone": msg.phone, "owner_phone": owner_phone},
        )
        return
    asyncio.create_task(dispatch_onboarding_agent(msg.tenant_id, owner_phone, msg.text))


async def _handle_inbound_message(msg: InboundMessage) -> None:
    """Loga, persiste mensagem inbound e dispara agente se tenant ativo."""
    if not _is_valid_phone(msg.phone):
        logger.warning("Mensagem descartada — phone inválido", extra={"tenant_id": msg.tenant_id, "phone": msg.phone})
        return
    logger.info("Mensagem inbound recebida", extra={"tenant_id": msg.tenant_id, "phone": msg.phone, "message_length": len(msg.text), "instance_id": msg.instance_id})
    await asyncio.to_thread(_persist_inbound_message, msg.tenant_id, msg.phone, msg.text, media_url=msg.image_url)
    if msg.tenant_status == _ACTIVE_STATUS:
        asyncio.create_task(
            dispatch_agent(msg.tenant_id, msg.tenant_name, msg.phone, text=msg.text, image_url=msg.image_url)
        )
    elif msg.tenant_status == _ONBOARDING_STATUS:
        await _route_onboarding_message(msg)


def _parse_message_content(payload: ZApiWebhookPayload) -> tuple[str, str | None]:
    """Extrai (text, image_url) do payload Z-API."""
    if payload.is_image_message:
        caption = payload.imageMessage.caption if (payload.imageMessage and payload.imageMessage.caption) else ""  # type: ignore[union-attr]
        return caption, payload.image_url
    return payload.text.message, None  # type: ignore[union-attr]


def _build_inbound_message(
    tenant_row: dict, payload: ZApiWebhookPayload, text: str, *, image_url: str | None
) -> InboundMessage:
    """Constrói um InboundMessage a partir do tenant_row e payload."""
    return InboundMessage(
        tenant_id=tenant_row["id"],
        tenant_status=tenant_row["status"],
        tenant_name=tenant_row.get("name", ""),
        phone=payload.phone,  # type: ignore[arg-type]
        text=text,
        instance_id=payload.instanceId,
        image_url=image_url,
    )


async def process_inbound_message(
    payload: ZApiWebhookPayload,
    received_token: str | None,
    expected_token: str,
) -> dict:
    """Processa webhook Z-API: valida token, resolve tenant e dispara agente."""
    _validate_token(received_token, expected_token)
    if not (payload.is_text_message or payload.is_image_message):
        return {"received": True}
    tenant_row = await asyncio.to_thread(_resolve_tenant, payload.instanceId)
    if tenant_row is None:
        return {"received": True}
    text, image_url = _parse_message_content(payload)
    msg = _build_inbound_message(tenant_row, payload, text, image_url=image_url)
    asyncio.create_task(_handle_inbound_message(msg))
    return {"received": True}
