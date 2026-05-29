"""
Serviço de notificações ao dono via WhatsApp (Story 3.6).

Responsabilidades:
- notify_owner_lead_scheduled: notifica o dono quando um lead agenda uma visita
- notify_owner_escalation: notifica o dono quando o agente não sabe responder
- contains_escalation_sentinel: detecta a sentinel [ESCALAR_DONO] na resposta do Claude

Todas as notificações são disparadas via asyncio.create_task no ponto de integração
(dispatcher) para não bloquear o fluxo principal (AC 8).
"""
from __future__ import annotations

import logging

from db.tenants import get_owner_phone
from services.zapi_client import send_message

logger = logging.getLogger(__name__)

# Sentinel configurável que o Claude inclui na resposta quando precisa escalar ao dono.
# O system prompt instrui o Claude a incluir esta string quando não sabe responder.
# O backend detecta e dispara notificação — a sentinel não é enviada ao lead (AC 7).
ESCALATION_SENTINEL = "[ESCALAR_DONO]"


def contains_escalation_sentinel(response: str) -> bool:
    """Retorna True se a resposta do Claude contém a sentinel de escalada."""
    return ESCALATION_SENTINEL in response


def _or_dash(value: object) -> str:
    """Retorna str(value) se truthy, '—' caso contrário."""
    return str(value) if value else "—"


def _format_scheduled_message(lead: dict) -> str:
    """Formata a mensagem de notificação de agendamento ao dono."""
    return (
        f"*Novo agendamento confirmado!*\n\n"
        f"*Nome:* {_or_dash(lead.get('name'))}\n"
        f"*Serviço:* {_or_dash(lead.get('service_type'))}\n"
        f"*Urgência:* {_or_dash(lead.get('urgency'))}\n"
        f"*Região:* {_or_dash(lead.get('region'))}\n"
        f"*Data/Hora:* {_or_dash(lead.get('scheduled_at'))}"
    )


async def notify_owner_lead_scheduled(tenant_id: str, lead: dict) -> None:
    """Notifica dono via WhatsApp quando lead agenda visita."""
    owner_phone = get_owner_phone(tenant_id)
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
    """Notifica dono via WhatsApp quando agente não sabe responder."""
    owner_phone = get_owner_phone(tenant_id)
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


def _format_cold_lead_message(lead: dict) -> str:
    """Formata a mensagem de notificação de lead frio ao dono."""
    name = lead.get("name") or "—"
    phone = lead.get("phone") or "—"
    return (
        f"*Lead marcado como frio após duas tentativas de reengajamento.*\n\n"
        f"*Nome:* {name}\n"
        f"*Telefone:* {phone}\n\n"
        f"Este lead não respondeu às mensagens automáticas e foi marcado como frio."
    )


async def notify_owner_lead_cold(tenant_id: str, lead: dict) -> None:
    """Notifica dono via WhatsApp quando lead é marcado como frio (Story 4.3).

    Busca owner_phone do tenant. Se ausente, loga aviso e retorna sem enviar.
    Nunca lança exceção — a falha é absorvida com log.

    Args:
        tenant_id: UUID do tenant.
        lead: Dicionário com dados do lead (id, name, phone).
    """
    owner_phone = get_owner_phone(tenant_id)
    if owner_phone is None:
        logger.warning(
            "Notificação de lead frio pulada — owner_phone ausente",
            extra={"tenant_id": tenant_id, "lead_id": lead.get("id")},
        )
        return
    logger.info(
        "Enviando notificação de lead frio ao dono",
        extra={
            "tenant_id": tenant_id,
            "lead_id": lead.get("id"),
            "notification_type": "cold",
        },
    )
    await send_message(tenant_id, owner_phone, _format_cold_lead_message(lead))
