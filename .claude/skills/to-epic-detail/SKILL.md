---
name: to-epic-detail
description: >
  Detalha uma Epic específica em Stories implementáveis, criando os arquivos de story
  individuais em docs/epics/. Use esta skill sempre que o usuário quiser detalhar uma
  Epic do projeto, preparar o backlog de uma Epic para implementação, ou quando disser
  "detalha a epic N", "quero trabalhar na epic N", "cria as stories da epic N", "próxima
  epic" ou qualquer variação. Acione após o PRD estar pronto. Trabalha uma Epic por vez —
  não tenta detalhar todas as Epics de uma só vez.
---

# Skill: to-epic-detail

Você é responsável por detalhar **uma Epic por vez** em Stories implementáveis e criar os arquivos de story no filesystem. O output desta skill é o que o agente de implementação vai receber — se as Stories forem ambíguas ou grandes demais, a implementação vai falhar.

## Pré-condições

Antes de começar:

1. **`docs/prd.md`** — obrigatório. Se não existir, instrua o usuário a criar com `to-prd`.
2. **Repositório remoto** — obrigatório. Execute `git remote -v`. Se não houver remote configurado, instrua o usuário a criar antes de continuar (o Bootstrap do `to-prd` cobre esse passo). Cada Epic cria uma branch que precisa ser pushada.
3. **`docs/architecture.md`** — opcional mas recomendado. Se existir, use para enriquecer as Stories com contexto técnico.

---

## Processo

### Passo 1 — Confirmar a Epic List

Leia `docs/prd.md` e extraia a lista de Epics. Apresente ao usuário para confirmação:

```
Epic 1: [Nome] — [goal]
Epic 2: [Nome] — [goal]
...
```

Pergunte apenas: **"A lista está correta para prosseguir?"**

Se o usuário identificar qualquer inconsistência — Epic faltando, ordem errada, goal impreciso — **não corrija aqui**. Instrua a retornar ao `to-prd` para atualizar `docs/prd.md` primeiro. A lista de Epics é domínio exclusivo do PRD.

Só avance após confirmação explícita.

### Passo 2 — Selecionar a Epic

Pergunte qual Epic o usuário quer detalhar agora. Se ele já indicou na mensagem de trigger (ex: "detalha a epic 2"), pule a pergunta.

### Passo 2.5 — Criar branch da Epic

Com a Epic selecionada, crie a branch de desenvolvimento antes de detalhar as stories:

```bash
git checkout main && git pull origin main && git checkout -b epic-N-[nome-kebab-case]
```

Onde `N` é o número da Epic e `[nome-kebab-case]` é o nome sem acentos.
Exemplo: `epic-2-whatsapp-integration`

Se o remote ainda não existir (sem `origin`), omita o `git pull` e crie só a branch local:
```bash
git checkout main && git checkout -b epic-N-[nome-kebab-case]
```

Todos os commits das stories desta Epic vão para esta branch. O merge para `main` acontece somente após `qa-review` aprovar a Epic completa.

### Passo 3 — Subagent detalha e escreve

Lance um **sub-agente via `Task`** com as seguintes instruções:

> Leia `docs/prd.md` [e `docs/architecture.md` se existir].
> Detalhe a Epic N seguindo as regras de Stories abaixo.
> Crie os arquivos de story imediatamente após definir cada Story, sem esperar aprovação.
> Siga exatamente o template de Story File e a estrutura de diretórios definidos nesta skill.

O sub-agente deve receber como contexto:
- O conteúdo da Epic selecionada extraído do PRD
- As regras de Stories desta skill (seção abaixo)
- O template de Story File
- A estrutura de diretórios esperada

---

## Epic de Go-Live — Regras Especiais

Quando a Epic sendo detalhada for a última do PRD (Epic de Go-Live), o sub-agente segue um processo diferente:

**1. Leia a Seção 4 do PRD integralmente** — especialmente o bloco "Integrações e Serviços Externos". Cada entrada com campo "Como validar" é um contrato: a Epic precisa entregar aquela validação com dados reais, não mocks.

**2. Derive as Stories a partir do contexto do projeto**, não de uma lista fixa. Perguntas que guiam a derivação:
- Há banco de dados? → Story de migrations em produção
- Há variáveis de ambiente por serviço? → Story de configuração de ambiente
- Há serviços externos com "Como validar"? → Uma Story por integração que não tenha sido validada end-to-end nas Epics anteriores
- Há fluxo principal do produto que ainda não foi testado com dados reais? → Story de smoke test

**3. Critério de conclusão da Epic**: um usuário real consegue executar o fluxo principal do produto. Não é "o código está correto", não é "os testes passam". É uso real.

**4. Não herde stories de outras Epics**: se uma integração foi implementada mas nunca validada com dados reais em produção, ela pertence aqui. Se já foi validada, não repita.

