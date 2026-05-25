"""
Testes para o serviço de envio de mensagens via Z-API (Story 2.3).

Cobre:
- Envio bem-sucedido (mock HTTP 200)
- Falha na 1ª tentativa e sucesso na 2ª (mock)
- Falha em todas as tentativas (mock HTTP 500 → retorna False)
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call


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


@pytest.mark.asyncio
async def test_send_message_returns_false_after_all_attempts_fail():
    """send_message retorna False (sem exception) quando todas as 3 tentativas falham com HTTP 500."""
    mock_client = _make_supabase_client()
    fail_response = _make_http_response(500)

    import importlib
    from services import zapi_client
    importlib.reload(zapi_client)

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

    assert result is False
    # 3 tentativas → 2 sleeps (após falha 1 e após falha 2; na 3ª não dorme)
    assert mock_sleep.call_count == 2
    # backoff exponencial: 1s, 2s
    mock_sleep.assert_any_call(1)
    mock_sleep.assert_any_call(2)
