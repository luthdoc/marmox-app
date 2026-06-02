"""Dispatcher do agente principal — processa mensagens de tenants ativos."""
from __future__ import annotations

import asyncio
import logging
from functools import partial

from db.conversation import load_conversation_history
from db.leads import get_or_create_lead, update_lead_qualification
from db.tenants import get_tenant_context
from services.agent_service import process_message, select_model
from services.message_delivery import deliver_message
from services.notification_service import (
    ESCALATION_SENTINEL,
    contains_escalation_sentinel,
    notify_owner_escalation,
    notify_owner_lead_scheduled,
)
from services.qualification import (
    _should_notify_scheduled,
    compute_lead_status,
    parse_lead_data_block,
)

logger = logging.getLogger(__name__)


async def _fetch_dispatch_context(
    tenant_id: str, phone: str
) -> tuple[dict, dict, list[dict]]:
    """Carrega lead, contexto do tenant e histórico em paralelo."""
    lead, tenant_context, history = await asyncio.gather(
        asyncio.to_thread(get_or_create_lead, tenant_id, phone),
        asyncio.to_thread(get_tenant_context, tenant_id),
        asyncio.to_thread(load_conversation_history, tenant_id, phone),
    )
    return lead, tenant_context, history


async def _apply_lead_update_and_notify(
    lead_id: str,
    tenant_id: str,
    *,
    lead: dict,
    lead_data_extracted: dict,
) -> None:
    """Atualiza qualificação do lead e notifica dono se transicionou para 'scheduled'."""
    new_status = compute_lead_status(lead.get("status", "new"), lead_data_extracted)
    patch_data = {
        key: lead_data_extracted.get(key)
        for key in ("name", "service_type", "material", "urgency", "region", "scheduled_at")
    }
    patch_data["status"] = new_status
    await asyncio.to_thread(update_lead_qualification, lead_id, tenant_id, patch_data)
    if _should_notify_scheduled(new_status, lead.get("status")):
        updated_lead = {**lead, **{k: v for k, v in patch_data.items() if v is not None}}
        asyncio.create_task(notify_owner_lead_scheduled(tenant_id, updated_lead))


async def _handle_agent_response(
    *,
    tenant_id: str,
    phone: str,
    lead: dict,
    raw_response: str,
) -> None:
    """Envia resposta limpa, persiste outbound e aplica atualizações de lead."""
    has_escalation = contains_escalation_sentinel(raw_response)
    lead_data_extracted, clean_response = parse_lead_data_block(raw_response)
    clean_response = clean_response.replace(ESCALATION_SENTINEL, "").strip()
    if not await deliver_message(tenant_id, phone, clean_response, lead_id=lead["id"]):
        return
    lead_id = lead["id"]
    if lead_data_extracted is not None:
        await _apply_lead_update_and_notify(lead_id, tenant_id, lead=lead, lead_data_extracted=lead_data_extracted)
    if has_escalation:
        asyncio.create_task(notify_owner_escalation(tenant_id, lead_id, phone))


async def dispatch_agent(
    tenant_id: str,
    tenant_name: str,
    phone: str,
    *,
    text: str = "",
    image_url: str | None = None,
) -> None:
    """Fire-and-forget: processa mensagem com Claude e envia resposta ao lead."""
    try:
        lead, tenant_context, history = await _fetch_dispatch_context(tenant_id, phone)
        model = select_model(text, image_url)
        raw_response = await process_message(
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            phone=phone,
            text=text,
            history=history,
            tenant_context=tenant_context,
            image_url=image_url,
            model=model,
        )
        await _handle_agent_response(
            tenant_id=tenant_id, phone=phone, lead=lead, raw_response=raw_response
        )
    except Exception as exc:
        logger.error(
            "Falha ao processar mensagem com agente — erro ignorado (fire-and-forget)",
            extra={"tenant_id": tenant_id, "phone": phone, "error": str(exc)},
        )