**5. Override da regra "evite enablers puros"**: para a Epic de Go-Live, stories operacionais sem entrega de feature nova (configurar ambiente, rodar migrations, registrar webhooks) são esperadas e válidas. O valor entregue é o sistema funcionando — não uma feature.

---

## Regras de Stories

**Sequenciamento:**
- Stories dentro de uma Epic devem ser sequenciais — nenhuma depende de outra que aparece depois
- Se A depende de B, B vem antes de A. Sempre.

**Tamanho:**
- Cada Story deve ser executável por um agente AI em sessão única, sem overflow de contexto
- Referência: "junior dev trabalhando 2-4 horas"
- Se parecer maior, quebre — mas o slice resultante ainda precisa entregar valor
- Evite enablers puros (ex: "configurar o banco de dados" sem entregar funcionalidade)

**Conteúdo:**
- Foque no "o quê" e "porquê", não no "como" — implementação é papel da arquitetura
- ACs devem ser testáveis, específicos, não ambíguos
- Inclua notas técnicas apenas quando uma decisão de arquitetura impacta diretamente esta Story

**Cross-cutting concerns:**
- Auth, logging, error handling, monitoring: fluem pelas Stories desde o início
- Nunca crie uma Story "adicionar logging" no final — incorpore ao comportamento esperado das Stories relevantes

**NFRs do PRD → ACs obrigatórios:**
Antes de escrever os ACs de cada Story, releia todos os NFRs do `docs/prd.md` e verifique quais têm implicação técnica na story em questão. Para cada NFR relevante, crie um AC explícito na story — nunca deixe o NFR apenas como Technical Note.

Exemplos de mapeamento obrigatório:
- Story que faz queries ao banco com NFR de isolamento → AC explícito: "Queries retornam apenas dados do contexto correto — nenhum dado de outro contexto é acessível"
- Story que recebe input externo com NFR de validação → AC explícito: "Todo campo de input externo é validado antes de ser processado (formato, tipo, limites)"
- Story que retorna dados ao cliente com NFR de segurança → AC explícito: "Response contém apenas os campos necessários — nenhum dado interno é exposto"
- Story com NFR de performance → AC explícito: "Operação completa dentro do limite definido no NFR (ex: p95 < Xms)"

Technical Notes são contexto de implementação, não contrato. O AC é o único input que o agente `dev` usa como contrato — se o NFR não virar AC, não será implementado nem testado.

---

## Estrutura de Diretórios

```
docs/
└── epics/
    ├── epic-1-[nome-kebab-case]/
    │   ├── 1.1-[nome-da-story].md
    │   ├── 1.2-[nome-da-story].md
    │   └── 1.3-[nome-da-story].md
    ├── epic-2-[nome-kebab-case]/
    │   ├── 2.1-[nome-da-story].md
    │   └── 2.2-[nome-da-story].md
    └── ...
```

**Naming:** kebab-case, sem acentos. Ex: `epic-1-setup-infraestrutura/`, `1.1-health-check-endpoint.md`

---

## Template de Story File

```markdown
# Story N.M: [Título da Story]

**Epic:** N — [Nome da Epic]
**Status:** pending

## User Story

As a [tipo de usuário],
I want [ação específica],
so that [benefício concreto].

## Acceptance Criteria

1. [Critério testável e específico]
2. [Critério testável e específico]
3. [Critério testável e específico]

## Technical Notes

> Decisões de arquitetura relevantes para esta story.
> Referencie seções específicas de docs/architecture.md.
> Se não houver nada relevante, deixe esta seção vazia.

## Tasks

- [ ] N.M.1: [descrição da task — granularidade de 30-60 min]
- [ ] N.M.2: [descrição da task]
- [ ] N.M.3: [descrição da task]

## Dependencies

- **Requires:** [Story N.X ou "none"]
- **Blocks:** [Story N.Y ou "none"]

## Change Log

| Date | Change | Notes |
|------|--------|-------|
```

---

## Regras para Tasks

- Granularidade: uma unidade de trabalho focado e entregável (referência: 30-60 minutos)
- Cada Task descreve **o que construir**, não como — a metodologia de implementação é responsabilidade da skill `dev`
- Tasks fundamentais (que outras dependem) vêm primeiro
- Tasks de infraestrutura/config vêm antes de Tasks de lógica de negócio

---

## Saída

Após o sub-agente criar todos os arquivos da Epic, informe:

> ✅ Epic N criada com M stories em `docs/epics/epic-N-[nome]/`
> Branch: `epic-N-[nome-kebab-case]`
>
> Stories criadas:
> - N.1 — [título]
> - N.2 — [título]
> - ...
>
> Próximo passo: `dev` para implementar a Story N.1 (os commits irão para a branch `epic-N-[nome]`).
