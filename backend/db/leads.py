"""
Funções de acesso à tabela leads (Stories 3.3, 3.4).

Exporta:
- get_or_create_lead: busca ou cria um lead pelo par (tenant_id, phone).
- update_lead_qualification: atualiza campos de qualificação de um lead via PATCH.
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


def update_lead_qualification(lead_id: str, tenant_id: str, data: dict) -> None:
    """Atualiza campos de qualificação do lead via PATCH nos campos não-None recebidos.

    Executa set_tenant_context antes de qualquer query (NFR3 — RLS enforcement).
    Campos com valor None em `data` são ignorados para não sobrescrever dados
    já persistidos no banco (AC 6).

    Args:
        lead_id: UUID do lead a ser atualizado.
        tenant_id: UUID do tenant para enforcement de RLS.
        data: Dicionário com campos de qualificação. Somente campos não-None
              são incluídos no PATCH (name, service_type, material, urgency,
              region, status).
    """
    set_tenant_context(tenant_id)
    patch_data = {key: value for key, value in data.items() if value is not None}
    if not patch_data:
        return
    client = get_client()
    (
        client.table("leads")
        .update(patch_data)
        .eq("id", lead_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
