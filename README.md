# Marmax

Agente de IA no WhatsApp para marmorarias. Qualificação de leads, agendamento de visitas e follow-up automático.

## Estrutura

```
backend/   — Python + FastAPI (agente IA, webhooks, scheduler)
frontend/  — Next.js (dashboard para donos de marmoraria)
```

## Backend

**Requisitos:** Python 3.11+

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

Variáveis de ambiente:

```bash
cp .env.example .env
# edite .env com suas credenciais
```

Iniciar servidor de desenvolvimento:

```bash
uvicorn main:app --reload
# disponível em http://localhost:8000
```

## Frontend

**Requisitos:** Node.js 20+

```bash
cd frontend
npm install
npm run dev
# disponível em http://localhost:3000
```

## Environment Setup

Cada app possui um arquivo `.env.example` com todas as variáveis necessárias documentadas.

### Backend

```bash
cd backend
cp .env.example .env
# Edite .env com suas credenciais reais
```

Variáveis necessárias (ver `backend/.env.example`):

| Variável | Obrigatória | Descrição |
|---|---|---|
| `SUPABASE_URL` | Sim | URL do projeto Supabase |
| `SUPABASE_SERVICE_KEY` | Sim | Chave de serviço do Supabase |
| `ANTHROPIC_API_KEY` | Sim | Chave da API Anthropic (Claude) |
| `ZAPI_INSTANCE_ID` | Sim | ID da instância Z-API |
| `ZAPI_TOKEN` | Sim | Token da instância Z-API |
| `APP_ENV` | Não | `development` ou `production` (padrão: `development`) |
| `LOG_LEVEL` | Não | Nível de log (padrão: `INFO`) |

### Frontend

```bash
cd frontend
cp .env.example .env.local
# Edite .env.local com suas credenciais reais
```

Variáveis necessárias (ver `frontend/.env.example`):

| Variável | Obrigatória | Descrição |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Sim | URL do projeto Supabase |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Sim | Chave anon do Supabase |
| `NEXT_PUBLIC_APP_ENV` | Não | `development` ou `production` (padrão: `development`) |
