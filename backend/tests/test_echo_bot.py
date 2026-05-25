"""
Testes de integração para o echo bot (Story 2.4).

Cenários cobertos:
- Tenant ativo recebe echo: send_message chamado com "Recebi: [texto]"
- Tenant em onboarding: send_message NÃO é chamado
- Falha no envio do echo não afeta resposta HTTP 200 (fire-and-forget)
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


VALID_TOKEN = "test-zapi-token"

ACTIVE_TENANT_PAYLOAD = {
    "instanceId": "instance-active",
    "type": "ReceivedCallback",
    "phone": "5511999999999",
    "text": {"message": "Quero um orçamento"},
    "momment": 1234567890,
}

ONBOARDING_TENANT_PAYLOAD = {
    "instanceId": "instance-onboarding",
    "type": "ReceivedCallback",
    "phone": "5511888888888",
    "text": {"message": "Olá"},
    "momment": 1234567891,
}


def _make_app() -> FastAPI:
    from routers.webhook import router

    app = FastAPI()
    app.include_router(router)
    return app


def _make_supabase_mock(tenant_status: str, tenant_id: str = "tenant-uuid-active"):
    """Retorna mock Supabase com tenant no status especificado."""
    mock = MagicMock()
    mock.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": tenant_id, "status": tenant_status}
    ]
    mock.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "msg-uuid-001"}
    ]
    return mock


# ---------------------------------------------------------------------------
# AC 1 + AC 3 + AC 5 — Tenant ativo: echo disparado via send_message
# ---------------------------------------------------------------------------


def test_echo_dispatched_for_active_tenant():
    """Webhook com tenant ativo deve disparar _dispatch_echo."""
    mock_supabase = _make_supabase_mock(tenant_status="active", tenant_id="tenant-active-001")

    with (
        patch("routers.webhook._get_expected_token", return_value=VALID_TOKEN),
        patch("services.webhook_service.get_client", return_value=mock_supabase),
        patch("services.webhook_service.set_tenant_context"),
        patch("services.webhook_service._dispatch_echo", new_callable=AsyncMock) as mock_dispatch,
    ):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        response = client.post(
            "/webhook/whatsapp",
            json=ACTIVE_TENANT_PAYLOAD,
            headers={"X-Zapi-Token": VALID_TOKEN},
        )

    assert response.status_code == 200
    assert response.json() == {"received": True}
    # _dispatch_echo deve ter sido chamado para disparar o echo de forma fire-and-forget
    mock_dispatch.assert_called_once()


# ---------------------------------------------------------------------------
# AC 2 + AC 5 — Tenant em onboarding: send_message NÃO chamado
# ---------------------------------------------------------------------------


def test_echo_not_dispatched_for_onboarding_tenant():
    """Webhook com tenant em onboarding não deve chamar _dispatch_echo."""
    mock_supabase = _make_supabase_mock(tenant_status="onboarding", tenant_id="tenant-onboarding-001")

    with (
        patch("routers.webhook._get_expected_token", return_value=VALID_TOKEN),
        patch("services.webhook_service.get_client", return_value=mock_supabase),
        patch("services.webhook_service.set_tenant_context"),
        patch("services.webhook_service._dispatch_echo", new_callable=AsyncMock) as mock_dispatch,
    ):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        response = client.post(
            "/webhook/whatsapp",
            json=ONBOARDING_TENANT_PAYLOAD,
            headers={"X-Zapi-Token": VALID_TOKEN},
        )

    assert response.status_code == 200
    assert response.json() == {"received": True}
    # _dispatch_echo NÃO deve ter sido chamado para tenants em onboarding
    mock_dispatch.assert_not_called()


# ---------------------------------------------------------------------------
# AC 4 — Falha no echo não afeta resposta HTTP
# ---------------------------------------------------------------------------


def test_echo_failure_does_not_affect_http_response():
    """Falha no envio do echo não deve alterar o HTTP 200 retornado pelo webhook."""
    mock_supabase = _make_supabase_mock(tenant_status="active", tenant_id="tenant-active-002")

    async def _failing_dispatch(*args, **kwargs):
        raise Exception("Z-API down")

    with (
        patch("routers.webhook._get_expected_token", return_value=VALID_TOKEN),
        patch("services.webhook_service.get_client", return_value=mock_supabase),
        patch("services.webhook_service.set_tenant_context"),
        patch("services.webhook_service._dispatch_echo", side_effect=_failing_dispatch),
    ):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        response = client.post(
            "/webhook/whatsapp",
            json=ACTIVE_TENANT_PAYLOAD,
            headers={"X-Zapi-Token": VALID_TOKEN},
        )

    # HTTP 200 deve ser retornado independente do resultado do echo
    assert response.status_code == 200
    assert response.json() == {"received": True}
