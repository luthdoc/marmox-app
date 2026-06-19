"""
Testes para o serviço de envio de mensagens via Meta WhatsApp Cloud API.

Cobre:
- Envio bem-sucedido (mock HTTP 200)
- Falha na 1ª tentativa e sucesso na 2ª (mock)
- Falha em todas as tentativas (mock HTTP 500 → retorna False)
"""
from __future__ import annotations

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

_META_ENV = {
    "META_WHATSAPP_ACCESS_TOKEN": "EAABs-test-token",
    "META_WHATSAPP_VERIFY_TOKEN": "verify-token-test",
}


def _make_supabase_client(phone_number_id="1220170564507810"):
    """Retorna mock do cliente Supabase com tenant válido."""
    tenant_row = {
        "id": "tenant-uuid-001",
        "whatsapp_phone_number_id": phone_number_id,
    }
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        tenant_row
    ]
    return client


def _make_http_response(status_code: int):
    resp = MagicMock()
    resp.status_code = status_code
    return resp


# ---------------------------------------------------------------------------
# Cenário 1: Envio bem-sucedido na primeira tentativa
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_message_returns_true_on_http_200():
    """send_message retorna True quando a requisição POST à Meta API retorna HTTP 200."""
    mock_client = _make_supabase_client()
    mock_response = _make_http_response(200)

    with (
        patch.dict(os.environ, _META_ENV),
        patch("services.meta_client.get_client", return_value=mock_client),
        patch("services.meta_client.httpx.AsyncClient") as MockAsyncClient,
    ):
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        MockAsyncClient.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        MockAsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)

        from services.meta_client import send_message
        result = await send_message("tenant-uuid-001", "5511999999999", "Olá!")

    assert result is True


# ---------------------------------------------------------------------------
# Cenário 2: Falha na 1ª tentativa, sucesso na 2ª
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_message_retries_and_returns_true_on_second_attempt():
    """send_message faz retry e retorna True quando sucesso ocorre na 2ª tentativa."""
    mock_client = _make_supabase_client()
    fail_response = _make_http_response(500)
    ok_response = _make_http_response(200)

    import importlib
    from services import meta_client
    importlib.reload(meta_client)

    with (
        patch.dict(os.environ, _META_ENV),
        patch("services.meta_client.get_client", return_value=mock_client),
        patch("services.meta_client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        patch("services.meta_client.httpx.AsyncClient") as MockAsyncClient,
    ):
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(side_effect=[fail_response, ok_response])
        MockAsyncClient.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        MockAsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await meta_client.send_message("tenant-uuid-001", "5511999999999", "Olá!")

    assert result is True
    mock_sleep.assert_called_once_with(1)


# ---------------------------------------------------------------------------
# Cenário 3: Falha em todas as 3 tentativas → retorna False sem exception
# ---------------------------------------------------------------------------


async def _run_all_attempts_fail():
    import importlib
    from services import meta_client
    importlib.reload(meta_client)

    mock_client = _make_supabase_client()
    fail_response = _make_http_response(500)

    with (
        patch.dict(os.environ, _META_ENV),
        patch("services.meta_client.get_client", return_value=mock_client),
        patch("services.meta_client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        patch("services.meta_client.httpx.AsyncClient") as MockAsyncClient,
    ):
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=fail_response)
        MockAsyncClient.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        MockAsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await meta_client.send_message("tenant-uuid-001", "5511999999999", "Olá!")
        return result, mock_sleep


@pytest.mark.asyncio
async def test_send_message_returns_false_after_all_attempts_fail():
    """send_message retorna False quando todas as 3 tentativas falham com HTTP 500."""
    result, _ = await _run_all_attempts_fail()
    assert result is False


@pytest.mark.asyncio
async def test_send_message_sleeps_twice_after_all_attempts_fail():
    """send_message realiza exatamente 2 sleeps quando todas as tentativas falham."""
    _, mock_sleep = await _run_all_attempts_fail()
    assert mock_sleep.call_count == 2


@pytest.mark.asyncio
async def test_send_message_first_backoff_is_one_second():
    """send_message aplica backoff de 1s após a 1ª tentativa falhar."""
    _, mock_sleep = await _run_all_attempts_fail()
    mock_sleep.assert_any_call(1)


@pytest.mark.asyncio
async def test_send_message_second_backoff_is_two_seconds():
    """send_message aplica backoff de 2s após a 2ª tentativa falhar."""
    _, mock_sleep = await _run_all_attempts_fail()
    mock_sleep.assert_any_call(2)
