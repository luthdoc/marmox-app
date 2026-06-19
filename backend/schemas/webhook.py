"""
Pydantic models para o payload de webhook da Meta WhatsApp Cloud API.

A Meta envia eventos via POST com estrutura entry[].changes[].value.messages[].
Este módulo modela mensagens de texto e imagem e expõe uma interface
normalizada compatível com o restante do sistema.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class MetaTextBody(BaseModel):
    model_config = {"extra": "ignore"}
    body: str = ""


class MetaImageBody(BaseModel):
    model_config = {"extra": "ignore"}
    id: Optional[str] = None
    caption: Optional[str] = None


class MetaMessage(BaseModel):
    model_config = {"extra": "ignore", "populate_by_name": True}

    id: str = ""
    sender: str = Field(default="", alias="from")
    timestamp: str = ""
    type: str = ""
    text: Optional[MetaTextBody] = None
    image: Optional[MetaImageBody] = None

    @property
    def phone(self) -> str:
        return self.sender

    @property
    def is_text_message(self) -> bool:
        return self.type == "text" and self.text is not None and bool(self.text.body)

    @property
    def is_image_message(self) -> bool:
        return self.type == "image" and self.image is not None and bool(self.image.id)

    @property
    def text_body(self) -> str:
        return self.text.body if self.text else ""

    @property
    def image_url(self) -> Optional[str]:
        """Retorna o media ID da imagem (usado para download via Meta API)."""
        return self.image.id if self.image else None

    @property
    def image_caption(self) -> str:
        return self.image.caption or "" if self.image else ""


class MetaMetadata(BaseModel):
    model_config = {"extra": "ignore"}
    display_phone_number: str = ""
    phone_number_id: str = ""


class MetaValue(BaseModel):
    model_config = {"extra": "ignore"}
    metadata: MetaMetadata = MetaMetadata()
    messages: list[MetaMessage] = []


class MetaChange(BaseModel):
    model_config = {"extra": "ignore"}
    value: MetaValue = MetaValue()
    field: str = ""


class MetaEntry(BaseModel):
    model_config = {"extra": "ignore"}
    id: str = ""
    changes: list[MetaChange] = []


class MetaWebhookPayload(BaseModel):
    """Payload de webhook recebido da Meta WhatsApp Cloud API."""

    model_config = {"extra": "ignore"}

    object: str = ""
    entry: list[MetaEntry] = []

    def get_messages(self) -> list[tuple[str, MetaMessage]]:
        """Retorna lista de (phone_number_id, message) de todos os eventos de mensagem."""
        result = []
        for entry in self.entry:
            for change in entry.changes:
                if change.field != "messages":
                    continue
                phone_number_id = change.value.metadata.phone_number_id
                for msg in change.value.messages:
                    result.append((phone_number_id, msg))
        return result
