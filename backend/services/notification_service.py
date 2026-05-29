"""
Serviço de notificações ao dono via WhatsApp (Story 3.6).

Responsabilidades:
- notify_owner_lead_scheduled: notifica o dono quando um lead agenda uma visita
- notify_owner_escalation: notifica o dono quando o agente não sabe responder
- contains_escalation_sentinel: detecta a sentinel [ESCALAR_DONO] na resposta do Claude
- _get_owner_phone: busca owner_phone do tenant com set_tenant_context (NFR3)

Todas as notificações são disparadas via asyncio.create_task no ponto de integração
(dispatcher) para não bloquear o fluxo principal (AC 8).
"""
from __future__ import annotations

import logging

from db.client import get_client, set_tenant_context
from services.zapi_client import send_message

logger = logging.getLogger(__name__)

# Sentinel configurável que o Claude inclui na resposta quando precisa escalar ao dono.
# O system prompt instrui o Claude a incluir esta string quando não sabe responder.
# O backend detecta e dispara notificação — a sentinel não é enviada ao lead (AC 7).
ESCALATION_SENTINEL = "[ESCALAR_DONO]"


def _get_owner_phone(tenant_id: str) -> str | None:
    """Busca o owner_phone do tenant no banco.

    Executa set_tenant_context antes da query (NFR3 — RLS enforcement).

    Args:
        tenant_id: UUID do tenant.

    Returns:
        owner_phone como string, ou None se ausente ou tenant não encontrado.
    """
    set_tenant_context(tenant_id)
    client = get_client()
    rows = (
        client.table("tenants")
        .select("owner_phone")
        .eq("id", tenant_id)
        .execute()
        .data
    )
    if not rows:
        return None
    return rows[0].get("owner_phone") or None


def contains_escalation_sentinel(response: str) -> bool:
    """Retorna True se a resposta do Claude contém a sentinel de escalada.

    Args:
        response: Texto bruto retornado pelo Claude (antes de remover a sentinel).

    Returns:
        True se ESCALATION_SENTINEL está presente, False caso contrário.
    """
    return ESCALATION_SENTINEL in response


def _format_scheduled_message(lead: dict) -> str:
    """Formata a mensagem de notificação de agendamento ao dono."""
    name = lead.get("name") or "—"
    service_type = lead.get("service_type") or "—"
    urgency = lead.get("urgency") or "—"
    region = lead.get("region") or "—"
    scheduled_at = lead.get("scheduled_at") or "—"
    return (
        f"*Novo agendamento confirmado!*\n\n"
        f"*Nome:* {name}\n"
        f"*Serviço:* {service_type}\n"
        f"*Urgência:* {urgency}\n"
        f"*Região:* {region}\n"
        f"*Data/Hora:* {scheduled_at}"
    )


async def notify_owner_lead_scheduled(tenant_id: str, lead: dict) -> None:
    """Notifica o dono via WhatsApp quando um lead agenda uma visita.

    Busca owner_phone do tenant. Se ausente, emite log de aviso e retorna sem enviar.
    A mensagem contém: nome, serviço, urgência, região e data/hora do agendamento (AC 4).
    Registra log info com tenant_id, lead_id e tipo de notificação (AC 9).

    Args:
        tenant_id: UUID do tenant.
        lead: Dicionário com dados do lead (id, name, service_type, urgency,
              region, scheduled_at).
    """
    owner_phone = _get_owner_phone(tenant_id)
    if owner_phone is None:
        logger.warning(
            "Notificação de agendamento pulada — owner_phone ausente",
            extra={"tenant_id": tenant_id, "lead_id": lead.get("id")},
        )
        return
    logger.info(
        "Enviando notificação de agendamento ao dono",
        extra={"tenant_id": tenant_id, "lead_id": lead.get("id"), "notification_type": "scheduled"},
    )
    await send_message(tenant_id, owner_phone, _format_scheduled_message(lead))


def _format_escalation_message(lead_phone: str) -> str:
    """Formata a mensagem de notificação de escalada ao dono."""
    return (
        f"*Atenção — dúvida pendente do lead!*\n\n"
        f"O agente não soube responder uma pergunta do cliente.\n"
        f"*Telefone do lead:* {lead_phone}\n\n"
        f"Por favor, entre em contato para esclarecer a dúvida."
    )


async def notify_owner_escalation(
    tenant_id: str, lead_id: str, lead_phone: str
) -> None:
    """Notifica o dono via WhatsApp quando o agente não sabe responder uma pergunta.

    Busca owner_phone do tenant. Se ausente, emite log de aviso e retorna sem enviar.
    A mensagem indica que há uma dúvida pendente do lead (AC 6).
    Registra log info com tenant_id, lead_id e tipo de notificação (AC 9).

    Args:
        tenant_id: UUID do tenant.
        lead_id: UUID do lead que gerou a escalada.
        lead_phone: Telefone do lead com dúvida pendente.
    """
    owner_phone = _get_owner_phone(tenant_id)
    if owner_phone is None:
        logger.warning(
            "Notificação de escalada pulada — owner_phone ausente",
            extra={"tenant_id": tenant_id, "lead_id": lead_id},
        )
        return
    logger.info(
        "Enviando notificação de escalada ao dono",
        extra={"tenant_id": tenant_id, "lead_id": lead_id, "notification_type": "escalation"},
    )
    await send_message(tenant_id, owner_phone, _format_escalation_message(lead_phone))
