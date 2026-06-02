"""Parser genérico de blocos delimitados nas respostas do Claude."""
from __future__ import annotations

import json
import re


def parse_delimited_json_block(response: str, tag: str) -> tuple[dict | None, str]:
    """Extrai JSON entre [TAG]...[/TAG] e retorna (dados, texto_sem_bloco).

    Retorna (None, response_original) se o bloco estiver ausente ou JSON inválido.
    """
    pattern = re.compile(rf"\[{re.escape(tag)}\]\s*(.*?)\s*\[/{re.escape(tag)}\]", re.DOTALL)
    match = pattern.search(response)
    if not match:
        return None, response

    raw_json = match.group(1).strip()
    clean_text = pattern.sub("", response).strip()

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        return None, response

    return data, clean_text
