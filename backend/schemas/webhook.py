"""
Pydantic models para o payload de webhook do Z-API (Story 2.2).

O Z-API envia eventos de diferentes tipos. Este módulo modela
o payload de mensagem de texto recebida (ReceivedCallback).
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ZApiTextPayload(BaseModel):
    """Conteúdo de texto da mensagem Z-API."""

    message: Optional[str] = None


class ZApiWebhookPayload(BaseModel):
    """Payload completo de webhook recebido do Z-API.

    Campos baseados na documentação Z-API para ReceivedCallback.
    Campos extras são ignorados (extra="ignore") para compatibilidade
    com outros tipos de evento enviados pelo Z-API.
    """

    model_config = {"extra": "ignore"}

    instanceId: str
    type: Optional[str] = None
    phone: Optional[str] = None
    text: Optional[ZApiTextPayload] = None
    momment: Optional[int] = None

    @property
    def is_text_message(self) -> bool:
        """Retorna True se o payload representa uma mensagem de texto válida."""
        return self.type == "ReceivedCallback" and self.text is not None and bool(self.text.message)
