"""
Testes unitários do roteamento de onboarding em webhook_service.py (Story 5.3).

Cobre:
- Roteamento para onboarding quando tenant.status == 'onboarding'
- Roteamento para active quando tenant.status == 'active'
- Phone diferente de owner_phone é descartado silenciosamente
- Ativação quando parse retorna onboarding_complete=True
- Ausência do bloco [DADOS_EMPRESA] na resposta enviada ao dono
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from schemas.webhook import ZApiWebhookPayload
from services.webhook_service import (
    _handle_inbound_message,
    InboundMessage,
)


TENANT_ID = "tenant-uuid-5003"
OWNER_PHONE = "5511999990001"
OTHER_PHONE = "5511888880002"

# Mensagem inbound de onboarding válida (owner_phone)
def _make_onboarding_msg(phone: str = OWNER_PHONE, text: str = "Marmox Pedras") -> InboundMessage:
    return InboundMessage(
        tenant_id=TENANT_ID,
        tenant_status="onboarding",
        tenant_name="",
        phone=phone,
        text=text,
        instance_id="instance-001",
    )


# ---------------------------------------------------------------------------
# Roteamento: onboarding vs active
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_onboarding_status_dispatches_onboarding_agent():
    """Mensagem de tenant em status 'onboarding' agenda _dispatch_onboarding_agent via create_task."""
    msg = _make_onboarding_msg()
    created_coroutines = []

    def capture_task(coro):
        created_coroutines.append(coro)
        return MagicMock()

    with (
        patch("services.webhook_service.asyncio.get_event_loop") as mock_loop,
        patch("services.webhook_service.asyncio.to_thread", new_callable=AsyncMock, return_value=OWNER_PHONE),
        patch("services.webhook_service.asyncio.create_task", side_effect=capture_task),
    ):
        mock_loop.return_value.run_in_executor = AsyncMock(return_value=None)
        await _handle_inbound_message(msg)

    # Cancela corrotinas não executadas para evitar warnings
    for coro in created_coroutines:
        coro.close()

    # Deve ter criado pelo menos uma task de onboarding
    assert len(created_coroutines) >= 1
    coro_names = [getattr(c, "__qualname__", "") or getattr(c, "cr_code", None) and c.cr_code.co_qualname for c in created_coroutines]
    assert any("onboarding" in str(n).lower() for n in coro_names)


@pytest.mark.asyncio
async def test_active_status_dispatches_main_agent():
    """Mensagem de tenant em status 'active' agenda _dispatch_agent (não onboarding)."""
    msg = InboundMessage(
        tenant_id=TENANT_ID,
        tenant_status="active",
        tenant_name="Marmox",
        phone=OWNER_PHONE,
        text="Quero uma bancada",
        instance_id="instance-001",
    )
    created_coroutines = []

    def capture_task(coro):
        created_coroutines.append(coro)
        return MagicMock()

    with (
        patch("services.webhook_service.asyncio.get_event_loop") as mock_loop,
        patch("services.webhook_service.asyncio.create_task", side_effect=capture_task),
    ):
        mock_loop.return_value.run_in_executor = AsyncMock(return_value=None)
        await _handle_inbound_message(msg)

    # Cancela corrotinas não executadas
    for coro in created_coroutines:
        coro.close()

    # Para active, deve criar task de _dispatch_agent (não onboarding)
    assert len(created_coroutines) >= 1
    coro_names = [getattr(c, "__qualname__", "") for c in created_coroutines]
    assert any("_dispatch_agent" in str(n) and "onboarding" not in str(n) for n in coro_names)


# ---------------------------------------------------------------------------
# Phone diferente de owner_phone — descartado
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_onboarding_message_from_non_owner_phone_is_discarded(caplog):
    """Mensagens de onboarding de phone != owner_phone são descartadas com log de aviso."""
    import logging

    msg = _make_onboarding_msg(phone=OTHER_PHONE)

    dispatched = []

    async def fake_to_thread(fn, *args, **kwargs):
        return OWNER_PHONE  # owner_phone retornado

    with (
        patch("services.webhook_service._persist_inbound_message"),
        patch("services.webhook_service.asyncio.to_thread", side_effect=fake_to_thread),
        patch("services.webhook_service.asyncio.get_event_loop") as mock_loop,
        patch("services.webhook_service.asyncio.create_task", side_effect=dispatched.append),
    ):
        mock_loop.return_value.run_in_executor = AsyncMock(return_value=None)
        with caplog.at_level(logging.WARNING, logger="services.webhook_service"):
            await _handle_inbound_message(msg)

    # Nenhuma task de dispatch de onboarding deve ser criada
    assert not any("onboarding" in str(t) for t in dispatched), "task de onboarding não deve ser criada para phone estranho"
    # Deve haver log de aviso
    assert any("onboarding" in r.message.lower() or "owner" in r.message.lower() for r in caplog.records)


# ---------------------------------------------------------------------------
# Ativação quando onboarding_complete=True
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_onboarding_activates_tenant_when_complete():
    """dispatch_onboarding_agent chama update_tenant_config e complete_onboarding quando onboarding_complete=True."""
    from services.onboarding_dispatch import dispatch_onboarding_agent

    dados_completos = {
        "name": "Marmox",
        "services": ["Bancada"],
        "regions": ["SP"],
        "business_hours": "Seg-Sex 8h-18h",
        "welcome_message": "Olá!",
        "onboarding_complete": True,
    }
    raw_response = "Configuração concluída! [DADOS_EMPRESA]{...}[/DADOS_EMPRESA]"
    clean_text = "Configuração concluída!"

    update_calls = []
    complete_calls = []

    async def fake_to_thread(fn, *args, **kwargs):
        if fn.__name__ == "update_tenant_config":
            update_calls.append(args)
        elif fn.__name__ == "complete_onboarding":
            complete_calls.append(args)
        elif fn.__name__ == "load_conversation_history":
            return []
        return None

    with (
        patch("services.onboarding_dispatch.set_tenant_context"),
        patch("services.onboarding_dispatch.asyncio.to_thread", side_effect=fake_to_thread),
        patch("services.onboarding_dispatch.process_onboarding_message", new_callable=AsyncMock, return_value=raw_response),
        patch("services.onboarding_dispatch.parse_empresa_block", return_value=(dados_completos, clean_text)),
        patch("services.onboarding_dispatch.send_message", new_callable=AsyncMock),
        patch("services.onboarding_dispatch.persist_outbound_message"),
    ):
        await dispatch_onboarding_agent(TENANT_ID, OWNER_PHONE, "Todas as infos fornecidas")

    assert len(update_calls) == 1, "update_tenant_config deve ser chamado uma vez"
    assert len(complete_calls) == 1, "complete_onboarding deve ser chamado uma vez"


# ---------------------------------------------------------------------------
# Bloco [DADOS_EMPRESA] não aparece na resposta enviada
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_onboarding_does_not_send_block_to_owner():
    """A resposta enviada ao dono não contém o bloco [DADOS_EMPRESA]."""
    from services.onboarding_dispatch import dispatch_onboarding_agent

    dados_parciais = {
        "name": "Marmox",
        "services": None,
        "regions": None,
        "business_hours": None,
        "welcome_message": None,
        "onboarding_complete": False,
    }
    clean_text = "Qual o nome da empresa?"
    raw_response = clean_text + "\n[DADOS_EMPRESA]{...}[/DADOS_EMPRESA]"

    sent_messages = []

    async def fake_send(tenant_id, phone, text):
        sent_messages.append(text)

    async def fake_to_thread(fn, *args, **kwargs):
        if fn.__name__ == "load_conversation_history":
            return []
        return None

    with (
        patch("services.onboarding_dispatch.set_tenant_context"),
        patch("services.onboarding_dispatch.asyncio.to_thread", side_effect=fake_to_thread),
        patch("services.onboarding_dispatch.process_onboarding_message", new_callable=AsyncMock, return_value=raw_response),
        patch("services.onboarding_dispatch.parse_empresa_block", return_value=(dados_parciais, clean_text)),
        patch("services.onboarding_dispatch.send_message", side_effect=fake_send),
        patch("services.onboarding_dispatch.persist_outbound_message"),
    ):
        await dispatch_onboarding_agent(TENANT_ID, OWNER_PHONE, "Olá")

    assert sent_messages, "send_message deve ter sido chamado"
    for msg in sent_messages:
        assert "[DADOS_EMPRESA]" not in msg
        assert "[/DADOS_EMPRESA]" not in msg


# ---------------------------------------------------------------------------
# Falha em _dispatch_onboarding_agent é absorvida
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_onboarding_absorbs_exceptions():
    """Falhas em dispatch_onboarding_agent são capturadas e não propagadas."""
    from services.onboarding_dispatch import dispatch_onboarding_agent

    async def fake_to_thread_raises(fn, *args, **kwargs):
        raise RuntimeError("DB error")

    with (
        patch("services.onboarding_dispatch.set_tenant_context"),
        patch("services.onboarding_dispatch.asyncio.to_thread", side_effect=fake_to_thread_raises),
    ):
        # Não deve lançar exceção
        await dispatch_onboarding_agent(TENANT_ID, OWNER_PHONE, "Olá")
