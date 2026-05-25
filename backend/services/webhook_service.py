"""
Service de processamento de webhooks do Z-API (Story 2.2).

Responsabilidades:
- Validar o token Z-API contra o esperado
- Resolver o tenant a partir do instanceId
- Persistir a mensagem inbound na tabela messages
- Emitir logs estruturados para cada mensagem recebida
"""
from __future__ import annotations

import logging

from db.client import get_client
from schemas.webhook import ZApiWebhookPayload

logger = logging.getLogger(__name__)


def process_inbound_message(
    payload: ZApiWebhookPayload,
    received_token: str | None,
    expected_token: str,
) -> dict:
    """Processa uma mensagem inbound recebida via webhook do Z-API.

    Valida o token recebido contra o esperado, resolve o tenant pelo instanceId
    e persiste a mensagem quando todos os critérios forem atendidos.
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
    if not received_token or received_token != expected_token:
        raise PermissionError("Token Z-API inválido ou ausente")

    if not payload.is_text_message:
        return {"received": True}

    client = get_client()

    tenant_result = (
        client.table("tenants")
        .select("id")
        .eq("zapi_instance_id", payload.instanceId)
        .execute()
    )

    if not tenant_result.data:
        logger.warning(
            "Tenant não encontrado para instanceId",
            extra={"instance_id": payload.instanceId},
        )
        return {"received": True}

    tenant_id = tenant_result.data[0]["id"]
    message_text = payload.text.message  # type: ignore[union-attr]

    logger.info(
        "Mensagem inbound recebida",
        extra={
            "tenant_id": tenant_id,
            "phone": payload.phone,
            "message_length": len(message_text),
            "instance_id": payload.instanceId,
        },
    )

    client.table("messages").insert(
        {
            "tenant_id": tenant_id,
            "direction": "inbound",
            "lead_id": None,
            "phone": payload.phone,
            "content": message_text,
        }
    ).execute()

    return {"received": True}
