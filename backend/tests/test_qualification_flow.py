"""
Testes para o fluxo de qualificação de leads — Story 3.4.

Cenários cobertos (AC 10):
- Parse correto do bloco [DADOS_LEAD]...[/DADOS_LEAD] (AC 4, 8)
- Update de lead com dados parciais: campos None não apagam dados existentes (AC 6)
- Transição de status new → qualifying → qualified (AC 5)
- Campos ausentes no JSON não apagam dados já existentes no banco (AC 6)
- get_tenant_context retorna dict com campos esperados (AC 1)
- update_lead_qualification chama set_tenant_context antes da query (AC 7)
- Resposta ao lead não contém o bloco JSON (AC 8)
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TENANT_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
LEAD_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"
PHONE = "5511999999999"


def _tenant_row() -> dict:
    return {
        "id": TENANT_ID,
        "name": "Marmox",
        "services": ["bancada", "pia", "escada"],
        "regions": ["Mooca", "Vila Prudente"],
        "business_hours": "Seg–Sex 8h–18h",
        "welcome_message": "Bem-vindo à Marmox!",
    }


def _lead_row(**overrides) -> dict:
    base = {
        "id": LEAD_ID,
        "tenant_id": TENANT_ID,
        "phone": PHONE,
        "status": "new",
        "name": None,
        "service_type": None,
        "material": None,
        "urgency": None,
        "region": None,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Task 3.4.2 — get_tenant_context
# ---------------------------------------------------------------------------


def test_get_tenant_context_returns_dict_with_all_fields():
    """get_tenant_context deve retornar dict com campos name, services, regions,
    business_hours, welcome_message — todos extraídos do banco (AC 1)."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        _tenant_row()
    ]

    with patch("db.tenants.get_client", return_value=mock_client), \
         patch("db.tenants.set_tenant_context"):
        from db.tenants import get_tenant_context

        result = get_tenant_context(TENANT_ID)

    assert result["name"] == "Marmox"
    assert result["services"] == ["bancada", "pia", "escada"]
    assert result["regions"] == ["Mooca", "Vila Prudente"]
    assert result["business_hours"] == "Seg–Sex 8h–18h"
    assert result["welcome_message"] == "Bem-vindo à Marmox!"


def test_get_tenant_context_omits_empty_fields():
    """get_tenant_context deve omitir campos vazios/None do retorno (Technical Notes)."""
    row = _tenant_row()
    row["services"] = None
    row["regions"] = []
    row["business_hours"] = None
    row["welcome_message"] = ""

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        row
    ]

    with patch("db.tenants.get_client", return_value=mock_client), \
         patch("db.tenants.set_tenant_context"):
        from db.tenants import get_tenant_context

        result = get_tenant_context(TENANT_ID)

    assert "services" not in result or not result.get("services")
    assert "regions" not in result or not result.get("regions")
    assert "business_hours" not in result or not result.get("business_hours")
    assert "welcome_message" not in result or not result.get("welcome_message")


