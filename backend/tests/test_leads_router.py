"""
Tests for leads router — PATCH /leads/{lead_id}/handoff endpoint (Story 4.4).

Verifies:
- 200 with updated lead for each eligible status transition
- 404 for non-existent lead
- 404 for lead belonging to another tenant
- 409 for lead already in 'cold' status
- 400 for missing X-Tenant-ID header
- 400 for invalid UUID in X-Tenant-ID
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


VALID_TENANT_ID = "123e4567-e89b-12d3-a456-426614174000"
VALID_LEAD_ID = "456e7890-e89b-12d3-a456-426614174001"


def _make_app() -> FastAPI:
    """Create isolated FastAPI app with only the leads router."""
    from routers.leads import router

    app = FastAPI()
    app.include_router(router)
    return app


def _patch_transition(return_value: dict | None, side_effect=None):
    """Patch transition_to_handoff service function."""
    if side_effect:
        return patch(
            "routers.leads.transition_to_handoff",
            side_effect=side_effect,
        )
    return patch(
        "routers.leads.transition_to_handoff",
        return_value=return_value,
    )


# ---------------------------------------------------------------------------
# AC1 — 200 with updated lead for eligible status transitions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "initial_status",
    ["new", "qualifying", "qualified", "scheduled", "handoff"],
)
def test_handoff_returns_200_for_eligible_statuses(initial_status):
    """PATCH /leads/{id}/handoff com status elegível deve retornar 200 com lead atualizado."""
    updated_lead = {
        "id": VALID_LEAD_ID,
        "tenant_id": VALID_TENANT_ID,
        "phone": "5511999999999",
        "name": "Ana",
        "status": "handoff",
        "last_contact_at": "2026-05-29T00:00:00+00:00",
    }

    with _patch_transition(updated_lead):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        response = client.patch(
            f"/leads/{VALID_LEAD_ID}/handoff",
            headers={"X-Tenant-ID": VALID_TENANT_ID},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "handoff"
    assert body["id"] == VALID_LEAD_ID


# ---------------------------------------------------------------------------
# AC4 — 404 for non-existent lead
# ---------------------------------------------------------------------------


def test_handoff_returns_404_for_nonexistent_lead():
    """PATCH /leads/{id}/handoff deve retornar 404 quando o lead não existe."""
    from services.leads_service import LeadNotFoundError

    with _patch_transition(None, side_effect=LeadNotFoundError("not found")):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        response = client.patch(
            f"/leads/{VALID_LEAD_ID}/handoff",
            headers={"X-Tenant-ID": VALID_TENANT_ID},
        )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# AC4 — 404 for lead belonging to another tenant
# ---------------------------------------------------------------------------


def test_handoff_returns_404_for_lead_of_another_tenant():
    """PATCH /leads/{id}/handoff deve retornar 404 quando o lead não pertence ao tenant."""
    from services.leads_service import LeadNotFoundError

    with _patch_transition(None, side_effect=LeadNotFoundError("wrong tenant")):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        response = client.patch(
            f"/leads/{VALID_LEAD_ID}/handoff",
            headers={"X-Tenant-ID": VALID_TENANT_ID},
        )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# AC5 — 409 for lead already cold
# ---------------------------------------------------------------------------


def test_handoff_returns_409_for_cold_lead():
    """PATCH /leads/{id}/handoff deve retornar 409 quando o lead já está com status cold."""
    from services.leads_service import LeadStatusError

    with _patch_transition(None, side_effect=LeadStatusError("already cold")):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        response = client.patch(
            f"/leads/{VALID_LEAD_ID}/handoff",
            headers={"X-Tenant-ID": VALID_TENANT_ID},
        )

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# AC3 — 400 for missing X-Tenant-ID header
# ---------------------------------------------------------------------------


def test_handoff_returns_400_when_tenant_id_header_missing():
    """PATCH /leads/{id}/handoff sem X-Tenant-ID deve retornar 400."""
    with _patch_transition({}):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        response = client.patch(f"/leads/{VALID_LEAD_ID}/handoff")

    assert response.status_code == 400


# ---------------------------------------------------------------------------
# AC3 — 400 for invalid UUID in X-Tenant-ID
# ---------------------------------------------------------------------------


def test_handoff_returns_400_for_invalid_uuid_tenant_id():
    """PATCH /leads/{id}/handoff com X-Tenant-ID inválido deve retornar 400."""
    with _patch_transition({}):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        response = client.patch(
            f"/leads/{VALID_LEAD_ID}/handoff",
            headers={"X-Tenant-ID": "not-a-uuid"},
        )

    assert response.status_code == 400
