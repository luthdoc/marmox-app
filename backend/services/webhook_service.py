"""Service de processamento de webhooks do Z-API."""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from functools import partial

from db.client import get_client, set_tenant_context
from db.conversation import load_conversation_history, persist_outbound_message
from db.leads import get_or_create_lead, update_lead_qualification
from db.tenants import complete_onboarding, get_owner_phone, get_tenant_context, update_tenant_config
from schemas.webhook import ZApiWebhookPayload
from services.agent_service import (
    _MODEL_HAIKU,
    _MODEL_SONNET,
    _is_complex_message,
    process_message,
)
from services.dispatch_helpers import _should_notify_scheduled
from services.notification_service import (
    ESCALATION_SENTINEL,
    contains_escalation_sentinel,
    notify_owner_escalation,
    notify_owner_lead_scheduled,
)
from services.onboarding_service import parse_empresa_block, process_onboarding_message
from services.qualification import compute_lead_status, parse_lead_data_block
from services.zapi_client import send_message

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


async def _handle_inbound_message(msg: InboundMessage) -> None:
    """Loga, persiste mensagem inbound e dispara agente se tenant ativo."""
    if not _is_valid_phone(msg.phone):
        logger.warning("Mensagem descartada — phone inválido", extra={"tenant_id": msg.tenant_id, "phone": msg.phone})
        return
    logger.info("Mensagem inbound recebida", extra={"tenant_id": msg.tenant_id, "phone": msg.phone, "message_length": len(msg.text), "instance_id": msg.instance_id})
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, partial(_persist_inbound_message, msg.tenant_id, msg.phone, msg.text, media_url=msg.image_url))
    if msg.tenant_status == _ACTIVE_STATUS:
        asyncio.create_task(
            _dispatch_agent(msg.tenant_id, msg.tenant_name, msg.phone, text=msg.text, image_url=msg.image_url)
        )
    elif msg.tenant_status == _ONBOARDING_STATUS:
        owner_phone = await asyncio.to_thread(get_owner_phone, msg.tenant_id)
        if owner_phone is not None and msg.phone != owner_phone:
            logger.warning(
                "Mensagem de onboarding descartada — phone não é do owner",
                extra={"tenant_id": msg.tenant_id, "phone": msg.phone, "owner_phone": owner_phone},
            )
            return
        asyncio.create_task(
            _dispatch_onboarding_agent(msg.tenant_id, owner_phone, msg.text)
        )


# Alias para compatibilidade com testes existentes que patcham _handle_text_message
_handle_text_message = _handle_inbound_message


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


async def _fetch_dispatch_context(
    tenant_id: str, phone: str
) -> tuple[dict, dict, list[dict]]:
    """Carrega lead, contexto do tenant e histórico em paralelo sequencial."""
    loop = asyncio.get_event_loop()
    lead = await loop.run_in_executor(None, partial(get_or_create_lead, tenant_id, phone))
    tenant_context = await loop.run_in_executor(None, partial(get_tenant_context, tenant_id))
    history = await loop.run_in_executor(None, partial(load_conversation_history, tenant_id, phone))
    return lead, tenant_context, history


def _select_model(text: str, image_url: str | None) -> str:
    """Seleciona modelo: Sonnet para imagens ou textos complexos; Haiku caso contrário."""
    if image_url or _is_complex_message(text):
        return _MODEL_SONNET
    return _MODEL_HAIKU


async def _apply_lead_update_and_notify(
    lead_id: str,
    tenant_id: str,
    *,
    loop: asyncio.AbstractEventLoop,
    lead: dict,
    lead_data_extracted: dict,
) -> None:
    """Atualiza qualificação do lead e notifica dono se status mudou para 'scheduled'."""
    new_status = compute_lead_status(lead.get("status", "new"), lead_data_extracted)
    patch_data = {
        key: lead_data_extracted.get(key)
        for key in ("name", "service_type", "material", "urgency", "region", "scheduled_at")
    }
    patch_data["status"] = new_status
    await loop.run_in_executor(
        None, partial(update_lead_qualification, lead_id, tenant_id, patch_data)
    )
    if _should_notify_scheduled(new_status, lead.get("status")):
        updated_lead = {**lead, **{k: v for k, v in patch_data.items() if v is not None}}
        asyncio.create_task(notify_owner_lead_scheduled(tenant_id, updated_lead))


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


