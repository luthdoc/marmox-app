"""Service de processamento de webhooks da Meta WhatsApp Cloud API."""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass

from db.client import get_client, set_tenant_context
from db.tenants import get_owner_phone
from schemas.webhook import MetaMessage
from services.agent_dispatch import dispatch_agent
from services.onboarding_dispatch import dispatch_onboarding_agent

logger = logging.getLogger(__name__)

_ACTIVE_STATUS = "active"
_ONBOARDING_STATUS = "onboarding"
_PHONE_RE = re.compile(r"^\d{10,15}$")


def _is_valid_phone(phone: str | None) -> bool:
    return phone is not None and bool(_PHONE_RE.match(phone))


@dataclass
class InboundMessage:
    tenant_id: str
    tenant_status: str
    tenant_name: str
    phone: str
    text: str
    instance_id: str
    image_url: str | None = None


def _resolve_tenant_by_phone_number_id(phone_number_id: str) -> dict | None:
    """Busca tenant pelo whatsapp_phone_number_id. Retorna row com id/status/name ou None."""
    client = get_client()
    result = (
        client.table("tenants")
        .select("id, status, name")
        .eq("whatsapp_phone_number_id", phone_number_id)
        .execute()
    )
    if not result.data:
        logger.warning(
            "Tenant não encontrado para phone_number_id",
            extra={"phone_number_id": phone_number_id},
        )
        return None
    return result.data[0]


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
    owner_phone = await asyncio.to_thread(get_owner_phone, msg.tenant_id)
    if owner_phone is not None and msg.phone != owner_phone:
        logger.warning(
            "Mensagem de onboarding descartada — phone não é do owner",
            extra={"tenant_id": msg.tenant_id, "phone": msg.phone, "owner_phone": owner_phone},
        )
        return
    asyncio.create_task(dispatch_onboarding_agent(msg.tenant_id, owner_phone, msg.text))


async def _handle_inbound_message(msg: InboundMessage) -> None:
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


async def process_inbound_message(
    phone_number_id: str,
    message: MetaMessage,
) -> dict:
    """Processa mensagem da Meta API: resolve tenant por phone_number_id e dispara agente."""
    if not (message.is_text_message or message.is_image_message):
        return {"received": True}

    tenant_row = await asyncio.to_thread(_resolve_tenant_by_phone_number_id, phone_number_id)
    if tenant_row is None:
        return {"received": True}

    text = message.text_body if message.is_text_message else message.image_caption
    image_url = message.image_url if message.is_image_message else None

    msg = InboundMessage(
        tenant_id=tenant_row["id"],
        tenant_status=tenant_row["status"],
        tenant_name=tenant_row.get("name", ""),
        phone=message.phone,
        text=text,
        instance_id=phone_number_id,
        image_url=image_url,
    )
    asyncio.create_task(_handle_inbound_message(msg))
    return {"received": True}
