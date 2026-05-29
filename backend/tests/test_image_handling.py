"""
Testes de tratamento de imagens (Story 3.5, AC 2, 3, 4, 9).

Cenários cobertos:
- Imagem persistida com media_url ao receber imageMessage
- process_message chamado com bloco image correto (mock da SDK)
- image_url passada via URL (sem download local)
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# AC 2 — image_url persistida em messages.media_url
# ---------------------------------------------------------------------------


def test_image_message_persisted_with_media_url():
    """imageMessage deve ser persistido em messages com media_url preenchido."""
    from services.webhook_service import _persist_inbound_message

    mock_supabase = MagicMock()
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "msg-uuid"}
    ]

    with (
        patch("services.webhook_service.get_client", return_value=mock_supabase),
        patch("services.webhook_service.set_tenant_context"),
    ):
        _persist_inbound_message(
            "tenant-uuid",
            "5511999999999",
            "",
            media_url="https://media.z-api.io/img/abc123.jpg",
        )

    insert_call = mock_supabase.table.return_value.insert.call_args
    assert insert_call is not None
    payload = insert_call[0][0]
    assert payload["media_url"] == "https://media.z-api.io/img/abc123.jpg"


def test_text_message_persisted_without_media_url():
    """Mensagem de texto deve ser persistida com media_url=None."""
    from services.webhook_service import _persist_inbound_message

    mock_supabase = MagicMock()
    mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "msg-uuid"}
    ]

    with (
        patch("services.webhook_service.get_client", return_value=mock_supabase),
        patch("services.webhook_service.set_tenant_context"),
    ):
        _persist_inbound_message("tenant-uuid", "5511999999999", "Olá")

    insert_call = mock_supabase.table.return_value.insert.call_args
    payload = insert_call[0][0]
    assert payload.get("media_url") is None


# ---------------------------------------------------------------------------
# AC 3, AC 4 — process_message com image_url envia bloco image via URL ao Claude
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_message_sends_image_block_to_claude():
    """process_message com image_url deve incluir bloco image no payload ao Claude."""
    from services.agent_service import process_message

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Resposta do Claude")]

    mock_create = AsyncMock(return_value=mock_response)

    with patch("services.agent_service.AsyncAnthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_client.messages.create = mock_create
        mock_anthropic.return_value = mock_client

        await process_message(
            tenant_id="tenant-001",
            tenant_name="Marmoraria",
            phone="5511999999999",
            text="O que acha desta pedra?",
            image_url="https://media.z-api.io/img/abc123.jpg",
            model="claude-sonnet-4-6",
        )

    assert mock_create.called
    call_kwargs = mock_create.call_args[1]
    messages = call_kwargs["messages"]
    assert call_kwargs["model"] == "claude-sonnet-4-6"

    # A mensagem do usuário deve ter content como lista com bloco text + bloco image
    user_message = messages[-1]
    assert user_message["role"] == "user"
    assert isinstance(user_message["content"], list)

    content_types = [block["type"] for block in user_message["content"]]
    assert "text" in content_types
    assert "image" in content_types

    image_block = next(b for b in user_message["content"] if b["type"] == "image")
    assert image_block["source"]["type"] == "url"
    assert image_block["source"]["url"] == "https://media.z-api.io/img/abc123.jpg"


@pytest.mark.asyncio
async def test_process_message_text_only_uses_string_content():
    """process_message sem image_url deve enviar mensagem como string simples."""
    from services.agent_service import process_message

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Resposta")]

    mock_create = AsyncMock(return_value=mock_response)

    with patch("services.agent_service.AsyncAnthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_client.messages.create = mock_create
        mock_anthropic.return_value = mock_client

        await process_message(
            tenant_id="tenant-001",
            tenant_name="Marmoraria",
            phone="5511999999999",
            text="Quero um orçamento",
        )

    call_kwargs = mock_create.call_args[1]
    messages = call_kwargs["messages"]
    user_message = messages[-1]
    # Sem imagem: content deve ser string direta
    assert isinstance(user_message["content"], str)
    assert user_message["content"] == "Quero um orçamento"


@pytest.mark.asyncio
async def test_process_message_uses_specified_model():
    """process_message deve usar o model passado como parâmetro."""
    from services.agent_service import process_message

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="ok")]

    mock_create = AsyncMock(return_value=mock_response)

    with patch("services.agent_service.AsyncAnthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_client.messages.create = mock_create
        mock_anthropic.return_value = mock_client

        await process_message(
            tenant_id="tenant-001",
            tenant_name="Marmoraria",
            phone="5511999999999",
            text="texto",
            model="claude-sonnet-4-6",
        )

    call_kwargs = mock_create.call_args[1]
    assert call_kwargs["model"] == "claude-sonnet-4-6"


@pytest.mark.asyncio
async def test_process_message_default_model_is_haiku():
    """process_message sem model explícito deve usar Haiku."""
    from services.agent_service import process_message

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="ok")]

    mock_create = AsyncMock(return_value=mock_response)

    with patch("services.agent_service.AsyncAnthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_client.messages.create = mock_create
        mock_anthropic.return_value = mock_client

        await process_message(
            tenant_id="tenant-001",
            tenant_name="Marmoraria",
            phone="5511999999999",
            text="texto",
        )

    call_kwargs = mock_create.call_args[1]
    assert call_kwargs["model"] == "claude-haiku-4-5-20251001"
