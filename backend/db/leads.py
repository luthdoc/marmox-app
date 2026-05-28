"""
Funções de acesso à tabela leads (Story 3.3).

Exporta:
- get_or_create_lead: busca ou cria um lead pelo par (tenant_id, phone).
"""
from __future__ import annotations

from db.client import get_client, set_tenant_context


def get_or_create_lead(tenant_id: str, phone: str) -> dict:
    """Busca ou cria um lead pelo par (tenant_id, phone).

    Executa set_tenant_context antes de qualquer query (NFR3 — RLS enforcement).
    Usa padrão SELECT-then-INSERT com ON CONFLICT DO NOTHING para evitar duplicatas
    em condições de concorrência.

    Args:
        tenant_id: UUID do tenant para enforcement de RLS.
        phone: Número do lead (formato Z-API, ex: "5511999999999").

    Returns:
        Dicionário com os dados do lead (campos da tabela leads).
        Se o lead não existia, retorna o registro criado com status "new".
    """
    set_tenant_context(tenant_id)
    client = get_client()

    rows = (
        client.table("leads")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("phone", phone)
        .execute()
        .data
    )

    if rows:
        return rows[0]

    inserted = (
        client.table("leads")
        .insert({"tenant_id": tenant_id, "phone": phone, "status": "new"})
        .execute()
        .data
    )
    return inserted[0]
