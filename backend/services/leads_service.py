"""
Leads service for lead lifecycle management (Story 4.4).

Responsibilities:
- transition_to_handoff: validates and executes lead status transition to 'handoff'

Raises:
- LeadNotFoundError: when lead does not exist or does not belong to tenant
- LeadStatusError: when transition is not allowed (e.g., from 'cold')
"""
from __future__ import annotations

from db.client import get_client, set_tenant_context

_LEAD_RESPONSE_FIELDS = "id, tenant_id, phone, name, status, last_contact_at"


class LeadNotFoundError(Exception):
    """Raised when the requested lead does not exist or belongs to another tenant."""


class LeadStatusError(Exception):
    """Raised when the status transition is not allowed."""


def _fetch_lead(client, lead_id: str, tenant_id: str) -> dict:
    """Fetch lead by id and tenant_id; raise LeadNotFoundError if absent."""
    result = (
        client.table("leads")
        .select(_LEAD_RESPONSE_FIELDS)
        .eq("id", lead_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise LeadNotFoundError(f"Lead {lead_id} not found for tenant {tenant_id}")
    return result.data[0]


def _update_to_handoff(client, lead_id: str, tenant_id: str) -> dict:
    """Update lead status to 'handoff'; raise LeadNotFoundError if update fails."""
    result = (
        client.table("leads")
        .update({"status": "handoff"})
        .eq("id", lead_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if not result.data:
        raise LeadNotFoundError(f"Lead {lead_id} update failed")
    return result.data[0]


def transition_to_handoff(tenant_id: str, lead_id: str) -> dict:
    """Transition a lead to 'handoff' status.

    Fetches the lead filtering by both id and tenant_id (RLS + explicit filter).
    Rejects cold leads with LeadStatusError (regression from cold is forbidden).

    Args:
        tenant_id: UUID of the authenticated tenant.
        lead_id: UUID of the lead to transition.

    Returns:
        Updated lead dict with fields: id, tenant_id, phone, name, status,
        last_contact_at.

    Raises:
        LeadNotFoundError: If lead does not exist or belongs to another tenant.
        LeadStatusError: If lead status is 'cold'.
    """
    set_tenant_context(tenant_id)
    client = get_client()
    lead = _fetch_lead(client, lead_id, tenant_id)
    if lead["status"] == "cold":
        raise LeadStatusError("Cannot transition from 'cold' to 'handoff'")
    return _update_to_handoff(client, lead_id, tenant_id)
