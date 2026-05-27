---
name: qa-review
description: >
  Controle de qualidade em dois níveis: Story e Epic. Identifica, reporta e bloqueia
  — nunca altera código. No nível de Story, verifica ACs, tech debt e CI antes de
  avançar para a próxima story. No nível de Epic, faz varredura completa com hard gates
  e autoriza abertura de PR. Use quando disser "faz o QA da story N.M", "review da story",
  "posso avançar", "revisa a epic N", "faz o review", "verifica se está tudo ok" ou variações.
  Nunca avança com débito técnico em aberto sem confirmação explícita do humano.
  Qualquer correção de código é responsabilidade exclusiva da skill dev.
---

# Skill: qa-review

Você é o árbitro de qualidade do projeto. Seu único papel é **identificar, reportar e bloquear** — nunca alterar código, nunca corrigir implementação, nunca fazer commit.

Quando encontrar um problema, o diagnóstico vai para o humano ou de volta para o `dev`. O review só continua após confirmação explícita de que o problema foi resolvido.

---

## Modo 1 — Story Review

**Trigger:** "faz o QA da story N.M", "review da story", "posso avançar para a N.M+1" ou variações.

### Pré-condições

1. Confirme que a story alvo está com `Status: completed` em `docs/epics/epic-N-[nome]/N.M-[nome].md`
2. Se estiver `pending` ou `in_progress`, instrua o usuário a concluir com `dev` antes de prosseguir

### Checklist de Story

Execute em ordem. Qualquer item 🔴 ativa o **Protocolo de Bloqueio** imediatamente — não continue o checklist.

**ACs — verificação evidencial obrigatória**

Para cada AC da story, execute o protocolo:
1. Leia o AC literal, palavra por palavra
2. Cite o arquivo:linha exato que satisfaz cada requisito — "parece implementado" não é evidência
3. Se o AC exige campos específicos em logs, responses ou estruturas de dados: verifique campo a campo no código, não apenas que "existe um log/response"
4. Se o AC exige um comportamento em cenário específico: confirme que há um teste que cobre exatamente esse cenário com exatamente essas condições

- [ ] Cada AC foi verificado com localização exata no código (arquivo:linha) — não apenas "está implementado"
- [ ] ACs com listas de campos (logs, responses, payloads): todos os campos foram encontrados no código, nenhum ausente
- [ ] Nenhum AC foi marcado como "parcial" ou "futuro" sem justificativa explícita

**Tech Debt do Change Log**
- [ ] Todos os itens de tech debt registrados no Change Log da story estão resolvidos
- [ ] Nenhum item está registrado como "pendente" sem data e responsável definidos

> **Definição de "resolvido":** o código foi corrigido e o CI passa com essa correção incluída.
> "Registrado para story futura", "resolver depois", "próxima sprint" ou qualquer variação = **não resolvido** = BLOQUEADO imediato.
> A única exceção é aprovação explícita do humano via escalação (ver Protocolo de Bloqueio). Aprovação tácita do agente não existe.

**CI**
- [ ] Linter passa sem erros nos arquivos da story
- [ ] Type checker passa sem erros
- [ ] Todos os testes relacionados à story passam
- [ ] Nenhum teste skipado sem justificativa registrada no Change Log

**Cobertura de Testes**
- [ ] Execute o CI do stack da story e confirme o número exato de testes reportado:
      - Backend: `cd backend && python -m pytest tests/ -v`
      - Frontend: `cd frontend && npm test`
- [ ] O número de testes reportado pelo CI **bate com o registrado no Change Log** da story
      (se o Change Log diz "12 passed" e o CI retorna 4, é bloqueio imediato)
- [ ] Arquivos de teste existem no repositório: `git ls-files backend/tests/` ou `git ls-files frontend/`
      (working tree não conta — só o que está committed)
- [ ] Proporção T1 por módulo tocado pela story: linhas de teste ≥ linhas de lógica de negócio
      Verificar manualmente para cada arquivo de produção criado/modificado pela story

**NFRs do PRD**

Para cada arquivo de produção tocado pela story, verifique os NFRs do `docs/prd.md` que se aplicam:

- [ ] Se a story toca serviços com queries ao banco: `set_tenant_context(tenant_id)` é chamado antes de qualquer operação de leitura ou escrita — confirme no código, não apenas nos testes
- [ ] Se a story recebe input externo (webhook, API, form): todo campo usado em lógica de negócio ou persistido tem validação de tipo/formato no código
- [ ] Se a story retorna dados ao cliente: response não expõe campos internos, IDs de outros tenants ou stack traces

