"""
Serviço de qualificação de leads — Story 3.4.

Responsabilidades:
- parse_lead_data_block: extrai e remove o bloco [DADOS_LEAD]...[/DADOS_LEAD] da resposta do Claude
- compute_lead_status: calcula a transição de status do lead com base nos dados extraídos
"""
from __future__ import annotations

import json
import re

_BLOCK_RE = re.compile(
    r"\[DADOS_LEAD\]\s*(.*?)\s*\[/DADOS_LEAD\]",
    re.DOTALL,
)

_REQUIRED_FOR_QUALIFIED = ("name", "service_type", "region")

_STATUS_PROGRESSION = ("new", "qualifying", "qualified", "scheduled", "handoff", "cold")


def parse_lead_data_block(response: str) -> tuple[dict | None, str]:
    """Extrai o bloco JSON delimitado da resposta do Claude e retorna dados e texto limpo.

    O bloco esperado tem o formato:
        [DADOS_LEAD]
        {"name": "...", "service_type": "...", ...}
        [/DADOS_LEAD]

    Se o bloco estiver ausente ou o JSON for inválido, retorna (None, response_original).
    O texto limpo nunca contém o bloco — é o que deve ser enviado ao lead (AC 8).

    Args:
        response: Texto completo retornado pelo Claude, possivelmente com o bloco.

    Returns:
        Tupla (dados_extraídos_ou_None, texto_sem_bloco).
    """
    match = _BLOCK_RE.search(response)
    if not match:
        return None, response

    raw_json = match.group(1).strip()
    clean_text = _BLOCK_RE.sub("", response).strip()

    try:
        lead_data = json.loads(raw_json)
    except json.JSONDecodeError:
        return None, response

    return lead_data, clean_text


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
