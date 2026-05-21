import logging
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


def configure_logging(stream: IO[str] | None = None) -> None:
    """Configura logging estruturado em JSON globalmente.

    Args:
        stream: destino dos logs (padrão: sys.stdout). Aceita qualquer IO[str],
                o que permite injetar StringIO nos testes sem tocar em stdout.
    """
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(
        _MarmaxFormatter(fmt="%(asctime)s %(levelname)s %(name)s %(message)s")
    )

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)
