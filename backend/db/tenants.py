"""
Funções de acesso à tabela tenants (Story 3.4).

Exporta:
- get_tenant_context: retorna contexto do tenant para injeção no system prompt.
"""
from __future__ import annotations

from db.client import get_client, set_tenant_context


_TENANT_CONTEXT_FIELDS = "name, services, regions, business_hours, welcome_message"


def _filter_empty_fields(row: dict) -> dict:
    """Remove campos None, lista vazia ou string vazia do row do tenant."""
    return {k: v for k, v in row.items() if v is not None and v != [] and v != ""}


def _query_tenant_row(client, tenant_id: str) -> dict | None:
    """Executa SELECT do tenant; retorna o primeiro row ou None."""
    rows = (
        client.table("tenants")
        .select(_TENANT_CONTEXT_FIELDS)
        .eq("id", tenant_id)
        .execute()
        .data
    )
    return rows[0] if rows else None


def get_tenant_context(tenant_id: str) -> dict:
    """Retorna o contexto do tenant para injeção no system prompt dinâmico."""
    set_tenant_context(tenant_id)
    client = get_client()
    row = _query_tenant_row(client, tenant_id)
    if row is None:
        return {}
    return _filter_empty_fields(row)
