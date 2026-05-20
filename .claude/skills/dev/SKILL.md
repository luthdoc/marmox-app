---
name: dev
description: >
  Implementa uma Story completa seguindo o método TDD XP do Akita (RED→GREEN→REFACTOR),
  com CI gate entre tasks e self-review antes de marcar como concluída.
  Usa subagents para paralelizar coleta de contexto, tasks independentes e self-review.
  Use esta skill sempre que o usuário quiser implementar uma story, começar a codar uma feature,
  executar uma tarefa de desenvolvimento, ou quando disser "implementa a story X.Y",
  "começa a implementação", "codifica a story", "vamos implementar", "executa a story" ou variações.
  Também acione quando o usuário apontar para um arquivo de story em docs/epics/ e pedir para executar.
  Esta skill é o coração do processo de desenvolvimento — toda implementação passa por aqui.
---

# Skill: dev

Você é responsável por implementar uma Story completa. O processo é determinístico: TDD por task, CI gate entre tasks, self-review antes de fechar. **Nenhuma exceção à ordem.**

Leia os protocolos de referência antes de começar:
- `references/xp-tdd-protocol.md` — regras do ciclo TDD
- `references/xp-refactoring.md` — gatilhos e restrições de refactoring
- `references/xp-ci-gate.md` — regras do CI gate entre tasks

---

## Pré-condições

Antes de começar, **spawn 3 subagents em paralelo** para coletar contexto:

| Subagent | Lê |
|---|---|
| A — Story | Arquivo da story alvo: tasks, ACs, status atual |
| B — Spec | `docs/prd.md` (seções relevantes) + `docs/architecture.md` |
| C — Codebase | Arquivos de código existentes relacionados à story |

Consolide os retornos num relatório único com: contexto técnico, ACs da story, tasks, dependências entre tasks, e arquivos que provavelmente serão tocados.

> **Se a story não foi especificada**: liste as pendentes (`Status: pending`) em `docs/epics/` e peça ao usuário para escolher antes de spawnar os subagents.

**Confirme o entendimento** com o usuário antes de começar: apresente as tasks, mapeie as dependências entre elas (qual bloqueia qual), e informe se há tasks que rodarão em paralelo.

---

## Mapeamento de Dependências entre Tasks

Antes de iniciar o ciclo de implementação, analise as tasks da story e classifique:

- **Bloqueante**: task A deve concluir antes de task B começar (B usa código criado por A)
- **Independente**: tasks sem dependência entre si podem rodar em paralelo

**Regra de paralelização**: tasks independentes rodam em subagents simultâneos, cada um executando o ciclo TDD completo. Tasks bloqueantes rodam em sequência.

Exemplo:
```
Task 1 (schema DB) → bloqueia Task 2 (model) e Task 3 (seed)
Task 2 e Task 3 → independentes entre si → rodam em paralelo
Task 4 (service) → bloqueia Task 5 (controller)
```

---

## Ciclo de Implementação

**Tasks bloqueantes** executam sequencialmente neste agente.
**Tasks independentes** executam via subagents em paralelo — cada subagent recebe o contexto completo da story e roda o ciclo abaixo de forma autônoma.

Para **cada Task** (ou subagent de task), execute nesta ordem exata:

### 1. RED — Escreva o teste primeiro

Antes de qualquer linha de código de produção:
- Escreva o teste que descreve o comportamento da task
- O teste deve cobrir **comportamento**, não implementação
  - ✅ "usuário recebe erro 401 ao acessar rota protegida sem token"
  - ❌ "função `checkAuth` retorna false"
- Execute o teste e confirme que ele **falha** — se passar, o teste está errado

### 2. GREEN — Implemente o mínimo necessário

- Escreva o código mínimo para fazer o teste passar
- Nada além do que o AC exige — sem "já que estou aqui" (Article IV: No Invention)
- Execute o teste e confirme que **apenas ele** passa (sem regressões)

### 3. REFACTOR — Limpe antes de marcar [x]

Após GREEN, verifique os gatilhos de refactoring nos **arquivos modificados ou criados**:

**Gatilho 1 — Arquivo > 300 linhas?**
→ Extraia módulo, funções helper, ou divida responsabilidades.

**Gatilho 2 — Lógica similar em 3+ lugares?**
→ Extraia função ou helper compartilhado.

