"""
Testes para histórico de conversa como contexto do agente (Story 3.2).

Cenários cobertos:
- load_conversation_history: retorna histórico formatado corretamente para o Claude
- load_conversation_history: histórico vazio (primeira mensagem) funciona sem erro
- load_conversation_history: direction inbound→"user", outbound→"assistant"
- load_conversation_history: respeita limite de 20 mensagens
- persist_outbound_message: persiste resposta outbound com os campos corretos
- persist_outbound_message: associa lead_id quando fornecido
- persist_outbound_message: usa lead_id=None quando não fornecido
- agent_service.process_message: passa histórico ao Claude antes da mensagem atual
- webhook_service._dispatch_agent: carrega histórico antes de chamar process_message
- webhook_service._dispatch_agent: persiste resposta outbound após send_message bem-sucedido
- webhook_service._dispatch_agent: não persiste outbound se send_message falhar
- webhook_service._dispatch_agent: chama set_tenant_context antes da query de histórico
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db_row(direction: str, content: str, created_at: str = "2024-01-01T00:00:00") -> dict:
    return {"direction": direction, "content": content, "created_at": created_at}


def _make_supabase_messages_mock(rows: list[dict]):
    """Mock de client.table('messages').select(...).eq(...).eq(...).order(...).limit(...).execute()"""
    mock = MagicMock()
    (
        mock.table.return_value
        .select.return_value
        .eq.return_value
        .eq.return_value
        .order.return_value
        .limit.return_value
        .execute.return_value
        .data
    ) = rows
    return mock


def _make_supabase_insert_mock():
    """Mock de client.table('messages').insert(...).execute()"""
    mock = MagicMock()
    mock.table.return_value.insert.return_value.execute.return_value.data = [{"id": "msg-001"}]
    return mock


# ---------------------------------------------------------------------------
# AC 2 + AC 6 — load_conversation_history: formato correto e mapeamento role
# ---------------------------------------------------------------------------


def test_load_history_maps_directions_to_roles():
    """load_conversation_history deve mapear inbound→user e outbound→assistant."""
    rows = [
        _make_db_row("inbound", "Olá, quero um orçamento"),
        _make_db_row("outbound", "Olá! Como posso ajudar?"),
        _make_db_row("inbound", "Granito preto"),
    ]
    mock_client = _make_supabase_messages_mock(rows)

    with (
        patch("db.conversation.get_client", return_value=mock_client),
        patch("db.conversation.set_tenant_context"),
    ):
        from db.conversation import load_conversation_history

        result = load_conversation_history("tenant-123", "5511999999999")

    assert result == [
        {"role": "user", "content": "Olá, quero um orçamento"},
        {"role": "assistant", "content": "Olá! Como posso ajudar?"},
        {"role": "user", "content": "Granito preto"},
    ]


def test_load_history_returns_empty_list_on_first_message():
    """load_conversation_history deve retornar [] quando não há histórico (primeira mensagem)."""
    mock_client = _make_supabase_messages_mock([])

    with (
        patch("db.conversation.get_client", return_value=mock_client),
        patch("db.conversation.set_tenant_context"),
    ):
        from db.conversation import load_conversation_history

        result = load_conversation_history("tenant-123", "5511000000000")

    assert result == []


def test_load_history_applies_limit():
    """load_conversation_history deve aplicar limit=20 na query (ou o valor passado)."""
    mock_client = _make_supabase_messages_mock([])

    with (
        patch("db.conversation.get_client", return_value=mock_client),
        patch("db.conversation.set_tenant_context"),
    ):
        from db.conversation import load_conversation_history

        load_conversation_history("tenant-123", "5511999999999", limit=20)

    # Verifica que .limit(20) foi chamado na chain
    chain = mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value
    chain.limit.assert_called_once_with(20)


# ---------------------------------------------------------------------------
# AC 3 — set_tenant_context é chamado antes da query
# ---------------------------------------------------------------------------


def test_load_history_calls_set_tenant_context_before_query():
    """load_conversation_history deve chamar set_tenant_context antes de qualquer query."""
    call_order = []

    mock_client = _make_supabase_messages_mock([])

    def track_set_tenant(tid):
        call_order.append("set_tenant_context")

    def track_get_client():
        call_order.append("get_client")
        return mock_client

    with (
        patch("db.conversation.get_client", side_effect=track_get_client),
        patch("db.conversation.set_tenant_context", side_effect=track_set_tenant),
    ):
        from db.conversation import load_conversation_history

        load_conversation_history("tenant-abc", "5511111111111")

    assert call_order.index("set_tenant_context") < call_order.index("get_client")


# ---------------------------------------------------------------------------
# AC 4 — persist_outbound_message: campos corretos
# ---------------------------------------------------------------------------


def test_persist_outbound_inserts_correct_fields():
    """persist_outbound_message deve inserir direction=outbound com os campos corretos."""
    mock_client = _make_supabase_insert_mock()

    with (
        patch("db.conversation.get_client", return_value=mock_client),
        patch("db.conversation.set_tenant_context"),
    ):
        from db.conversation import persist_outbound_message

        persist_outbound_message(
            tenant_id="tenant-xyz",
            phone="5511888888888",
            content="Resposta do agente",
        )

    insert_call = mock_client.table.return_value.insert.call_args
    payload = insert_call.args[0]

    assert payload["tenant_id"] == "tenant-xyz"
    assert payload["phone"] == "5511888888888"
    assert payload["content"] == "Resposta do agente"
    assert payload["direction"] == "outbound"


def test_persist_outbound_with_lead_id():
    """persist_outbound_message deve incluir lead_id quando fornecido."""
    mock_client = _make_supabase_insert_mock()

    with (
        patch("db.conversation.get_client", return_value=mock_client),
        patch("db.conversation.set_tenant_context"),
    ):
        from db.conversation import persist_outbound_message

        persist_outbound_message(
            tenant_id="tenant-xyz",
            phone="5511888888888",
            content="Resposta",
            lead_id="lead-uuid-001",
        )

    insert_call = mock_client.table.return_value.insert.call_args
    payload = insert_call.args[0]
    assert payload["lead_id"] == "lead-uuid-001"


def test_persist_outbound_without_lead_id_defaults_to_none():
    """persist_outbound_message deve usar lead_id=None quando não fornecido."""
    mock_client = _make_supabase_insert_mock()

    with (
        patch("db.conversation.get_client", return_value=mock_client),
        patch("db.conversation.set_tenant_context"),
    ):
        from db.conversation import persist_outbound_message

        persist_outbound_message(
            tenant_id="tenant-xyz",
            phone="5511888888888",
            content="Resposta",
        )

    insert_call = mock_client.table.return_value.insert.call_args
    payload = insert_call.args[0]
    assert payload["lead_id"] is None


# ---------------------------------------------------------------------------
# AC 1 — agent_service.process_message aceita e passa history ao Claude
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_message_passes_history_before_current_message():
    """process_message deve enviar histórico antes da mensagem atual no array messages do Claude."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Resposta do agente")]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    history = [
        {"role": "user", "content": "Olá"},
        {"role": "assistant", "content": "Olá! Como posso ajudar?"},
    ]

    with patch("services.agent_service.AsyncAnthropic", return_value=mock_client):
        from services.agent_service import process_message

        await process_message(
            tenant_id="tenant-123",
            tenant_name="Marmoraria Silva",
            phone="5511999999999",
            text="Quero granito preto",
            history=history,
        )

    call_kwargs = mock_client.messages.create.call_args.kwargs
    messages = call_kwargs["messages"]

    # Histórico deve aparecer antes da mensagem atual
    assert messages[0] == {"role": "user", "content": "Olá"}
    assert messages[1] == {"role": "assistant", "content": "Olá! Como posso ajudar?"}
    assert messages[-1] == {"role": "user", "content": "Quero granito preto"}


