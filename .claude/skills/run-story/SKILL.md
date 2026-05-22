---
name: run-story
description: >
  Dispara o ciclo automático DEV → QA → FIX para uma Story específica.
  O agente run-story roda de forma autônoma: implementa, verifica, corrige
  em loop até aprovação e commita. Use: /run-story 1.2 ou /run-story 1.3.
  Acione quando quiser executar uma story do início ao fim sem intervenção manual.
---

# Skill: run-story

## Input

Extraia o número da story do argumento do comando:
- `/run-story 1.2` → story `1.2`
- `/run-story-1.2` → story `1.2`

Se nenhum número for identificado no argumento, liste as stories com `Status: pending`
em `docs/epics/` e peça ao usuário qual executar.

## Ação

Spawn o agente `run-story` (definido em `.claude/agents/run-story.md`) com o prompt:

```
Execute o ciclo automático completo para a story [NÚMERO EXTRAÍDO].
Siga todas as instruções definidas em `.claude/agents/run-story.md`.
```

O agente roda de forma autônoma — DEV → QA → FIX em loop até aprovação ou escalonamento.
Aguarde a conclusão e reporte o resultado final ao usuário.
