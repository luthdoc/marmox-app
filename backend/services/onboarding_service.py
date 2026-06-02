"""
Serviço do agente de onboarding via WhatsApp (Story 5.2).

Responsabilidades:
- process_onboarding_message: chama Claude Haiku com system prompt de onboarding
  e retorna a resposta bruta (inclui bloco [DADOS_EMPRESA]).
- parse_empresa_block: extrai o JSON do bloco [DADOS_EMPRESA] e retorna
  (dados, texto_limpo). Retorna (None, raw) se bloco ausente ou malformado.
"""
from __future__ import annotations

import json
import re

from anthropic import AsyncAnthropic

from services.agent_service import _MODEL_HAIKU

_ONBOARDING_SYSTEM = (
    "Você é o assistente de configuração do Marmax — um sistema de atendimento por WhatsApp "
    "para marmorarias. Seu papel é guiar o dono da marmoraria na configuração inicial do assistente.\n\n"
    "Você precisa coletar exatamente cinco informações:\n"
    "1. Nome da empresa (name)\n"
    "2. Serviços oferecidos (services) — lista, ex: Bancada, Piso, Escada\n"
    "3. Regiões atendidas (regions) — lista, ex: São Paulo, ABC Paulista\n"
    "4. Horário de funcionamento (business_hours) — ex: Seg-Sex 8h-18h\n"
    "5. Mensagem de boas-vindas (welcome_message) — texto enviado ao cliente na primeira mensagem\n\n"
    "Colete uma informação por vez, em ordem natural. Seja cordial e objetivo.\n"
    "NUNCA mencione preços, prazos ou informações que não foram fornecidas pelo dono — "
    "se não souber, peça a informação ao dono.\n\n"
    "Ao final de CADA resposta, inclua obrigatoriamente o bloco abaixo com os dados coletados "
    "até o momento. Campos ainda não coletados devem aparecer como null. NUNCA omita o bloco.\n\n"
    "[DADOS_EMPRESA]\n"
    '{"name": <string|null>, "services": <list|null>, "regions": <list|null>, '
    '"business_hours": <string|null>, "welcome_message": <string|null>, '
    '"onboarding_complete": <bool>}\n'
    "[/DADOS_EMPRESA]\n\n"
    'onboarding_complete deve ser true apenas quando TODOS os cinco campos forem não-nulos.'
)

_BLOCK_PATTERN = re.compile(
    r"\[DADOS_EMPRESA\]\s*(.*?)\s*\[/DADOS_EMPRESA\]",
    re.DOTALL,
)


def parse_empresa_block(raw: str) -> tuple[dict | None, str]:
    """Extrai o JSON do bloco [DADOS_EMPRESA] e retorna (dados, texto_limpo).

    Se o bloco estiver ausente ou o JSON for malformado, retorna (None, raw).
    O texto_limpo tem o bloco removido mas preserva o restante da resposta.
    """
    match = _BLOCK_PATTERN.search(raw)
    if not match:
        return None, raw
    json_str = match.group(1).strip()
    try:
        dados = json.loads(json_str)
    except json.JSONDecodeError:
        return None, raw
    texto_limpo = _BLOCK_PATTERN.sub("", raw).strip()
    return dados, texto_limpo


async def process_onboarding_message(
    tenant_id: str,
    text: str,
    history: list[dict],
) -> str:
    """Chama Claude Haiku com system prompt de onboarding e retorna resposta bruta.

    O histórico deve conter as mensagens anteriores da conversa de onboarding
    (carregamento é responsabilidade do chamador).
    A resposta bruta inclui o bloco [DADOS_EMPRESA] — use parse_empresa_block
    para extrair os dados e obter o texto limpo.
    """
    client = AsyncAnthropic()
    messages = list(history)
    messages.append({"role": "user", "content": text})
    response = await client.messages.create(
        model=_MODEL_HAIKU,
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": _ONBOARDING_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=messages,
    )
    return response.content[0].text
