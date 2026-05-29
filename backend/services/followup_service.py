"""
Follow-up service for automated lead re-engagement (Story 4.3).

Responsibilities:
- send_first_followup: sends re-engagement message and records follow_up_1_sent_at
- send_second_followup: sends second attempt, marks lead cold, notifies owner
- run_followup_job: hourly job that iterates active tenants and triggers follow-ups

Templates use {name} placeholder — defaults to "você" when name is NULL.
Z-API failures are logged and not propagated — the job continues processing remaining leads.
"""
from __future__ import annotations

import asyncio
import logging

from db.client import get_client, set_tenant_context
from services.followup_query import (
    get_leads_for_first_followup,
    get_leads_for_second_followup,
)
from services.notification_service import notify_owner_lead_cold
from services.zapi_client import send_message

logger = logging.getLogger(__name__)

FIRST_FOLLOWUP_TEMPLATE = (
    "Olá, {name}! Tudo bem? 😊\n\n"
    "Vi que você demonstrou interesse em nossos serviços de mármores e pedras. "
    "Ainda posso ajudar você? Conte comigo para tirar todas as suas dúvidas!"
)

SECOND_FOLLOWUP_TEMPLATE = (
    "Oi, {name}! Tentei entrar em contato antes mas não consegui.\n\n"
    "Se ainda tiver interesse em nossos serviços, estou à disposição. "
    "Qualquer dúvida, é só chamar aqui!"
)


def _interpolate(template: str, lead: dict) -> str:
    """Interpolate lead name into template, defaulting to 'você' if None."""
    name = lead.get("name") or "você"
    return template.format(name=name)


async def send_first_followup(tenant_id: str, lead: dict) -> None:
    """Send first re-engagement message and record follow_up_1_sent_at.

    Z-API failures are logged and not propagated.
    set_tenant_context is called before the database update (NFR3).

    Args:
        tenant_id: UUID of the tenant.
        lead: Lead dict with at least id, phone, name.
    """
    message = _interpolate(FIRST_FOLLOWUP_TEMPLATE, lead)
    try:
        await send_message(tenant_id, lead["phone"], message)
    except Exception as exc:
        logger.warning(
            "Falha ao enviar primeiro follow-up via Z-API",
            extra={"tenant_id": tenant_id, "lead_id": lead.get("id"), "error": str(exc)},
        )
        return

    set_tenant_context(tenant_id)
    client = get_client()
    from datetime import datetime, timezone

    now_iso = datetime.now(timezone.utc).isoformat()
    client.table("leads").update({"follow_up_1_sent_at": now_iso}).eq(
        "id", lead["id"]
    ).execute()


async def send_second_followup(tenant_id: str, lead: dict) -> None:
    """Send second follow-up attempt, mark lead cold, and notify owner.

    Z-API failures are logged and not propagated. Owner notification is
    called regardless of Z-API result (lead is cold either way after two attempts).
    set_tenant_context is called before the database update (NFR3).

    Args:
        tenant_id: UUID of the tenant.
        lead: Lead dict with at least id, phone, name.
    """
    message = _interpolate(SECOND_FOLLOWUP_TEMPLATE, lead)
    try:
        await send_message(tenant_id, lead["phone"], message)
    except Exception as exc:
        logger.warning(
            "Falha ao enviar segundo follow-up via Z-API",
            extra={"tenant_id": tenant_id, "lead_id": lead.get("id"), "error": str(exc)},
        )

    set_tenant_context(tenant_id)
    client = get_client()
    client.table("leads").update({"status": "cold"}).eq("id", lead["id"]).execute()
    await notify_owner_lead_cold(tenant_id, lead)


def _process_tenant_followups(tenant: dict) -> None:
    """Run the follow-up loop for a single tenant synchronously."""
    tenant_id = tenant["id"]
    try:
        first_leads = get_leads_for_first_followup(tenant_id)
        second_leads = get_leads_for_second_followup(tenant_id)
        asyncio.run(_process_leads(tenant_id, first_leads, second_leads))
    except Exception as exc:
        logger.error(
            "Erro ao processar follow-ups do tenant",
            extra={"tenant_id": tenant_id, "error": str(exc)},
        )


async def _process_leads(
    tenant_id: str, first_leads: list[dict], second_leads: list[dict]
) -> None:
    """Send follow-ups for all eligible leads of a tenant."""
    for lead in first_leads:
        try:
            await send_first_followup(tenant_id, lead)
        except Exception as exc:
            logger.error(
                "Erro inesperado no send_first_followup",
                extra={"tenant_id": tenant_id, "lead_id": lead.get("id"), "error": str(exc)},
            )
    for lead in second_leads:
        try:
            await send_second_followup(tenant_id, lead)
        except Exception as exc:
            logger.error(
                "Erro inesperado no send_second_followup",
                extra={"tenant_id": tenant_id, "lead_id": lead.get("id"), "error": str(exc)},
            )


def run_followup_job() -> None:
    """Execute the hourly follow-up job.

    Iterates all tenants with status='active', fetches leads eligible for
    first and second follow-up, and dispatches messages accordingly.
    Per-tenant failures are logged and do not interrupt remaining tenants.
    """
    logger.info("follow_up_job: started")
    client = get_client()
    tenants_result = (
        client.table("tenants")
        .select("id, status, owner_phone")
        .eq("status", "active")
        .execute()
    )
    tenants = tenants_result.data or []
    for tenant in tenants:
        _process_tenant_followups(tenant)
    logger.info("follow_up_job: completed", extra={"tenants_processed": len(tenants)})
