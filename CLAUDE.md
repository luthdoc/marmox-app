# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Marmax is a WhatsApp AI agent SaaS for marble/stone companies (marmorarias). The agent handles 24/7 lead qualification, visit scheduling, and follow-up automation. Sold at R$ 297/month + R$ 500 setup.

Full requirements: `docs/prd.md` — read it before making product decisions.
Design system: `apple-DESIGN.md` — reference for all UI/dashboard decisions.

## Repository Structure

Monorepo with two apps:

```
backend/   — Python + FastAPI (AI agent, webhooks, scheduling)
frontend/  — Next.js (dashboard for marble company owners)
```

## Backend (Python + FastAPI)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload          # dev server (port 8000)
uvicorn main:app --host 0.0.0.0    # production
```

Key responsibilities: receive Z-API webhooks, orchestrate Claude (Haiku/Sonnet cascade), persist to Supabase, run follow-up scheduler.

## Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev        # dev server (port 3000)
npm run build
npm run lint
```

Dashboard purpose: data management only — lets owners view leads and edit agent configuration. Not a CRM.

## Architecture

### Message Flow

```
WhatsApp lead → Z-API webhook → POST /webhook/whatsapp
                                        ↓
                              Agent orchestration service
                                  ↓           ↓
                            Claude Haiku   Claude Sonnet
                            (simple tasks) (complex + Vision)
                                        ↓
                                   Supabase
                                        ↓
                            Z-API → WhatsApp response
```

### Multi-tenancy

Every database table has a `tenant_id` column. Row Level Security (RLS) is enforced at the Supabase level — never rely solely on application-layer filtering. Each marble company is one tenant.

### Agent Routing

- Default: Claude Haiku (`claude-haiku-4-5-20251001`) for triage, data collection, follow-ups
- Escalate to Claude Sonnet (`claude-sonnet-4-6`) for: image analysis (Vision), complaints, ambiguous intent, anything requiring reasoning
- System prompt is dynamic: tenant data (company name, services, regions, hours) is injected per request
- Prompt caching is enabled on the system prompt to reduce cost

### WhatsApp Integration

Z-API or Evolution API self-hosted connects to the marble company's existing number via QR code. Webhook endpoint receives all inbound messages. Never use the official Meta API in MVP.

### Follow-up Scheduler

Background job runs hourly. Two-touch sequence per lead:

1. 48h after last contact with no response → re-engagement message
2. 7 days after first follow-up with no response → second attempt → mark as `cold`

Leads in status `qualified`, `scheduled`, `handoff`, or `cold` are excluded from follow-up.

### Tenant Lifecycle

`tenant.status` drives routing:

- `onboarding` → webhook routes to onboarding agent (collects company config via WhatsApp chat)
- `active` → webhook routes to main agent

## Environment Variables

See `.env.example` (to be created in `backend/`). Required:

```
SUPABASE_URL
SUPABASE_SERVICE_KEY
ANTHROPIC_API_KEY
ZAPI_INSTANCE_ID
ZAPI_TOKEN
```

## Design System

All dashboard UI must follow `apple-DESIGN.md`. Key constraints:

- Single accent: `#0066cc` (Action Blue) — no second brand color
- Typography: SF Pro Display/Text via `system-ui, -apple-system` stack; Inter as fallback
- No shadows on UI chrome — only on product/hero imagery
- No decorative gradients
- Body text at 17px, not 16px
- Border radius: `pill` (9999px) for CTAs, `lg` (18px) for cards, `sm` (8px) for utility buttons

