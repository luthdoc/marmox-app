"""
Testes para os endpoints GET e POST /webhook/whatsapp — Meta WhatsApp Cloud API.

Cenários cobertos:
- GET: verify_token correto → retorna hub.challenge
- GET: verify_token errado → 403
- POST: payload sem mensagem válida → 200 silencioso
- POST: mensagem válida com tenant encontrado → 200 + persistência
- POST: tenant não encontrado → 200 sem persistir
- POST: phone com formato inválido → 200 sem persistir
"""
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

VALID_VERIFY_TOKEN = "marmax-webhook-test"
VALID_PHONE_NUMBER_ID = "1220170564507810"
VALID_TENANT_ID = "tenant-uuid-123"
VALID_PHONE = "5511999999999"
VALID_MESSAGE = "Olá, quero um orçamento"

VALID_META_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [{
        "id": "WABA123",
        "changes": [{
            "value": {
                "messaging_product": "whatsapp",
                "metadata": {
                    "display_phone_number": "15550000000",
                    "phone_number_id": VALID_PHONE_NUMBER_ID,
                },
                "contacts": [{"profile": {"name": "Test User"}, "wa_id": VALID_PHONE}],
                "messages": [{
                    "from": VALID_PHONE,
                    "id": "wamid.123",
                    "timestamp": "1234567890",
                    "type": "text",
                    "text": {"body": VALID_MESSAGE},
                }],
            },
            "field": "messages",
        }],
    }],
}


def _make_app() -> FastAPI:
    from routers.webhook import router
    app = FastAPI()
    app.include_router(router)
    return app


def _mock_settings(verify_token: str = VALID_VERIFY_TOKEN):
    settings = MagicMock()
    settings.meta_whatsapp_verify_token = verify_token
    return settings


# ---------------------------------------------------------------------------
# GET — verificação do webhook
# ---------------------------------------------------------------------------


def test_get_webhook_returns_challenge_when_verify_token_correct():
    """GET /webhook/whatsapp com verify_token correto deve retornar hub.challenge."""
    with patch("routers.webhook._get_settings", return_value=_mock_settings()):
        client = TestClient(_make_app())
        response = client.get(
            "/webhook/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": VALID_VERIFY_TOKEN,
                "hub.challenge": "challenge-abc123",
            },
        )
    assert response.status_code == 200
    assert response.text == "challenge-abc123"


def test_get_webhook_returns_403_when_verify_token_wrong():
    """GET /webhook/whatsapp com verify_token errado deve retornar 403."""
    with patch("routers.webhook._get_settings", return_value=_mock_settings()):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        response = client.get(
            "/webhook/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong-token",
                "hub.challenge": "challenge-abc123",
            },
        )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# POST — payload sem mensagem válida retorna 200
# ---------------------------------------------------------------------------


def test_post_webhook_returns_200_for_status_update():
    """POST com evento de status (sem messages) deve retornar 200."""
    status_payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "WABA123",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "15550000000", "phone_number_id": VALID_PHONE_NUMBER_ID},
                    "statuses": [{"id": "wamid.123", "status": "delivered"}],
                },
                "field": "messages",
            }],
        }],
    }
    client = TestClient(_make_app())
    response = client.post("/webhook/whatsapp", json=status_payload)
    assert response.status_code == 200
    assert response.json() == {"received": True}


# ---------------------------------------------------------------------------
# POST — tenant não encontrado
# ---------------------------------------------------------------------------


def test_post_webhook_returns_200_when_tenant_not_found():
    """POST com phone_number_id sem tenant correspondente deve retornar 200."""
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    with patch("services.webhook_service.get_client", return_value=mock_supabase):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        response = client.post("/webhook/whatsapp", json=VALID_META_PAYLOAD)

    assert response.status_code == 200
    assert response.json() == {"received": True}


def test_post_webhook_does_not_persist_when_tenant_not_found():
    """POST com tenant não encontrado não deve inserir em messages."""
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    with patch("services.webhook_service.get_client", return_value=mock_supabase):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        client.post("/webhook/whatsapp", json=VALID_META_PAYLOAD)

    insert_calls = [
        c for c in mock_supabase.table.call_args_list
        if c.args and c.args[0] == "messages"
    ]
    assert len(insert_calls) == 0


# ---------------------------------------------------------------------------
# POST — mensagem válida com tenant encontrado
# ---------------------------------------------------------------------------


