"""Fixtures globais de teste — limpeza de tasks fire-and-forget."""
from __future__ import annotations

import asyncio

import pytest


@pytest.fixture(autouse=True)
def cancel_leaked_tasks():
    """Cancela tasks asyncio pendentes no teardown para evitar race conditions cross-test."""
    yield
    try:
        loop = asyncio.get_event_loop_policy().get_event_loop()
        if loop.is_closed() or loop.is_running():
            return
        pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    except Exception:
        pass
