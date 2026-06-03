-- Migration: 008_evolution_instance_name
-- O backend usa evolution_instance_name para identificar a instância WhatsApp
-- do tenant na Evolution API. As migrations anteriores tinham zapi_instance_id
-- e zapi_token (legado Z-API) — mantidos para não quebrar dados existentes.

ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS evolution_instance_name TEXT;
