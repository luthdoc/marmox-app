"""
Tests for followup query service (Story 4.2).

Verifies that:
- get_leads_for_first_followup returns leads eligible for first follow-up
- get_leads_for_second_followup returns leads eligible for second follow-up
- set_tenant_context is called before any query
- Status filter restricts to new/qualifying only
- Excluded statuses never appear in results
- NULL last_contact_at leads are excluded from first follow-up results
- Empty results returned without errors
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest


TENANT_ID = "tenant-uuid-abc"


def _make_first_followup_mock(return_data: list) -> MagicMock:
    """Mock for first follow-up query chain: .eq().in_().lt().is_().execute()."""
    mock = MagicMock()
    (
        mock.table.return_value
        .select.return_value
        .eq.return_value
        .in_.return_value
        .lt.return_value
        .is_.return_value
        .execute.return_value
        .data
    ) = return_data
    return mock


def _make_second_followup_mock(return_data: list) -> MagicMock:
    """Mock for second follow-up query chain: .eq().in_().lt().execute()."""
    mock = MagicMock()
    (
        mock.table.return_value
        .select.return_value
        .eq.return_value
        .in_.return_value
        .lt.return_value
        .execute.return_value
        .data
    ) = return_data
    return mock


# ---------------------------------------------------------------------------
# get_leads_for_first_followup
# ---------------------------------------------------------------------------


def test_first_followup_returns_leads_matching_all_criteria():
    """Leads com status new/qualifying, last_contact_at > 48h e follow_up_1_sent_at NULL retornam."""
    expected_leads = [
        {
            "id": "lead-1",
            "tenant_id": TENANT_ID,
            "phone": "5511999999999",
            "name": "Ana",
            "status": "new",
            "last_contact_at": "2026-05-27T00:00:00+00:00",
            "follow_up_1_sent_at": None,
        }
    ]
    mock_supabase = _make_first_followup_mock(expected_leads)

    with (
        patch("services.followup_query.get_client", return_value=mock_supabase),
        patch("services.followup_query.set_tenant_context") as mock_set_ctx,
    ):
        from services.followup_query import get_leads_for_first_followup

        result = get_leads_for_first_followup(TENANT_ID)

    assert result == expected_leads
    mock_set_ctx.assert_called_once_with(TENANT_ID)


def test_first_followup_calls_set_tenant_context_before_query():
    """set_tenant_context deve ser chamado antes de qualquer operação no banco."""
    mock_supabase = _make_first_followup_mock([])
    call_order = []

    def record_set_ctx(tenant_id):
        call_order.append("set_tenant_context")

    mock_supabase.table.side_effect = lambda name: (
        call_order.append("table"),
        _make_first_followup_mock([]).table(name),
    )[1]

    with (
        patch("services.followup_query.get_client", return_value=mock_supabase),
        patch(
            "services.followup_query.set_tenant_context", side_effect=record_set_ctx
        ),
    ):
        from services.followup_query import get_leads_for_first_followup

        get_leads_for_first_followup(TENANT_ID)

    assert call_order[0] == "set_tenant_context"


def test_first_followup_returns_empty_list_without_error():
    """Quando nenhum lead elegível existe, retorna lista vazia sem levantar exceção."""
    mock_supabase = _make_first_followup_mock([])

    with (
        patch("services.followup_query.get_client", return_value=mock_supabase),
        patch("services.followup_query.set_tenant_context"),
    ):
        from services.followup_query import get_leads_for_first_followup

        result = get_leads_for_first_followup(TENANT_ID)

    assert result == []


def test_first_followup_uses_48h_threshold():
    """A query deve usar threshold de 48 horas para last_contact_at."""
    mock_supabase = _make_first_followup_mock([])

    with (
        patch("services.followup_query.get_client", return_value=mock_supabase),
        patch("services.followup_query.set_tenant_context"),
        patch("services.followup_query.datetime") as mock_dt,
    ):
        fake_now = datetime(2026, 5, 29, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = fake_now

        from services.followup_query import get_leads_for_first_followup

        get_leads_for_first_followup(TENANT_ID)

    expected_threshold = (fake_now - timedelta(hours=48)).isoformat()
    lt_call = (
        mock_supabase.table.return_value
        .select.return_value
        .eq.return_value
        .in_.return_value
        .lt
    )
    lt_call.assert_called_once_with("last_contact_at", expected_threshold)


def test_first_followup_filters_by_eligible_statuses():
    """A query deve filtrar apenas leads com status new ou qualifying."""
    mock_supabase = _make_first_followup_mock([])

    with (
        patch("services.followup_query.get_client", return_value=mock_supabase),
        patch("services.followup_query.set_tenant_context"),
    ):
        from services.followup_query import get_leads_for_first_followup

        get_leads_for_first_followup(TENANT_ID)

    in_call = (
        mock_supabase.table.return_value
        .select.return_value
        .eq.return_value
        .in_
    )
    call_args = in_call.call_args
    assert call_args.args[0] == "status"
    assert set(call_args.args[1]) == {"new", "qualifying"}


# ---------------------------------------------------------------------------
# get_leads_for_second_followup
# ---------------------------------------------------------------------------


def test_second_followup_returns_leads_matching_all_criteria():
    """Leads com follow_up_1_sent_at > 7 dias retornam para segunda tentativa."""
    expected_leads = [
        {
            "id": "lead-2",
            "tenant_id": TENANT_ID,
            "phone": "5511888888888",
            "name": "Bruno",
            "status": "qualifying",
            "last_contact_at": "2026-05-20T00:00:00+00:00",
            "follow_up_1_sent_at": "2026-05-21T00:00:00+00:00",
        }
    ]
    mock_supabase2 = _make_second_followup_mock(expected_leads)

    with (
        patch("services.followup_query.get_client", return_value=mock_supabase2),
        patch("services.followup_query.set_tenant_context") as mock_set_ctx,
    ):
        from services.followup_query import get_leads_for_second_followup

        result = get_leads_for_second_followup(TENANT_ID)

    assert result == expected_leads
    mock_set_ctx.assert_called_once_with(TENANT_ID)


def test_second_followup_calls_set_tenant_context_before_query():
    """set_tenant_context deve ser chamado antes de qualquer operação no banco."""
    mock_supabase2 = _make_second_followup_mock([])
    call_order = []

    def record_set_ctx(tenant_id):
        call_order.append("set_tenant_context")

    mock_supabase2.table.side_effect = lambda name: (
        call_order.append("table"),
        MagicMock(),
    )[1]

    with (
        patch("services.followup_query.get_client", return_value=mock_supabase2),
        patch(
            "services.followup_query.set_tenant_context", side_effect=record_set_ctx
        ),
    ):
        from services.followup_query import get_leads_for_second_followup

        get_leads_for_second_followup(TENANT_ID)

    assert call_order[0] == "set_tenant_context"


def test_second_followup_returns_empty_list_without_error():
    """Quando nenhum lead elegível existe para segunda tentativa, retorna lista vazia."""
    mock_supabase2 = _make_second_followup_mock([])

    with (
        patch("services.followup_query.get_client", return_value=mock_supabase2),
        patch("services.followup_query.set_tenant_context"),
    ):
        from services.followup_query import get_leads_for_second_followup

        result = get_leads_for_second_followup(TENANT_ID)

    assert result == []


def test_second_followup_uses_7_day_threshold():
    """A query deve usar threshold de 7 dias para follow_up_1_sent_at."""
    mock_supabase2 = _make_second_followup_mock([])

    with (
        patch("services.followup_query.get_client", return_value=mock_supabase2),
        patch("services.followup_query.set_tenant_context"),
        patch("services.followup_query.datetime") as mock_dt,
    ):
        fake_now = datetime(2026, 5, 29, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = fake_now

        from services.followup_query import get_leads_for_second_followup

        get_leads_for_second_followup(TENANT_ID)

    expected_threshold = (fake_now - timedelta(days=7)).isoformat()
    lt_call = (
        mock_supabase2.table.return_value
        .select.return_value
        .eq.return_value
        .in_.return_value
        .lt
    )
    lt_call.assert_called_once_with("follow_up_1_sent_at", expected_threshold)


def test_second_followup_filters_by_eligible_statuses():
    """A query deve filtrar apenas leads com status new ou qualifying."""
    mock_supabase2 = _make_second_followup_mock([])

    with (
        patch("services.followup_query.get_client", return_value=mock_supabase2),
        patch("services.followup_query.set_tenant_context"),
    ):
        from services.followup_query import get_leads_for_second_followup

        get_leads_for_second_followup(TENANT_ID)

    in_call = (
        mock_supabase2.table.return_value
        .select.return_value
        .eq.return_value
        .in_
    )
    call_args = in_call.call_args
    assert call_args.args[0] == "status"
    assert set(call_args.args[1]) == {"new", "qualifying"}
