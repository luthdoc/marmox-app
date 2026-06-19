-- Migration: 009_meta_api
-- Descrição: Adiciona whatsapp_phone_number_id para integração com Meta WhatsApp Cloud API.
--            Substitui evolution_instance_name como identificador do número WhatsApp do tenant.
--            evolution_instance_name é mantido para não quebrar dados existentes.
-- Executar no Supabase SQL Editor.

ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS whatsapp_phone_number_id TEXT;

CREATE INDEX IF NOT EXISTS idx_tenants_whatsapp_phone_number_id
    ON tenants(whatsapp_phone_number_id);
