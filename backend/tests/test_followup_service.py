"""
Tests for followup execution service (Story 4.3).

Verifies that:
- send_first_followup sends message and updates follow_up_1_sent_at
- send_second_followup sends message, marks lead cold, notifies owner
- Z-API failures do not interrupt the job loop
- owner_phone NULL does not raise exception
- run_followup_job iterates active tenants and processes both follow-up types
"""
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest


TENANT_ID = "tenant-uuid-abc"
LEAD_FIRST = {
    "id": "lead-1",
    "tenant_id": TENANT_ID,
    "phone": "5511999999999",
    "name": "Ana",
    "status": "new",
    "last_contact_at": "2026-05-27T00:00:00+00:00",
    "follow_up_1_sent_at": None,
}
LEAD_SECOND = {
    "id": "lead-2",
    "tenant_id": TENANT_ID,
    "phone": "5511888888888",
    "name": "Bruno",
    "status": "qualifying",
    "last_contact_at": "2026-05-20T00:00:00+00:00",
    "follow_up_1_sent_at": "2026-05-21T00:00:00+00:00",
}


# ---------------------------------------------------------------------------
# send_first_followup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_first_followup_sends_message_and_updates_timestamp():
    """send_first_followup deve enviar mensagem e atualizar follow_up_1_sent_at."""
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        LEAD_FIRST
    ]

    with (
        patch("services.followup_service.send_message", new_callable=AsyncMock, return_value=True) as mock_send,
        patch("services.followup_service.get_client", return_value=mock_supabase),
        patch("services.followup_service.set_tenant_context"),
    ):
        from services.followup_service import send_first_followup

        await send_first_followup(TENANT_ID, LEAD_FIRST)

    mock_send.assert_called_once()
    call_args = mock_send.call_args
    assert call_args.args[0] == TENANT_ID
    assert call_args.args[1] == LEAD_FIRST["phone"]

    # Update follow_up_1_sent_at was called
    update_call = mock_supabase.table.return_value.update.call_args
    assert "follow_up_1_sent_at" in update_call.args[0]


@pytest.mark.asyncio
async def test_first_followup_uses_lead_name_in_template():
    """send_first_followup deve interpolar o nome do lead no template."""
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []

    with (
        patch("services.followup_service.send_message", new_callable=AsyncMock, return_value=True) as mock_send,
        patch("services.followup_service.get_client", return_value=mock_supabase),
        patch("services.followup_service.set_tenant_context"),
    ):
        from services.followup_service import send_first_followup

        await send_first_followup(TENANT_ID, LEAD_FIRST)

    message_text = mock_send.call_args.args[2]
    assert "Ana" in message_text


@pytest.mark.asyncio
async def test_first_followup_uses_voce_when_name_is_none():
    """send_first_followup deve usar 'você' quando o nome do lead for None."""
    lead_no_name = {**LEAD_FIRST, "name": None}
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []

    with (
        patch("services.followup_service.send_message", new_callable=AsyncMock, return_value=True) as mock_send,
        patch("services.followup_service.get_client", return_value=mock_supabase),
        patch("services.followup_service.set_tenant_context"),
    ):
        from services.followup_service import send_first_followup

        await send_first_followup(TENANT_ID, lead_no_name)

    message_text = mock_send.call_args.args[2]
    assert "você" in message_text


@pytest.mark.asyncio
async def test_first_followup_calls_set_tenant_context_before_update():
    """send_first_followup deve chamar set_tenant_context antes do update."""
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []
    call_order = []

    def record_set_ctx(tenant_id):
        call_order.append("set_tenant_context")

    mock_supabase.table.side_effect = lambda name: (
        call_order.append("table"),
        MagicMock(),
    )[1]

    with (
        patch("services.followup_service.send_message", new_callable=AsyncMock, return_value=True),
        patch("services.followup_service.get_client", return_value=mock_supabase),
        patch("services.followup_service.set_tenant_context", side_effect=record_set_ctx),
    ):
        from services.followup_service import send_first_followup

        await send_first_followup(TENANT_ID, LEAD_FIRST)

    assert call_order[0] == "set_tenant_context"


