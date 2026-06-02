"""
Serviço de qualificação de leads — Story 3.4.

Responsabilidades:
- parse_lead_data_block: extrai e remove o bloco [DADOS_LEAD]...[/DADOS_LEAD] da resposta do Claude
- compute_lead_status: calcula a transição de status do lead com base nos dados extraídos
- _should_notify_scheduled: detecta transição para status 'scheduled'
"""
from __future__ import annotations

from services.claude_blocks import parse_delimited_json_block

_REQUIRED_FOR_QUALIFIED = ("name", "service_type", "region")

_STATUS_PROGRESSION = ("new", "qualifying", "qualified", "scheduled", "handoff", "cold")


def parse_lead_data_block(response: str) -> tuple[dict | None, str]:
    """Extrai o bloco [DADOS_LEAD]...[/DADOS_LEAD] da resposta do Claude.

    Wrapper sobre parse_delimited_json_block com tag "DADOS_LEAD".
    Retorna (None, response_original) se o bloco estiver ausente ou JSON inválido.
    """
    return parse_delimited_json_block(response, "DADOS_LEAD")


def _should_notify_scheduled(new_status: str, old_status: str | None) -> bool:
    """Retorna True se o lead acabou de ser agendado (transição para 'scheduled')."""
    return new_status == "scheduled" and old_status != "scheduled"


def _is_locked_status(current_status: str) -> bool:
    """Retorna True se o status é avançado demais para regredir (>= scheduled)."""
    idx = _STATUS_PROGRESSION.index(current_status) if current_status in _STATUS_PROGRESSION else 0
    return idx >= _STATUS_PROGRESSION.index("scheduled")


def _is_qualified_or_above(current_status: str) -> bool:
    """Retorna True se o status é qualified ou superior."""
    idx = _STATUS_PROGRESSION.index(current_status) if current_status in _STATUS_PROGRESSION else 0
    return idx >= _STATUS_PROGRESSION.index("qualified")


def _next_status_from_qualifying(current_status: str, extracted: dict) -> str:
    """Calcula transição a partir de new/qualifying com base nos dados extraídos."""
    if all(extracted.get(field) for field in _REQUIRED_FOR_QUALIFIED):
        return "qualified"
    if current_status == "new":
        return "qualifying"
    return current_status


def compute_lead_status(current_status: str, extracted: dict) -> str:
    """Calcula o próximo status do lead com base nos dados extraídos até agora."""
    if _is_locked_status(current_status):
        return current_status
    if current_status == "qualified" and extracted.get("scheduled_at"):
        return "scheduled"
    if _is_qualified_or_above(current_status):
        return current_status
    return _next_status_from_qualifying(current_status, extracted)
