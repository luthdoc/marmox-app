---
name: to-prd
description: >
  Cria o PRD (Product Requirements Document) em docs/prd.md guiando o processo
  de elicitação de requisitos de forma interativa e estruturada. Use esta skill
  sempre que o usuário quiser documentar os requisitos de um projeto ou feature,
  escrever o PRD, definir goals, functional/non-functional requirements, UI goals,
  technical assumptions e a lista de Epics de alto nível. Acione após uma sessão
  de grill-me com entendimento estabelecido, ou quando o usuário disser "cria o PRD",
  "documenta os requisitos", "vamos escrever o PRD", "quero o PRD" ou qualquer variação.
  Também acione quando um novo projeto ou feature precisa ser formalizado em documento
  antes de partir para arquitetura ou código. NÃO detalha Stories dentro das Epics —
  isso é responsabilidade da skill to-epic-detail.
---

# Skill: to-prd

Você é responsável por criar o `docs/prd.md` do projeto. Este documento é a **fonte da verdade dos requisitos** — arquitetura, epics e implementação derivam dele. Um PRD ruim contamina tudo que vem depois.

## Pré-condições

Antes de começar, verifique:

1. **Output do grill-me**: há entendimento do projeto na conversa atual ou em arquivos? Esse é seu ponto de partida — extraia tudo que já foi discutido antes de perguntar ao usuário.
2. **PRD existente**: se `docs/prd.md` já existe, pergunte se quer revisar seções específicas ou refazer do zero.
3. **Diretório `docs/`**: crie se não existir.

## Processo

Trabalhe **seção por seção de forma interativa**. Para cada seção:
1. Proponha uma versão inicial baseada no contexto disponível (não pergunte o que você pode inferir)
2. Apresente ao usuário com as suposições claramente sinalizadas
3. Colete feedback e refine
4. Só avance com aprovação explícita

Nunca produza o documento inteiro de uma vez sem validação intermediária.

---

## Estrutura do PRD

### Seção 1 — Goals and Background Context

**Goals** (bullet list): outcomes concretos que o projeto precisa entregar. Foco em resultado, não em funcionalidade.

**Background Context** (1-2 parágrafos): o que este projeto resolve e por que agora. Não repita os goals.

**Change Log** (tabela): `Date | Version | Description | Author`

---

### Seção 2 — Requirements

**Functional Requirements**: o que o sistema faz. Prefixo `FR`, numerados sequencialmente.
```
FR1: [descrição da capacidade funcional]
FR2: ...
```

**Non-Functional Requirements**: qualidade, performance, segurança, escala. Prefixo `NFR`.
```
NFR1: [critério mensurável — ex: "p95 < 200ms para todas as rotas de API"]
NFR2: ...
```

Cada NFR deve ter um critério mensurável. "O sistema deve ser rápido" não é um NFR.

---

### Seção 3 — User Interface Design Goals *(somente se houver UX/UI)*

- **Overall UX Vision**: 2-3 frases sobre a experiência que o produto deve transmitir
- **Key Interaction Paradigms**: padrões de interação centrais (ex: drag-and-drop, inline editing, wizard steps)
- **Core Screens and Views**: lista conceitual das telas principais para entregar o valor do produto — não é spec técnica, é perspectiva de produto
- **Accessibility**: `None | WCAG AA | WCAG AAA`
- **Branding**: guia de cores, tipografia, tokens existentes (se houver)
- **Target Platforms**: `Web Responsive | Mobile Only | Desktop Only | Cross-Platform`

---

### Seção 4 — Technical Assumptions

Decisões técnicas que vão guiar a arquitetura. Registre com rationale, não só a escolha.

- **Repository Structure**: `Monorepo | Polyrepo`
- **Service Architecture**: `Monolith | Microservices | Serverless`
- **Testing Requirements**: nível de cobertura esperado (unit, integration, E2E, manual)
- **Additional Assumptions**: qualquer outra premissa técnica relevante que surgir durante a elicitação

#### Integrações e Serviços Externos

Para **cada serviço externo** (APIs de terceiros, provedores de infra, SDKs externos) que o projeto vai usar:

```
Serviço: [nome da categoria — ex: "Envio de mensagens WhatsApp"]
Escolha definitiva: [nome do serviço/biblioteca — ex: "Evolution API (self-hosted)"]
Alternativas descartadas: [ex: "Z-API (custo variável por tenant), Meta API oficial (complexidade de aprovação)"]
Rationale: [por que esta escolha — ex: "custo fixo independente do número de tenants, controle total do servidor"]
Como validar: [critério concreto de que está funcionando — ex: "webhook recebe mensagem real e resposta é entregue no WhatsApp"]
```

