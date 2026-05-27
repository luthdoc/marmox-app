"""
Testes de integração para o despacho de mensagens via webhook (Story 2.4 → 3.1).

Cenários cobertos:
- Tenant ativo: send_message é chamado com a resposta do agente Claude
- Tenant em onboarding: send_message NÃO é chamado
- Falha no envio não afeta resposta HTTP 200 (fire-and-forget)
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


def _make_supabase_mock(tenant_status: str, tenant_id: str = "tenant-uuid-active", tenant_name: str = "Marmoraria Teste"):
    """Retorna mock Supabase com tenant no status especificado."""
    mock = MagicMock()
    mock.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": tenant_id, "status": tenant_status, "name": tenant_name}
    ]
    mock.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "msg-uuid-001"}
    ]
    return mock


# ---------------------------------------------------------------------------
# AC 6 (Story 3.1) — Tenant ativo: send_message chamado com resposta do agente
# ---------------------------------------------------------------------------


def test_active_tenant_receives_agent_response_via_send_message():
    """Tenant ativo deve receber send_message com a resposta gerada pelo agente Claude."""
    tenant_id = "tenant-active-001"
    agent_response = "Olá! Sou o assistente virtual. Como posso ajudar?"
    mock_supabase = _make_supabase_mock(tenant_status="active", tenant_id=tenant_id)

    with (
        patch("routers.webhook._get_expected_token", return_value=VALID_TOKEN),
        patch("services.webhook_service.get_client", return_value=mock_supabase),
        patch("services.webhook_service.set_tenant_context"),
        patch(
            "services.webhook_service.process_message",
            new_callable=AsyncMock,
            return_value=agent_response,
        ),
        patch("services.webhook_service.send_message", new_callable=AsyncMock) as mock_send,
    ):
        with TestClient(_make_app(), raise_server_exceptions=False) as client:
            client.post(
                "/webhook/whatsapp",
                json=ACTIVE_TENANT_PAYLOAD,
                headers={"X-Zapi-Token": VALID_TOKEN},
            )

        mock_send.assert_called_once_with(
            tenant_id,
            ACTIVE_TENANT_PAYLOAD["phone"],
            agent_response,
        )


# ---------------------------------------------------------------------------
# AC 7 (Story 3.1) — Tenant em onboarding: send_message NÃO chamado
# ---------------------------------------------------------------------------


def test_onboarding_tenant_does_not_receive_echo():
    """Tenant em onboarding não deve gerar chamada a send_message."""
    mock_supabase = _make_supabase_mock(tenant_status="onboarding", tenant_id="tenant-onboarding-001")

    with (
        patch("routers.webhook._get_expected_token", return_value=VALID_TOKEN),
        patch("services.webhook_service.get_client", return_value=mock_supabase),
        patch("services.webhook_service.set_tenant_context"),
        patch("services.webhook_service.process_message", new_callable=AsyncMock),
        patch("services.webhook_service.send_message", new_callable=AsyncMock) as mock_send,
    ):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        client.post(
            "/webhook/whatsapp",
            json=ONBOARDING_TENANT_PAYLOAD,
            headers={"X-Zapi-Token": VALID_TOKEN},
        )

    mock_send.assert_not_called()


# ---------------------------------------------------------------------------
# AC 6 (Story 3.1) — Falha no agente/envio não afeta resposta HTTP
# ---------------------------------------------------------------------------


def test_agent_failure_does_not_affect_http_response():
    """Falha em process_message não deve alterar o HTTP 200 retornado pelo webhook."""
    mock_supabase = _make_supabase_mock(tenant_status="active", tenant_id="tenant-active-002")

    with (
        patch("routers.webhook._get_expected_token", return_value=VALID_TOKEN),
        patch("services.webhook_service.get_client", return_value=mock_supabase),
        patch("services.webhook_service.set_tenant_context"),
        patch(
            "services.webhook_service.process_message",
            new_callable=AsyncMock,
            side_effect=Exception("API indisponível"),
        ),
        patch("services.webhook_service.send_message", new_callable=AsyncMock),
    ):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        response = client.post(
            "/webhook/whatsapp",
            json=ACTIVE_TENANT_PAYLOAD,
            headers={"X-Zapi-Token": VALID_TOKEN},
        )

    # HTTP 200 deve ser retornado independente do resultado do agente
    assert response.status_code == 200
    assert response.json() == {"received": True}