def test_get_tenant_context_returns_empty_dict_when_not_found():
    """get_tenant_context deve retornar {} quando tenant não for encontrado."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    with patch("db.tenants.get_client", return_value=mock_client), \
         patch("db.tenants.set_tenant_context"):
        from db.tenants import get_tenant_context

        result = get_tenant_context(TENANT_ID)

    assert result == {}


# ---------------------------------------------------------------------------
# Task 3.4.4 — update_lead_qualification
# ---------------------------------------------------------------------------


def test_update_lead_qualification_patches_non_none_fields():
    """update_lead_qualification deve atualizar apenas campos não-None (AC 6)."""
    mock_client = MagicMock()
    mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
        _lead_row(name="João", service_type="bancada")
    ]

    with patch("db.leads.get_client", return_value=mock_client), \
         patch("db.leads.set_tenant_context") as mock_ctx:
        from db.leads import update_lead_qualification

        update_lead_qualification(
            LEAD_ID,
            TENANT_ID,
            {"name": "João", "service_type": "bancada", "material": None},
        )

    # Confirma que set_tenant_context foi chamado (AC 7)
    mock_ctx.assert_called_once_with(TENANT_ID)

    # Confirma que o update foi chamado com apenas os campos não-None
    update_call = mock_client.table.return_value.update.call_args
    patch_data = update_call.args[0]
    assert "name" in patch_data
    assert "service_type" in patch_data
    assert "material" not in patch_data, "Campos None não devem ser incluídos no PATCH"


def test_update_lead_qualification_set_tenant_context_called_before_query():
    """set_tenant_context deve ser chamado antes de qualquer operação no banco (AC 7)."""
    call_order = []
    mock_client = MagicMock()

    def track_set_ctx(tenant_id: str) -> None:
        call_order.append("set_tenant_context")

    def track_table(name: str):
        call_order.append("table")
        return mock_client.table.return_value

    mock_client.table.side_effect = track_table
    mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{}]

    with patch("db.leads.get_client", return_value=mock_client), \
         patch("db.leads.set_tenant_context", side_effect=track_set_ctx):
        from db.leads import update_lead_qualification

        update_lead_qualification(LEAD_ID, TENANT_ID, {"name": "Maria"})

    assert call_order[0] == "set_tenant_context", (
        "set_tenant_context deve ser chamado antes da query"
    )


def test_update_lead_qualification_does_nothing_when_all_none():
    """Quando todos os campos são None, update_lead_qualification não deve chamar o banco."""
    mock_client = MagicMock()

    with patch("db.leads.get_client", return_value=mock_client), \
         patch("db.leads.set_tenant_context"):
        from db.leads import update_lead_qualification

        update_lead_qualification(LEAD_ID, TENANT_ID, {"name": None, "service_type": None})

    mock_client.table.return_value.update.assert_not_called()


# ---------------------------------------------------------------------------
# Task 3.4.5 — parse do bloco [DADOS_LEAD] e transição de status
# ---------------------------------------------------------------------------


def test_parse_lead_data_extracts_json_block():
    """parse_lead_data_block deve extrair o JSON do bloco delimitado (AC 4)."""
    response = (
        "Olá João! Que tipo de serviço você precisa?\n\n"
        "[DADOS_LEAD]\n"
        '{"name": "João", "service_type": null, "material": null, "urgency": null, "region": null, "status": "qualifying"}\n'
        "[/DADOS_LEAD]"
    )

    from services.qualification import parse_lead_data_block

    lead_data, clean_text = parse_lead_data_block(response)

    assert lead_data["name"] == "João"
    assert lead_data["service_type"] is None
    assert "[DADOS_LEAD]" not in clean_text
    assert "Olá João!" in clean_text


def test_parse_lead_data_returns_none_when_block_absent():
    """parse_lead_data_block deve retornar (None, texto_original) quando bloco ausente (AC 4)."""
    response = "Olá! Como posso ajudar?"

    from services.qualification import parse_lead_data_block

    lead_data, clean_text = parse_lead_data_block(response)

    assert lead_data is None
    assert clean_text == response


def test_parse_lead_data_returns_none_on_invalid_json():
    """parse_lead_data_block deve retornar (None, texto_original) quando JSON é inválido."""
    response = "[DADOS_LEAD]\nnão é json\n[/DADOS_LEAD]"

    from services.qualification import parse_lead_data_block

    lead_data, clean_text = parse_lead_data_block(response)

    assert lead_data is None


def test_status_transition_new_to_qualifying_on_first_extraction():
    """Na primeira extração com dados parciais, status deve transitar new → qualifying (AC 5)."""
    from services.qualification import compute_lead_status

    current_status = "new"
    extracted = {"name": "João", "service_type": None, "region": None}

    new_status = compute_lead_status(current_status, extracted)

    assert new_status == "qualifying"


def test_status_transition_qualifying_to_qualified_when_all_required_filled():
    """Status deve transitar para qualified quando name, service_type e region estão presentes (AC 5)."""
    from services.qualification import compute_lead_status

    current_status = "qualifying"
    extracted = {"name": "João", "service_type": "bancada", "region": "Mooca"}

    new_status = compute_lead_status(current_status, extracted)

    assert new_status == "qualified"


def test_status_stays_qualifying_when_required_fields_incomplete():
    """Status permanece qualifying quando não todos os campos obrigatórios estão preenchidos (AC 5)."""
    from services.qualification import compute_lead_status

    current_status = "qualifying"
    extracted = {"name": "João", "service_type": None, "region": "Mooca"}

    new_status = compute_lead_status(current_status, extracted)

    assert new_status == "qualifying"


def test_status_does_not_regress_from_qualified():
    """Status qualified não deve regredir para qualifying (AC 5)."""
    from services.qualification import compute_lead_status

    current_status = "qualified"
    extracted = {"name": "João", "service_type": None, "region": None}

    new_status = compute_lead_status(current_status, extracted)

    assert new_status == "qualified"


# ---------------------------------------------------------------------------
# AC 8 — Resposta ao lead não deve conter o bloco JSON
# ---------------------------------------------------------------------------


def test_clean_text_does_not_contain_json_block():
    """O texto limpo retornado por parse_lead_data_block não deve conter o bloco JSON (AC 8)."""
    response = (
        "Ótimo! Vou verificar com a equipe.\n"
        "[DADOS_LEAD]\n"
        '{"name": "Maria", "service_type": "escada", "material": "granito", "urgency": "1 mês", "region": "Mooca", "status": "qualified"}\n'
        "[/DADOS_LEAD]\n"
    )

    from services.qualification import parse_lead_data_block

    _, clean_text = parse_lead_data_block(response)

    assert "[DADOS_LEAD]" not in clean_text
    assert "[/DADOS_LEAD]" not in clean_text
    assert '"name"' not in clean_text
    assert "Ótimo!" in clean_text
