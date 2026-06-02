"""
Testes unitários para as funções de escrita em db/tenants.py (Story 5.1).

Cobre:
- update_tenant_config: persiste campos válidos, ignora chaves não reconhecidas
- complete_onboarding: atualiza status para 'active'
- get_owner_phone: retorna owner_phone ou None
- set_tenant_context chamado antes de qualquer query (NFR3)
"""
from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from db.tenants import complete_onboarding, get_owner_phone, update_tenant_config


TENANT_ID = "tenant-uuid-5001"


# ---------------------------------------------------------------------------
# update_tenant_config
# ---------------------------------------------------------------------------


def test_update_tenant_config_persists_valid_fields():
    """update_tenant_config salva os cinco campos válidos no banco."""
    mock_client = MagicMock()
    config = {
        "name": "Marmox Pedras",
        "services": ["Bancada", "Piso"],
        "regions": ["SP", "ABC"],
        "business_hours": "Seg-Sex 8h-18h",
        "welcome_message": "Olá! Bem-vindo.",
    }
    with (
        patch("db.tenants.set_tenant_context") as mock_ctx,
        patch("db.tenants.get_client", return_value=mock_client),
    ):
        update_tenant_config(TENANT_ID, config)

        mock_ctx.assert_called_once_with(TENANT_ID)
        mock_client.table.assert_called_once_with("tenants")
        update_call = mock_client.table.return_value.update
        update_call.assert_called_once_with(config)


def test_update_tenant_config_ignores_unknown_keys():
    """update_tenant_config ignora silenciosamente chaves não reconhecidas."""
    mock_client = MagicMock()
    config = {
        "name": "Marmox",
        "unknown_field": "valor inválido",
        "another_unknown": 42,
    }
    expected_filtered = {"name": "Marmox"}
    with (
        patch("db.tenants.set_tenant_context"),
        patch("db.tenants.get_client", return_value=mock_client),
    ):
        update_tenant_config(TENANT_ID, config)

        update_call = mock_client.table.return_value.update
        update_call.assert_called_once_with(expected_filtered)


def test_update_tenant_config_calls_set_tenant_context_before_query():
    """set_tenant_context é chamado antes de qualquer operação de escrita (NFR3)."""
    call_order = []
    mock_client = MagicMock()

    def record_ctx(tid):
        call_order.append("set_tenant_context")

    mock_client.table.side_effect = lambda _: (
        call_order.append("table") or MagicMock()
    )

    with (
        patch("db.tenants.set_tenant_context", side_effect=record_ctx),
        patch("db.tenants.get_client", return_value=mock_client),
    ):
        update_tenant_config(TENANT_ID, {"name": "X"})

    assert call_order[0] == "set_tenant_context"
    assert "table" in call_order


def test_update_tenant_config_with_empty_config_calls_update_with_empty_dict():
    """update_tenant_config com config vazio chama update com dict vazio."""
    mock_client = MagicMock()
    with (
        patch("db.tenants.set_tenant_context"),
        patch("db.tenants.get_client", return_value=mock_client),
    ):
        update_tenant_config(TENANT_ID, {})

        update_call = mock_client.table.return_value.update
        update_call.assert_called_once_with({})


# ---------------------------------------------------------------------------
# complete_onboarding
# ---------------------------------------------------------------------------


def test_complete_onboarding_sets_status_active():
    """complete_onboarding atualiza status para 'active' no banco."""
    mock_client = MagicMock()
    with (
        patch("db.tenants.set_tenant_context") as mock_ctx,
        patch("db.tenants.get_client", return_value=mock_client),
    ):
        complete_onboarding(TENANT_ID)

        mock_ctx.assert_called_once_with(TENANT_ID)
        update_call = mock_client.table.return_value.update
        update_call.assert_called_once_with({"status": "active"})
        eq_call = mock_client.table.return_value.update.return_value.eq
        eq_call.assert_called_once_with("id", TENANT_ID)


def test_complete_onboarding_calls_set_tenant_context_before_query():
    """set_tenant_context é chamado antes de qualquer operação de escrita (NFR3)."""
    call_order = []
    mock_client = MagicMock()

    def record_ctx(tid):
        call_order.append("set_tenant_context")

    mock_client.table.side_effect = lambda _: (
        call_order.append("table") or MagicMock()
    )

    with (
        patch("db.tenants.set_tenant_context", side_effect=record_ctx),
        patch("db.tenants.get_client", return_value=mock_client),
    ):
        complete_onboarding(TENANT_ID)

    assert call_order[0] == "set_tenant_context"


# ---------------------------------------------------------------------------
# get_owner_phone
# ---------------------------------------------------------------------------


def test_get_owner_phone_returns_phone_when_present():
    """get_owner_phone retorna o número quando owner_phone está definido."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"owner_phone": "5511999990001"}
    ]
    with (
        patch("db.tenants.set_tenant_context") as mock_ctx,
        patch("db.tenants.get_client", return_value=mock_client),
    ):
        result = get_owner_phone(TENANT_ID)

        mock_ctx.assert_called_once_with(TENANT_ID)
        assert result == "5511999990001"


def test_get_owner_phone_returns_none_when_row_not_found():
    """get_owner_phone retorna None quando tenant não existe no banco."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    with (
        patch("db.tenants.set_tenant_context"),
        patch("db.tenants.get_client", return_value=mock_client),
    ):
        result = get_owner_phone(TENANT_ID)

        assert result is None


def test_get_owner_phone_returns_none_when_field_is_null():
    """get_owner_phone retorna None quando owner_phone está NULL no banco."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"owner_phone": None}
    ]
    with (
        patch("db.tenants.set_tenant_context"),
        patch("db.tenants.get_client", return_value=mock_client),
    ):
        result = get_owner_phone(TENANT_ID)

        assert result is None


def test_get_owner_phone_calls_set_tenant_context_before_query():
    """set_tenant_context é chamado antes de qualquer leitura do banco (NFR3)."""
    call_order = []
    mock_client = MagicMock()

    def record_ctx(tid):
        call_order.append("set_tenant_context")

    mock_client.table.side_effect = lambda _: (
        call_order.append("table") or MagicMock()
    )

    with (
        patch("db.tenants.set_tenant_context", side_effect=record_ctx),
        patch("db.tenants.get_client", return_value=mock_client),
    ):
        get_owner_phone(TENANT_ID)

    assert call_order[0] == "set_tenant_context"
