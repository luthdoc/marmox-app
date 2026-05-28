"""
Testes para db/leads.py — função get_or_create_lead (Story 3.3).

Cenários cobertos (AC 8):
- Lead inexistente: cria e retorna com status "new"
- Lead já existente: retorna sem duplicar
- RLS ativo: query com tenant errado retorna vazio (isolamento por tenant)
- set_tenant_context é chamado antes de qualquer query (AC 6)

Cobertura AC 4 (last_contact_at):
- persist_outbound_message atualiza last_contact_at no lead quando lead_id fornecido
"""
from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TENANT_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
OTHER_TENANT_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
PHONE = "5511999999999"
LEAD_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"


def _new_lead_row() -> dict:
    return {
        "id": LEAD_ID,
        "tenant_id": TENANT_ID,
        "phone": PHONE,
        "status": "new",
        "name": None,
        "created_at": "2024-01-01T00:00:00+00:00",
        "last_contact_at": None,
    }


# ---------------------------------------------------------------------------
# AC 8a — Lead inexistente: cria e retorna com status "new"
# ---------------------------------------------------------------------------


def test_get_or_create_lead_creates_when_not_found():
    """Quando não existe lead com (tenant_id, phone), deve inserir e retornar com status 'new'."""
    mock_client = MagicMock()
    # SELECT retorna vazio (lead não existe)
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    # INSERT retorna o lead criado
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [_new_lead_row()]

    with patch("db.leads.get_client", return_value=mock_client), \
         patch("db.leads.set_tenant_context") as mock_set_ctx:

        from db.leads import get_or_create_lead
        result = get_or_create_lead(TENANT_ID, PHONE)

    assert result["id"] == LEAD_ID
    assert result["status"] == "new"
    assert result["phone"] == PHONE
    assert result["tenant_id"] == TENANT_ID
    # set_tenant_context deve ter sido chamado com o tenant_id correto (AC 6)
    mock_set_ctx.assert_called_once_with(TENANT_ID)


# ---------------------------------------------------------------------------
# AC 8b — Lead já existente: retorna sem duplicar
# ---------------------------------------------------------------------------


def test_get_or_create_lead_returns_existing_without_duplicate():
    """Quando já existe lead com (tenant_id, phone), deve retornar sem inserir novamente."""
    mock_client = MagicMock()
    existing_lead = _new_lead_row()
    existing_lead["status"] = "qualifying"
    # SELECT retorna o lead existente
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [existing_lead]

    with patch("db.leads.get_client", return_value=mock_client), \
         patch("db.leads.set_tenant_context"):

        from db.leads import get_or_create_lead
        result = get_or_create_lead(TENANT_ID, PHONE)

    assert result["id"] == LEAD_ID
    assert result["status"] == "qualifying"
    # INSERT não deve ter sido chamado
    mock_client.table.return_value.insert.assert_not_called()


# ---------------------------------------------------------------------------
# AC 8c — RLS ativo: query com tenant errado retorna vazio
# ---------------------------------------------------------------------------


def test_get_or_create_lead_rls_isolation():
    """Com RLS ativo, query com tenant errado não deve encontrar leads de outro tenant."""
    mock_client = MagicMock()
    # SELECT com outro tenant retorna vazio (RLS filtra)
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    # INSERT cria lead para o outro tenant
    other_lead = _new_lead_row()
    other_lead["tenant_id"] = OTHER_TENANT_ID
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [other_lead]

    with patch("db.leads.get_client", return_value=mock_client), \
         patch("db.leads.set_tenant_context") as mock_set_ctx:

        from db.leads import get_or_create_lead
        get_or_create_lead(OTHER_TENANT_ID, PHONE)

    # set_tenant_context deve ter sido chamado com OTHER_TENANT_ID, não TENANT_ID
    mock_set_ctx.assert_called_once_with(OTHER_TENANT_ID)


# ---------------------------------------------------------------------------
# AC 6 — set_tenant_context chamado antes de qualquer query
# ---------------------------------------------------------------------------


def test_set_tenant_context_called_before_query():
    """set_tenant_context deve ser chamado antes de qualquer operação no banco."""
    call_order = []

    mock_client = MagicMock()

    def track_set_ctx(tenant_id: str) -> None:
        call_order.append("set_tenant_context")

    def track_select(*args, **kwargs):
        call_order.append("select")
        return mock_client.table.return_value.select.return_value

    mock_client.table.return_value.select.side_effect = track_select
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        _new_lead_row()
    ]

    with patch("db.leads.get_client", return_value=mock_client), \
         patch("db.leads.set_tenant_context", side_effect=track_set_ctx):

        from db.leads import get_or_create_lead
        get_or_create_lead(TENANT_ID, PHONE)

    assert call_order[0] == "set_tenant_context", (
        "set_tenant_context deve ser chamado antes de qualquer query"
    )


# ---------------------------------------------------------------------------
# AC 4 — persist_outbound_message atualiza last_contact_at do lead
# ---------------------------------------------------------------------------


def test_persist_outbound_updates_last_contact_at_when_lead_id_provided():
    """persist_outbound_message deve atualizar last_contact_at no lead quando lead_id é fornecido."""
    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [{"id": "msg-001"}]
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{}]

    with patch("db.conversation.get_client", return_value=mock_client), \
         patch("db.conversation.set_tenant_context"):

        from db.conversation import persist_outbound_message
        persist_outbound_message(
            tenant_id=TENANT_ID,
            phone=PHONE,
            content="Resposta",
            lead_id=LEAD_ID,
        )

    # Verifica que UPDATE foi chamado na tabela leads com eq("id", LEAD_ID)
    update_calls = [
        call_args
        for call_args in mock_client.table.call_args_list
        if call_args.args[0] == "leads"
    ]
    assert len(update_calls) >= 1, "UPDATE na tabela leads deve ter sido chamado"


def test_persist_outbound_does_not_update_last_contact_at_without_lead_id():
    """persist_outbound_message não deve tentar atualizar leads quando lead_id é None."""
    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [{"id": "msg-001"}]

    with patch("db.conversation.get_client", return_value=mock_client), \
         patch("db.conversation.set_tenant_context"):

        from db.conversation import persist_outbound_message
        persist_outbound_message(
            tenant_id=TENANT_ID,
            phone=PHONE,
            content="Resposta",
            lead_id=None,
        )

    # Verifica que UPDATE na tabela leads NÃO foi chamado
    leads_table_calls = [
        call_args
        for call_args in mock_client.table.call_args_list
        if call_args.args[0] == "leads"
    ]
    assert len(leads_table_calls) == 0, "UPDATE na tabela leads não deve ser chamado sem lead_id"
