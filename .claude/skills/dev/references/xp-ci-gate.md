# XP CI Gate — Método Akita

> Severidade: ADVISORY
> Aplica-se a: @dev em Interactive, Pre-Flight e YOLO modes
> Diferença por modo — ver seção "Comportamento por modo" abaixo

## Regra: CI completo entre tasks

Após marcar cada task [x], ANTES de apresentar o PLANO DA PRÓXIMA TASK:

```bash
npm run lint && npm run typecheck && npm test
```

## Comportamento por modo

### Interactive / Pre-Flight

Se qualquer comando falhar:
1. Reverter o [x] da task recém-marcada
2. Investigar a falha
3. Corrigir
4. Re-executar a validação completa
5. Só marcar [x] e avançar quando TUDO passar

### YOLO mode

O CI roda igualmente após cada task. Falha aciona a seguinte rotina autônoma:

1. Registrar o erro no log interno (contexto da sessão)
2. Tentar corrigir autonomamente — máximo 2 tentativas
3. Re-executar CI após cada tentativa de correção
4. Se CI passar: registrar a correção no Change Log da story e avançar
5. Se CI ainda falhar após 2 tentativas: **PARAR e escalonar para o humano**

Formato de escalação em YOLO:

```
BLOQUEIO YOLO — CI Gate falhou após 2 tentativas

Task: {nome da task}
Erro: {mensagem de erro do CI}
Tentativas: 2 correções autônomas realizadas
Última saída CI: {trecho relevante}

Intervenção manual necessária. O que fazer?
```

O agente não avança para a próxima task enquanto a escalação não for resolvida.

## Exceção: test suite lenta

Se `package.json` definir script `"test:fast"` (unit only):
- Entre tasks: `npm run test:fast`
- Ao final de TODAS as tasks: `npm test` (suíte completa)

## Ambiente sem runner configurado

Se o projeto não possuir `package.json` com script `test`:
- Registrar no Change Log da story: "CI gate não executado — sem runner configurado"
- Registrar como tech debt via `*backlog-debt`
- Avançar sem bloquear (CI gate é pré-requisito de ambiente, não de protocolo)

## Relação com Article V (Constitution)

Esta rule COMPLEMENTA o Artigo V — não substitui.
O Artigo V garante CI ao final da story.
Esta rule adiciona CI intermediário após cada task.
Ambos devem ser satisfeitos quando o ambiente estiver configurado.