async def _call_agent(
    *,
    tenant_id: str,
    tenant_name: str,
    phone: str,
    text: str,
    image_url: str | None,
    lead: dict,
    tenant_context: dict,
    history: list[dict],
) -> str:
    """Chama process_message com o modelo selecionado e retorna resposta bruta."""
    model = _select_model(text, image_url)
    return await process_message(
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        phone=phone,
        text=text,
        history=history,
        tenant_context=tenant_context,
        lead_data=lead,
        image_url=image_url,
        model=model,
    )


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
    await send_message(tenant_id, phone, clean_response)
    loop = asyncio.get_event_loop()
    lead_id = lead["id"]
    await loop.run_in_executor(
        None,
        partial(persist_outbound_message, tenant_id=tenant_id, phone=phone, content=clean_response, lead_id=lead_id),
    )
    if lead_data_extracted is not None:
        await _apply_lead_update_and_notify(lead_id, tenant_id, loop=loop, lead=lead, lead_data_extracted=lead_data_extracted)
    if has_escalation:
        asyncio.create_task(notify_owner_escalation(tenant_id, lead_id, phone))


async def _dispatch_agent(
    tenant_id: str,
    tenant_name: str,
    phone: str,
    *,
    text: str = "",
    image_url: str | None = None,
) -> None:
    """Fire-and-forget: processa mensagem com Claude e envia resposta."""
    try:
        lead, tenant_context, history = await _fetch_dispatch_context(tenant_id, phone)
        raw_response = await _call_agent(
            tenant_id=tenant_id, tenant_name=tenant_name, phone=phone,
            text=text, image_url=image_url, lead=lead,
            tenant_context=tenant_context, history=history,
        )
        await _handle_agent_response(tenant_id=tenant_id, phone=phone, lead=lead, raw_response=raw_response)
    except Exception as exc:
        logger.error(
            "Falha ao processar mensagem com agente — erro ignorado (fire-and-forget)",
            extra={"tenant_id": tenant_id, "phone": phone, "error": str(exc)},
        )


async def _dispatch_onboarding_agent(
    tenant_id: str,
    owner_phone: str | None,
    text: str,
) -> None:
    """Fire-and-forget: processa mensagem do dono com agente de onboarding.

    Carrega histórico, chama process_onboarding_message, remove o bloco
    [DADOS_EMPRESA] da resposta e envia o texto limpo ao dono. Se
    onboarding_complete=True, persiste a configuração e ativa o tenant.
    Falhas são absorvidas com log (AC8).
    """
    try:
        set_tenant_context(tenant_id)
        phone = owner_phone or ""
        history = await asyncio.to_thread(load_conversation_history, tenant_id, phone)
        raw_response = await process_onboarding_message(tenant_id, text, history)
        dados, clean_response = parse_empresa_block(raw_response)
        await send_message(tenant_id, phone, clean_response)
        persist_outbound_message(tenant_id=tenant_id, phone=phone, content=clean_response, lead_id=None)
        if dados is not None and dados.get("onboarding_complete"):
            await asyncio.to_thread(update_tenant_config, tenant_id, dados)
            await asyncio.to_thread(complete_onboarding, tenant_id)
            confirmation = (
                "Configuração concluída! Seu assistente já está ativo e pronto "
                "para atender seus clientes no WhatsApp."
            )
            await send_message(tenant_id, phone, confirmation)
    except Exception as exc:
        logger.error(
            "Falha no dispatch de onboarding — erro ignorado (fire-and-forget)",
            extra={"tenant_id": tenant_id, "phone": owner_phone, "error": str(exc)},
        )
