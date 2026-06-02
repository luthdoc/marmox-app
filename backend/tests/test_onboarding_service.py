"""
Testes unitários do serviço de onboarding (Story 5.2).

Cobre:
- parse_empresa_block: resposta completa, incompleta, sem bloco, malformada
- process_onboarding_message: chamada ao Claude com mock do cliente Anthropic
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.onboarding_service import parse_empresa_block, process_onboarding_message


TENANT_ID = "tenant-uuid-5002"

# Resposta completa com todos os campos preenchidos
RAW_COMPLETE = (
    "Ótimo! Já tenho todas as informações necessárias.\n\n"
    "[DADOS_EMPRESA]\n"
    '{"name": "Marmox Pedras", "services": ["Bancada", "Piso"], '
    '"regions": ["SP", "ABC"], "business_hours": "Seg-Sex 8h-18h", '
    '"welcome_message": "Olá! Bem-vindo.", "onboarding_complete": true}\n'
    "[/DADOS_EMPRESA]"
)

# Resposta com campos parcialmente preenchidos
RAW_PARTIAL = (
    "Entendido! Qual o nome da empresa?\n\n"
    "[DADOS_EMPRESA]\n"
    '{"name": "Marmox Pedras", "services": null, "regions": null, '
    '"business_hours": null, "welcome_message": null, "onboarding_complete": false}\n'
    "[/DADOS_EMPRESA]"
)

# Resposta sem bloco algum
RAW_NO_BLOCK = "Olá! Para configurar o assistente, preciso de algumas informações."

# Resposta com bloco malformado (JSON inválido)
RAW_MALFORMED = (
    "Continuando...\n\n"
    "[DADOS_EMPRESA]\n"
    "{name: broken json\n"
    "[/DADOS_EMPRESA]"
)


# ---------------------------------------------------------------------------
# parse_empresa_block
# ---------------------------------------------------------------------------


def test_parse_empresa_block_extracts_dados_from_complete_response():
    """parse_empresa_block extrai JSON e limpa o bloco da resposta completa."""
    dados, texto_limpo = parse_empresa_block(RAW_COMPLETE)

    assert dados is not None
    assert dados["name"] == "Marmox Pedras"
    assert dados["services"] == ["Bancada", "Piso"]
    assert dados["regions"] == ["SP", "ABC"]
    assert dados["business_hours"] == "Seg-Sex 8h-18h"
    assert dados["welcome_message"] == "Olá! Bem-vindo."
    assert dados["onboarding_complete"] is True
    assert "[DADOS_EMPRESA]" not in texto_limpo
    assert "[/DADOS_EMPRESA]" not in texto_limpo


def test_parse_empresa_block_extracts_partial_dados():
    """parse_empresa_block extrai dados parciais com campos null."""
    dados, texto_limpo = parse_empresa_block(RAW_PARTIAL)

    assert dados is not None
    assert dados["name"] == "Marmox Pedras"
    assert dados["services"] is None
    assert dados["onboarding_complete"] is False
    assert "[DADOS_EMPRESA]" not in texto_limpo


def test_parse_empresa_block_returns_none_when_no_block():
    """parse_empresa_block retorna (None, raw) quando bloco está ausente."""
    dados, texto_limpo = parse_empresa_block(RAW_NO_BLOCK)

    assert dados is None
    assert texto_limpo == RAW_NO_BLOCK


def test_parse_empresa_block_returns_none_on_malformed_json():
    """parse_empresa_block retorna (None, raw) quando JSON está malformado."""
    dados, texto_limpo = parse_empresa_block(RAW_MALFORMED)

    assert dados is None
    assert texto_limpo == RAW_MALFORMED


def test_parse_empresa_block_texto_limpo_preserves_non_block_content():
    """O texto limpo retornado preserva o conteúdo fora do bloco."""
    dados, texto_limpo = parse_empresa_block(RAW_COMPLETE)

    assert "Ótimo! Já tenho todas as informações necessárias." in texto_limpo


# ---------------------------------------------------------------------------
# process_onboarding_message
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_onboarding_message_returns_raw_response():
    """process_onboarding_message retorna o texto bruto da resposta do Claude."""
    expected_response = "Qual o nome da empresa? [DADOS_EMPRESA]{...}[/DADOS_EMPRESA]"
    mock_anthropic = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=expected_response)]
    mock_anthropic.messages.create = AsyncMock(return_value=mock_message)

    with patch("services.onboarding_service.AsyncAnthropic", return_value=mock_anthropic):
        result = await process_onboarding_message(TENANT_ID, "Olá!", [])

    assert result == expected_response


@pytest.mark.asyncio
async def test_process_onboarding_message_passes_history_to_claude():
    """process_onboarding_message inclui o histórico na chamada ao Claude."""
    history = [
        {"role": "user", "content": "Quero configurar o assistente"},
        {"role": "assistant", "content": "Ótimo! [DADOS_EMPRESA]{...}[/DADOS_EMPRESA]"},
    ]
    mock_anthropic = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="resposta")]
    mock_anthropic.messages.create = AsyncMock(return_value=mock_message)

    with patch("services.onboarding_service.AsyncAnthropic", return_value=mock_anthropic):
        await process_onboarding_message(TENANT_ID, "Nova mensagem", history)

    call_kwargs = mock_anthropic.messages.create.call_args.kwargs
    messages = call_kwargs["messages"]
    # Histórico + mensagem atual
    assert len(messages) == 3
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "Nova mensagem"


@pytest.mark.asyncio
async def test_process_onboarding_message_uses_haiku_model():
    """process_onboarding_message usa o modelo Haiku."""
    mock_anthropic = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="resposta")]
    mock_anthropic.messages.create = AsyncMock(return_value=mock_message)

    with patch("services.onboarding_service.AsyncAnthropic", return_value=mock_anthropic):
        await process_onboarding_message(TENANT_ID, "Olá", [])

    call_kwargs = mock_anthropic.messages.create.call_args.kwargs
    assert "haiku" in call_kwargs["model"].lower()


@pytest.mark.asyncio
async def test_process_onboarding_message_uses_cache_control_on_system_prompt():
    """process_onboarding_message habilita cache_control ephemeral no system prompt."""
    mock_anthropic = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="resposta")]
    mock_anthropic.messages.create = AsyncMock(return_value=mock_message)

    with patch("services.onboarding_service.AsyncAnthropic", return_value=mock_anthropic):
        await process_onboarding_message(TENANT_ID, "Olá", [])

    call_kwargs = mock_anthropic.messages.create.call_args.kwargs
    system = call_kwargs["system"]
    # system deve ser lista de blocos com cache_control
    assert isinstance(system, list)
    assert any(
        block.get("cache_control", {}).get("type") == "ephemeral"
        for block in system
        if isinstance(block, dict)
    )
