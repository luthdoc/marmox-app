"""
Serviço de envio de mensagens via Z-API (Story 2.3).

Responsabilidades:
- Lookup de credenciais do tenant na tabela tenants (com cache de 30s)
- Envio de mensagens via POST para o endpoint Z-API de texto
- Retry exponencial: até 3 tentativas com backoff 1s, 2s, 4s
- Logging estruturado para cada tentativa e resultado final
- Persistência da mensagem outbound em messages após envio bem-sucedido
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import TypedDict

import httpx

from db.client import get_client, set_tenant_context

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cache de credenciais de tenant (TTL de 30 segundos)
# ---------------------------------------------------------------------------

_CACHE_TTL_SECONDS = 30

# Estrutura: { tenant_id: (zapi_instance_id, zapi_token, cached_at_monotonic) }
_tenant_credential_cache: dict[str, tuple[str, str, float]] = {}


class TenantCredentials(TypedDict):
    zapi_instance_id: str
    zapi_token: str


def _parse_tenant_credentials(row: dict) -> tuple[str, str]:
    """Extrai instance_id e token do row do banco; lança ValueError se ausentes."""
    instance_id = row.get("zapi_instance_id")
    token = row.get("zapi_token")
    if not instance_id or not token:
        raise ValueError("Credenciais Z-API ausentes no tenant")
    return instance_id, token


def _get_tenant_credentials(tenant_id: str) -> TenantCredentials | None:
    """Retorna as credenciais Z-API do tenant, usando cache de 30s.

    Args:
        tenant_id: UUID do tenant.

    Returns:
        TenantCredentials com instance_id e token, ou None se não encontrado.
    """
    now = time.monotonic()
    cached = _tenant_credential_cache.get(tenant_id)
    if cached is not None:
        instance_id, token, cached_at = cached
        if now - cached_at < _CACHE_TTL_SECONDS:
            return {"zapi_instance_id": instance_id, "zapi_token": token}

    client = get_client()
    tenant_query = (
        client.table("tenants")
        .select("zapi_instance_id, zapi_token")
        .eq("id", tenant_id)
        .execute()
    )

    if not tenant_query.data:
        return None

    instance_id, token = _parse_tenant_credentials(tenant_query.data[0])
    _tenant_credential_cache[tenant_id] = (instance_id, token, now)
    return {"zapi_instance_id": instance_id, "zapi_token": token}


# ---------------------------------------------------------------------------
# Envio de mensagens
# ---------------------------------------------------------------------------

_MAX_ATTEMPTS = 3
_ZAPI_BASE_URL = "https://api.z-api.io/instances/{instance_id}/token/{token}/send-text"


@dataclass
class SendContext:
    url: str
    payload: dict
    tenant_id: str
    phone: str
    text: str


def _log_send_success(ctx: SendContext, attempt: int) -> None:
    """Loga tentativa de envio bem-sucedida."""
    logger.info(
        "Tentativa de envio Z-API",
        extra={
            "tenant_id": ctx.tenant_id,
            "phone": ctx.phone,
            "message_length": len(ctx.text),
            "attempt_number": attempt,
            "success": True,
        },
    )


def _log_send_failure(ctx: SendContext, attempt: int, error: str | None = None) -> None:
    """Loga tentativa de envio com falha."""
    extra: dict = {
        "tenant_id": ctx.tenant_id,
        "phone": ctx.phone,
        "message_length": len(ctx.text),
        "attempt_number": attempt,
        "success": False,
    }
    if error is not None:
        extra["error"] = error
    label = "Tentativa de envio Z-API — erro de rede" if error else "Tentativa de envio Z-API"
    logger.info(label, extra=extra)


async def _attempt_post(
    http_client: httpx.AsyncClient,
    ctx: SendContext,
    attempt: int,
) -> bool:
    """Executa uma tentativa de POST ao Z-API e loga o resultado.

    Returns:
        True se a tentativa foi bem-sucedida (HTTP 2xx), False caso contrário.
    """
    try:
        response = await http_client.post(ctx.url, json=ctx.payload)
        success = response.status_code < 300
        if success:
            _log_send_success(ctx, attempt)
        else:
            _log_send_failure(ctx, attempt)
        return success
    except Exception as exc:
        _log_send_failure(ctx, attempt, error=str(exc))
        return False


async def _retry_send(http_client: httpx.AsyncClient, ctx: SendContext) -> bool:
    """Executa loop de retry com backoff exponencial (até 3 tentativas).

    Returns:
        True se alguma tentativa foi bem-sucedida, False caso contrário.
    """
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        success = await _attempt_post(http_client, ctx, attempt)
        if success:
            return True
        if attempt < _MAX_ATTEMPTS:
            await asyncio.sleep(2 ** (attempt - 1))  # backoff: 1s, 2s
    return False


async def send_message(tenant_id: str, phone: str, text: str) -> bool:
    """Envia uma mensagem WhatsApp via Z-API com retry exponencial.

    Busca as credenciais do tenant, faz até 3 tentativas com backoff
    exponencial (1s, 2s, 4s) e persiste a mensagem enviada na tabela
    messages em caso de sucesso.

    Args:
        tenant_id: UUID do tenant que envia a mensagem.
        phone: Número do destinatário no formato E.164 sem '+' (ex: 5511999999999).
        text: Texto da mensagem a ser enviada.

    Returns:
        True se a mensagem foi enviada com sucesso (HTTP 2xx), False caso contrário.
    """
    credentials = _get_tenant_credentials(tenant_id)
    if credentials is None:
        logger.error(
            "Tenant não encontrado para envio de mensagem",
            extra={"tenant_id": tenant_id, "phone": phone},
        )
        return False

    instance_id = credentials["zapi_instance_id"]
    token = credentials["zapi_token"]
    url = _ZAPI_BASE_URL.format(instance_id=instance_id, token=token)
    ctx = SendContext(url=url, payload={"phone": phone, "message": text}, tenant_id=tenant_id, phone=phone, text=text)

    async with httpx.AsyncClient() as http_client:
        success = await _retry_send(http_client, ctx)

    if success:
        _persist_outbound_message(tenant_id, phone, text)
        return True

    logger.error(
        "Falha ao enviar mensagem Z-API após todas as tentativas",
        extra={
            "tenant_id": tenant_id,
            "phone": phone,
            "error": f"HTTP não-2xx em {_MAX_ATTEMPTS} tentativas",
        },
    )
    return False


def _persist_outbound_message(tenant_id: str, phone: str, content: str) -> None:
    """Persiste a mensagem enviada com sucesso na tabela messages (NFR3: RLS ativo via set_tenant_context).

    Args:
        tenant_id: UUID do tenant remetente.
        phone: Número do destinatário.
        content: Texto da mensagem enviada.
    """
    set_tenant_context(tenant_id)
    client = get_client()
    client.table("messages").insert(
        {
            "tenant_id": tenant_id,
            "direction": "outbound",
            "lead_id": None,
            "phone": phone,
            "content": content,
        }
    ).execute()
