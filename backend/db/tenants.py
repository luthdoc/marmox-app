"""
Funções de acesso à tabela tenants (Stories 3.4, 5.1).

Exporta:
- get_tenant_context: retorna contexto do tenant para injeção no system prompt.
- update_tenant_config: persiste configuração coletada pelo onboarding.
- complete_onboarding: marca tenant como 'active'.
- get_owner_phone: retorna o telefone do dono do tenant.
"""
from __future__ import annotations

from db.client import get_client, set_tenant_context


_TENANT_CONTEXT_FIELDS = "name, services, regions, business_hours, welcome_message"

_ALLOWED_CONFIG_FIELDS = frozenset(
    {"name", "services", "regions", "business_hours", "welcome_message"}
)


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


def update_tenant_config(tenant_id: str, config: dict) -> None:
    """Persiste configuração coletada pelo onboarding no tenant.

    Apenas os campos name, services, regions, business_hours e welcome_message
    são escritos. Chaves não reconhecidas são ignoradas silenciosamente (AC3).
    set_tenant_context é chamado antes de qualquer query (NFR3).
    """
    set_tenant_context(tenant_id)
    client = get_client()
    filtered = {k: v for k, v in config.items() if k in _ALLOWED_CONFIG_FIELDS}
    (
        client.table("tenants")
        .update(filtered)
        .eq("id", tenant_id)
        .execute()
    )


def complete_onboarding(tenant_id: str) -> None:
    """Atualiza status do tenant para 'active', concluindo o onboarding.

    set_tenant_context é chamado antes de qualquer query (NFR3).
    """
    set_tenant_context(tenant_id)
    client = get_client()
    (
        client.table("tenants")
        .update({"status": "active"})
        .eq("id", tenant_id)
        .execute()
    )


def get_owner_phone(tenant_id: str) -> str | None:
    """Retorna o owner_phone do tenant ou None se ausente.

    Consolida a lógica de notification_service._get_owner_phone (AC5, AC6).
    set_tenant_context é chamado antes de qualquer query (NFR3).
    """
    set_tenant_context(tenant_id)
    client = get_client()
    rows = (
        client.table("tenants")
        .select("owner_phone")
        .eq("id", tenant_id)
        .execute()
        .data
    )
    if not rows:
        return None
    return rows[0].get("owner_phone") or None