**Gatilho 3 — Code smells (verificação de 30 segundos)?**
- Função > 20 linhas sem comentário justificando a complexidade?
- Nomes genéricos: `data`, `info`, `temp`, `result`, `obj`?
- Condicionais aninhadas > 3 níveis?
→ Refatore (preferido) ou documente como tech debt com TODO comentado.

**Restrição absoluta**: NUNCA refatore código que esta task não tocou. Refactoring cross-story exige uma story dedicada.

### 4. CI Gate — Execute antes de avançar

```bash
npm run lint && npm run typecheck && npm test
```

Se existir `test:fast` no `package.json`, use entre tasks:
```bash
npm run lint && npm run typecheck && npm run test:fast
```

**Se o CI falhar com múltiplas falhas:**
→ Spawn um subagent por falha para diagnosticar em paralelo. Consolide as correções, depois re-execute o CI completo.

**Se o CI falhar com falha única:**
1. Reverta o [x] da task
2. Investigue, corrija
3. Re-execute o CI completo
4. Só marque [x] e avance quando **tudo** passar

Se o projeto não tiver script `test`, registre no Change Log: `"CI gate não executado — sem runner configurado"` e registre como tech debt.

### 5. Marque a task [x] e avance para a próxima

---

## CI Gate Unificado após Tasks Paralelas

Quando subagents de tasks paralelas concluírem seus ciclos TDD individuais, **antes de avançar para a próxima task bloqueante**:

1. Integre as mudanças de todos os subagents
2. Execute o CI completo no código combinado:

```bash
npm run lint && npm run typecheck && npm test
```

Se falhar, trate como CI gate normal (diagnóstico paralelo se múltiplas falhas).

---

## Verificação de Proporção 1:1

Antes de marcar qualquer task [x]:
- Estime linhas de lógica de negócio implementadas
- Estime linhas de testes escritos
- Se **linhas de teste < linhas de código**: adicione testes antes de [x]

Isentos da proporção 1:1:
- Arquivos de configuração
- Tipos TypeScript puros
- Mocks e fixtures
- Código gerado automaticamente (scaffolding, migrations)

---

## Self-Review antes de "Concluída"

Após todas as tasks estarem marcadas [x] e o CI passar, **spawn um subagent por arquivo modificado** para revisar em paralelo. Cada subagent verifica:

1. Cada teste cobre comportamento, não implementação?
2. Alguma linha de produção sem teste correspondente?
3. Naming expressivo? (leitura como documentação)
4. Algum TODO/FIXME adicionado?
5. O código implementa APENAS o que o AC exige?

Consolide os relatórios dos subagents. Para cada problema encontrado: corrija antes de marcar a story como concluída. Todo TODO/FIXME → item de tech debt no Change Log.

---

## CI Final da Story

Após a self-review, execute o CI completo (não `test:fast`):

```bash
npm run lint && npm run typecheck && npm test
```

Article V: CI completo ao final de toda story, independente dos CI gates intermediários.

---

## Commit e Push

Após CI final passar:

```bash
git add .
git commit -m "feat(story-N.M): [descrição concisa do que foi implementado]"
git push
```

Convenção de commit message:
- `feat(story-N.M):` para novas funcionalidades
- `fix(story-N.M):` para correções
- Use o título da Story como base para a descrição

---

## Atualização do Arquivo da Story

Ao finalizar, atualize o arquivo da story:

```markdown
**Status:** completed

## Change Log

| Date | Change | Notes |
|------|--------|-------|
| [data] | Story implementada | Tasks N.M.1 a N.M.X concluídas |
| [data] | Tech debt registrado | [se houver TODOs] |
```

---

## Saída

Ao concluir, informe:

> ✅ Story N.M concluída.
> - Tasks: N.M.1 ✅ N.M.2 ✅ N.M.3 ✅
> - Paralelas: [lista de tasks que rodaram em paralelo, se houver]
> - CI: lint ✅ typecheck ✅ tests ✅
> - Commit: `feat(story-N.M): [descrição]`
>
> [Se for a última story da Epic:]
> Todas as stories da Epic N foram implementadas.
> Próximo passo: `eng-review` para revisar e refatorar o código da Epic N.
>
> [Se houver stories restantes:]
> Próxima story: N.X — [título]. Pronto para começar?
