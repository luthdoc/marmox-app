"""
Dispatcher de onboarding — handler fire-and-forget para mensagens do dono
durante a configuração inicial do tenant (Story 5.3).
"""
from __future__ import annotations

import asyncio
import logging

from db.client import set_tenant_context
from db.conversation import load_conversation_history, persist_outbound_message
from db.tenants import complete_onboarding, update_tenant_config
from services.onboarding_service import parse_empresa_block, process_onboarding_message
from services.zapi_client import send_message

logger = logging.getLogger(__name__)

_ACTIVATION_MESSAGE = (
    "Configuração concluída! Seu assistente já está ativo e pronto "
    "para atender seus clientes no WhatsApp."
)


async def _activate_tenant(tenant_id: str, phone: str, dados: dict) -> None:
    """Persiste configuração e ativa tenant após onboarding_complete=True."""
    await asyncio.to_thread(update_tenant_config, tenant_id, dados)
    await asyncio.to_thread(complete_onboarding, tenant_id)
    await send_message(tenant_id, phone, _ACTIVATION_MESSAGE)


async def dispatch_onboarding_agent(
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
        await asyncio.to_thread(persist_outbound_message, tenant_id=tenant_id, phone=phone, content=clean_response, lead_id=None)
        if dados is not None and dados.get("onboarding_complete"):
            await _activate_tenant(tenant_id, phone, dados)
    except Exception as exc:
        logger.error(
            "Falha no dispatch de onboarding — erro ignorado (fire-and-forget)",
            extra={"tenant_id": tenant_id, "phone": owner_phone, "error": str(exc)},
        )
