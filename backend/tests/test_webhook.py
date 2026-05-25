"""
Testes para o endpoint POST /webhook/whatsapp (Story 2.2).

Cenários cobertos:
- Token ausente → 401
- Token incorreto → 401
- Payload inválido (não ReceivedCallback) → 200
- Mensagem sem text.message → 200
- Mensagem válida com tenant encontrado → 200 + persistência no banco
- Tenant não encontrado → 200 sem persistir
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


VALID_TOKEN = "test-zapi-token"

VALID_PAYLOAD = {
    "instanceId": "instance-abc",
    "type": "ReceivedCallback",
    "phone": "5511999999999",
    "text": {"message": "Olá, quero um orçamento"},
    "momment": 1234567890,
}


def _make_app() -> FastAPI:
    """Cria app FastAPI isolada com apenas o router de webhook."""
    from routers.webhook import router

    app = FastAPI()
    app.include_router(router)
    return app


def _make_client_with_token(token: str = VALID_TOKEN) -> TestClient:
    """Cria TestClient com o token esperado mockado."""
    app = _make_app()
    with patch("routers.webhook._get_expected_token", return_value=token):
        return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# AC 2 — Token ausente retorna 401
# ---------------------------------------------------------------------------


def test_webhook_returns_401_when_token_is_missing():
    """POST /webhook/whatsapp sem header X-Zapi-Token deve retornar HTTP 401."""
    with patch("routers.webhook._get_expected_token", return_value=VALID_TOKEN):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        response = client.post("/webhook/whatsapp", json=VALID_PAYLOAD)
    assert response.status_code == 401


def test_webhook_returns_401_when_token_is_wrong():
    """POST /webhook/whatsapp com token incorreto deve retornar HTTP 401."""
    with patch("routers.webhook._get_expected_token", return_value=VALID_TOKEN):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        response = client.post(
            "/webhook/whatsapp",
            json=VALID_PAYLOAD,
            headers={"X-Zapi-Token": "wrong-token"},
        )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# AC 3 — Payload inválido retorna 200 silenciosamente
# ---------------------------------------------------------------------------


def test_webhook_returns_200_for_non_text_payload():
    """POST /webhook/whatsapp com type diferente de ReceivedCallback deve retornar 200."""
    with patch("routers.webhook._get_expected_token", return_value=VALID_TOKEN):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        response = client.post(
            "/webhook/whatsapp",
            json={"instanceId": "x", "type": "SomeOtherEvent", "phone": "55119"},
            headers={"X-Zapi-Token": VALID_TOKEN},
        )
    assert response.status_code == 200
    assert response.json() == {"received": True}


def test_webhook_returns_200_for_payload_without_text_message():
    """POST /webhook/whatsapp sem campo text.message deve retornar 200 sem persistir."""
    with patch("routers.webhook._get_expected_token", return_value=VALID_TOKEN):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        response = client.post(
            "/webhook/whatsapp",
            json={"instanceId": "x", "type": "ReceivedCallback", "phone": "55119"},
            headers={"X-Zapi-Token": VALID_TOKEN},
        )
    assert response.status_code == 200
    assert response.json() == {"received": True}


# ---------------------------------------------------------------------------
# AC 4 — Tenant não encontrado: 200 sem persistir
# ---------------------------------------------------------------------------


def test_webhook_returns_200_when_tenant_not_found():
    """POST /webhook/whatsapp com instanceId sem tenant deve retornar 200 sem persistir."""
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    with patch("routers.webhook._get_expected_token", return_value=VALID_TOKEN), patch(
        "services.webhook_service.get_client", return_value=mock_supabase
    ):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        response = client.post(
            "/webhook/whatsapp",
            json=VALID_PAYLOAD,
            headers={"X-Zapi-Token": VALID_TOKEN},
        )

    assert response.status_code == 200
    assert response.json() == {"received": True}

    # Não deve ter inserido nada em messages
    insert_calls = [
        call
        for call in mock_supabase.table.call_args_list
        if call.args and call.args[0] == "messages"
    ]
    assert len(insert_calls) == 0


# ---------------------------------------------------------------------------
# AC 1 + AC 5 — Mensagem válida com tenant: 200 + persistência
# ---------------------------------------------------------------------------


def test_webhook_returns_200_and_persists_message_when_tenant_found():
    """POST /webhook/whatsapp com payload válido e tenant existente deve retornar 200 e persistir."""
    tenant_id = "tenant-uuid-123"
    mock_supabase = MagicMock()

    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": tenant_id, "zapi_instance_id": "instance-abc", "status": "onboarding"}
    ]
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "msg-uuid-456"}
    ]

    with patch("routers.webhook._get_expected_token", return_value=VALID_TOKEN), patch(
        "services.webhook_service.get_client", return_value=mock_supabase
    ):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        response = client.post(
            "/webhook/whatsapp",
            json=VALID_PAYLOAD,
            headers={"X-Zapi-Token": VALID_TOKEN},
        )

    assert response.status_code == 200
    assert response.json() == {"received": True}

    # Confirma que insert foi chamado na tabela messages
    messages_insert_called = any(
        call.args and call.args[0] == "messages"
        for call in mock_supabase.table.call_args_list
    )
    assert messages_insert_called

    # Confirma campos obrigatórios no insert
    insert_call = mock_supabase.table.return_value.insert.call_args
    inserted_data = insert_call.args[0]
    assert inserted_data["tenant_id"] == tenant_id
    assert inserted_data["direction"] == "inbound"
    assert inserted_data["lead_id"] is None
