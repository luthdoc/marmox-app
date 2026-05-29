"""
Testes de integração para o despacho de mensagens via webhook (Story 2.4 → 3.1).

Cenários cobertos:
- Tenant ativo: send_message é chamado com a resposta do agente Claude
- Tenant em onboarding: send_message NÃO é chamado
- Falha no envio não afeta resposta HTTP 200 (fire-and-forget)
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
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


def test_active_tenant_webhook_schedules_agent_dispatch():
    """Tenant ativo deve agendar _dispatch_agent ao receber mensagem pelo webhook.

    O dispatch é fire-and-forget — este teste verifica que a task é criada
    com os parâmetros corretos. O comportamento de send_message dentro de
    _dispatch_agent é coberto pelos testes de test_agent_history.py.
    """
    tenant_id = "tenant-active-001"
    tenant_name = "Marmoraria Teste"
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
            side_effect=lambda *args, **kwargs: dispatched_calls.append((args, kwargs)) or None,
        ),
    ):
        with TestClient(_make_app(), raise_server_exceptions=False) as client:
            response = client.post(
                "/webhook/whatsapp",
                json=ACTIVE_TENANT_PAYLOAD,
                headers={"X-Zapi-Token": VALID_TOKEN},
            )

    assert response.status_code == 200
    assert len(dispatched_calls) == 1
    args, kwargs = dispatched_calls[0]
    assert args[0] == tenant_id
    assert args[2] == ACTIVE_TENANT_PAYLOAD["phone"]
    assert kwargs.get("text") == ACTIVE_TENANT_PAYLOAD["text"]["message"]


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
        patch("services.webhook_service.load_conversation_history", return_value=[]),
        patch("services.webhook_service.persist_outbound_message"),
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
        patch("services.webhook_service.load_conversation_history", return_value=[]),
        patch("services.webhook_service.persist_outbound_message"),
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
