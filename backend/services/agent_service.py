"""
Serviço do agente Claude Haiku para processamento de mensagens (Story 3.1).

Responsabilidades:
- Receber texto de uma mensagem inbound com contexto de tenant
- Chamar o Claude Haiku com system prompt dinâmico (tenant name injetado)
- Retornar o texto da resposta do Claude ao chamador
- Habilitar prompt caching via cache_control ephemeral no system prompt
"""
from __future__ import annotations

from anthropic import AsyncAnthropic

_MODEL = "claude-haiku-4-5-20251001"

_SYSTEM_PROMPT_TEMPLATE = (
    "Você é o assistente virtual da {tenant_name}. "
    "Seu papel é responder às dúvidas e solicitações de clientes de forma clara e prestativa. "
    "Você nunca deve fingir ser humano — sempre deixe claro que é um assistente virtual. "
    "Seja cordial, objetivo e profissional."
)


async def process_message(
    tenant_id: str,
    tenant_name: str,
    phone: str,
    text: str,
    history: list[dict] | None = None,
) -> str:
    """Processa uma mensagem inbound chamando o Claude Haiku e retorna a resposta.

    Injeta o nome do tenant no system prompt dinamicamente. O system prompt
    é enviado com cache_control ephemeral para habilitar prompt caching (NFR5).
    O histórico de conversa é inserido antes da mensagem atual para que o Claude
    tenha contexto das trocas anteriores (Story 3.2).

    Args:
        tenant_id: UUID do tenant.
        tenant_name: Nome da empresa do tenant, injetado no system prompt.
        phone: Número do remetente.
        text: Texto da mensagem inbound a ser processada.
        history: Mensagens anteriores no formato [{"role": "user"|"assistant", "content": "..."}].
                 Inseridas antes da mensagem atual. None ou [] equivalem a sem histórico.

    Returns:
        Texto da resposta gerada pelo Claude Haiku.

    Raises:
        Exception: Propaga qualquer exceção da SDK Anthropic ao chamador.
    """
    client = AsyncAnthropic()
    system_text = _SYSTEM_PROMPT_TEMPLATE.format(tenant_name=tenant_name)

    messages = list(history) if history else []
    messages.append({"role": "user", "content": text})

    response = await client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": system_text,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=messages,
    )

    return response.content[0].text
