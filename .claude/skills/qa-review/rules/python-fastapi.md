# Rules: Python / FastAPI

> Princípio: o framework facilita misturar código síncrono e assíncrono — isso não significa que misturar é correto. Cada anti-pattern abaixo tem consequências silenciosas que só aparecem em produção sob carga ou em cenários de segurança.

Estas regras são **hard gates** quando o stack é Python + FastAPI. Qualquer violação bloqueia o PR.

---

## PF1 — Sem I/O síncrono dentro de handlers async

**Regra:** nenhuma chamada de I/O bloqueante (banco de dados, HTTP, disco, sleep) pode ocorrer dentro de uma função `async def` sem ser executada via `asyncio.to_thread()` ou usando um cliente assíncrono equivalente.

**Por quê:** uma chamada síncrona bloqueante dentro de uma coroutine bloqueia o event loop inteiro do Uvicorn. Sob carga, isso serializa todos os requests enquanto a chamada bloqueia.

**Como checar:** para cada função `async def` nos arquivos de produção, verifique se ela chama diretamente funções síncronas que fazem I/O. Clientes Supabase síncronos (`.execute()` sem `await`), `requests.get()`, `open()` sem contexto async, `time.sleep()` — todos bloqueiam.

```python
# ❌ bloqueia o event loop
async def _persist_message(tenant_id: str, content: str) -> None:
    client = get_client()
    client.table("messages").insert({...}).execute()  # síncrono!

# ✅ delega para thread pool
async def _persist_message(tenant_id: str, content: str) -> None:
    await asyncio.to_thread(_persist_message_sync, tenant_id, content)
```

**Exceção permitida:** código síncrono que faz apenas computação em memória (sem I/O) pode ser chamado diretamente de funções async.

---

## PF2 — Settings não é instanciado no caminho de cada request

**Regra:** `Settings()` (pydantic-settings) ou qualquer classe que leia variáveis de ambiente deve ser instanciada uma única vez no boot da aplicação — nunca dentro de um endpoint, middleware, ou função chamada por request.

**Por quê:** cada instanciação lê e valida todas as variáveis de ambiente. Em um endpoint de alta frequência, isso adiciona overhead desnecessário a cada requisição.

**Como checar:** busque por `Settings()` fora de `main.py`, `core/config.py` ou funções marcadas com `@lru_cache`. Qualquer `Settings()` dentro de um router, service, ou middleware chamado por request é violação.

```python
# ❌ lê env vars a cada request
def _get_expected_token() -> str:
    return Settings().zapi_token

# ✅ lido uma vez no boot
_EXPECTED_TOKEN: str = Settings().zapi_token

def _get_expected_token() -> str:
    return _EXPECTED_TOKEN
```

---

## PF3 — Níveis de log condizem com severidade real

**Regra:** o nível de log deve refletir a gravidade do evento:
- `DEBUG`: informação de diagnóstico, irrelevante em produção
- `INFO`: evento esperado e normal do sistema
- `WARNING`: algo inesperado mas recuperável aconteceu
- `ERROR`: falha que requer atenção, operação não concluída

**Violação mais comum:** usar `logger.info()` para logar falhas de rede, erros de validação, ou tentativas mal-sucedidas.

```python
# ❌ falha de rede logada como INFO — passa despercebida em produção
logger.info("Tentativa de envio Z-API — erro de rede", extra={...})

# ✅
logger.warning("Tentativa de envio Z-API — erro de rede", extra={...})
logger.error("Falha após todas as tentativas", extra={...})
```

**Como checar:** leia cada chamada de log nos arquivos de produção. Pergunte: "se isso acontecer em produção às 3h da manhã, o nível de alerta está correto?"

---

## PF4 — Dependências de teste fora do requirements de produção

**Regra:** pacotes usados exclusivamente em testes (`pytest`, `pytest-asyncio`, `httpx` para testes, `factory-boy`, etc.) não podem estar em `requirements.txt`. Use `requirements-dev.txt` ou extras `[dev]` no `pyproject.toml`.

**Por quê:** o container de produção (Railway, Render, etc.) instala tudo que está em `requirements.txt`. Pacotes de teste aumentam a imagem, aumentam a superfície de ataque, e podem conflitar com dependências de produção.

**Como checar:** leia `requirements.txt` e identifique qualquer pacote que só é importado em arquivos dentro de `tests/`.

```
# requirements.txt — só produção
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
supabase>=2.4.0
httpx>=0.27.0

# requirements-dev.txt — desenvolvimento e CI
-r requirements.txt
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

---

## PF5 — asyncio_mode configurado explicitamente

**Regra:** projetos que usam `pytest-asyncio` devem ter `asyncio_mode = "auto"` configurado em `pyproject.toml` (seção `[tool.pytest.ini_options]`) ou em `pytest.ini`.

**Por quê:** sem `asyncio_mode = "auto"`, testes `async def` sem o decorator `@pytest.mark.asyncio` são coletados pelo pytest mas **nunca executados** — passam silenciosamente sem rodar o corpo do teste. Isso cria falsos positivos: o CI fica verde mas o comportamento nunca foi testado.

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

**Como checar:** se o projeto tem `pytest-asyncio` em qualquer requirements e não tem `asyncio_mode` configurado, é violação.

---

## PF6 — Docstrings e comentários conferem com o código real

**Regra:** todo comentário ou docstring que descreve um contrato observável (campos de log, parâmetros de backoff, sequência de operações, condições de disparo) deve ser verificado contra o código real. Divergência é tratada como bug, não como "doc desatualizada".

**Por quê:** docstrings que mentem sobre o comportamento enganam quem mantém o código. Se a docstring diz `"backoff: 1s, 2s, 4s"` e o código só faz `1s, 2s`, a docstring está ativamente errada e vai causar diagnósticos incorretos de bugs em produção.

**Como checar:**
1. Para cada docstring que lista campos de log: abra o código e verifique que todos os campos listados estão no `extra={}` da chamada de log
2. Para cada docstring que descreve backoff/retry: calcule os valores reais do código e compare
3. Para cada docstring que descreve fluxo condicional: trace o código e confirme as condições

```python
# ❌ docstring mente — backoff real é 1s, 2s (nunca chega a 4s)
"""
Faz até 3 tentativas com backoff exponencial (1s, 2s, 4s).
"""
for attempt in range(1, 4):
    ...
    if attempt < 3:
        await asyncio.sleep(2 ** (attempt - 1))  # 1s, 2s — para aqui

# ✅
"""
Faz até 3 tentativas com backoff exponencial (1s após falha 1, 2s após falha 2).
"""
```
