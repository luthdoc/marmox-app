"""
Leads router — lead lifecycle management endpoints (Story 4.4).

Endpoints:
- PATCH /leads/{lead_id}/handoff: transition lead to 'handoff' status

Authentication: X-Tenant-ID header (UUID) identifies the authenticated tenant.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Header, HTTPException

from services.leads_service import (
    LeadNotFoundError,
    LeadStatusError,
    transition_to_handoff,
)

router = APIRouter(tags=["leads"])


def _validate_tenant_id(raw: str | None) -> str:
    """Parse and validate X-Tenant-ID header as UUID.

    Args:
        raw: Raw header value, or None if absent.

    Returns:
        Validated UUID string.

    Raises:
        HTTPException 400 if missing or not a valid UUID.
    """
    if not raw:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header is required")
    try:
        uuid.UUID(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="X-Tenant-ID must be a valid UUID")
    return raw


@router.patch("/leads/{lead_id}/handoff")
def patch_lead_handoff(
    lead_id: str,
    x_tenant_id: str | None = Header(default=None),
) -> dict:
    """Transition a lead to 'handoff' status.

    Args:
        lead_id: UUID of the lead to transition.
        x_tenant_id: Tenant identifier from X-Tenant-ID header.

    Returns:
        Updated lead dict with fields: id, tenant_id, phone, name, status,
        last_contact_at.

    Raises:
        HTTPException 400: Missing or invalid X-Tenant-ID header.
        HTTPException 404: Lead not found or belongs to another tenant.
        HTTPException 409: Lead is already 'cold' (regression forbidden).
    """
    tenant_id = _validate_tenant_id(x_tenant_id)
    try:
        return transition_to_handoff(tenant_id, lead_id)
    except LeadNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except LeadStatusError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
