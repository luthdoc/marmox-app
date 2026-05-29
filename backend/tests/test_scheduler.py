"""
Tests for APScheduler integration in FastAPI lifespan.

Verifies that:
- The scheduler starts on application startup
- The followup_job is registered with the correct id
- The scheduler shuts down when the lifespan ends
"""
from unittest.mock import MagicMock, patch

import pytest


def test_scheduler_starts_and_registers_followup_job():
    """Startup deve iniciar o scheduler e registrar o job 'followup_job'."""
    mock_scheduler = MagicMock()
    mock_scheduler.get_jobs.return_value = [MagicMock(id="followup_job")]

    with patch("main.BackgroundScheduler", return_value=mock_scheduler):
        from fastapi.testclient import TestClient

        import main as main_module

        with TestClient(main_module.app):
            mock_scheduler.start.assert_called_once()
            mock_scheduler.add_job.assert_called_once()
            call_kwargs = mock_scheduler.add_job.call_args
            assert call_kwargs.kwargs.get("id") == "followup_job" or (
                len(call_kwargs.args) > 0
                and call_kwargs.kwargs.get("id") == "followup_job"
            )


def test_scheduler_shutdown_called_on_lifespan_exit():
    """Shutdown deve chamar scheduler.shutdown() ao encerrar o lifespan."""
    mock_scheduler = MagicMock()

    with patch("main.BackgroundScheduler", return_value=mock_scheduler):
        from fastapi.testclient import TestClient

        import main as main_module

        with TestClient(main_module.app):
            pass  # lifespan enters and exits here

        mock_scheduler.shutdown.assert_called_once()


def test_followup_job_trigger_is_interval_60_minutes():
    """O job followup_job deve usar trigger 'interval' com hours=1."""
    mock_scheduler = MagicMock()

    with patch("main.BackgroundScheduler", return_value=mock_scheduler):
        from fastapi.testclient import TestClient

        import main as main_module

        with TestClient(main_module.app):
            call_kwargs = mock_scheduler.add_job.call_args
            assert call_kwargs.kwargs.get("trigger") == "interval"
            assert call_kwargs.kwargs.get("hours") == 1
