# Rules: Cleanliness

> Princípio: código que não executa hoje não pertence ao repositório. Código para requisitos que não existem ainda é dívida técnica disfarçada de previsão.

Estas regras são **hard gates**. Qualquer violação bloqueia o PR até ser corrigida.

---

## CL1 — Sem código morto

**Regra:** nenhuma função, variável, import, export, classe, ou bloco de código pode existir no código-fonte sem ser referenciado e executado em algum caminho real do sistema.

**Como checar:** verifique warnings do linter (`no-unused-vars`, `no-unused-imports`). Faça busca de referências em funções exportadas que não aparecem em nenhum import.

**O que fazer se falhar:** delete. Se "pode ser útil no futuro", não pertence ao código agora — pertence ao backlog.

---

## CL2 — Sem código comentado

**Regra:** nenhum bloco de código pode estar comentado no código-fonte. Comentários explicam o *porquê* de uma decisão não-óbvia — nunca preservam código removido.

**Por quê:** código comentado é lixo com contexto perdido. Ninguém sabe se ainda é válido, se foi substituído, ou se pode ser deletado. O histórico de git existe para isso.

```
// ❌
// function oldCalculation(x) {
//   return x * 1.15;
// }

// ✅ (se a decisão não for óbvia)
// Usamos 1.15 porque inclui IOF — ver contrato com fornecedor X
const rate = 1.15;
```

**O que fazer se falhar:** delete o código comentado. Se precisar de referência histórica, use `git log`.

---

## CL3 — Sem abstrações especulativas

**Regra:** nenhuma abstração (interface, classe base, factory, adapter, configuração parametrizável) pode existir para suportar casos de uso que não existem ainda como requisito explícito no PRD.

**Por quê:** YAGNI — You Ain't Gonna Need It. Abstrações prematuras aumentam complexidade sem entregar valor. Quando o caso de uso real aparecer, a abstração especulativa geralmente está errada de qualquer forma.

**Como checar:** para cada abstração encontrada, pergunte: existe um requisito no PRD que justifica esta generalização hoje? Se não, é especulativa.

```
// ❌ especulativo — só tem um provider hoje
interface PaymentProvider { ... }
class StripeProvider implements PaymentProvider { ... }
class PaypalProvider implements PaymentProvider { ... } // não existe requisito

// ✅ direto — quando o segundo provider aparecer, extrai a interface
function chargeWithStripe(amount, card) { ... }
```

---

## CL4 — Nomes expressivos em todos os identificadores

**Regra:** nenhuma variável, função, classe, ou arquivo pode ter nome genérico que não descreve o que representa ou faz.

**Nomes proibidos sem qualificador:** `data`, `info`, `temp`, `result`, `obj`, `val`, `item`, `thing`, `stuff`, `misc`, `util` (como nome de arquivo ou módulo inteiro), `helper` (idem), `manager`, `handler` (sem qualificador do domínio).

**Como checar:** leia cada identificador isoladamente. Sem o contexto do código ao redor, você consegue dizer o que ele representa? Se não, o nome está errado.

```
// ❌
const data = await fetchUser(id);
function processInfo(obj) { ... }

// ✅
const user = await fetchUser(id);
function formatUserDisplayName(user: User) { ... }
```

---

## CL5 — Todo TODO/FIXME tem item de tech debt registrado

**Regra:** nenhum comentário `TODO`, `FIXME`, `HACK`, ou `XXX` pode existir no código sem um item correspondente no Change Log da story ou em um sistema de rastreamento.

**Formato obrigatório:**
```
// TODO(story-N.M): [descrição] — registrado em Change Log [data]
```

**Por quê:** TODOs sem rastreamento desaparecem. O Change Log é a garantia de que o débito foi conscientemente aceito, não esquecido.

**O que fazer se falhar:** registre no Change Log da story ou delete o TODO se não for mais relevante.

