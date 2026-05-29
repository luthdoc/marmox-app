-- Migration 005: Adiciona owner_phone à tabela tenants (Story 5.1)
-- Idempotente: ADD COLUMN IF NOT EXISTS
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS owner_phone TEXT;