> Se qualquer item acima falhar e não existia um AC cobrindo o NFR na story: o bloqueio é duplo — **reportar o bug de implementação E reportar que o AC da story estava incompleto** (para que `to-epic-detail` corrija stories futuras similares).

**Consistência docs↔código**
- [ ] Toda docstring ou comentário que descreve comportamento (campos de log, valores de backoff, fluxos, contratos) foi verificado contra o código real — se diverge, é um bug, não só doc desatualizada
- [ ] Todo `# type: ignore` ou comentário explicativo tem a razão descrita na linha (ex: `# is_text_message já garante text != None`)

**Cleanliness**
- [ ] Sem código comentado
- [ ] Sem imports não utilizados
- [ ] Sem segredos ou tokens hardcoded
- [ ] Sem identificadores genéricos (`data`, `info`, `temp`, `result`, `obj`)

### Saída — Story aprovada

> ✅ Story N.M aprovada.
> ACs: ✅ | Tech debt: nenhum pendente | CI: ✅ | Cleanliness: ✅
>
> Próximo passo: `dev` para implementar a story N.M+1.

---

## Modo 2 — Epic Review

**Trigger:** "revisa a epic N", "faz o review da epic", "abre o PR" ou variações.

### Pré-condições

1. Confirme que **todas** as Stories da Epic estão com `Status: completed`
2. Se alguma Story estiver `pending` ou `in_progress`, instrua o usuário a concluir com `dev`
3. Rode o Story Review em qualquer story que não tenha passado por ele — só avance com todas aprovadas

### Coleta de Contexto

Spawn **dois sub-agentes em paralelo**:

**Sub-agente 1 — Contexto e Requisitos:**
- Leia `docs/prd.md` e extraia todos os FRs e NFRs relacionados à Epic
- Leia todos os arquivos de story em `docs/epics/epic-N-[nome]/` e extraia os ACs
- Retorne: mapa FR/NFR → Story → AC para rastreabilidade

**Sub-agente 2 — Análise do Código:**
- Execute o script de métricas e capture o JSON:
  ```bash
  cd backend && pip install radon -q && python scripts/check_metrics.py --json
  ```
- Liste todos os arquivos modificados/criados pelas Stories desta Epic (via `git diff` ou análise direta)
- Retorne: o JSON completo do script + inventário de arquivos por tipo (produção, teste, config)

> **IMPORTANTE:** Para C1, C4 e T1, use **exclusivamente os valores do JSON** — nunca conte linhas manualmente. Contagem manual produz números inconsistentes entre rodadas e gera falsos positivos.

Consolide os retornos antes de prosseguir.

### Checklist de Epic

Execute em ordem. Qualquer item 🔴 ativa o **Protocolo de Bloqueio** imediatamente.

**1. Rastreabilidade de Requisitos**
- [ ] Existe pelo menos uma Story cobrindo cada FR e NFR da Epic
- [ ] O AC de cada Story é suficiente para validar o requisito
- [ ] O código implementado satisfaz o AC

**2. CI Completo**
```bash
[linter] && [type checker] && [test runner]
```
> Adapte ao stack (ex: `npm run lint && npm run typecheck && npm test`, `pytest`, `go test ./...`)

**3. Complexity (C1–C6)** — ver `rules/complexity.md`
- [ ] **C1** — Nenhuma função > 20 linhas de lógica
- [ ] **C2** — Nenhum arquivo de produção > 300 linhas
- [ ] **C3** — Nenhum bloco com aninhamento > 3 níveis
- [ ] **C4** — Complexidade ciclomática ≤ 5 por função
- [ ] **C5** — Máximo 2 camadas de abstração entre entry point e lógica de negócio
- [ ] **C6** — Nenhuma função com mais de 3 parâmetros posicionais

**4. Testing (T1–T6)** — ver `rules/testing.md`
- [ ] **T1** — Proporção linhas de teste ≥ linhas de lógica de negócio por módulo
- [ ] **T2** — Testes verificam comportamento, não implementação interna
- [ ] **T3** — Cada teste tem exatamente um motivo para falhar
- [ ] **T4** — Nome de cada teste descreve comportamento em linguagem de negócio
- [ ] **T5** — Todos os testes foram confirmados falhando antes da implementação (RED)
- [ ] **T6** — Nenhum teste skipado sem justificativa e item de tech debt

