# Rules: Security

> Princípio: segurança não é feature — é pré-requisito. Código que funciona mas expõe dados ou permite acesso indevido não está pronto.

Estas regras são **hard gates**. Qualquer violação bloqueia o PR até ser corrigida. Não existe exceção para estas regras.

---

## S1 — Nenhum segredo hardcoded

**Regra:** nenhuma chave de API, senha, token, connection string, secret, ou credencial pode aparecer literal no código-fonte.

**Como checar:** busque por padrões como strings longas com caracteres aleatórios, palavras-chave `password`, `secret`, `token`, `key`, `api_key`, `auth` atribuídas a strings literais.

```bash
# Verificação básica
grep -rn "password\s*=\s*['\"]" src/
grep -rn "secret\s*=\s*['\"]" src/
grep -rn "api_key\s*=\s*['\"]" src/
```

**O que fazer se falhar:** mova para variável de ambiente. Documente no README quais variáveis são necessárias. Invalide o segredo exposto imediatamente.

---

## S2 — Todo input externo é validado antes de ser usado

**Regra:** qualquer dado vindo de fora do sistema (body de requisição, query params, headers, arquivos, eventos externos) deve ser validado quanto a tipo, formato e limites antes de ser processado ou persistido.

**Por quê:** input não validado é a origem de injection attacks, crashes por tipo inesperado, e corrupção de dados.

**Como checar:** trace cada ponto de entrada do sistema. Verifique se há validação explícita (schema, parser, assertions) antes de qualquer uso do dado.

**O que fazer se falhar:** adicione validação no ponto de entrada. A validação deve rejeitar explicitamente o que não está no contrato esperado — não apenas ignorar campos extras.

---

## S3 — Autorização verificada no servidor

**Regra:** toda operação que exige permissão deve verificar autorização no servidor, independente de qualquer verificação feita no cliente.

**Por quê:** verificações client-side são UX, não segurança. Qualquer requisição pode ser feita diretamente ao servidor sem passar pela interface.

**Como checar:** para cada rota ou endpoint que manipula dados sensíveis ou restritos, verifique se há verificação de sessão/token e de permissão no handler servidor. Verificação apenas no middleware de rota não é suficiente se o endpoint pode ser chamado diretamente.

---

## S4 — Dados retornados são mínimos necessários

**Regra:** nenhuma resposta pode retornar mais dados do que o consumidor precisa para a operação solicitada.

**Por quê:** over-fetching expõe campos sensíveis acidentalmente e aumenta a superfície de ataque.

**Como checar:** para cada response de API ou query, verifique se campos como senha (mesmo hash), tokens internos, IDs de sistema, dados de outros usuários, ou metadados internos estão sendo retornados sem necessidade explícita.

```
// ❌ retorna tudo do registro
return await db.users.findById(id);

// ✅ projeta apenas o necessário
return await db.users.findById(id, { select: ['id', 'name', 'email'] });
```

---

## S5 — Dependências sem vulnerabilidades conhecidas críticas

**Regra:** nenhum pacote adicionado nesta Epic pode ter vulnerabilidade de severidade `high` ou `critical` conhecida no momento do merge.

**Como checar:**
```bash
npm audit --audit-level=high
# ou equivalente para o package manager do projeto
```

**O que fazer se falhar:** atualize o pacote para versão corrigida, substitua por alternativa segura, ou documente explicitamente por que o risco é aceitável (com aprovação). Vulnerabilidades `low` e `moderate` registre como tech debt mas não bloqueiam.

