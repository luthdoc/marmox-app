# XP Refactoring Protocol — Método Akita

> Severidade: ADVISORY
> Aplica-se a: @dev após implementar cada task (Interactive, Pre-Flight e YOLO modes)
> Restrição crítica: APENAS arquivos que a task corrente modificou ou criou
> Diferença por modo — ver seção "Comportamento por modo" abaixo

## Gatilho 1: Tamanho de arquivo

Para cada arquivo modificado ou criado pela task:
- Se o arquivo ultrapassar 300 linhas → refatorar antes de marcar [x]
- Opções: extrair módulo, extrair funções helper, dividir responsabilidades

## Gatilho 2: Duplicação de código

Verificação visual após implementação:
- Existe lógica similar em 3+ lugares no mesmo arquivo ou nos arquivos tocados?
- Se sim → extrair função ou helper compartilhado

## Gatilho 3: Code smells (verificação de 30 segundos)

Checar nos arquivos modificados:
- Funções com mais de 20 linhas sem comentário justificando a complexidade?
- Nomes genéricos não-expressivos: `data`, `info`, `temp`, `result`, `obj`?
- Condicionais aninhadas em mais de 3 níveis?

Se QUALQUER resposta for "sim":
- Opção A: refatorar imediatamente (preferido)
- Opção B: documentar como tech debt no Change Log com TODO comentado no código

## Restrição de escopo (Article IV — No Invention)

NUNCA refatorar código que a story corrente NÃO tocou.
Refactoring cross-story requer uma story dedicada via @sm *draft.

Este protocolo NÃO autoriza:
- Reestruturar módulos não relacionados à task
- Criar novas abstrações cross-codebase
- Mover arquivos fora do escopo da story

## Comportamento por modo

| Gatilho | Interactive / Pre-Flight | YOLO |
|---------|--------------------------|------|
| Gatilho 1 — >300 linhas | Refatora e reporta ao humano antes de [x] | Refatora silenciosamente antes de [x] |
| Gatilho 2 — Duplicação | Reporta e aguarda confirmação para extrair | Extrai helper silenciosamente |
| Gatilho 3 — Code smells | Apresenta opções A/B ao humano | Aplica Opção A (refatora) ou registra tech debt autonomamente |

Em YOLO mode, nenhum gatilho gera checkpoint humano.
A restrição de escopo (Article IV) é inegociável em qualquer modo — YOLO não a suspende.