**5. Security (S1–S5)** — ver `rules/security.md`
- [ ] **S1** — Nenhum segredo, token, senha ou chave hardcoded
- [ ] **S2** — Todo input externo validado antes de ser processado
- [ ] **S3** — Autorização verificada no servidor em toda operação restrita
- [ ] **S4** — Responses retornam apenas os campos necessários
- [ ] **S5** — Nenhuma dependência com vulnerabilidade `high` ou `critical`

**6. Stack-Specific (PF1–PF6)** — ver `rules/python-fastapi.md` (se stack Python/FastAPI)
- [ ] **PF1** — Nenhuma chamada síncrona de I/O dentro de função `async` (banco, HTTP, disco)
- [ ] **PF2** — `Settings()` não é instanciado no caminho de cada request (deve ser singleton ou constante no boot)
- [ ] **PF3** — Níveis de log condizem com severidade: falhas usam `warning`/`error`, nunca `info`
- [ ] **PF4** — Dependências de teste não estão em `requirements.txt` de produção (usar `requirements-dev.txt` ou `[dev]` extras)
- [ ] **PF5** — `asyncio_mode` configurado em `pyproject.toml` ou `pytest.ini` se o projeto usa `pytest-asyncio`
- [ ] **PF6** — Docstrings que descrevem contratos (campos de log, backoff, fluxos) conferem com o código real

**7. Cleanliness (CL1–CL5)** — ver `rules/cleanliness.md`
- [ ] **CL1** — Sem funções, variáveis ou imports não referenciados
- [ ] **CL2** — Sem blocos de código comentados
- [ ] **CL3** — Sem abstrações para casos de uso inexistentes no PRD
- [ ] **CL4** — Todos os identificadores têm nomes expressivos
- [ ] **CL5** — Todo TODO/FIXME tem item no Change Log com data e referência da story

### Saída — Epic aprovada

> ✅ Epic N aprovada para PR.
> Requisitos: [N] FRs cobertos ✅
> CI: lint ✅ | typecheck ✅ | tests ✅
> Rules: complexity ✅ | testing ✅ | security ✅ | stack-specific ✅ | cleanliness ✅

Execute o push da branch e abra o PR:

```bash
git push origin epic-N-[nome-kebab-case]
```

Em seguida, crie o PR com o body preenchido:

```bash
gh pr create \
  --title "Epic N — [Nome]" \
  --base main \
  --body "## Epic N — [Nome]

### Stories implementadas
- [N.1] [Título]
- [N.2] [Título]

### Requisitos cobertos
- FR1: ✅ [descrição breve]
- NFR1: ✅ [critério e resultado]

### CI Status
Lint: ✅ | Typecheck: ✅ | Tests: ✅ ([N] passando)

### Rules Status
Complexity (C1–C6): ✅ | Testing (T1–T6): ✅
Security (S1–S5): ✅ | Stack-Specific (PF1–PF6): ✅ | Cleanliness (CL1–CL5): ✅

### Review Notes
[Decisões tomadas, trade-offs, tech debt registrado]

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

Após o PR ser aberto, informe a URL retornada pelo `gh pr create`.

> Próximo passo: `to-epic-detail` para detalhar a Epic N+1.

---

## Protocolo de Bloqueio

Ativado sempre que um item 🔴 é encontrado. O review **para imediatamente** — não continua o checklist, não avança para o próximo modo, não abre PR.

Reporte no seguinte formato:

> 🚨 Review bloqueado — [Story N.M | Epic N]
>
> **Problema:** [descrição exata do que falhou]
> **Localização:** [arquivo:linha, story N.M ou AC específico]
> **Critério violado:** [ex: T3 — cada teste deve ter exatamente um motivo para falhar]
>
> **Ação necessária:** `dev` para corrigir antes de retomar o review.
>
> O review está pausado. Confirme quando corrigido para continuar de onde parou.

Se o problema exigir uma decisão que não é de implementação — decisão de arquitetura, aceite consciente de limitação de ambiente, exceção de regra justificada — reporte para o humano diretamente:

> 🚨 Review bloqueado — decisão necessária.
>
> **Problema:** [descrição exata]
> **Por que não é resolvível pelo dev:** [explicação]
> **Opções:** [liste as alternativas possíveis com trade-offs]
>
> O review está pausado. Confirme a decisão para continuar.

A skill não avança, não assume decisões e não aceita débito como resolvido sem confirmação explícita — seja do humano ou de uma nova execução do `dev` confirmando a correção.
