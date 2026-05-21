# Rules: Complexity

> Princípio: código complexo que funciona ainda é código ruim. O objetivo é o mínimo que satisfaz o requisito — nada mais.

Estas regras são **hard gates**. Qualquer violação bloqueia o PR até ser corrigida.

---

## C1 — Tamanho de função

**Regra:** nenhuma função ou método pode ter mais de 20 linhas de lógica (excluindo linhas em branco e comentários).

**Por quê:** funções longas fazem mais de uma coisa. Se não cabe em 20 linhas, tem responsabilidade demais.

**Como checar:** conte manualmente ou use o linter configurado. Funções que violam a regra devem ser extraídas em funções menores com nomes expressivos.

**Exceção permitida:** funções de orquestração pura (que só chamam outras funções em sequência, sem lógica condicional própria) podem ter até 30 linhas. Documente com comentário: `// orchestration — sem lógica de negócio`.

---

## C2 — Tamanho de arquivo

**Regra:** nenhum arquivo de produção pode ter mais de 300 linhas.

**Por quê:** arquivo grande é sintoma de múltiplas responsabilidades no mesmo lugar.

**Como checar:** `wc -l [arquivo]` ou equivalente. Se ultrapassar, extraia módulos por responsabilidade.

**Exceção permitida:** arquivos de configuração, schemas de banco de dados, e arquivos gerados automaticamente estão isentos.

---

## C3 — Profundidade de aninhamento

**Regra:** nenhum bloco de código pode ter mais de 3 níveis de aninhamento (`if`, `for`, `while`, `try`, closures, etc.).

**Por quê:** aninhamento profundo é complexidade ciclomática acumulada — difícil de ler, difícil de testar, fácil de quebrar.

**Como checar:** inspecione visualmente. Se ultrapassar 3 níveis, use early return, extração de função, ou inversão de condicional.

```
// ❌ 4 níveis
if (a) {
  for (b) {
    if (c) {
      try { ... }   // nível 4
    }
  }
}

// ✅ early return + extração
if (!a) return;
for (b) {
  processItem(c);
}
```

---

## C4 — Complexidade ciclomática por função

**Regra:** nenhuma função pode ter complexidade ciclomática acima de 5.

**Como calcular:** comece com 1. Some +1 para cada: `if`, `else if`, `else`, `for`, `while`, `do`, `case`, `&&`, `||`, `??`, `?.` com lógica condicional, `catch`.

**Por quê:** complexidade ciclomática acima de 5 aumenta exponencialmente o número de caminhos de teste necessários para cobertura real.

**O que fazer se falhar:** extraia blocos condicionais em funções com nomes que descrevem a decisão.

---

## C5 — Profundidade de abstração

**Regra:** no máximo 2 camadas de abstração entre o ponto de entrada (rota, controller, handler) e a lógica de negócio real.

**Por quê:** abstrações em excesso escondem o que o código realmente faz. Toda camada que não adiciona comportamento adiciona apenas complexidade de navegação.

**Exemplo permitido:**
```
handler → service → repository
```

**Violação:**
```
handler → service → adapter → transformer → util → helper
```

**Como checar:** trace o caminho de chamada de qualquer endpoint ou função pública. Se precisar de mais de 2 saltos para chegar à lógica real, a abstração é especulativa.

---

## C6 — Parâmetros de função

**Regra:** nenhuma função pode ter mais de 3 parâmetros posicionais.

**Por quê:** mais de 3 parâmetros indica que a função está fazendo coisas demais ou que os dados deveriam ser agrupados em um objeto com semântica própria.

**O que fazer se falhar:** agrupe parâmetros relacionados em um objeto tipado com nome expressivo.

```
// ❌
function createUser(name, email, role, tenantId, plan) {}

// ✅
function createUser(user: CreateUserInput) {}
```
