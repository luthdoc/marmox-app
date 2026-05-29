"""
Follow-up query service (Story 4.2).

Provides isolated query functions that return leads eligible for each
follow-up attempt. Used by the follow-up executor (Story 4.3) to retrieve
leads without duplicating query logic.

Excluded statuses (never returned by either function):
    qualified, scheduled, handoff, cold
"""
from datetime import datetime, timedelta, timezone

from db.client import get_client, set_tenant_context

_ELIGIBLE_STATUSES = ("new", "qualifying")
_LEAD_FIELDS = "id, tenant_id, phone, name, status, last_contact_at, follow_up_1_sent_at"


def get_leads_for_first_followup(tenant_id: str) -> list[dict]:
    """Return leads eligible for the first follow-up attempt.

    Eligibility criteria:
    - status IN ('new', 'qualifying')
    - last_contact_at < now() - 48 hours  (NULL last_contact_at excluded)
    - follow_up_1_sent_at IS NULL

    Args:
        tenant_id: UUID of the tenant to query leads for.

    Returns:
        List of lead dicts with fields: id, tenant_id, phone, name,
        status, last_contact_at, follow_up_1_sent_at.
    """
    set_tenant_context(tenant_id)
    threshold = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    client = get_client()
    result = (
        client.table("leads")
        .select(_LEAD_FIELDS)
        .eq("tenant_id", tenant_id)
        .lt("last_contact_at", threshold)
        .is_("follow_up_1_sent_at", "null")
        .execute()
    )
    return result.data or []


def get_leads_for_second_followup(tenant_id: str) -> list[dict]:
    """Return leads eligible for the second follow-up attempt.

    Eligibility criteria:
    - status IN ('new', 'qualifying')
    - follow_up_1_sent_at < now() - 7 days

    Args:
        tenant_id: UUID of the tenant to query leads for.

    Returns:
        List of lead dicts with fields: id, tenant_id, phone, name,
        status, last_contact_at, follow_up_1_sent_at.
    """
    set_tenant_context(tenant_id)
    threshold = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    client = get_client()
    result = (
        client.table("leads")
        .select(_LEAD_FIELDS)
        .eq("tenant_id", tenant_id)
        .lt("follow_up_1_sent_at", threshold)
        .execute()
    )
    return result.data or []
