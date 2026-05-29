-- Migration: 003_tenant_context
-- Descrição: Adiciona campos de contexto do tenant usados no system prompt dinâmico
--            (Story 3.4). Migration aditiva — não altera colunas existentes.
-- Executar no Supabase SQL Editor ou via CLI.

-- ============================================================
-- Tabela: tenants — contexto para system prompt dinâmico
-- ============================================================
ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS services         TEXT[],
    ADD COLUMN IF NOT EXISTS regions          TEXT[],
    ADD COLUMN IF NOT EXISTS business_hours   TEXT,
    ADD COLUMN IF NOT EXISTS welcome_message  TEXT;
