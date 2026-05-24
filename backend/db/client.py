"""
Cliente Supabase singleton para o backend Marmax.

Fornece:
- get_client(): retorna a instância singleton do cliente Supabase.
- set_tenant_context(tenant_id): define app.tenant_id na sessão Postgres
  para que as políticas RLS filtrem corretamente por tenant.

Fluxo de uso em produção:
    tenant_id = extrair da requisição
    set_tenant_context(tenant_id)
    client = get_client()
    client.table("leads").select("*").execute()
"""
from __future__ import annotations

from supabase import Client, create_client

from core.config import Settings

_client: Client | None = None


def get_client() -> Client:
    """Retorna o singleton do cliente Supabase.

    Inicializa na primeira chamada usando SUPABASE_URL e SUPABASE_SERVICE_KEY
    carregados via core.config.Settings.

    Returns:
        Instância singleton do cliente Supabase.
    """
    global _client
    if _client is None:
        settings = Settings()
        _client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _client


def set_tenant_context(tenant_id: str) -> None:
    """Define o tenant_id na sessão Postgres para enforcement de RLS.

    Executa `SET LOCAL app.tenant_id = '<tenant_id>'` via RPC do Supabase.
    Deve ser chamada antes de qualquer query que precise de isolamento de tenant.

    Args:
        tenant_id: UUID do tenant no formato string (ex: '123e4567-e89b-12d3-a456-426614174000').
    """
    client = get_client()
    client.rpc("set_config", {"parameter": "app.tenant_id", "value": tenant_id}).execute()
