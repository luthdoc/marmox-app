"""
Funções de acesso ao histórico de conversa na tabela messages (Story 3.2 + 3.3).

Exporta:
- load_conversation_history: carrega histórico de mensagens de um lead formatado para o Claude.
- persist_outbound_message: persiste a resposta outbound do agente na tabela messages
  e atualiza last_contact_at no lead correspondente quando lead_id é fornecido (AC 4, Story 3.3).
"""
from __future__ import annotations

from datetime import datetime, timezone

from db.client import get_client, set_tenant_context

_DIRECTION_TO_ROLE: dict[str, str] = {"inbound": "user", "outbound": "assistant"}


def _query_messages(client, tenant_id: str, phone: str, *, limit: int) -> list[dict]:
    """Executa a query de mensagens na tabela messages e retorna os dados brutos."""
    return (
        client.table("messages")
        .select("direction, content, created_at")
        .eq("tenant_id", tenant_id)
        .eq("phone", phone)
        .order("created_at", desc=False)
        .limit(limit)
        .execute()
        .data
    )


def load_conversation_history(
    tenant_id: str,
    phone: str,
    limit: int = 20,
) -> list[dict]:
    """Carrega histórico de mensagens formatado para o Claude."""
    set_tenant_context(tenant_id)
    rows = _query_messages(get_client(), tenant_id, phone, limit=limit)
    return [
        {"role": _DIRECTION_TO_ROLE[row["direction"]], "content": row["content"]}
        for row in rows
        if row["direction"] in _DIRECTION_TO_ROLE
    ]


def persist_outbound_message(
    tenant_id: str,
    phone: str,
    content: str,
    *,
    lead_id: str | None = None,
) -> None:
    """Persiste resposta outbound e atualiza last_contact_at do lead."""
    set_tenant_context(tenant_id)
    client = get_client()
    client.table("messages").insert(
        {
            "tenant_id": tenant_id,
            "direction": "outbound",
            "phone": phone,
            "content": content,
            "lead_id": lead_id,
        }
    ).execute()
    if lead_id is not None:
        now = datetime.now(tz=timezone.utc).isoformat()
        client.table("leads").update({"last_contact_at": now}).eq("id", lead_id).execute()
