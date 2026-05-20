# Marmax — Product Requirements Document

## Section 1 — Goals and Background Context

### Goals

- Reduzir o tempo de primeiro contato com leads de marmorarias de horas/dias para segundos, com disponibilidade 24/7
- Qualificar e organizar leads automaticamente, entregando ao dono um resumo estruturado em vez de mensagens bagunçadas no WhatsApp
- Aumentar a taxa de conversão de orçamentos ao eliminar a perda de leads por falta de resposta rápida
- Validar o modelo de negócio com 3 clientes pagantes e retenção >70% no 2º mês pago

### Background Context

Donos de marmorarias pequenas e médias acumulam as funções de operação e vendas sem equipe dedicada. Leads chegam pelo WhatsApp a qualquer hora e frequentemente ficam sem resposta por horas ou dias — tempo suficiente para o cliente fechar com um concorrente. A dor não é falta de demanda, é incapacidade operacional de atender com velocidade e disponibilidade.

O Marmax resolve isso com um agente de IA no WhatsApp da marmoraria que qualifica leads, agenda visitas, executa follow-up automático e escala para o dono apenas quando necessário. O serviço é vendido como SaaS (R$ 297/mês + R$ 500 setup) e validado via pilotos gratuitos de 30 dias com prospecção direta.

### Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-05-19 | 0.1 | Versão inicial | Luis Matheus |
| 2026-05-19 | 0.2 | Recriado sem stories (movidas para eng-epic) | Luis Matheus |

---

## Section 2 — Requirements

### Functional Requirements

**FR1:** O agente recebe e responde mensagens no WhatsApp 24/7, sem intervenção humana para os fluxos cobertos.

**FR2:** O agente se identifica como "assistente virtual da [Nome da Marmoraria]" na primeira mensagem de cada nova conversa, nunca fingindo ser humano.

**FR3:** O agente coleta dados de qualificação do lead em conversa natural: nome, tipo de serviço desejado, material preferido (se aplicável), urgência/prazo e bairro/região.

**FR4:** O agente analisa imagens enviadas pelo lead usando Claude Vision e inclui uma descrição do ambiente/serviço no contexto do lead.

**FR5:** O agente propõe e confirma agendamento de visita técnica com base nos dados coletados.

**FR6:** Ao qualificar um lead, o agente notifica o dono da marmoraria via WhatsApp com resumo estruturado (nome, serviço, urgência, agendamento).

**FR7:** O agente executa follow-up automático em 2 etapas para leads sem resposta: mensagem de reengajamento em 48h e segunda tentativa em 7 dias. Após isso, o lead é marcado como frio e para de receber mensagens automáticas.

**FR8:** Quando não souber responder algo, o agente informa o lead que vai verificar com a equipe e notifica o dono simultaneamente, sem inventar informações.

**FR9:** Um agente de onboarding configura a marmoraria via chat no WhatsApp, coletando: nome da empresa, serviços oferecidos, regiões atendidas, horário de funcionamento e mensagem de boas-vindas.

**FR10:** O dashboard web permite ao dono visualizar e editar os dados de configuração da empresa a qualquer momento.

**FR11:** O sistema suporta múltiplas marmorarias com dados completamente isolados entre clientes (multi-tenancy).

**FR12:** O agente usa Claude Haiku para tarefas simples (triagem, coleta de dados, follow-up), escalando para Claude Sonnet em situações complexas (reclamações, intenções ambíguas, análise de imagens).

### Non-Functional Requirements

**NFR1:** Tempo de resposta do agente < 5 segundos (p95) para mensagens de texto simples.

**NFR2:** Disponibilidade do serviço >= 99% medida mensalmente.

**NFR3:** Nenhuma query retorna dados de um tenant diferente do autenticado — garantido via Row Level Security no Supabase, não apenas por lógica de aplicação.

**NFR4:** O agente nunca afirma informações não cadastradas sobre a marmoraria (ex: preços, prazos) — se não souber, escala.

**NFR5:** Custo de LLM por cliente ≤ R$ 30/mês em volume de até 200 conversas/mês.

**NFR6:** Dados pessoais de leads (nome, telefone, intenção) devem ser deletáveis sob solicitação, em conformidade com LGPD.

---

## Section 3 — User Interface Design Goals

