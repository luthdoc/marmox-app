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

## Variáveis de Ambiente

Veja `backend/.env.example` para a lista completa de variáveis necessárias.
