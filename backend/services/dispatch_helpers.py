"""Helpers auxiliares reutilizáveis do dispatcher (sem dependência circular)."""
from __future__ import annotations


def _should_notify_scheduled(new_status: str, old_status: str | None) -> bool:
    """Retorna True se o lead acabou de ser agendado (transição para 'scheduled')."""
    return new_status == "scheduled" and old_status != "scheduled"
