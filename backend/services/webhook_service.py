"""
Service de processamento de webhooks do Z-API (Story 2.2 + 2.4 + 3.1 + 3.2 + 3.3 + 3.4 + 3.5).

Responsabilidades:
- Validar o token Z-API contra o esperado
- Resolver o tenant a partir do instanceId
- Persistir a mensagem inbound na tabela messages (com media_url para imagens, Story 3.5)
- Emitir logs estruturados para cada mensagem recebida
- Disparar agente Claude Haiku (fire-and-forget) para tenants com status "active" (Story 3.1)
- Carregar histórico de conversa e passar ao agente (Story 3.2)
- Persistir a resposta outbound após envio bem-sucedido (Story 3.2)
- Buscar ou criar lead antes de processar com o agente (Story 3.3)
- Injetar contexto completo do tenant no agente (Story 3.4)
- Parsear bloco [DADOS_LEAD] da resposta e atualizar qualificação do lead (Story 3.4)
- Rotear para Sonnet em imagens ou mensagens complexas (Story 3.5)
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from functools import partial

from db.client import get_client, set_tenant_context
from db.conversation import load_conversation_history, persist_outbound_message
from db.leads import get_or_create_lead, update_lead_qualification
from db.tenants import get_tenant_context
from schemas.webhook import ZApiWebhookPayload
from services.agent_service import (
    _MODEL_HAIKU,
    _MODEL_SONNET,
    _is_complex_message,
    process_message,
)
from services.qualification import compute_lead_status, parse_lead_data_block
from services.zapi_client import send_message

logger = logging.getLogger(__name__)

_ACTIVE_STATUS = "active"
_PHONE_RE = re.compile(r"^\d{10,15}$")


def _is_valid_phone(phone: str | None) -> bool:
    """Retorna True se o phone está no formato numérico Z-API (10–15 dígitos, sem '+')."""
    return phone is not None and bool(_PHONE_RE.match(phone))


@dataclass
class InboundMessage:
    """Agrupa os dados de uma mensagem inbound para processamento interno."""

    tenant_id: str
    tenant_status: str
    tenant_name: str
    phone: str
    text: str
    instance_id: str
    image_url: str | None = None


def _validate_token(received_token: str | None, expected_token: str) -> None:
    """Lança PermissionError se o token for ausente ou inválido."""
    if not received_token or received_token != expected_token:
        raise PermissionError("Token Z-API inválido ou ausente")


def _resolve_tenant(instance_id: str) -> dict | None:
    """Busca o tenant pelo instanceId. Retorna row com id/status/name ou None."""
    client = get_client()
    tenant_query_result = (
        client.table("tenants")
        .select("id, status, name")
        .eq("zapi_instance_id", instance_id)
        .execute()
    )
    if not tenant_query_result.data:
        logger.warning(
            "Tenant não encontrado para instanceId",
            extra={"instance_id": instance_id},
        )
        return None
    return tenant_query_result.data[0]


def _persist_inbound_message(
    tenant_id: str,
    phone: str,
    content: str,
    media_url: str | None = None,
) -> None:
    """Persiste a mensagem inbound na tabela messages (NFR3: RLS ativo via set_tenant_context).

    Para mensagens de imagem, media_url é preenchido com a URL da imagem (Story 3.5, AC 2).
    """
    set_tenant_context(tenant_id)
    client = get_client()
    row: dict = {
        "tenant_id": tenant_id,
        "direction": "inbound",
        "lead_id": None,
        "phone": phone,
        "content": content,
    }
    if media_url is not None:
        row["media_url"] = media_url
    client.table("messages").insert(row).execute()


def _log_invalid_phone(msg: InboundMessage) -> None:
    """Loga aviso de mensagem descartada por phone em formato inválido."""
    logger.warning(
        "Mensagem descartada — phone com formato inválido",
        extra={"tenant_id": msg.tenant_id, "phone": msg.phone},
    )


def _log_inbound_received(msg: InboundMessage) -> None:
    """Loga recebimento de mensagem inbound."""
    logger.info(
        "Mensagem inbound recebida",
        extra={
            "tenant_id": msg.tenant_id,
            "phone": msg.phone,
            "message_length": len(msg.text),
            "instance_id": msg.instance_id,
        },
    )


async def _handle_inbound_message(msg: InboundMessage) -> None:
    """Loga, persiste mensagem inbound (texto ou imagem) e dispara agente se tenant ativo.

    Mensagens com phone em formato inválido (S2) são descartadas com log de aviso.
    Quando msg.image_url está presente, persiste media_url e despacha para Sonnet (Story 3.5).
    """
    if not _is_valid_phone(msg.phone):
        _log_invalid_phone(msg)
        return
    _log_inbound_received(msg)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        partial(
            _persist_inbound_message,
            msg.tenant_id,
            msg.phone,
            msg.text,
            msg.image_url,
        ),
    )
    if msg.tenant_status == _ACTIVE_STATUS:
        asyncio.create_task(
            _dispatch_agent(
                msg.tenant_id,
                msg.tenant_name,
                msg.phone,
                text=msg.text,
                image_url=msg.image_url,
            )
        )


# Alias para compatibilidade com testes existentes que patcham _handle_text_message
_handle_text_message = _handle_inbound_message


async def process_inbound_message(
    payload: ZApiWebhookPayload,
    received_token: str | None,
    expected_token: str,
) -> dict:
    """Processa uma mensagem inbound recebida via webhook do Z-API.

    Valida o token recebido contra o esperado, resolve o tenant pelo instanceId
    e persiste a mensagem quando todos os critérios forem atendidos.
    Para tenants com status "active", dispara o agente Claude via fire-and-forget.
    Retorna sempre {"received": True} para payloads que passaram na validação
    de token — nunca levanta 4xx para payloads desconhecidos do Z-API.

    Args:
        payload: Payload decodificado do webhook Z-API.
        received_token: Valor do header X-Zapi-Token recebido na requisição.
        expected_token: Token configurado via variável de ambiente ZAPI_TOKEN.

    Returns:
        Dicionário {"received": True} para respostas de sucesso.

    Raises:
        PermissionError: Se o token for ausente ou inválido.
    """
    _validate_token(received_token, expected_token)

    is_processable = payload.is_text_message or payload.is_image_message
    if not is_processable:
        return {"received": True}

    tenant_row = await asyncio.to_thread(_resolve_tenant, payload.instanceId)
    if tenant_row is None:
        return {"received": True}

    if payload.is_image_message:
        # is_image_message garante imageMessage.url não nulo; caption opcional como texto
        text_content = (
            payload.imageMessage.caption  # type: ignore[union-attr]
            if payload.imageMessage and payload.imageMessage.caption  # type: ignore[union-attr]
            else ""
        )
        image_url = payload.image_url
    else:
        # is_text_message garante text.message não nulo
        text_content = payload.text.message  # type: ignore[union-attr]
        image_url = None

    msg = InboundMessage(
        tenant_id=tenant_row["id"],
        tenant_status=tenant_row["status"],
        tenant_name=tenant_row.get("name", ""),
        phone=payload.phone,  # type: ignore[arg-type]
        text=text_content,
        instance_id=payload.instanceId,
        image_url=image_url,
    )
    asyncio.create_task(_handle_inbound_message(msg))

    return {"received": True}


async def _dispatch_agent(
    tenant_id: str,
    tenant_name: str,
    phone: str,
    text: str = "",
    image_url: str | None = None,
) -> None:
    """Processa a mensagem com o agente Claude e envia a resposta ao remetente.

    Executado via asyncio.create_task (fire-and-forget). Falhas são logadas
    e não propagadas para não afetar o fluxo principal do webhook.

    Fluxo (Story 3.2 + 3.3 + 3.4 + 3.5):
    1. Busca ou cria lead via get_or_create_lead (Story 3.3).
    2. Carrega contexto do tenant via get_tenant_context (Story 3.4).
    3. Carrega histórico de conversa via run_in_executor (não bloqueia event loop).
    4. Seleciona modelo: Sonnet se imagem presente ou texto complexo; Haiku caso contrário (Story 3.5).
    5. Chama process_message com histórico + contexto + modelo + image_url opcional.
    6. Parseia bloco [DADOS_LEAD] da resposta bruta (Story 3.4).
    7. Envia ao lead apenas o texto limpo (sem o bloco JSON) (Story 3.4, AC 8).
    8. Persiste resposta outbound na tabela messages apenas se o envio foi bem-sucedido.
    9. Atualiza qualificação do lead se bloco [DADOS_LEAD] foi extraído (Story 3.4).

    Args:
        tenant_id: UUID do tenant.
        tenant_name: Nome da empresa do tenant, injetado no system prompt do agente.
        phone: Número do remetente original.
        text: Texto da mensagem recebida (pode ser vazio para mensagens de imagem pura).
        image_url: URL da imagem, se presente. None = mensagem de texto puro (Story 3.5).
    """
    try:
        loop = asyncio.get_event_loop()
        lead = await loop.run_in_executor(
            None,
            partial(get_or_create_lead, tenant_id, phone),
        )
        lead_id = lead["id"]
        tenant_context = await loop.run_in_executor(
            None,
            partial(get_tenant_context, tenant_id),
        )
        history = await loop.run_in_executor(
            None,
            partial(load_conversation_history, tenant_id, phone),
        )

        # Seleção de modelo: Sonnet para imagens ou textos complexos (Story 3.5, AC 5, AC 6)
        if image_url or _is_complex_message(text):
            model = _MODEL_SONNET
        else:
            model = _MODEL_HAIKU

        raw_response = await process_message(
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            phone=phone,
            text=text,
            history=history,
            tenant_context=tenant_context,
            lead_data=lead,
            image_url=image_url,
            model=model,
        )
        lead_data_extracted, clean_response = parse_lead_data_block(raw_response)
        await send_message(tenant_id, phone, clean_response)
        await loop.run_in_executor(
            None,
            partial(
                persist_outbound_message,
                tenant_id=tenant_id,
                phone=phone,
                content=clean_response,
                lead_id=lead_id,
            ),
        )
        if lead_data_extracted is not None:
            new_status = compute_lead_status(
                lead.get("status", "new"), lead_data_extracted
            )
            patch_data = {
                key: lead_data_extracted.get(key)
                for key in ("name", "service_type", "material", "urgency", "region")
            }
            patch_data["status"] = new_status
            await loop.run_in_executor(
                None,
                partial(update_lead_qualification, lead_id, tenant_id, patch_data),
            )
    except Exception as exc:
        logger.error(
            "Falha ao processar mensagem com agente — erro ignorado (fire-and-forget)",
            extra={"tenant_id": tenant_id, "phone": phone, "error": str(exc)},
        )
