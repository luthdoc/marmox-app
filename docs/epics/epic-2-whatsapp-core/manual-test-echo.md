# Teste Manual: Echo Bot de Ponta a Ponta (Story 2.4)

## Objetivo

Validar o fluxo completo de echo: mensagem enviada pelo WhatsApp → Z-API webhook → backend → resposta automática `"Recebi: [texto]"` recebida no WhatsApp.

## Pré-requisitos

- Backend rodando (Railway ou local com `uvicorn main:app --reload`)
- Instância Z-API ativa com webhook apontando para o backend
- Acesso ao Supabase (dashboard ou psql)
- Um número de WhatsApp para enviar a mensagem de teste

## 1. Seed do Tenant no Banco

Execute o SQL abaixo no Supabase (SQL Editor ou psql):

```sql
INSERT INTO tenants (
    id,
    name,
    status,
    zapi_instance_id,
    zapi_token,
    created_at
) VALUES (
    gen_random_uuid(),
    'Marmoraria Teste Echo',
    'active',
    '<SEU_ZAPI_INSTANCE_ID>',   -- Ex: 'ABC123XYZ'
    '<SEU_ZAPI_TOKEN>',          -- Token da instância Z-API
    now()
)
RETURNING id;
```

> Substitua `<SEU_ZAPI_INSTANCE_ID>` e `<SEU_ZAPI_TOKEN>` pelos valores reais da sua instância Z-API.
> Anote o `id` retornado — será útil para verificar mensagens persistidas.

## 2. Configurar Webhook no Z-API

No painel da instância Z-API, configure o webhook de mensagens recebidas para:

```
POST https://<SEU_BACKEND_URL>/webhook/whatsapp
Header: X-Zapi-Token: <ZAPI_TOKEN_CONFIGURADO_NO_BACKEND>
```

> O token no header deve bater com a variável `ZAPI_TOKEN` do backend (não necessariamente o token da instância Z-API).

## 3. Enviar Mensagem de Teste

Pelo WhatsApp conectado à instância Z-API, envie qualquer mensagem de texto. Exemplo:

```
Olá, quero um orçamento de mármore carrara
```

## 4. Verificar o Echo

Aguarde até 5 segundos. Você deve receber no mesmo número a resposta:

```
Recebi: Olá, quero um orçamento de mármore carrara
```

## 5. Verificar Persistência no Banco

```sql
-- Mensagem inbound (recebida)
SELECT id, direction, phone, content, created_at
FROM messages
WHERE tenant_id = '<ID_DO_TENANT_SEED>'
ORDER BY created_at DESC
LIMIT 5;

-- Deve conter:
-- direction = 'inbound', content = 'Olá, quero um orçamento de mármore carrara'
-- direction = 'outbound', content = 'Recebi: Olá, quero um orçamento de mármore carrara'
```

## 6. Testar Cenário Onboarding (sem echo)

Para confirmar que tenants em onboarding não recebem echo:

```sql
-- Alterar status do tenant para onboarding
UPDATE tenants
SET status = 'onboarding'
WHERE id = '<ID_DO_TENANT_SEED>';
```

Envie outra mensagem pelo WhatsApp. Nenhum echo deve ser recebido. A mensagem deve aparecer na tabela `messages` com `direction = 'inbound'` mas sem correspondente `outbound`.

Restaure o status:

```sql
UPDATE tenants SET status = 'active' WHERE id = '<ID_DO_TENANT_SEED>';
```

## 7. Verificar Logs do Backend

Nos logs do backend, as seguintes entradas devem aparecer para cada mensagem processada:

```
INFO  Mensagem inbound recebida  {"tenant_id": "...", "phone": "...", "message_length": N, "instance_id": "..."}
INFO  Tentativa de envio Z-API   {"attempt_number": 1, "success": true}
```

## Limpeza (Opcional)

```sql
-- Remover tenant de teste e suas mensagens
DELETE FROM messages WHERE tenant_id = '<ID_DO_TENANT_SEED>';
DELETE FROM tenants WHERE id = '<ID_DO_TENANT_SEED>';
```
