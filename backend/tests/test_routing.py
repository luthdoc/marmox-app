"""
Testes de roteamento Haiku→Sonnet (Story 3.5, AC 5, 6, 7, 8).

Cenários cobertos:
- Payload com imageMessage → dispatch_agent chamado com image_url e model=Sonnet
- Texto com palavra de reclamação → model=Sonnet
- Texto simples → model=Haiku (default)
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


VALID_PHONE_NUMBER_ID = "1220170564507810"
TENANT_ID = "tenant-routing-001"
PHONE = "5511999999999"
IMAGE_URL = "img_media_id_abc123"

IMAGE_PAYLOAD = {
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
                "messages": [{
                    "from": PHONE,
                    "id": "wamid.img001",
                    "timestamp": "1234567890",
                    "type": "image",
                    "image": {"id": IMAGE_URL, "caption": ""},
                }],
            },
            "field": "messages",
        }],
    }],
}

TENANT_ACTIVE = {"id": TENANT_ID, "status": "active", "name": "Marmoraria Teste"}


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
# AC 8 — imageMessage → dispatch_agent chamado com image_url
# ---------------------------------------------------------------------------


def test_image_message_routes_to_sonnet():
    """Payload com imageMessage deve chamar dispatch_agent com image_url."""
    import threading

    mock_supabase = _make_supabase_mock()
    dispatched: list = []
    dispatch_event = threading.Event()

    async def fake_dispatch(tenant_id, tenant_name, phone, text, image_url=None):
        dispatched.append({"tenant_id": tenant_id, "image_url": image_url})
        dispatch_event.set()

    with (
        patch("services.webhook_service.get_client", return_value=mock_supabase),
        patch("services.webhook_service.set_tenant_context"),
        patch("services.webhook_service.dispatch_agent", side_effect=fake_dispatch),
    ):
        with TestClient(_make_app(), raise_server_exceptions=False) as client:
            client.post(
                "/webhook/whatsapp",
                json=IMAGE_PAYLOAD,
            )
            dispatch_event.wait(timeout=3.0)

    assert len(dispatched) == 1
    assert dispatched[0]["image_url"] == IMAGE_URL


def test_image_message_process_message_uses_sonnet():
    """Quando image_url presente, process_message deve receber model='claude-sonnet-4-6'."""
    process_calls: list = []

    async def fake_process_message(**kwargs):
        process_calls.append(kwargs)
        return "Resposta do Sonnet [DADOS_LEAD]\n{}\n[/DADOS_LEAD]"

    lead = {"id": "lead-uuid", "status": "new"}
    context = {}
    history = []

    with (
        patch("services.agent_dispatch.get_or_create_lead", return_value=lead),
        patch("services.agent_dispatch.get_tenant_context", return_value=context),
        patch("services.agent_dispatch.load_conversation_history", return_value=history),
        patch("services.agent_dispatch.process_message", side_effect=fake_process_message),
        patch("services.agent_dispatch.deliver_message", new_callable=AsyncMock, return_value=True),
        patch("services.agent_dispatch.update_lead_qualification"),
    ):
        asyncio.run(
            _run_dispatch_agent_with_image(
                "tenant-001",
                "Marmoraria",
                PHONE,
                IMAGE_URL,
            )
        )

    assert len(process_calls) == 1
    assert process_calls[0]["model"] == "claude-sonnet-4-6"
    assert process_calls[0]["image_url"] == IMAGE_URL


async def _run_dispatch_agent_with_image(tenant_id, tenant_name, phone, image_url):
    from services.agent_dispatch import dispatch_agent
    await dispatch_agent(tenant_id, tenant_name, phone, image_url=image_url)


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
        patch("services.agent_dispatch.get_or_create_lead", return_value=lead),
        patch("services.agent_dispatch.get_tenant_context", return_value={}),
        patch("services.agent_dispatch.load_conversation_history", return_value=[]),
        patch("services.agent_dispatch.process_message", side_effect=fake_process_message),
        patch("services.agent_dispatch.deliver_message", new_callable=AsyncMock, return_value=True),
        patch("services.agent_dispatch.update_lead_qualification"),
    ):
        asyncio.run(
            _run_dispatch_agent_text(
                "tenant-001",
                "Marmoraria",
                PHONE,
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
        patch("services.agent_dispatch.get_or_create_lead", return_value=lead),
        patch("services.agent_dispatch.get_tenant_context", return_value={}),
        patch("services.agent_dispatch.load_conversation_history", return_value=[]),
        patch("services.agent_dispatch.process_message", side_effect=fake_process_message),
        patch("services.agent_dispatch.deliver_message", new_callable=AsyncMock, return_value=True),
        patch("services.agent_dispatch.update_lead_qualification"),
    ):
        asyncio.run(
            _run_dispatch_agent_text(
                "tenant-001",
                "Marmoraria",
                PHONE,
                "Quero um orçamento de granito preto",
            )
        )

    assert len(process_calls) == 1
    assert process_calls[0]["model"] == "claude-haiku-4-5-20251001"


async def _run_dispatch_agent_text(tenant_id, tenant_name, phone, text):
    from services.agent_dispatch import dispatch_agent
    await dispatch_agent(tenant_id, tenant_name, phone, text=text)


# ---------------------------------------------------------------------------
# AC 7 — Schema reconhece imageMessage (MetaMessage)
# ---------------------------------------------------------------------------


def test_schema_recognizes_image_message():
    """MetaMessage deve expor is_image_message=True para payload com type=image."""
    from schemas.webhook import MetaMessage

    msg = MetaMessage.model_validate({
        "from": "5511999999999",
        "id": "wamid.001",
        "timestamp": "1234567890",
        "type": "image",
        "image": {"id": "img_media_id_abc123", "caption": "foto"},
    })
    assert msg.is_image_message is True
    assert msg.image_url == "img_media_id_abc123"


def test_schema_image_url_none_when_no_image():
    """MetaMessage deve expor image_url=None para mensagens de texto."""
    from schemas.webhook import MetaMessage

    msg = MetaMessage.model_validate({
        "from": "5511999999999",
        "id": "wamid.001",
        "timestamp": "1234567890",
        "type": "text",
        "text": {"body": "olá"},
    })
    assert msg.is_image_message is False
    assert msg.image_url is None


def test_schema_is_image_message_false_for_text():
    """MetaMessage.is_image_message deve ser False para mensagens de texto."""
    from schemas.webhook import MetaMessage

    msg = MetaMessage.model_validate({
        "from": "5511999999999",
        "id": "wamid.001",
        "timestamp": "1234567890",
        "type": "text",
        "text": {"body": "Quero um orçamento"},
    })
    assert msg.is_image_message is False
