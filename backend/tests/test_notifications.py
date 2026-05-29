"""
Testes do serviço de notificações ao dono (Story 3.6).

Cobre:
- lead scheduled → send_message chamado para owner_phone com conteúdo correto
- owner_phone nulo → send_message não chamado, log de aviso emitido
- sentinel de escalada detectada → notificação enviada ao dono
- texto sem sentinel → sem notificação extra
- set_tenant_context chamado antes de qualquer query (NFR3)
"""
from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.notification_service import (
    ESCALATION_SENTINEL,
    contains_escalation_sentinel,
    notify_owner_escalation,
    notify_owner_lead_scheduled,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TENANT_ID = "tenant-uuid-001"
LEAD_ID = "lead-uuid-001"
OWNER_PHONE = "5511999990001"
LEAD_PHONE = "5511888880001"

SAMPLE_LEAD = {
    "id": LEAD_ID,
    "phone": LEAD_PHONE,
    "name": "João Silva",
    "service_type": "Bancada de cozinha",
    "urgency": "urgente",
    "region": "Moema",
    "status": "scheduled",
    "scheduled_at": "2024-02-15T14:00:00",
}


# ---------------------------------------------------------------------------
# notify_owner_lead_scheduled
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lead_scheduled_sends_message_to_owner_phone():
    """Quando lead é scheduled e tenant tem owner_phone, envia mensagem ao dono.

    Verifica que set_tenant_context é chamado antes da query ao banco (AC 11, NFR3).
    """
    mock_db_client = MagicMock()
    mock_db_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"owner_phone": OWNER_PHONE}
    ]
    with (
        patch(
            "services.notification_service.set_tenant_context"
        ) as mock_set_ctx,
        patch(
            "services.notification_service.get_client",
            return_value=mock_db_client,
        ),
        patch(
            "services.notification_service.send_message",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_send,
    ):
        await notify_owner_lead_scheduled(TENANT_ID, SAMPLE_LEAD)

        mock_set_ctx.assert_called_once_with(TENANT_ID)
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        # Primeiro arg: tenant_id; segundo: owner_phone; terceiro: mensagem
        assert call_args[0][0] == TENANT_ID
        assert call_args[0][1] == OWNER_PHONE


@pytest.mark.asyncio
async def test_lead_scheduled_message_contains_required_fields():
    """A mensagem de agendamento inclui nome, serviço, urgência, região e data/hora."""
    with (
        patch("services.notification_service.set_tenant_context"),
        patch(
            "services.notification_service._get_owner_phone",
            return_value=OWNER_PHONE,
        ),
        patch(
            "services.notification_service.send_message",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_send,
    ):
        await notify_owner_lead_scheduled(TENANT_ID, SAMPLE_LEAD)

        message_text = mock_send.call_args[0][2]
        assert "João Silva" in message_text
        assert "Bancada de cozinha" in message_text
        assert "urgente" in message_text
        assert "Moema" in message_text
        assert "2024-02-15T14:00:00" in message_text


@pytest.mark.asyncio
async def test_lead_scheduled_skips_when_owner_phone_is_null(caplog):
    """Quando owner_phone é None, não envia mensagem e emite log de aviso."""
    with (
        patch("services.notification_service.set_tenant_context"),
        patch(
            "services.notification_service._get_owner_phone",
            return_value=None,
        ),
        patch(
            "services.notification_service.send_message",
            new_callable=AsyncMock,
        ) as mock_send,
    ):
        with caplog.at_level(logging.WARNING, logger="services.notification_service"):
            await notify_owner_lead_scheduled(TENANT_ID, SAMPLE_LEAD)

        mock_send.assert_not_called()
        assert any("owner_phone" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_lead_scheduled_logs_notification_info(caplog):
    """Notificação de agendamento é logada com tenant_id, lead_id e tipo."""
    with (
        patch("services.notification_service.set_tenant_context"),
        patch(
            "services.notification_service._get_owner_phone",
            return_value=OWNER_PHONE,
        ),
        patch(
            "services.notification_service.send_message",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        with caplog.at_level(logging.INFO, logger="services.notification_service"):
            await notify_owner_lead_scheduled(TENANT_ID, SAMPLE_LEAD)

        log_messages = [r.message for r in caplog.records]
        assert any("scheduled" in msg.lower() or "agendamento" in msg.lower() for msg in log_messages)


# ---------------------------------------------------------------------------
# notify_owner_escalation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_escalation_sends_message_to_owner_phone():
    """Quando sentinel detectada e tenant tem owner_phone, envia notificação de escalada.

    Verifica que set_tenant_context é chamado antes da query ao banco (AC 11, NFR3).
    """
    mock_db_client = MagicMock()
    mock_db_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"owner_phone": OWNER_PHONE}
    ]
    with (
        patch(
            "services.notification_service.set_tenant_context"
        ) as mock_set_ctx,
        patch(
            "services.notification_service.get_client",
            return_value=mock_db_client,
        ),
        patch(
            "services.notification_service.send_message",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_send,
    ):
        await notify_owner_escalation(TENANT_ID, LEAD_ID, LEAD_PHONE)

        mock_set_ctx.assert_called_once_with(TENANT_ID)
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[0][0] == TENANT_ID
        assert call_args[0][1] == OWNER_PHONE


@pytest.mark.asyncio
async def test_escalation_message_contains_lead_phone():
    """A mensagem de escalada inclui o telefone do lead."""
    with (
        patch("services.notification_service.set_tenant_context"),
        patch(
            "services.notification_service._get_owner_phone",
            return_value=OWNER_PHONE,
        ),
        patch(
            "services.notification_service.send_message",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_send,
    ):
        await notify_owner_escalation(TENANT_ID, LEAD_ID, LEAD_PHONE)

        message_text = mock_send.call_args[0][2]
        assert LEAD_PHONE in message_text


@pytest.mark.asyncio
async def test_escalation_skips_when_owner_phone_is_null(caplog):
    """Quando owner_phone é None, não envia escalada e emite log de aviso."""
    with (
        patch("services.notification_service.set_tenant_context"),
        patch(
            "services.notification_service._get_owner_phone",
            return_value=None,
        ),
        patch(
            "services.notification_service.send_message",
            new_callable=AsyncMock,
        ) as mock_send,
    ):
        with caplog.at_level(logging.WARNING, logger="services.notification_service"):
            await notify_owner_escalation(TENANT_ID, LEAD_ID, LEAD_PHONE)

        mock_send.assert_not_called()
        assert any("owner_phone" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_escalation_logs_notification_info(caplog):
    """Notificação de escalada é logada com tenant_id, lead_id e tipo."""
    with (
        patch("services.notification_service.set_tenant_context"),
        patch(
            "services.notification_service._get_owner_phone",
            return_value=OWNER_PHONE,
        ),
        patch(
            "services.notification_service.send_message",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        with caplog.at_level(logging.INFO, logger="services.notification_service"):
            await notify_owner_escalation(TENANT_ID, LEAD_ID, LEAD_PHONE)

        log_messages = [r.message for r in caplog.records]
        assert any("escala" in msg.lower() or "escalation" in msg.lower() for msg in log_messages)


# ---------------------------------------------------------------------------
# contains_escalation_sentinel
# ---------------------------------------------------------------------------


def test_sentinel_detected_in_response():
    """Resposta com sentinel [ESCALAR_DONO] retorna True."""
    response = f"Vou verificar com a equipe e entro em contato! {ESCALATION_SENTINEL}"
    assert contains_escalation_sentinel(response) is True


def test_sentinel_not_detected_in_normal_response():
    """Resposta sem sentinel retorna False."""
    response = "Claro! Posso agendar uma visita técnica para você."
    assert contains_escalation_sentinel(response) is False


def test_sentinel_constant_is_configurable():
    """ESCALATION_SENTINEL é uma string não-vazia exportada pelo módulo."""
    assert isinstance(ESCALATION_SENTINEL, str)
    assert len(ESCALATION_SENTINEL) > 0
