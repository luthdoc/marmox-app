-- Migration: 002_lead_qualification
-- Descrição: Adiciona colunas de qualificação à tabela leads, owner_phone a tenants,
--            e media_url a messages. Migration aditiva — não altera colunas existentes.
-- Executar no Supabase SQL Editor ou via CLI.

-- ============================================================
-- Tabela: leads — campos de qualificação
-- ============================================================
ALTER TABLE leads
    ADD COLUMN IF NOT EXISTS service_type  TEXT,
    ADD COLUMN IF NOT EXISTS material      TEXT,
    ADD COLUMN IF NOT EXISTS urgency       TEXT,
    ADD COLUMN IF NOT EXISTS region        TEXT,
    ADD COLUMN IF NOT EXISTS scheduled_at  TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS notes         TEXT;

-- ============================================================
-- Tabela: tenants — contato do dono (Story 3.6)
-- ============================================================
ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS owner_phone TEXT;

-- ============================================================
-- Tabela: messages — URL de mídia (Story 3.5)
-- ============================================================
ALTER TABLE messages
    ADD COLUMN IF NOT EXISTS media_url TEXT;
