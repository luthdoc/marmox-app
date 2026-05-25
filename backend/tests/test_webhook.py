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
from unittest.mock import AsyncMock, MagicMock, patch

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
# AC 1 — Mensagem válida com tenant encontrado retorna 200
# ---------------------------------------------------------------------------


def test_webhook_returns_200_when_tenant_found():
    """POST /webhook/whatsapp com payload válido e tenant existente deve retornar 200."""
    tenant_id = "tenant-uuid-123"
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": tenant_id, "zapi_instance_id": "instance-abc", "status": "onboarding"}
    ]
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "msg-uuid-456"}
    ]

    with (
        patch("routers.webhook._get_expected_token", return_value=VALID_TOKEN),
        patch("services.webhook_service.get_client", return_value=mock_supabase),
        patch("services.webhook_service.set_tenant_context"),
    ):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        response = client.post(
            "/webhook/whatsapp",
            json=VALID_PAYLOAD,
            headers={"X-Zapi-Token": VALID_TOKEN},
        )

    assert response.status_code == 200
    assert response.json() == {"received": True}


# ---------------------------------------------------------------------------
# AC 5 — Mensagem válida com tenant encontrado persiste campos corretos
# ---------------------------------------------------------------------------


def test_webhook_persists_message_with_correct_fields_when_tenant_found():
    """POST /webhook/whatsapp com tenant existente deve inserir mensagem com campos obrigatórios."""
    tenant_id = "tenant-uuid-123"
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": tenant_id, "zapi_instance_id": "instance-abc", "status": "onboarding"}
    ]
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "msg-uuid-456"}
    ]

    with (
        patch("routers.webhook._get_expected_token", return_value=VALID_TOKEN),
        patch("services.webhook_service.get_client", return_value=mock_supabase),
        patch("services.webhook_service.set_tenant_context"),
    ):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        client.post(
            "/webhook/whatsapp",
            json=VALID_PAYLOAD,
            headers={"X-Zapi-Token": VALID_TOKEN},
        )

    messages_insert_called = any(
        call.args and call.args[0] == "messages"
        for call in mock_supabase.table.call_args_list
    )
    assert messages_insert_called

    insert_call = mock_supabase.table.return_value.insert.call_args
    inserted_data = insert_call.args[0]
    assert inserted_data["tenant_id"] == tenant_id
    assert inserted_data["direction"] == "inbound"
    assert inserted_data["lead_id"] is None


# ---------------------------------------------------------------------------
# NFR3 — set_tenant_context é chamado antes de persistir mensagem inbound
# ---------------------------------------------------------------------------


def test_set_tenant_context_called_before_persisting_inbound_message():
    """set_tenant_context deve ser chamado com o tenant_id correto antes de inserir em messages."""
    tenant_id = "tenant-uuid-rls"
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": tenant_id, "status": "onboarding"}
    ]
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "msg-uuid-rls"}
    ]

    with (
        patch("routers.webhook._get_expected_token", return_value=VALID_TOKEN),
        patch("services.webhook_service.get_client", return_value=mock_supabase),
        patch("services.webhook_service.set_tenant_context") as mock_set_ctx,
    ):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        client.post(
            "/webhook/whatsapp",
            json=VALID_PAYLOAD,
            headers={"X-Zapi-Token": VALID_TOKEN},
        )

    mock_set_ctx.assert_called_once_with(tenant_id)


# ---------------------------------------------------------------------------
# S2 — Phone com formato inválido: retorna 200, não persiste, não gera echo
# ---------------------------------------------------------------------------

_INVALID_PHONE_PAYLOAD = {
    "instanceId": "instance-abc",
    "type": "ReceivedCallback",
    "phone": "55-11-9999",  # formato inválido: contém hífens
    "text": {"message": "Olá"},
    "momment": 1234567890,
}


def _make_supabase_with_active_tenant(tenant_id: str) -> MagicMock:
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": tenant_id, "status": "active"}
    ]
    return mock_supabase


def test_webhook_returns_200_for_invalid_phone_format():
    """Webhook deve retornar 200 mesmo quando o phone tem formato inválido."""
    mock_supabase = _make_supabase_with_active_tenant("tenant-uuid-s2")

    with (
        patch("routers.webhook._get_expected_token", return_value=VALID_TOKEN),
        patch("services.webhook_service.get_client", return_value=mock_supabase),
        patch("services.webhook_service.set_tenant_context"),
        patch("services.webhook_service.send_message", new_callable=AsyncMock),
    ):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        response = client.post(
            "/webhook/whatsapp",
            json=_INVALID_PHONE_PAYLOAD,
            headers={"X-Zapi-Token": VALID_TOKEN},
        )

    assert response.status_code == 200
    assert response.json() == {"received": True}


def test_invalid_phone_format_is_not_persisted():
    """Mensagem com phone em formato inválido não deve ser inserida em messages."""
    mock_supabase = _make_supabase_with_active_tenant("tenant-uuid-s2")

    with (
        patch("routers.webhook._get_expected_token", return_value=VALID_TOKEN),
        patch("services.webhook_service.get_client", return_value=mock_supabase),
        patch("services.webhook_service.set_tenant_context"),
        patch("services.webhook_service.send_message", new_callable=AsyncMock),
    ):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        client.post(
            "/webhook/whatsapp",
            json=_INVALID_PHONE_PAYLOAD,
            headers={"X-Zapi-Token": VALID_TOKEN},
        )

    insert_calls = [
        call for call in mock_supabase.table.call_args_list
        if call.args and call.args[0] == "messages"
    ]
    assert len(insert_calls) == 0


def test_invalid_phone_format_does_not_trigger_echo():
    """Mensagem com phone em formato inválido não deve chamar send_message."""
    mock_supabase = _make_supabase_with_active_tenant("tenant-uuid-s2")

    with (
        patch("routers.webhook._get_expected_token", return_value=VALID_TOKEN),
        patch("services.webhook_service.get_client", return_value=mock_supabase),
        patch("services.webhook_service.set_tenant_context"),
        patch("services.webhook_service.send_message", new_callable=AsyncMock) as mock_send,
    ):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        client.post(
            "/webhook/whatsapp",
            json=_INVALID_PHONE_PAYLOAD,
            headers={"X-Zapi-Token": VALID_TOKEN},
        )

    mock_send.assert_not_called()
