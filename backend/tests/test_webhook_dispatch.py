"""
Testes de despacho do webhook para o agente (Story 3.1).

Cenários cobertos:
- Tenant ativo: process_message é chamado via _dispatch_agent
- Tenant em onboarding: process_message NÃO é chamado
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


VALID_TOKEN = "test-zapi-token"

ACTIVE_TENANT_PAYLOAD = {
    "instanceId": "instance-active",
    "type": "ReceivedCallback",
    "phone": "5511999999999",
    "text": {"message": "Quero um orçamento de granito"},
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


def _make_supabase_mock(tenant_status: str, tenant_id: str = "tenant-uuid-active", tenant_name: str = "Marmoraria Teste"):
    """Retorna mock Supabase com tenant no status especificado, incluindo name."""
    mock = MagicMock()
    mock.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": tenant_id, "status": tenant_status, "name": tenant_name}
    ]
    mock.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "msg-uuid-001"}
    ]
    return mock


# ---------------------------------------------------------------------------
# AC 9 — Tenant ativo: process_message é chamado
# ---------------------------------------------------------------------------


def test_active_tenant_dispatches_to_agent():
    """Tenant ativo deve agendar _dispatch_agent com parâmetros corretos."""
    tenant_id = "tenant-active-001"
    tenant_name = "Marmoraria Silva"
    mock_supabase = _make_supabase_mock(
        tenant_status="active", tenant_id=tenant_id, tenant_name=tenant_name
    )
    dispatched_calls: list = []

    with (
        patch("routers.webhook._get_expected_token", return_value=VALID_TOKEN),
        patch("services.webhook_service.get_client", return_value=mock_supabase),
        patch("services.webhook_service.set_tenant_context"),
        patch(
            "services.webhook_service._dispatch_agent",
            new_callable=AsyncMock,
            side_effect=lambda *a, **kw: dispatched_calls.append((a, kw)) or None,
        ),
    ):
        with TestClient(_make_app(), raise_server_exceptions=False) as client:
            client.post(
                "/webhook/whatsapp",
                json=ACTIVE_TENANT_PAYLOAD,
                headers={"X-Zapi-Token": VALID_TOKEN},
            )

    assert len(dispatched_calls) == 1
    args, kwargs = dispatched_calls[0]
    assert args[0] == tenant_id
    assert args[1] == tenant_name
    assert args[2] == ACTIVE_TENANT_PAYLOAD["phone"]
    assert kwargs.get("text") == ACTIVE_TENANT_PAYLOAD["text"]["message"]


# ---------------------------------------------------------------------------
# AC 9 — Tenant em onboarding: process_message NÃO é chamado
# ---------------------------------------------------------------------------


def test_onboarding_tenant_does_not_dispatch_to_agent():
    """Tenant em onboarding não deve resultar em chamada a process_message."""
    mock_supabase = _make_supabase_mock(
        tenant_status="onboarding",
        tenant_id="tenant-onboarding-001",
        tenant_name="Marmoraria Nova",
    )

    with (
        patch("routers.webhook._get_expected_token", return_value=VALID_TOKEN),
        patch("services.webhook_service.get_client", return_value=mock_supabase),
        patch("services.webhook_service.set_tenant_context"),
        patch("services.webhook_service.load_conversation_history", return_value=[]),
        patch("services.webhook_service.persist_outbound_message"),
        patch(
            "services.webhook_service.process_message",
            new_callable=AsyncMock,
        ) as mock_process,
        patch("services.webhook_service.send_message", new_callable=AsyncMock),
    ):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        client.post(
            "/webhook/whatsapp",
            json=ONBOARDING_TENANT_PAYLOAD,
            headers={"X-Zapi-Token": VALID_TOKEN},
        )

    mock_process.assert_not_called()