**Overall UX Vision:** Interface utilitária e direta voltada para o dono de marmoraria sem familiaridade com tecnologia. Operável no celular com mínimo de cliques. O dashboard serve o agente — não há complexidade desnecessária.

**Key Interaction Paradigms:**
- Campos inline editáveis nas configurações (sem modais ou fluxos de múltiplos passos)
- Lista de leads com status visual claro
- Visualização de conversa em leitura apenas

**Core Screens and Views:**
- Login — autenticação por email e senha
- Configurações da empresa — dados que alimentam o agente: nome, serviços, regiões, horários, mensagem de boas-vindas
- Lista de leads — nome, serviço, status, data do último contato
- Detalhe do lead — histórico de conversa completo e dados qualificados

**Accessibility:** None (MVP)

**Branding:** Seguir `apple-DESIGN.md` — Action Blue `#0066cc`, SF Pro / Inter, sem gradientes decorativos, sem sombras em UI chrome, body text em 17px.

**Target Platforms:** Web Responsive (mobile-first)

---

## Section 4 — Technical Assumptions

| Decisão | Escolha | Rationale |
|---------|---------|-----------|
| Repository Structure | Monorepo | Backend Python e frontend Next.js no mesmo repositório para simplicidade operacional no MVP |
| Service Architecture | Monolith | FastAPI único; sem microserviços até necessidade comprovada de escala |
| WhatsApp Integration | Z-API / Evolution API self-hosted | Conecta no número existente da marmoraria via QR code, custo zero por mensagem. Migrar para API oficial Meta ao escalar |
| LLM | Anthropic Claude | Haiku para triagem e coleta; Sonnet para análise de imagens e situações complexas. Prompt caching habilitado |
| Banco de Dados | Supabase (PostgreSQL) | Gerenciado, com RLS nativo para multi-tenancy, Auth integrado e Storage para imagens |
| Multi-tenancy | Banco compartilhado + tenant_id + RLS | Seguro, sem overhead operacional, padrão da indústria para SaaS early-stage |
| Backend Hosting | Railway | Deploy de Python simples, ~$5-10/mês. Migrar para VPS/Fly.io ao escalar |
| Frontend Hosting | Vercel | Deploy automático de Next.js, gratuito no plano inicial |
| Auth | Supabase Auth (email/senha) | Integrado ao banco, sem dependência externa adicional |
| Idioma do agente | Português do Brasil | Único idioma suportado no MVP |
| Testing | Manual | Sem cobertura automatizada obrigatória na fase de validação do MVP |
| Integrações externas | Nenhuma além de WhatsApp e LLM | Sem pagamento, CRM externo ou calendário no MVP |

---

## Section 5 — Epic List

```
Epic 1: Foundation          — Monorepo, backend e frontend deployáveis com health-check, logging e env vars configurados
Epic 2: WhatsApp Core       — Integração Z-API funcional: receber webhooks, enviar mensagens, persistir no Supabase com multi-tenancy base
Epic 3: AI Agent Core       — Orquestração Claude (cascade Haiku→Sonnet), qualificação de leads, análise de imagens, contexto persistido
Epic 4: Lead Lifecycle      — Follow-up automático, notificação ao dono, handoff ao lead, marcação de lead frio
Epic 5: Onboarding Agent    — Agente configura a marmoraria via WhatsApp e popula o banco
Epic 6: Dashboard           — Interface Next.js para login, visualização de leads e edição de configurações
```

---

## Section 6 — Next Steps

**Architect Prompt:**
> Com base no PRD em `docs/prd.md`, crie o documento de arquitetura do Marmax. Stack: Python/FastAPI no Railway, Next.js na Vercel, Supabase (PostgreSQL + RLS + Storage), Z-API para WhatsApp, Claude Haiku/Sonnet com prompt caching. Detalhe: estrutura de pastas do monorepo, schema completo do banco com RLS, fluxo de processamento de mensagens (webhook → agente → resposta), serviço de scheduling para follow-up, e como o tenant_id flui por todas as camadas.

**UX Expert Prompt:**
> Com base no PRD em `docs/prd.md` e no design system em `apple-DESIGN.md`, crie o documento de design do dashboard Marmax. O usuário é um dono de marmoraria sem familiaridade técnica, acessa principalmente pelo celular. Foco nas 4 telas: Login, Configurações da empresa, Lista de leads e Detalhe do lead. O dashboard serve apenas para gerenciar dados que alimentam o agente — não é um CRM completo.