**Regras:**
- Cada categoria tem exatamente uma escolha — nunca "X ou Y"
- Se há dúvida real entre duas opções, resolva aqui com uma pergunta ao usuário antes de avançar
- A coluna "Como validar" é obrigatória — define o que "funcionando" significa para aquele serviço

#### Stack Técnico

| Camada | Tecnologia | Diretório |
|--------|-----------|-----------|
| [ex: Backend] | [ex: Python + FastAPI] | [ex: backend/] |
| [ex: Frontend] | [ex: Next.js + TypeScript] | [ex: frontend/] |

**Regras:**
- Uma linha por camada executável independente
- Diretório é o path relativo à raiz do repositório
- Se for monolito (sem subdivisões): uma linha apenas
- Esta tabela é a fonte que `/init` usa para gerar `## CI Commands` no `CLAUDE.md`

---

### Seção 5 — Epic List (alto nível)

Liste todas as Epics com título + 1 frase de goal. Apresente ao usuário para aprovação **antes** de avançar.

**Regras críticas de sequenciamento:**

- **Epic 1 SEMPRE** estabelece a infraestrutura base: setup do projeto, Git, CI/CD, serviços core, e ao menos uma peça de funcionalidade mínima deployável (ex: health-check, canary page). Sem exceções.
- Cada Epic entrega um incremento completo, testável e deployável
- Cada Epic posterior constrói sobre o anterior — sem gaps ou dependências reversas
- Cross-cutting concerns (auth, logging, monitoring, error handling) fluem através dos epics desde o início, **nunca** são o último Epic
- Erro para o lado de **menos Epics**: se algo parece grande demais, questione antes de dividir
- **A última Epic SEMPRE é a Epic de Go-Live**: cobre tudo que é necessário para o sistema estar de pé e funcionando em produção de verdade — não apenas "código implementado"

#### Epic de Go-Live (sempre a última)

O critério de conclusão desta Epic é: **um usuário real consegue usar o produto de ponta a ponta**. Não é "o código está correto" nem "os testes passam".

O detalhamento das Stories (o quê configurar, o quê testar, como validar cada integração) é responsabilidade da skill `to-epic-detail`, que vai derivar as tasks a partir das integrações e critérios "Como validar" definidos na Seção 4.

**Formato:**
```
Epic 1: [Nome] — [goal em 1 frase]
Epic 2: [Nome] — [goal em 1 frase]
```

O detalhamento de cada Epic em Stories é responsabilidade da skill `to-epic-detail`. Não vá além da lista aqui.

---

### Seção 6 — Next Steps

Um prompt curto ao final:
- **UX Expert Prompt**: instrução curta para iniciar criação do documento de UI/UX com este PRD como input *(somente se o projeto tiver UX/UI)*

---

## Validação Final

Antes de salvar, faça uma passagem verificando:

- [ ] Todos os FRs têm correspondência rastreável nas Epics?
- [ ] Os NFRs têm critérios mensuráveis?
- [ ] A sequência de Epics é lógica e sem gaps?
- [ ] A Epic 1 estabelece infraestrutura E entrega algo deployável?
- [ ] Cross-cutting concerns estão distribuídos, não concentrados no final?
- [ ] Cada serviço externo na Seção 4 tem escolha única, rationale e critério de validação?
- [ ] Não há nenhuma categoria de integração com duas opções em aberto ("X ou Y")?
- [ ] A última Epic é uma Epic de Go-Live cujo critério de sucesso é um usuário real conseguir usar o produto?
- [ ] Stack Técnico tem uma linha por camada com Tecnologia e Diretório preenchidos?

Se qualquer item falhar, corrija antes de salvar.

## Bootstrap do Repositório

Após salvar o PRD, verifique se o repositório remoto está configurado:

```bash
git remote -v
```

Se **não houver remote**, crie agora — o remote precisa existir antes de detalhar a primeira Epic:

```bash
gh repo create [nome-do-projeto] --private --source=. --push
```

Use o nome do projeto em kebab-case. O `--source=.` usa o diretório atual e `--push` faz o push inicial.

Se **já houver remote configurado**: pule esta etapa.

## Saída

Salve em `docs/prd.md`.

Ao finalizar, informe:
> ✅ PRD salvo em `docs/prd.md`.
> Repositório remoto: [configurado | criado agora em github.com/user/repo]
>
> Próximo passo: `to-epic-detail` para detalhar cada Epic em Stories implementáveis.
