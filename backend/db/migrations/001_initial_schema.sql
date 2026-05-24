-- Migration: 001_initial_schema
-- Descrição: Cria as tabelas base (tenants, leads, messages) com
--            multi-tenancy via tenant_id, RLS habilitado em leads e messages,
--            e índices obrigatórios.
-- Executar no Supabase SQL Editor ou via CLI.

-- ============================================================
-- Tabela: tenants
-- ============================================================
CREATE TABLE IF NOT EXISTS tenants (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name             TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'onboarding'
                         CHECK (status IN ('onboarding', 'active')),
    zapi_instance_id TEXT,
    zapi_token       TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- Tabela: leads
-- ============================================================
CREATE TABLE IF NOT EXISTS leads (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    phone           TEXT NOT NULL,
    name            TEXT,
    status          TEXT NOT NULL DEFAULT 'new'
                        CHECK (status IN ('new', 'qualifying', 'qualified', 'scheduled', 'handoff', 'cold')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_contact_at TIMESTAMPTZ
);

-- ============================================================
-- Tabela: messages
-- ============================================================
CREATE TABLE IF NOT EXISTS messages (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id  UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lead_id    UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    direction  TEXT NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    content    TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- Índices obrigatórios
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_leads_tenant_id
    ON leads(tenant_id);

CREATE INDEX IF NOT EXISTS idx_messages_tenant_id_lead_id
    ON messages(tenant_id, lead_id);

-- ============================================================
-- Row Level Security — leads
-- ============================================================
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;

CREATE POLICY leads_tenant_isolation ON leads
    USING (tenant_id = current_setting('app.tenant_id')::uuid);

-- ============================================================
-- Row Level Security — messages
-- ============================================================
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY messages_tenant_isolation ON messages
    USING (tenant_id = current_setting('app.tenant_id')::uuid);
