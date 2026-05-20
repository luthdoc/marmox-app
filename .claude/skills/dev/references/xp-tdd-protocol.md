# XP TDD Protocol — Método Akita

> Severidade: ADVISORY
> Aplica-se a: @dev em Interactive, Pre-Flight e YOLO modes
> Diferença por modo — ver seção "Comportamento por modo" abaixo

## Regra 1: Ordem TDD obrigatória

Ao implementar cada task da story, a ordem de execução é SEMPRE:

1. Escrever o TESTE que descreve o comportamento da task (RED)
2. Verificar que o teste FALHA (se já passar, o teste está errado)
3. Implementar o código mínimo para o teste passar (GREEN)
4. Verificar que APENAS o novo teste passou (sem regressões)
5. Refatorar se necessário (REFACTOR — ver xp-refactoring.md)

Esta regra SUBSTITUI a ordem padrão de `dev-develop-story.md`
("implementar → escrever testes") para projetos com Método Akita habilitado.

Ao apresentar o plano de cada task, incluir obrigatoriamente:
- Descrição do teste RED que será escrito primeiro
- Comportamento esperado que o teste vai validar

## Regra 2: Proporção 1:1

Antes de marcar qualquer task [x], verificar:
- Linhas estimadas de lógica de negócio implementadas
- Linhas estimadas de testes escritos
- Se linhas de teste < linhas de código: adicionar testes antes de [x]

Exceções isentas da proporção 1:1:
- Arquivos de configuração
- Tipos TypeScript puros
- Mocks e fixtures
- Código gerado automaticamente (scaffolding, migrations)

## Regra 3: Self-Review antes de "Ready for Review"

ANTES de executar o story-dod-checklist e setar status "Ready for Review",
fazer uma passagem de releitura em CADA arquivo modificado verificando:

1. Cada teste cobre o comportamento, não a implementação?
   (ex: "usuário recebe erro ao logar com senha errada", não "função retorna false")
2. Alguma linha de produção sem teste correspondente?
3. Naming expressivo? (leitura como documentação)
4. Algum TODO/FIXME adicionado? → criar item em tech debt antes de continuar
5. Código implementa APENAS o que a AC exige? (Artigo IV da Constitution)

Esta passagem é ADICIONAL ao CodeRabbit self-healing que acontece em seguida.

## Comportamento por modo

| Regra | Interactive / Pre-Flight | YOLO |
|-------|--------------------------|------|
| Regra 1 — Ordem TDD | Aplicada; inclusa no 📋 PLANO | Aplicada silenciosamente (sem checkpoint) |
| Regra 2 — Proporção 1:1 | Verificada antes de [x]; bloqueia se falhar | Verificada antes de [x]; bloqueia se falhar |
| Regra 3 — Self-review | Realizada; resultado reportado ao humano | Realizada autonomamente; só reporta se encontrar violação |

Em YOLO mode, nenhuma regra gera checkpoint humano durante execução normal.
Violações na Regra 2 (proporção) bloqueiam [x] mesmo em YOLO — o agente adiciona os testes faltantes antes de avançar.
