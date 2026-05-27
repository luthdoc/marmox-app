"""
Módulo de acesso ao banco de dados.

Exporta:
- get_client: retorna a instância singleton do cliente Supabase.
- set_tenant_context: define app.tenant_id na sessão Postgres para RLS.
"""
from db.client import get_client, set_tenant_context

__all__ = ["get_client", "set_tenant_context"]
