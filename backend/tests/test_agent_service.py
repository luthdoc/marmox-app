"""
Testes para backend/services/agent_service.py (Story 3.1).

Cenários cobertos:
- Claude é chamado com o system prompt contendo o tenant name
- A resposta do Claude é retornada corretamente
- Falha na API do Claude propaga a exceção ao chamador
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# AC 3 + AC 4 — process_message chama Claude com system prompt correto
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_message_calls_claude_with_correct_system_prompt():
    """process_message deve chamar Claude com system prompt identificando o tenant."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Olá! Como posso ajudar?")]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    with patch("services.agent_service.AsyncAnthropic", return_value=mock_client):
        from services.agent_service import process_message

        await process_message(
            tenant_id="tenant-123",
            tenant_name="Marmoraria Silva",
            phone="5511999999999",
            text="Quero um orçamento",
        )

    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args.kwargs

    # AC 4 — system prompt identifica o assistente como da empresa do tenant
    system_blocks = call_kwargs["system"]
    assert isinstance(system_blocks, list)
    system_text = system_blocks[0]["text"]
    assert "Marmoraria Silva" in system_text
    assert "nunca" in system_text.lower() or "não" in system_text.lower()


@pytest.mark.asyncio
async def test_process_message_passes_user_text_as_message():
    """process_message deve enviar o texto do usuário como conteúdo da mensagem."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Resposta do agente")]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    with patch("services.agent_service.AsyncAnthropic", return_value=mock_client):
        from services.agent_service import process_message

        await process_message(
            tenant_id="tenant-123",
            tenant_name="Granitos Pereira",
            phone="5511888888888",
            text="Qual o preço do granito branco?",
        )

    call_kwargs = mock_client.messages.create.call_args.kwargs
    messages = call_kwargs["messages"]
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Qual o preço do granito branco?"


# ---------------------------------------------------------------------------
# AC 3 — process_message retorna o texto da resposta do Claude
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_message_returns_claude_response_text():
    """process_message deve retornar o texto da primeira mensagem de conteúdo do Claude."""
    expected_response = "Olá! Sou o assistente da Marmoraria Teste. Como posso ajudar?"

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=expected_response)]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    with patch("services.agent_service.AsyncAnthropic", return_value=mock_client):
        from services.agent_service import process_message

        result = await process_message(
            tenant_id="tenant-456",
            tenant_name="Marmoraria Teste",
            phone="5511777777777",
            text="Olá",
        )

    assert result == expected_response


# ---------------------------------------------------------------------------
# AC 5 — cache_control ephemeral no system prompt
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_message_sends_cache_control_on_system_prompt():
    """process_message deve enviar cache_control ephemeral no system prompt."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Resposta")]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    with patch("services.agent_service.AsyncAnthropic", return_value=mock_client):
        from services.agent_service import process_message

        await process_message(
            tenant_id="tenant-789",
            tenant_name="Pedras Nobres",
            phone="5511666666666",
            text="Teste",
        )

    call_kwargs = mock_client.messages.create.call_args.kwargs
    system_blocks = call_kwargs["system"]
    last_block = system_blocks[-1]
    assert last_block.get("cache_control") == {"type": "ephemeral"}


# ---------------------------------------------------------------------------
# AC 3 — process_message usa modelo Claude Haiku correto
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_message_uses_claude_haiku_model():
    """process_message deve usar claude-haiku-4-5-20251001 como modelo."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Resposta")]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    with patch("services.agent_service.AsyncAnthropic", return_value=mock_client):
        from services.agent_service import process_message

        await process_message(
            tenant_id="tenant-model",
            tenant_name="Empresa Modelo",
            phone="5511555555555",
            text="Teste de modelo",
        )

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# AC 8 — Falha na API propaga exceção ao chamador
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_message_propagates_api_exception():
    """Falha na API do Claude deve propagar a exceção ao chamador."""
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(side_effect=Exception("API indisponível"))

    with patch("services.agent_service.AsyncAnthropic", return_value=mock_client):
        from services.agent_service import process_message

        with pytest.raises(Exception, match="API indisponível"):
            await process_message(
                tenant_id="tenant-err",
                tenant_name="Empresa Erro",
                phone="5511444444444",
                text="Teste de falha",
            )
