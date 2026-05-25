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

from db.client import get_client, set_tenant_context
from schemas.webhook import ZApiWebhookPayload
from services.zapi_client import send_message

logger = logging.getLogger(__name__)

_ACTIVE_STATUS = "active"


def _validate_token(received_token: str | None, expected_token: str) -> None:
    """Lança PermissionError se o token for ausente ou inválido."""
    if not received_token or received_token != expected_token:
        raise PermissionError("Token Z-API inválido ou ausente")


def _resolve_tenant(instance_id: str) -> dict | None:
    """Busca o tenant pelo instanceId. Retorna row com id/status ou None."""
    client = get_client()
    result = (
        client.table("tenants")
        .select("id, status")
        .eq("zapi_instance_id", instance_id)
        .execute()
    )
    if not result.data:
        logger.warning(
            "Tenant não encontrado para instanceId",
            extra={"instance_id": instance_id},
        )
        return None
    return result.data[0]


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


async def _handle_text_message(tenant_id: str, tenant_status: str, phone: str, text: str) -> None:
    """Loga, persiste mensagem inbound e dispara echo se tenant estiver ativo."""
    logger.info(
        "Mensagem inbound recebida",
        extra={
            "tenant_id": tenant_id,
            "phone": phone,
            "message_length": len(text),
        },
    )
    _persist_inbound_message(tenant_id, phone, text)
    if tenant_status == _ACTIVE_STATUS:
        asyncio.create_task(_dispatch_echo(tenant_id, phone, text))


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

    tenant_id = tenant_row["id"]
    tenant_status = tenant_row["status"]
    # is_text_message garante que text não é None; o type checker não consegue inferir
    message_text = payload.text.message  # type: ignore[union-attr]
    asyncio.create_task(_handle_text_message(tenant_id, tenant_status, payload.phone, message_text))

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
