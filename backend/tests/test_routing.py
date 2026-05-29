"""
Testes de roteamento Haiku→Sonnet (Story 3.5, AC 5, 6, 7, 8).

Cenários cobertos:
- Payload com imageMessage → process_message chamado com image_url e model=Sonnet
- Texto com palavra de reclamação → model=Sonnet
- Texto simples → model=Haiku (default)
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient


VALID_TOKEN = "test-zapi-token"

IMAGE_PAYLOAD = {
    "instanceId": "instance-active",
    "type": "ReceivedCallback",
    "phone": "5511999999999",
    "imageMessage": {"url": "https://media.z-api.io/img/abc123.jpg", "caption": ""},
    "momment": 1234567890,
}

COMPLAINT_PAYLOAD = {
    "instanceId": "instance-active",
    "type": "ReceivedCallback",
    "phone": "5511999999999",
    "text": {"message": "Estou com problema no pedido"},
    "momment": 1234567890,
}

SIMPLE_PAYLOAD = {
    "instanceId": "instance-active",
    "type": "ReceivedCallback",
    "phone": "5511999999999",
    "text": {"message": "Quero um orçamento"},
    "momment": 1234567890,
}

TENANT_ACTIVE = {"id": "tenant-routing-001", "status": "active", "name": "Marmoraria Teste"}


def _make_app() -> FastAPI:
    from routers.webhook import router
    app = FastAPI()
    app.include_router(router)
    return app


def _make_supabase_mock(tenant: dict = TENANT_ACTIVE) -> MagicMock:
    mock = MagicMock()
    mock.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [tenant]
    mock.table.return_value.insert.return_value.execute.return_value.data = [{"id": "msg-uuid"}]
    return mock


# ---------------------------------------------------------------------------
# AC 8 — imageMessage → process_message chamado com image_url e model=Sonnet
# ---------------------------------------------------------------------------


def test_image_message_routes_to_sonnet():
    """Payload com imageMessage deve chamar process_message com model=Sonnet e image_url."""
    mock_supabase = _make_supabase_mock()
    dispatched: list = []

    async def fake_dispatch(tenant_id, tenant_name, phone, text, image_url=None):
        dispatched.append({"tenant_id": tenant_id, "image_url": image_url})

    with (
        patch("routers.webhook._get_expected_token", return_value=VALID_TOKEN),
        patch("services.webhook_service.get_client", return_value=mock_supabase),
        patch("services.webhook_service.set_tenant_context"),
        patch("services.webhook_service._dispatch_agent", side_effect=fake_dispatch),
    ):
        with TestClient(_make_app(), raise_server_exceptions=False) as client:
            client.post(
                "/webhook/whatsapp",
                json=IMAGE_PAYLOAD,
                headers={"X-Zapi-Token": VALID_TOKEN},
            )

    assert len(dispatched) == 1
    assert dispatched[0]["image_url"] == "https://media.z-api.io/img/abc123.jpg"


def test_image_message_process_message_uses_sonnet():
    """Quando image_url presente, process_message deve receber model='claude-sonnet-4-6'."""
    process_calls: list = []

    async def fake_process_message(**kwargs):
        process_calls.append(kwargs)
        return "Resposta do Sonnet [DADOS_LEAD]\n{}\n[/DADOS_LEAD]"

    mock_supabase = _make_supabase_mock()
    lead = {"id": "lead-uuid", "status": "new"}
    context = {}
    history = []

    with (
        patch("services.webhook_service.get_or_create_lead", return_value=lead),
        patch("services.webhook_service.get_tenant_context", return_value=context),
        patch("services.webhook_service.load_conversation_history", return_value=history),
        patch("services.webhook_service.process_message", side_effect=fake_process_message),
        patch("services.webhook_service.send_message", new_callable=AsyncMock),
        patch("services.webhook_service.persist_outbound_message"),
        patch("services.webhook_service.update_lead_qualification"),
        patch("services.webhook_service.set_tenant_context"),
    ):
        asyncio.run(
            _run_dispatch_agent_with_image(
                "tenant-001",
                "Marmoraria",
                "5511999999999",
                "https://media.z-api.io/img/abc123.jpg",
            )
        )

    assert len(process_calls) == 1
    assert process_calls[0]["model"] == "claude-sonnet-4-6"
    assert process_calls[0]["image_url"] == "https://media.z-api.io/img/abc123.jpg"


async def _run_dispatch_agent_with_image(tenant_id, tenant_name, phone, image_url):
    from services.webhook_service import _dispatch_agent
    await _dispatch_agent(tenant_id, tenant_name, phone, image_url=image_url)


# ---------------------------------------------------------------------------
# AC 5 / AC 8 — texto com palavra de reclamação → model=Sonnet
# ---------------------------------------------------------------------------


def test_complaint_text_routes_to_sonnet():
    """Texto com palavra de reclamação deve chamar process_message com model=Sonnet."""
    process_calls: list = []

    async def fake_process_message(**kwargs):
        process_calls.append(kwargs)
        return "ok [DADOS_LEAD]\n{}\n[/DADOS_LEAD]"

    lead = {"id": "lead-uuid", "status": "new"}

    with (
        patch("services.webhook_service.get_or_create_lead", return_value=lead),
        patch("services.webhook_service.get_tenant_context", return_value={}),
        patch("services.webhook_service.load_conversation_history", return_value=[]),
        patch("services.webhook_service.process_message", side_effect=fake_process_message),
        patch("services.webhook_service.send_message", new_callable=AsyncMock),
        patch("services.webhook_service.persist_outbound_message"),
        patch("services.webhook_service.update_lead_qualification"),
        patch("services.webhook_service.set_tenant_context"),
    ):
        asyncio.run(
            _run_dispatch_agent_text(
                "tenant-001",
                "Marmoraria",
                "5511999999999",
                "Estou com problema no meu pedido",
            )
        )

    assert len(process_calls) == 1
    assert process_calls[0]["model"] == "claude-sonnet-4-6"


def test_simple_text_routes_to_haiku():
    """Texto simples sem indicadores de complexidade deve usar model=Haiku."""
    process_calls: list = []

    async def fake_process_message(**kwargs):
        process_calls.append(kwargs)
        return "ok [DADOS_LEAD]\n{}\n[/DADOS_LEAD]"

    lead = {"id": "lead-uuid", "status": "new"}

    with (
        patch("services.webhook_service.get_or_create_lead", return_value=lead),
        patch("services.webhook_service.get_tenant_context", return_value={}),
        patch("services.webhook_service.load_conversation_history", return_value=[]),
        patch("services.webhook_service.process_message", side_effect=fake_process_message),
        patch("services.webhook_service.send_message", new_callable=AsyncMock),
        patch("services.webhook_service.persist_outbound_message"),
        patch("services.webhook_service.update_lead_qualification"),
        patch("services.webhook_service.set_tenant_context"),
    ):
        asyncio.run(
            _run_dispatch_agent_text(
                "tenant-001",
                "Marmoraria",
                "5511999999999",
                "Quero um orçamento de granito preto",
            )
        )

    assert len(process_calls) == 1
    assert process_calls[0]["model"] == "claude-haiku-4-5-20251001"


async def _run_dispatch_agent_text(tenant_id, tenant_name, phone, text):
    from services.webhook_service import _dispatch_agent
    await _dispatch_agent(tenant_id, tenant_name, phone, text=text)


# ---------------------------------------------------------------------------
# AC 7 — Schema reconhece imageMessage
# ---------------------------------------------------------------------------


def test_schema_recognizes_image_message():
    """ZApiWebhookPayload deve expor is_image_message=True para payload com imageMessage."""
    from schemas.webhook import ZApiWebhookPayload

    payload = ZApiWebhookPayload(
        instanceId="inst-1",
        type="ReceivedCallback",
        phone="5511999999999",
        imageMessage={"url": "https://example.com/img.jpg", "caption": "foto"},
    )
    assert payload.is_image_message is True
    assert payload.image_url == "https://example.com/img.jpg"


def test_schema_image_url_none_when_no_image():
    """ZApiWebhookPayload deve expor image_url=None para mensagens de texto."""
    from schemas.webhook import ZApiWebhookPayload

    payload = ZApiWebhookPayload(
        instanceId="inst-1",
        type="ReceivedCallback",
        phone="5511999999999",
        text={"message": "olá"},
    )
    assert payload.is_image_message is False
    assert payload.image_url is None


def test_schema_is_image_message_false_for_text():
    """ZApiWebhookPayload.is_image_message deve ser False para mensagens de texto."""
    from schemas.webhook import ZApiWebhookPayload

    payload = ZApiWebhookPayload(
        instanceId="inst-1",
        type="ReceivedCallback",
        phone="5511999999999",
        text={"message": "Quero um orçamento"},
    )
    assert payload.is_image_message is False
