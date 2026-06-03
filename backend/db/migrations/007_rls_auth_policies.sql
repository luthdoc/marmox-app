-- Migration: 007_rls_auth_policies
-- As políticas de RLS anteriores usam current_setting('app.tenant_id'), que só
-- funciona no backend (service_role). O frontend usa Supabase Auth (JWT), então
-- as queries retornavam vazio silenciosamente.
--
-- Solução: políticas baseadas em auth.uid() via tabela tenants.
-- O backend usa service_role key, que bypassa RLS por completo — não é afetado.

-- ============================================================
-- Tabela: tenants — habilita RLS e expõe ao usuário dono
-- ============================================================
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenants_owner ON tenants;
CREATE POLICY tenants_owner ON tenants
    USING (user_id = auth.uid());

-- ============================================================
-- Tabela: leads — substitui política de backend por auth.uid()
-- ============================================================
DROP POLICY IF EXISTS leads_tenant_isolation ON leads;
CREATE POLICY leads_tenant_isolation ON leads
    USING (
        tenant_id IN (
            SELECT id FROM tenants WHERE user_id = auth.uid()
        )
    );

-- ============================================================
-- Tabela: messages — substitui política de backend por auth.uid()
-- ============================================================
DROP POLICY IF EXISTS messages_tenant_isolation ON messages;
CREATE POLICY messages_tenant_isolation ON messages
    USING (
        tenant_id IN (
            SELECT id FROM tenants WHERE user_id = auth.uid()
        )
    );

-- ============================================================
-- Tabela: conversations — mesma política
-- ============================================================
DROP POLICY IF EXISTS conversations_tenant_isolation ON conversations;
CREATE POLICY conversations_tenant_isolation ON conversations
    USING (
        tenant_id IN (
            SELECT id FROM tenants WHERE user_id = auth.uid()
        )
    );