def _make_tenant_supabase(tenant_id: str = VALID_TENANT_ID, status: str = "onboarding"):
    mock = MagicMock()
    mock.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": tenant_id, "status": status, "name": "Marmoraria João"}
    ]
    mock.table.return_value.insert.return_value.execute.return_value.data = [{"id": "msg-uuid-456"}]
    return mock


def test_post_webhook_returns_200_when_tenant_found():
    """POST com payload válido e tenant existente deve retornar 200."""
    mock_supabase = _make_tenant_supabase()

    with (
        patch("services.webhook_service.get_client", return_value=mock_supabase),
        patch("services.webhook_service.set_tenant_context"),
    ):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        response = client.post("/webhook/whatsapp", json=VALID_META_PAYLOAD)

    assert response.status_code == 200
    assert response.json() == {"received": True}


def _post_and_capture_persist():
    """Dispara POST e captura os argumentos de _persist_inbound_message."""
    import threading

    captured: list = []
    event = threading.Event()

    def capture(tenant_id: str, phone: str, content: str, media_url=None) -> None:
        captured.append({"tenant_id": tenant_id, "phone": phone, "content": content})
        event.set()

    mock_supabase = _make_tenant_supabase()

    with (
        patch("services.webhook_service.get_client", return_value=mock_supabase),
        patch("services.webhook_service.set_tenant_context"),
        patch("services.webhook_service._persist_inbound_message", side_effect=capture),
        patch("services.webhook_service.dispatch_agent", new_callable=AsyncMock),
    ):
        with TestClient(_make_app(), raise_server_exceptions=False) as client:
            client.post("/webhook/whatsapp", json=VALID_META_PAYLOAD)
            event.wait(timeout=3.0)

    return captured


def test_post_webhook_persists_message_when_tenant_found():
    """POST com tenant existente deve chamar _persist_inbound_message."""
    calls = _post_and_capture_persist()
    assert len(calls) == 1


def test_post_webhook_persists_correct_tenant_id():
    """POST deve passar tenant_id correto a _persist_inbound_message."""
    calls = _post_and_capture_persist()
    assert calls[0]["tenant_id"] == VALID_TENANT_ID


def test_post_webhook_persists_correct_phone():
    """POST deve passar phone correto a _persist_inbound_message."""
    calls = _post_and_capture_persist()
    assert calls[0]["phone"] == VALID_PHONE


def test_post_webhook_persists_correct_content():
    """POST deve passar content correto a _persist_inbound_message."""
    calls = _post_and_capture_persist()
    assert calls[0]["content"] == VALID_MESSAGE


# ---------------------------------------------------------------------------
# POST — phone com formato inválido
# ---------------------------------------------------------------------------

_INVALID_PHONE_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [{
        "id": "WABA123",
        "changes": [{
            "value": {
                "messaging_product": "whatsapp",
                "metadata": {"display_phone_number": "15550000000", "phone_number_id": VALID_PHONE_NUMBER_ID},
                "messages": [{
                    "from": "55-11-9999",
                    "id": "wamid.456",
                    "timestamp": "1234567890",
                    "type": "text",
                    "text": {"body": "Olá"},
                }],
            },
            "field": "messages",
        }],
    }],
}


def test_post_webhook_returns_200_for_invalid_phone():
    """POST com phone inválido deve retornar 200."""
    mock_supabase = _make_tenant_supabase(status="active")

    with (
        patch("services.webhook_service.get_client", return_value=mock_supabase),
        patch("services.webhook_service.set_tenant_context"),
        patch("services.webhook_service.dispatch_agent", new_callable=AsyncMock),
    ):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        response = client.post("/webhook/whatsapp", json=_INVALID_PHONE_PAYLOAD)

    assert response.status_code == 200


def test_post_webhook_does_not_persist_invalid_phone():
    """POST com phone inválido não deve inserir em messages."""
    mock_supabase = _make_tenant_supabase(status="active")

    with (
        patch("services.webhook_service.get_client", return_value=mock_supabase),
        patch("services.webhook_service.set_tenant_context"),
        patch("services.webhook_service.dispatch_agent", new_callable=AsyncMock),
    ):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        client.post("/webhook/whatsapp", json=_INVALID_PHONE_PAYLOAD)

    insert_calls = [
        c for c in mock_supabase.table.call_args_list
        if c.args and c.args[0] == "messages"
    ]
    assert len(insert_calls) == 0
