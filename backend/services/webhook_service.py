"""
Service de processamento de webhooks do Z-API (Story 2.2 + 2.4).

Responsabilidades:
- Validar o token Z-API contra o esperado
- Resolver o tenant a partir do instanceId
- Persistir a mensagem inbound na tabela messages
- Emitir logs estruturados para cada mensagem recebida
- Disparar echo automático (fire-and-forget) para tenants com status "active" (Story 2.4)
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from functools import partial

from db.client import get_client, set_tenant_context
from schemas.webhook import ZApiWebhookPayload
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
    phone: str
    text: str
    instance_id: str


def _validate_token(received_token: str | None, expected_token: str) -> None:
    """Lança PermissionError se o token for ausente ou inválido."""
    if not received_token or received_token != expected_token:
        raise PermissionError("Token Z-API inválido ou ausente")


def _resolve_tenant(instance_id: str) -> dict | None:
    """Busca o tenant pelo instanceId. Retorna row com id/status ou None."""
    client = get_client()
    tenant_query_result = (
        client.table("tenants")
        .select("id, status")
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


def _persist_inbound_message(tenant_id: str, phone: str, content: str) -> None:
    """Persiste a mensagem inbound na tabela messages (NFR3: RLS ativo via set_tenant_context)."""
    set_tenant_context(tenant_id)
    client = get_client()
    client.table("messages").insert(
        {
            "tenant_id": tenant_id,
            "direction": "inbound",
            "lead_id": None,
            "phone": phone,
            "content": content,
        }
    ).execute()


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


async def _handle_text_message(msg: InboundMessage) -> None:
    """Loga, persiste mensagem inbound e dispara echo se tenant estiver ativo.

    Mensagens com phone em formato inválido (S2) são descartadas com log de aviso.
    """
    if not _is_valid_phone(msg.phone):
        _log_invalid_phone(msg)
        return
    _log_inbound_received(msg)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        partial(_persist_inbound_message, msg.tenant_id, msg.phone, msg.text),
    )
    if msg.tenant_status == _ACTIVE_STATUS:
        asyncio.create_task(_dispatch_echo(msg.tenant_id, msg.phone, msg.text))


def process_inbound_message(
    payload: ZApiWebhookPayload,
    received_token: str | None,
    expected_token: str,
) -> dict:
    """Processa uma mensagem inbound recebida via webhook do Z-API.

    Valida o token recebido contra o esperado, resolve o tenant pelo instanceId
    e persiste a mensagem quando todos os critérios forem atendidos.
    Para tenants com status "active", dispara echo automático via fire-and-forget.
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

    if not payload.is_text_message:
        return {"received": True}

    tenant_row = _resolve_tenant(payload.instanceId)
    if tenant_row is None:
        return {"received": True}

    # is_text_message garante que text e phone não são None; o type checker não consegue inferir
    msg = InboundMessage(
        tenant_id=tenant_row["id"],
        tenant_status=tenant_row["status"],
        phone=payload.phone,  # type: ignore[arg-type]
        text=payload.text.message,  # type: ignore[union-attr]
        instance_id=payload.instanceId,
    )
    asyncio.create_task(_handle_text_message(msg))

    return {"received": True}


async def _dispatch_echo(tenant_id: str, phone: str, original_text: str) -> None:
    """Envia o echo da mensagem recebida para o remetente.

    Executado via asyncio.create_task (fire-and-forget). Falhas são logadas
    e não propagadas para não afetar o fluxo principal do webhook.

    Args:
        tenant_id: UUID do tenant que receberá o envio.
        phone: Número do remetente original.
        original_text: Texto da mensagem recebida.
    """
    try:
        echo_text = f"Recebi: {original_text}"
        await send_message(tenant_id, phone, echo_text)
    except Exception as exc:
        logger.error(
            "Falha ao enviar echo — erro ignorado (fire-and-forget)",
            extra={"tenant_id": tenant_id, "phone": phone, "error": str(exc)},
        )
