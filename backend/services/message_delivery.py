"""Entrega canônica de mensagens outbound: send via Z-API + persist em messages."""
from __future__ import annotations

import asyncio

from db.conversation import persist_outbound_message
from services.zapi_client import send_message


async def deliver_message(
    tenant_id: str, phone: str, text: str, *, lead_id: str | None = None
) -> bool:
    """Envia via Z-API; persiste outbound em messages somente se envio OK."""
    if not await send_message(tenant_id, phone, text):
        return False
    await asyncio.to_thread(
        persist_outbound_message,
        tenant_id=tenant_id,
        phone=phone,
        content=text,
        lead_id=lead_id,
    )
    return True
