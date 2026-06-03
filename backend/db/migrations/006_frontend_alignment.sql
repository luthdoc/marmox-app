-- Migration: 006_frontend_alignment
-- Corrige divergências entre o schema das migrations anteriores e as queries
-- do frontend dashboard. Todas as alterações são aditivas.

-- ============================================================
-- 1. tenants.user_id
-- Liga cada tenant ao usuário do Supabase Auth que o controla.
-- Usado em: dashboard/configuracoes/page.tsx
-- ============================================================
ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL;

-- ============================================================
-- 2. Tabela: conversations
-- Intermediária entre leads e messages. Um lead tem uma conversa,
-- uma conversa tem muitas mensagens.
-- Usado em: dashboard/leads/[id]/page.tsx
-- ============================================================
CREATE TABLE IF NOT EXISTS conversations (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id  UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lead_id    UUID NOT NULL REFERENCES leads(id)   ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_conversations_lead_id
    ON conversations(lead_id);

CREATE INDEX IF NOT EXISTS idx_conversations_tenant_id
    ON conversations(tenant_id);

ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

CREATE POLICY conversations_tenant_isolation ON conversations
    USING (tenant_id = current_setting('app.tenant_id')::uuid);

-- ============================================================
-- 3. messages.conversation_id
-- Liga cada mensagem à sua conversa.
-- Usado em: dashboard/leads/[id]/page.tsx
-- ============================================================
ALTER TABLE messages
    ADD COLUMN IF NOT EXISTS conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL;

-- ============================================================
-- 4. leads.neighborhood
-- Campo de localização exibido como "Bairro" no dashboard.
-- A coluna region (002) é mantida — usada pelo backend do agente.
-- Usado em: dashboard/leads/[id]/page.tsx, components/LeadDetails.tsx
-- ============================================================
ALTER TABLE leads
    ADD COLUMN IF NOT EXISTS neighborhood TEXT;
