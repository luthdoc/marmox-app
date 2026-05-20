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
  isso é responsabilidade da skill eng-epic.
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

---

### Seção 5 — Epic List (alto nível)

Liste todas as Epics com título + 1 frase de goal. Apresente ao usuário para aprovação **antes** de avançar.

**Regras críticas de sequenciamento:**

- **Epic 1 SEMPRE** estabelece a infraestrutura base: setup do projeto, Git, CI/CD, serviços core, e ao menos uma peça de funcionalidade mínima deployável (ex: health-check, canary page). Sem exceções.
- Cada Epic entrega um incremento completo, testável e deployável
- Cada Epic posterior constrói sobre o anterior — sem gaps ou dependências reversas
- Cross-cutting concerns (auth, logging, monitoring, error handling) fluem através dos epics desde o início, **nunca** são o último Epic
- Erro para o lado de **menos Epics**: se algo parece grande demais, questione antes de dividir

**Formato:**
```
Epic 1: [Nome] — [goal em 1 frase]
Epic 2: [Nome] — [goal em 1 frase]
```

O detalhamento de cada Epic em Stories é responsabilidade da skill `eng-epic`. Não vá além da lista aqui.

---

### Seção 6 — Next Steps

Dois prompts curtos ao final:
- **UX Expert Prompt**: instrução curta para iniciar criação do documento de UI/UX com este PRD como input
- **Architect Prompt**: instrução curta para iniciar criação da arquitetura com este PRD como input

---

## Validação Final

Antes de salvar, faça uma passagem verificando:

- [ ] Todos os FRs têm correspondência rastreável nas Epics?
- [ ] Os NFRs têm critérios mensuráveis?
- [ ] A sequência de Epics é lógica e sem gaps?
- [ ] A Epic 1 estabelece infraestrutura E entrega algo deployável?
- [ ] Cross-cutting concerns estão distribuídos, não concentrados no final?

Se qualquer item falhar, corrija antes de salvar.

## Saída

Salve em `docs/prd.md`.

Ao finalizar, informe:
> ✅ PRD salvo em `docs/prd.md`.
> Próximos passos sugeridos:
> - `eng-architect` para criar o documento de arquitetura com base neste PRD.
> - `eng-epic` para quebrar cada Epic em Stories implementáveis.
