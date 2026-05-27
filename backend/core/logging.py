import logging
import os
import sys
from typing import IO

from pythonjsonlogger.json import JsonFormatter


class _MarmaxFormatter(JsonFormatter):
    """JsonFormatter com campos renomeados para o padrão do projeto."""

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = log_record.pop("asctime", None) or self.formatTime(record)
        log_record["level"] = log_record.pop("levelname", record.levelname)
        log_record["logger"] = log_record.pop("name", record.name)
        log_record.setdefault("message", record.getMessage())


def configure_logging(stream: IO[str] | None = None, log_level: str | None = None) -> None:
    """Configura logging estruturado em JSON globalmente.

    Args:
        stream: destino dos logs (padrão: sys.stdout). Aceita qualquer IO[str],
                o que permite injetar StringIO nos testes sem tocar em stdout.
        log_level: nível de log (ex: "DEBUG", "INFO", "WARNING"). Se None, lê
                   da variável de ambiente LOG_LEVEL (padrão: "INFO").
    """
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(
        _MarmaxFormatter(fmt="%(asctime)s %(levelname)s %(name)s %(message)s")
    )

    effective_level = log_level or os.environ.get("LOG_LEVEL", "INFO")
    root = logging.getLogger()
    root.setLevel(getattr(logging, effective_level.upper(), logging.INFO))
    root.handlers.clear()
    root.addHandler(handler)