# ---------------------------------------------------------------------------
# send_second_followup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_second_followup_sends_message_marks_cold_and_notifies_owner():
    """send_second_followup deve enviar mensagem, marcar cold e notificar dono."""
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        {**LEAD_SECOND, "status": "cold"}
    ]

    with (
        patch("services.followup_service.send_message", new_callable=AsyncMock, return_value=True) as mock_send,
        patch("services.followup_service.get_client", return_value=mock_supabase),
        patch("services.followup_service.set_tenant_context"),
        patch(
            "services.followup_service.notify_owner_lead_cold",
            new_callable=AsyncMock,
        ) as mock_notify,
    ):
        from services.followup_service import send_second_followup

        await send_second_followup(TENANT_ID, LEAD_SECOND)

    mock_send.assert_called_once()
    update_call = mock_supabase.table.return_value.update.call_args
    assert update_call.args[0].get("status") == "cold"
    mock_notify.assert_called_once_with(TENANT_ID, LEAD_SECOND)


@pytest.mark.asyncio
async def test_second_followup_zapi_failure_does_not_propagate():
    """Falha no envio Z-API em send_second_followup não deve propagar exceção."""
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []

    with (
        patch("services.followup_service.send_message", new_callable=AsyncMock, side_effect=Exception("Z-API down")),
        patch("services.followup_service.get_client", return_value=mock_supabase),
        patch("services.followup_service.set_tenant_context"),
        patch("services.followup_service.notify_owner_lead_cold", new_callable=AsyncMock),
    ):
        from services.followup_service import send_second_followup

        # Should not raise
        await send_second_followup(TENANT_ID, LEAD_SECOND)


@pytest.mark.asyncio
async def test_first_followup_zapi_failure_does_not_propagate():
    """Falha no envio Z-API em send_first_followup não deve propagar exceção."""
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []

    with (
        patch("services.followup_service.send_message", new_callable=AsyncMock, side_effect=Exception("Z-API down")),
        patch("services.followup_service.get_client", return_value=mock_supabase),
        patch("services.followup_service.set_tenant_context"),
    ):
        from services.followup_service import send_first_followup

        await send_first_followup(TENANT_ID, LEAD_FIRST)


# ---------------------------------------------------------------------------
# notify_owner_lead_cold (in notification_service)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notify_owner_lead_cold_sends_message_to_owner():
    """notify_owner_lead_cold deve buscar owner_phone e enviar mensagem ao dono."""
    with (
        patch("services.notification_service.get_owner_phone", return_value="5511777777777"),
        patch("services.notification_service.send_message", new_callable=AsyncMock) as mock_send,
    ):
        from services.notification_service import notify_owner_lead_cold

        await notify_owner_lead_cold(TENANT_ID, LEAD_SECOND)

    mock_send.assert_called_once()
    assert mock_send.call_args.args[1] == "5511777777777"


@pytest.mark.asyncio
async def test_notify_owner_lead_cold_owner_phone_null_does_not_raise():
    """notify_owner_lead_cold com owner_phone NULL deve retornar sem exceção."""
    with (
        patch("services.notification_service.get_owner_phone", return_value=None),
        patch("services.notification_service.send_message", new_callable=AsyncMock) as mock_send,
    ):
        from services.notification_service import notify_owner_lead_cold

        await notify_owner_lead_cold(TENANT_ID, LEAD_SECOND)

    mock_send.assert_not_called()


# ---------------------------------------------------------------------------
# run_followup_job
# ---------------------------------------------------------------------------


def test_run_followup_job_processes_all_active_tenants():
    """run_followup_job deve iterar sobre todos os tenants ativos."""
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "tenant-1", "status": "active", "owner_phone": "5511777777777"},
        {"id": "tenant-2", "status": "active", "owner_phone": None},
    ]

    with (
        patch("services.followup_service.get_client", return_value=mock_supabase),
        patch("services.followup_service.get_leads_for_first_followup", return_value=[]) as mock_first,
        patch("services.followup_service.get_leads_for_second_followup", return_value=[]) as mock_second,
    ):
        from services.followup_service import run_followup_job

        run_followup_job()

    assert mock_first.call_count == 2
    assert mock_second.call_count == 2
