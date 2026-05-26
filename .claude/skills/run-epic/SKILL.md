---
name: run-epic
description: >
  Dispara o ciclo automático completo de uma Epic: executa todas as Stories em sequência
  (DEV → QA → FIX por story), verifica regressões de CI entre stories, e ao final
  executa Epic QA isolado + abre PR se aprovado. Use: /run-epic 2 ou /run-epic 3.
  Acione quando quiser executar uma Epic do início ao fim sem intervenção manual.
---

# Skill: run-epic

## Input

Extraia o número da epic do argumento do comando:
- `/run-epic 2` → epic `2`
- `/run-epic-2` → epic `2`

Se nenhum número for identificado no argumento, liste as epics disponíveis em `docs/epics/`
(diretórios `epic-N-*`) e as stories com `Status: pending` em cada uma. Peça ao usuário qual executar.

## Ação

Spawn o agente `run-epic` (definido em `.claude/agents/run-epic.md`) com o prompt:

```
Execute o ciclo automático completo para a Epic [NÚMERO EXTRAÍDO].
Siga todas as instruções definidas em `.claude/agents/run-epic.md`.
```

O agente roda de forma autônoma:
- Verifica/cria a branch da Epic
- Executa cada story pendente via run-story (DEV → QA → FIX)
- Verifica regressões de CI após cada story
- Executa Epic QA isolado ao final
- Abre PR se aprovado

Aguarde a conclusão e reporte o resultado final ao usuário.
