"""Testes para o helper de entrega canônica de mensagens outbound."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

TENANT_ID = "tenant-uuid-001"
PHONE = "5511999999999"
TEXT = "Olá, lead!"
LEAD_ID = "lead-uuid-001"


@pytest.mark.asyncio
async def test_deliver_message_returns_true_and_persists_on_success():
    """deliver_message retorna True e chama persist quando send_message bem-sucedido."""
    with (
        patch("services.message_delivery.send_message", new_callable=AsyncMock, return_value=True),
        patch("services.message_delivery.persist_outbound_message") as mock_persist,
    ):
        from services.message_delivery import deliver_message

        result = await deliver_message(TENANT_ID, PHONE, TEXT, lead_id=LEAD_ID)

    assert result is True
    mock_persist.assert_called_once_with(
        tenant_id=TENANT_ID,
        phone=PHONE,
        content=TEXT,
        lead_id=LEAD_ID,
    )


@pytest.mark.asyncio
async def test_deliver_message_returns_false_and_does_not_persist_on_failure():
    """deliver_message retorna False e não persiste quando send_message retorna False."""
    with (
        patch("services.message_delivery.send_message", new_callable=AsyncMock, return_value=False),
        patch("services.message_delivery.persist_outbound_message") as mock_persist,
    ):
        from services.message_delivery import deliver_message

        result = await deliver_message(TENANT_ID, PHONE, TEXT)

    assert result is False
    mock_persist.assert_not_called()


@pytest.mark.asyncio
async def test_deliver_message_passes_lead_id_to_persist():
    """deliver_message passa lead_id correto para persist_outbound_message."""
    with (
        patch("services.message_delivery.send_message", new_callable=AsyncMock, return_value=True),
        patch("services.message_delivery.persist_outbound_message") as mock_persist,
    ):
        from services.message_delivery import deliver_message

        await deliver_message(TENANT_ID, PHONE, TEXT, lead_id=LEAD_ID)

    assert mock_persist.call_args.kwargs["lead_id"] == LEAD_ID


@pytest.mark.asyncio
async def test_deliver_message_uses_none_lead_id_when_omitted():
    """deliver_message usa lead_id=None quando não fornecido."""
    with (
        patch("services.message_delivery.send_message", new_callable=AsyncMock, return_value=True),
        patch("services.message_delivery.persist_outbound_message") as mock_persist,
    ):
        from services.message_delivery import deliver_message

        await deliver_message(TENANT_ID, PHONE, TEXT)

    assert mock_persist.call_args.kwargs["lead_id"] is None
