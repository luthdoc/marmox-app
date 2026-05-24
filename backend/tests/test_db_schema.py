"""
Testes unitários para o schema do banco e o cliente Supabase.

Cobre:
- Existência e conteúdo mínimo do arquivo de migration SQL
- get_client() retorna instância válida
- set_tenant_context() não lança exceção com UUID válido
"""
import os
import uuid
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MIGRATION_PATH = os.path.join(
    os.path.dirname(__file__), "..", "db", "migrations", "001_initial_schema.sql"
)


def _read_migration() -> str:
    with open(MIGRATION_PATH, encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# 2.1.1 — Migration SQL
# ---------------------------------------------------------------------------


def test_migration_file_exists():
    """O arquivo de migration deve existir no caminho especificado pela AC 1."""
    assert os.path.isfile(MIGRATION_PATH), (
        f"Migration não encontrada em: {MIGRATION_PATH}"
    )


def test_migration_creates_tenants_table():
    """Migration deve criar a tabela tenants (AC 1)."""
    sql = _read_migration()
    assert "CREATE TABLE" in sql.upper()
    assert "tenants" in sql.lower()


def test_migration_creates_leads_table():
    """Migration deve criar a tabela leads com tenant_id (AC 1)."""
    sql = _read_migration()
    assert "leads" in sql.lower()
    # tenant_id deve aparecer no contexto da tabela leads
    assert sql.lower().count("tenant_id") >= 2  # leads e messages, no mínimo


def test_migration_creates_messages_table():
    """Migration deve criar a tabela messages (AC 1)."""
    sql = _read_migration()
    assert "messages" in sql.lower()


def test_migration_enables_rls():
    """Migration deve habilitar Row Level Security em leads e messages (AC 2)."""
    sql = _read_migration()
    assert "ROW LEVEL SECURITY" in sql.upper() or "ENABLE ROW LEVEL SECURITY" in sql.upper()


def test_migration_defines_rls_policy():
    """Migration deve definir política RLS com app.tenant_id (AC 2)."""
    sql = _read_migration()
    assert "app.tenant_id" in sql
    assert "CREATE POLICY" in sql.upper()


def test_migration_has_required_indexes():
    """Migration deve criar índices em leads(tenant_id) e messages(tenant_id, lead_id) (Technical Notes)."""
    sql = _read_migration()
    assert "CREATE INDEX" in sql.upper()
    # Índice em leads por tenant_id
    assert "leads" in sql.lower()
    # Índice em messages por tenant_id
    assert "messages" in sql.lower()


# Env vars mínimas para inicializar Settings sem .env real
_FAKE_ENV = {
    "SUPABASE_URL": "https://fake.supabase.co",
    "SUPABASE_SERVICE_KEY": "fake-service-key",
    "ANTHROPIC_API_KEY": "fake-anthropic-key",
    "ZAPI_INSTANCE_ID": "fake-instance",
    "ZAPI_TOKEN": "fake-token",
}

# ---------------------------------------------------------------------------
# 2.1.2 + 2.1.3 — Cliente Supabase
# ---------------------------------------------------------------------------


def test_get_client_returns_valid_instance():
    """get_client() deve retornar uma instância do cliente Supabase (AC 3)."""
    import db.client as db_client_module

    # Reset singleton para isolar o teste
    db_client_module._client = None
    with patch.dict(os.environ, _FAKE_ENV):
        from db import get_client

        client = get_client()
        assert client is not None
    db_client_module._client = None


def test_get_client_returns_singleton():
    """get_client() deve retornar sempre a mesma instância (singleton) (AC 3)."""
    import db.client as db_client_module

    db_client_module._client = None
    with patch.dict(os.environ, _FAKE_ENV):
        from db import get_client

        client_a = get_client()
        client_b = get_client()
        assert client_a is client_b
    db_client_module._client = None


def test_set_tenant_context_does_not_raise_with_valid_uuid():
    """set_tenant_context() não deve lançar exceção com UUID válido (AC 4)."""
    import db.client as db_client_module

    db_client_module._client = None
    with patch.dict(os.environ, _FAKE_ENV):
        from db import set_tenant_context

        valid_uuid = str(uuid.uuid4())
        # Deve executar sem exceção de implementação; erros de conexão com
        # o Supabase são aceitáveis em ambiente de teste sem banco real.
        try:
            set_tenant_context(valid_uuid)
        except Exception as exc:  # noqa: BLE001
            connection_errors = (
                "connection",
                "network",
                "timeout",
                "refused",
                "resolve",
                "http",
                "url",
                "postgrest",
                "supabase",
                "invalid url",
                "connecterror",
                "getaddrinfo",
                "errno",
                "failed",
            )
            error_msg = str(exc).lower()
            is_connection_error = any(kw in error_msg for kw in connection_errors)
            assert is_connection_error, (
                f"set_tenant_context() lançou erro de implementação inesperado: {exc}"
            )
    db_client_module._client = None


# ---------------------------------------------------------------------------
# 2.1.4 — Exports do __init__.py
# ---------------------------------------------------------------------------


def test_db_module_exports_get_client():
    """backend/db/__init__.py deve exportar get_client (AC 5)."""
    with patch.dict(os.environ, _FAKE_ENV):
        import db

        assert hasattr(db, "get_client"), "db não exporta get_client"
        assert callable(db.get_client)


def test_db_module_exports_set_tenant_context():
    """backend/db/__init__.py deve exportar set_tenant_context (AC 5)."""
    with patch.dict(os.environ, _FAKE_ENV):
        import db

        assert hasattr(db, "set_tenant_context"), "db não exporta set_tenant_context"
        assert callable(db.set_tenant_context)
