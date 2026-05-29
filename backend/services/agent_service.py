"""
Serviço do agente Claude para processamento de mensagens (Story 3.1 + 3.4 + 3.5).

Responsabilidades:
- Receber texto (e opcionalmente imagem) de uma mensagem inbound com contexto de tenant e lead
- Chamar o Claude com system prompt dinâmico completo do tenant (Story 3.4)
- Retornar o texto bruto da resposta do Claude ao chamador (inclui bloco [DADOS_LEAD])
- Habilitar prompt caching via cache_control ephemeral no system prompt
- Suportar roteamento Haiku→Sonnet via parâmetro model (Story 3.5)
- Construir bloco image no payload Claude quando image_url fornecida (Story 3.5)
"""
from __future__ import annotations

from typing import Optional

from anthropic import AsyncAnthropic

_MODEL_HAIKU = "claude-haiku-4-5-20251001"
_MODEL_SONNET = "claude-sonnet-4-6"

# Alias para compatibilidade com código legado que referencia _MODEL
_MODEL = _MODEL_HAIKU

# Palavras-chave que indicam mensagem complexa e ativam roteamento para Sonnet.
# Lista configurável — edite aqui para ajustar a sensibilidade do detector.
COMPLEXITY_KEYWORDS: list[str] = [
    "problema",
    "erro",
    "insatisfeito",
    "insatisfação",
    "reclamação",
    "reclamar",
    "defeito",
    "quebrado",
    "danificado",
    "péssimo",
    "horrível",
    "não funciona",
    "cancelar",
    "reembolso",
    "devolução",
]

_SYSTEM_BASE = (
    "Você é o assistente virtual da {tenant_name}. "
    "Seu papel é atender clientes interessados em serviços de marmoraria de forma clara e natural. "
    "Você nunca deve fingir ser humano — sempre deixe claro que é um assistente virtual. "
    "Seja cordial, objetivo e profissional.\n\n"
    "NUNCA invente informações sobre preços ou prazos que não estejam no contexto abaixo — "
    "se não souber, diga que vai verificar com a equipe."
)

_SECTION_SERVICES = "\n\nServiços oferecidos: {services}"
_SECTION_REGIONS = "\nRegiões atendidas: {regions}"
_SECTION_HOURS = "\nHorário de funcionamento: {business_hours}"
_SECTION_WELCOME = "\nMensagem de boas-vindas: {welcome_message}"

_QUALIFICATION_INSTRUCTIONS = """

COLETA DE DADOS DO LEAD
Ao longo da conversa, colete naturalmente os seguintes dados do cliente:
- Nome
- Tipo de serviço desejado
- Material preferido (se aplicável)
- Urgência ou prazo
- Bairro ou região

Ao final de cada resposta, adicione obrigatoriamente o bloco abaixo com os dados coletados ATÉ AGORA.
Campos ainda não coletados devem aparecer como null. NUNCA omita o bloco.

[DADOS_LEAD]
{"name": <string|null>, "service_type": <string|null>, "material": <string|null>, "urgency": <string|null>, "region": <string|null>, "status": <"new"|"qualifying"|"qualified">}
[/DADOS_LEAD]"""


def _build_system_prompt(tenant_name: str, tenant_context: dict) -> str:
    """Constrói o system prompt completo com contexto do tenant e instruções de qualificação.

    Injeta somente os campos presentes no contexto (campos ausentes/vazios são omitidos).
    O bloco de instruções de qualificação é sempre incluído.

    Args:
        tenant_name: Nome da empresa do tenant.
        tenant_context: Dicionário retornado por get_tenant_context, com campos opcionais.

    Returns:
        System prompt completo pronto para injeção no Claude.
    """
    prompt = _SYSTEM_BASE.format(tenant_name=tenant_name)

    services = tenant_context.get("services")
    if services:
        prompt += _SECTION_SERVICES.format(services=", ".join(services))

    regions = tenant_context.get("regions")
    if regions:
        prompt += _SECTION_REGIONS.format(regions=", ".join(regions))

    business_hours = tenant_context.get("business_hours")
    if business_hours:
        prompt += _SECTION_HOURS.format(business_hours=business_hours)

    welcome_message = tenant_context.get("welcome_message")
    if welcome_message:
        prompt += _SECTION_WELCOME.format(welcome_message=welcome_message)

    prompt += _QUALIFICATION_INSTRUCTIONS
    return prompt


def _is_complex_message(text: str) -> bool:
    """Retorna True se o texto contém palavras-chave de complexidade que ativam Sonnet.

    Verificação case-insensitive contra COMPLEXITY_KEYWORDS.
    """
    normalized = text.lower()
    return any(keyword in normalized for keyword in COMPLEXITY_KEYWORDS)


async def process_message(
    tenant_id: str,
    tenant_name: str,
    phone: str,
    text: str = "",
    history: list[dict] | None = None,
    tenant_context: dict | None = None,
    lead_data: dict | None = None,
    image_url: Optional[str] = None,
    model: str = _MODEL_HAIKU,
) -> str:
    """Processa uma mensagem inbound chamando o Claude e retorna a resposta bruta.

    Injeta contexto completo do tenant no system prompt (AC 1, AC 2, AC 3).
    O system prompt é enviado com cache_control ephemeral para habilitar prompt caching (NFR5).
    O histórico de conversa é inserido antes da mensagem atual (Story 3.2).
    Quando image_url é fornecida, constrói bloco image no payload (Story 3.5, AC 3, AC 4).

    A resposta retornada é o texto bruto do Claude, que pode incluir o bloco
    [DADOS_LEAD]...[/DADOS_LEAD]. O chamador é responsável por separar o texto
    limpo do bloco de dados usando parse_lead_data_block (AC 8).

    Args:
        tenant_id: UUID do tenant.
        tenant_name: Nome da empresa do tenant, injetado no system prompt.
        phone: Número do remetente.
        text: Texto da mensagem inbound a ser processada.
        history: Mensagens anteriores no formato [{"role": "user"|"assistant", "content": "..."}].
                 Inseridas antes da mensagem atual. None ou [] equivalem a sem histórico.
        tenant_context: Dicionário com campos de contexto do tenant (services, regions,
                        business_hours, welcome_message). None equivale a contexto vazio.
        lead_data: Dados de qualificação já coletados do lead (reservado para uso futuro).
        image_url: URL da imagem a ser enviada ao Claude via bloco image. None = sem imagem.
        model: Identificador do modelo Claude a usar. Default: Haiku. Use Sonnet para imagens
               ou mensagens complexas (Story 3.5, AC 6).

    Returns:
        Texto bruto da resposta gerada pelo Claude (pode conter bloco [DADOS_LEAD]).

    Raises:
        Exception: Propaga qualquer exceção da SDK Anthropic ao chamador.
    """
    client = AsyncAnthropic()
    system_text = _build_system_prompt(tenant_name, tenant_context or {})

    messages = list(history) if history else []

    if image_url:
        user_content: str | list = [
            {"type": "text", "text": text} if text else {"type": "text", "text": ""},
            {
                "type": "image",
                "source": {
                    "type": "url",
                    "url": image_url,
                },
            },
        ]
    else:
        user_content = text

    messages.append({"role": "user", "content": user_content})

    response = await client.messages.create(
        model=model,
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
