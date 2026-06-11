"""
Testes de despacho do webhook para o agente — Meta WhatsApp Cloud API.

Cenários cobertos:
- Tenant ativo: dispatch_agent é chamado com parâmetros corretos
- Tenant em onboarding: dispatch_agent NÃO é chamado
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

VALID_PHONE_NUMBER_ID = "1220170564507810"
ACTIVE_TENANT_ID = "tenant-active-001"
ONBOARDING_TENANT_ID = "tenant-onboarding-001"
ACTIVE_PHONE = "5511999999999"
ONBOARDING_PHONE = "5511888888888"
ACTIVE_MESSAGE = "Quero um orçamento de granito"
ONBOARDING_MESSAGE = "Olá"


def _make_meta_payload(phone: str, message: str, phone_number_id: str = VALID_PHONE_NUMBER_ID) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "WABA123",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "15550000000",
                        "phone_number_id": phone_number_id,
                    },
                    "messages": [{
                        "from": phone,
                        "id": "wamid.001",
                        "timestamp": "1234567890",
                        "type": "text",
                        "text": {"body": message},
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


def _make_supabase_mock(tenant_status: str, tenant_id: str, tenant_name: str = "Marmoraria Teste"):
    mock = MagicMock()
    mock.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": tenant_id, "status": tenant_status, "name": tenant_name}
    ]
    mock.table.return_value.insert.return_value.execute.return_value.data = [{"id": "msg-uuid-001"}]
    return mock


# ---------------------------------------------------------------------------
# Tenant ativo: dispatch_agent é chamado
# ---------------------------------------------------------------------------


def test_active_tenant_dispatches_to_agent():
    """Tenant ativo deve agendar dispatch_agent com parâmetros corretos."""
    import threading

    tenant_name = "Marmoraria Silva"
    mock_supabase = _make_supabase_mock("active", ACTIVE_TENANT_ID, tenant_name)
    dispatched: list = []
    event = threading.Event()

    async def capture_dispatch(*a, **kw):
        dispatched.append((a, kw))
        event.set()

    with (
        patch("services.webhook_service.get_client", return_value=mock_supabase),
        patch("services.webhook_service.set_tenant_context"),
        patch("services.webhook_service.dispatch_agent", side_effect=capture_dispatch),
    ):
        with TestClient(_make_app(), raise_server_exceptions=False) as client:
            client.post(
                "/webhook/whatsapp",
                json=_make_meta_payload(ACTIVE_PHONE, ACTIVE_MESSAGE),
            )
            event.wait(timeout=3.0)

    assert len(dispatched) == 1
    args, kwargs = dispatched[0]
    assert args[0] == ACTIVE_TENANT_ID
    assert args[1] == tenant_name
    assert args[2] == ACTIVE_PHONE
    assert kwargs.get("text") == ACTIVE_MESSAGE


# ---------------------------------------------------------------------------
# Tenant em onboarding: dispatch_agent NÃO é chamado
# ---------------------------------------------------------------------------


def test_onboarding_tenant_does_not_dispatch_to_agent():
    """Tenant em onboarding não deve resultar em chamada a dispatch_agent."""
    mock_supabase = _make_supabase_mock("onboarding", ONBOARDING_TENANT_ID)

    with (
        patch("services.webhook_service.get_client", return_value=mock_supabase),
        patch("services.webhook_service.set_tenant_context"),
        patch("services.webhook_service.dispatch_agent", new_callable=AsyncMock) as mock_dispatch,
    ):
        client = TestClient(_make_app(), raise_server_exceptions=False)
        client.post(
            "/webhook/whatsapp",
            json=_make_meta_payload(ONBOARDING_PHONE, ONBOARDING_MESSAGE),
        )

    mock_dispatch.assert_not_called()
