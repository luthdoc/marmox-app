-- Migration: 008_evolution_api
-- Descrição: Substitui colunas Z-API por evolution_instance_name na tabela tenants.
--            evolution_instance_name é o nome da instância criada no servidor
--            Evolution API self-hosted (ex: "marmoraria-joao").
-- Executar no Supabase SQL Editor.

-- Adiciona nova coluna
ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS evolution_instance_name TEXT;

-- Remove colunas Z-API legadas
ALTER TABLE tenants
    DROP COLUMN IF EXISTS zapi_instance_id,
    DROP COLUMN IF EXISTS zapi_token;
