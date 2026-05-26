"""
Testes para o serviço de envio de mensagens via Z-API (Story 2.3).

Cobre:
- Envio bem-sucedido (mock HTTP 200)
- Falha na 1ª tentativa e sucesso na 2ª (mock)
- Falha em todas as tentativas (mock HTTP 500 → retorna False)
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_supabase_client(zapi_instance_id="inst123", zapi_token="tok456"):
    """Retorna um mock do cliente Supabase com tenant válido."""
    tenant_row = {
        "id": "tenant-uuid-001",
        "zapi_instance_id": zapi_instance_id,
        "zapi_token": zapi_token,
    }
    client = MagicMock()
    # encadeia .table().select().eq().execute()
    client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        tenant_row
    ]
    # encadeia .table().insert().execute() para persistência de mensagem
    client.table.return_value.insert.return_value.execute.return_value = MagicMock()
    return client


def _make_http_response(status_code: int):
    """Retorna um mock de resposta httpx com o status_code especificado."""
    resp = MagicMock()
    resp.status_code = status_code
    return resp


# ---------------------------------------------------------------------------
# Cenário 1: Envio bem-sucedido na primeira tentativa
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_message_returns_true_on_http_200():
    """send_message retorna True quando a requisição POST ao Z-API retorna HTTP 200."""
    mock_client = _make_supabase_client()
    mock_response = _make_http_response(200)

    with (
        patch("services.zapi_client.get_client", return_value=mock_client),
        patch("services.zapi_client.set_tenant_context"),
        patch("services.zapi_client.httpx.AsyncClient") as MockAsyncClient,
    ):
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        MockAsyncClient.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        MockAsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)

        from services.zapi_client import send_message

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

    with (
        patch("services.zapi_client.get_client", return_value=mock_client),
        patch("services.zapi_client.asyncio.sleep", new_callable=AsyncMock),
        patch("services.zapi_client.httpx.AsyncClient") as MockAsyncClient,
    ):
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(side_effect=[fail_response, ok_response])
        MockAsyncClient.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        MockAsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)

        from services import zapi_client
        # recarregar para garantir estado limpo do cache
        import importlib
        importlib.reload(zapi_client)

        with (
            patch("services.zapi_client.get_client", return_value=mock_client),
            patch("services.zapi_client.set_tenant_context"),
            patch("services.zapi_client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            patch("services.zapi_client.httpx.AsyncClient") as MockAsyncClient2,
        ):
            mock_http2 = AsyncMock()
            mock_http2.post = AsyncMock(side_effect=[fail_response, ok_response])
            MockAsyncClient2.return_value.__aenter__ = AsyncMock(return_value=mock_http2)
            MockAsyncClient2.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await zapi_client.send_message(
                "tenant-uuid-001", "5511999999999", "Olá!"
            )

        assert result is True
        # deve ter dormido 1s entre tentativas (backoff exponencial: 2^0 = 1)
        mock_sleep.assert_called_once_with(1)


# ---------------------------------------------------------------------------
# Cenário 3: Falha em todas as 3 tentativas → retorna False sem exception
# ---------------------------------------------------------------------------


async def _run_all_attempts_fail():
    """Executa send_message com todas as tentativas falhando (HTTP 500); retorna (result, mock_sleep)."""
    import importlib
    from services import zapi_client
    importlib.reload(zapi_client)

    mock_client = _make_supabase_client()
    fail_response = _make_http_response(500)

    with (
        patch("services.zapi_client.get_client", return_value=mock_client),
        patch("services.zapi_client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        patch("services.zapi_client.httpx.AsyncClient") as MockAsyncClient,
    ):
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=fail_response)
        MockAsyncClient.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        MockAsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await zapi_client.send_message(
            "tenant-uuid-001", "5511999999999", "Olá!"
        )
        return result, mock_sleep


@pytest.mark.asyncio
async def test_send_message_returns_false_after_all_attempts_fail():
    """send_message retorna False quando todas as 3 tentativas falham com HTTP 500."""
    result, _ = await _run_all_attempts_fail()
    assert result is False


@pytest.mark.asyncio
async def test_send_message_sleeps_twice_after_all_attempts_fail():
    """send_message realiza exatamente 2 sleeps (entre tentativas 1→2 e 2→3) quando todas falham."""
    _, mock_sleep = await _run_all_attempts_fail()
    assert mock_sleep.call_count == 2


@pytest.mark.asyncio
async def test_send_message_first_backoff_is_one_second_after_all_attempts_fail():
    """send_message aplica backoff de 1s após a 1ª tentativa falhar."""
    _, mock_sleep = await _run_all_attempts_fail()
    mock_sleep.assert_any_call(1)


@pytest.mark.asyncio
async def test_send_message_second_backoff_is_two_seconds_after_all_attempts_fail():
    """send_message aplica backoff de 2s após a 2ª tentativa falhar."""
    _, mock_sleep = await _run_all_attempts_fail()
    mock_sleep.assert_any_call(2)


# ---------------------------------------------------------------------------
# NFR3 — set_tenant_context é chamado antes de persistir mensagem outbound
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_tenant_context_called_before_persisting_outbound_message():
    """set_tenant_context deve ser chamado com o tenant_id correto antes de inserir em messages."""
    import importlib
    from services import zapi_client
    importlib.reload(zapi_client)

    mock_client = _make_supabase_client()
    mock_response = _make_http_response(200)

    with (
        patch("services.zapi_client.get_client", return_value=mock_client),
        patch("services.zapi_client.set_tenant_context") as mock_set_ctx,
        patch("services.zapi_client.httpx.AsyncClient") as MockAsyncClient,
    ):
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(return_value=mock_response)
        MockAsyncClient.return_value.__aenter__ = AsyncMock(return_value=mock_http)
        MockAsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await zapi_client.send_message("tenant-uuid-001", "5511999999999", "Olá!")

    assert result is True
    mock_set_ctx.assert_called_once_with("tenant-uuid-001")