@pytest.mark.asyncio
async def test_process_message_works_without_history():
    """process_message deve funcionar sem histórico (history=[] ou omitido)."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Olá!")]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    with patch("services.agent_service.AsyncAnthropic", return_value=mock_client):
        from services.agent_service import process_message

        result = await process_message(
            tenant_id="tenant-123",
            tenant_name="Marmoraria Silva",
            phone="5511999999999",
            text="Primeira mensagem",
        )

    assert result == "Olá!"
    call_kwargs = mock_client.messages.create.call_args.kwargs
    messages = call_kwargs["messages"]
    assert len(messages) == 1
    assert messages[0] == {"role": "user", "content": "Primeira mensagem"}


# ---------------------------------------------------------------------------
# AC 2 + AC 5 — webhook_service._dispatch_agent: carrega histórico via run_in_executor
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_agent_loads_history_and_passes_to_process_message():
    """_dispatch_agent deve carregar histórico e passá-lo a process_message."""
    history = [{"role": "user", "content": "Mensagem anterior"}]
    tenant_ctx = {"name": "Marmoraria", "services": ["bancada"]}

    with (
        patch(
            "services.webhook_service.get_or_create_lead",
            return_value={"id": "lead-001", "tenant_id": "tenant-001", "phone": "5511999999999", "status": "new"},
        ),
        patch(
            "services.webhook_service.get_tenant_context",
            return_value=tenant_ctx,
        ),
        patch(
            "services.webhook_service.load_conversation_history",
            return_value=history,
        ),
        patch(
            "services.webhook_service.process_message",
            new_callable=AsyncMock,
            return_value="Resposta",
        ) as mock_process,
        patch("services.webhook_service.send_message", new_callable=AsyncMock),
        patch("services.webhook_service.persist_outbound_message"),
        patch("services.webhook_service.parse_lead_data_block", return_value=(None, "Resposta")),
        patch("services.webhook_service.update_lead_qualification"),
    ):
        from services.webhook_service import _dispatch_agent

        await _dispatch_agent("tenant-001", "Marmoraria", "5511999999999", "Olá")

    mock_process.assert_called_once_with(
        tenant_id="tenant-001",
        tenant_name="Marmoraria",
        phone="5511999999999",
        text="Olá",
        history=history,
        tenant_context=tenant_ctx,
        lead_data={"id": "lead-001", "tenant_id": "tenant-001", "phone": "5511999999999", "status": "new"},
    )


# ---------------------------------------------------------------------------
# AC 4 — webhook_service._dispatch_agent: persiste outbound após send_message
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_agent_persists_outbound_after_send_success():
    """_dispatch_agent deve persistir a resposta outbound após send_message bem-sucedido."""
    with (
        patch(
            "services.webhook_service.get_or_create_lead",
            return_value={"id": "lead-001", "tenant_id": "tenant-001", "phone": "5511999999999", "status": "new"},
        ),
        patch("services.webhook_service.get_tenant_context", return_value={}),
        patch(
            "services.webhook_service.load_conversation_history",
            return_value=[],
        ),
        patch(
            "services.webhook_service.process_message",
            new_callable=AsyncMock,
            return_value="Resposta do agente",
        ),
        patch("services.webhook_service.send_message", new_callable=AsyncMock),
        patch(
            "services.webhook_service.persist_outbound_message",
        ) as mock_persist,
        patch(
            "services.webhook_service.parse_lead_data_block",
            return_value=(None, "Resposta do agente"),
        ),
        patch("services.webhook_service.update_lead_qualification"),
    ):
        from services.webhook_service import _dispatch_agent

        await _dispatch_agent("tenant-001", "Marmoraria", "5511999999999", "Olá")

    mock_persist.assert_called_once_with(
        tenant_id="tenant-001",
        phone="5511999999999",
        content="Resposta do agente",
        lead_id="lead-001",
    )


@pytest.mark.asyncio
async def test_dispatch_agent_does_not_persist_if_send_fails():
    """_dispatch_agent não deve persistir outbound se send_message falhar."""
    with (
        patch(
            "services.webhook_service.get_or_create_lead",
            return_value={"id": "lead-001", "tenant_id": "tenant-001", "phone": "5511999999999", "status": "new"},
        ),
        patch(
            "services.webhook_service.load_conversation_history",
            return_value=[],
        ),
        patch(
            "services.webhook_service.process_message",
            new_callable=AsyncMock,
            return_value="Resposta",
        ),
        patch(
            "services.webhook_service.send_message",
            new_callable=AsyncMock,
            side_effect=Exception("Falha no envio"),
        ),
        patch(
            "services.webhook_service.persist_outbound_message",
        ) as mock_persist,
    ):
        from services.webhook_service import _dispatch_agent

        # fire-and-forget não propaga — mas internamente deve capturar antes de persist
        await _dispatch_agent("tenant-001", "Marmoraria", "5511999999999", "Olá")

    mock_persist.assert_not_called()
