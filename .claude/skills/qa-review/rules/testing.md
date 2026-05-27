# Rules: Testing

> Princípio: um teste que não pode falhar não protege nada. Testes testam comportamento — o que o sistema faz, não como ele faz.

Estas regras são **hard gates**. Qualquer violação bloqueia o PR até ser corrigida.

---

## T1 — Proporção código/teste

**Regra:** linhas de teste ≥ linhas de lógica de negócio por módulo (ratio ≥ 1.0).

**Como calcular:** use o script `backend/scripts/check_metrics.py --json` e leia o campo `t1_ratio` por módulo. **Não conte linhas manualmente** — o script produz números determinísticos, evitando falsos positivos por contagem manual inconsistente.

**Tolerância:** ratio entre 0.9 e 1.0 não é bloqueio — registre como observação se o módulo teve cobertura recente aumentada. Ratio < 0.9 é bloqueio.

**Exceção permitida:** arquivos de configuração, tipos TypeScript/interfaces puras, mocks e fixtures, migrations e schemas gerados.

---

## T2 — Testes cobrem comportamento, não implementação

**Regra:** nenhum teste pode verificar detalhes internos de implementação — nomes de funções privadas, estrutura interna de objetos, sequência de chamadas internas.

**Por quê:** testes de implementação quebram quando você refatora sem mudar comportamento. São falsos positivos e freios ao refactoring legítimo.

**Como checar:** leia o nome e o assert de cada teste. Se o teste quebraria ao renomear uma função interna sem mudar o comportamento externo, é um teste de implementação.

```
// ❌ testa implementação
expect(userService._hashPassword).toHaveBeenCalled();

// ✅ testa comportamento
expect(await login(wrongPassword)).toEqual({ error: 'invalid_credentials' });
```

---

## T3 — Cada teste tem exatamente um motivo para falhar

**Regra:** nenhum teste pode verificar múltiplos comportamentos independentes em um único caso.

**Por quê:** testes com múltiplos asserts verificando coisas diferentes mascaram qual comportamento quebrou e tornam o diagnóstico mais lento.

**Como checar:** se um teste falhar, a mensagem de falha deve identificar exatamente qual comportamento quebrou sem ambiguidade.

**Exceção permitida:** múltiplos asserts são permitidos quando verificam facetas do mesmo comportamento coeso (ex: um objeto retornado com seus campos relacionados).

---

## T4 — Nome do teste descreve o comportamento esperado

**Regra:** o nome de todo teste deve ser legível como uma frase que descreve o que o sistema faz em determinada condição.

**Formato recomendado:** `[contexto] — [ação] — [resultado esperado]`

```
// ❌
test('checkAuth')
test('returns false')
test('user test 3')

// ✅
test('usuário sem token — acessa rota protegida — recebe 401')
test('item fora de estoque — tentativa de compra — retorna erro com motivo')
```

---

## T5 — Nenhum teste pode passar sem o código de produção existir

**Regra:** execute os testes antes de escrever o código de produção (RED do TDD). Se algum teste já passar antes da implementação, o teste não está testando nada — delete ou corrija.

**Como checar:** na fase de RED de cada task, confirme que o teste falha. Se passar, o comportamento já existe ou o teste está vazio/trivial.

---

## T6 — Sem testes desabilitados sem justificativa

**Regra:** nenhum teste pode estar skipado (`skip`, `xtest`, `xit`, `.todo`, `pending`) sem um comentário explicando por quê e um item de tech debt registrado.

**Por quê:** testes skipados são buracos silenciosos na cobertura. Se não pode passar agora, documente o motivo e registre o débito.

