"""
Funções de acesso à tabela tenants (Story 3.4).

Exporta:
- get_tenant_context: retorna contexto do tenant para injeção no system prompt.
"""
from __future__ import annotations

from db.client import get_client, set_tenant_context


def get_tenant_context(tenant_id: str) -> dict:
    """Retorna o contexto do tenant para injeção no system prompt dinâmico.

    Executa set_tenant_context antes de qualquer query (NFR3 — RLS enforcement).
    Campos vazios (None, lista vazia, string vazia) são omitidos do retorno para
    evitar injeção de placeholders inúteis no prompt (Technical Notes).

    Args:
        tenant_id: UUID do tenant.

    Returns:
        Dicionário com campos não-vazios de: name, services, regions,
        business_hours, welcome_message. Retorna {} se tenant não encontrado.
    """
    set_tenant_context(tenant_id)
    client = get_client()

    rows = (
        client.table("tenants")
        .select("name, services, regions, business_hours, welcome_message")
        .eq("id", tenant_id)
        .execute()
        .data
    )

    if not rows:
        return {}

    row = rows[0]
    return {
        key: value
        for key, value in row.items()
        if value is not None and value != [] and value != ""
    }
