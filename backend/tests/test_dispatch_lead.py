"""
Testes de integração de leads no _dispatch_agent (Story 3.3, AC 7).

Cenários cobertos (AC 7):
- _dispatch_agent chama get_or_create_lead com (tenant_id, phone)
- _dispatch_agent passa lead_id ao persist_outbound_message
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


TENANT_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
PHONE = "5511999999999"
LEAD_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"


def _make_lead_row() -> dict:
    return {
        "id": LEAD_ID,
        "tenant_id": TENANT_ID,
        "phone": PHONE,
        "status": "new",
    }


# ---------------------------------------------------------------------------
# AC 7a — _dispatch_agent chama get_or_create_lead
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_agent_calls_get_or_create_lead():
    """_dispatch_agent deve chamar get_or_create_lead com (tenant_id, phone)."""
    with (
        patch("services.webhook_service.load_conversation_history", return_value=[]),
        patch("services.webhook_service.get_tenant_context", return_value={}),
        patch(
            "services.webhook_service.process_message",
            new_callable=AsyncMock,
            return_value="Resposta",
        ),
        patch("services.webhook_service.send_message", new_callable=AsyncMock),
        patch("services.webhook_service.persist_outbound_message"),
        patch("services.webhook_service.parse_lead_data_block", return_value=(None, "Resposta")),
        patch("services.webhook_service.update_lead_qualification"),
        patch(
            "services.webhook_service.get_or_create_lead",
            return_value=_make_lead_row(),
        ) as mock_get_or_create,
    ):
        from services.webhook_service import _dispatch_agent

        await _dispatch_agent(TENANT_ID, "Marmoraria Teste", PHONE, text="Olá")

    mock_get_or_create.assert_called_once_with(TENANT_ID, PHONE)


# ---------------------------------------------------------------------------
# AC 7b — _dispatch_agent passa lead_id ao persist_outbound_message
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_agent_passes_lead_id_to_persist():
    """_dispatch_agent deve passar o lead_id retornado por get_or_create_lead ao persist_outbound_message."""
    with (
        patch("services.webhook_service.load_conversation_history", return_value=[]),
        patch("services.webhook_service.get_tenant_context", return_value={}),
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
        patch(
            "services.webhook_service.get_or_create_lead",
            return_value=_make_lead_row(),
        ),
    ):
        from services.webhook_service import _dispatch_agent

        await _dispatch_agent(TENANT_ID, "Marmoraria Teste", PHONE, text="Olá")

    mock_persist.assert_called_once_with(
        tenant_id=TENANT_ID,
        phone=PHONE,
        content="Resposta do agente",
        lead_id=LEAD_ID,
    )
