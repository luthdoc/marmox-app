"""
Testes para logging estruturado em JSON.
Verifica que os logs produzem os campos obrigatórios.
"""
import json
import logging
import io


def test_log_record_contains_required_fields():
    """Log em nível INFO deve conter timestamp, level, logger e message em JSON."""
    from core.logging import configure_logging

    stream = io.StringIO()
    configure_logging(stream=stream)

    logger = logging.getLogger("test_logger")
    logger.info("mensagem de teste")

    output = stream.getvalue().strip()
    record = json.loads(output)

    assert "timestamp" in record
    assert "level" in record
    assert "logger" in record
    assert "message" in record
    assert record["level"] == "INFO"
    assert record["message"] == "mensagem de teste"
    assert record["logger"] == "test_logger"


def test_log_level_error_is_recorded_correctly():
    """Log em nível ERROR deve registrar level como ERROR."""
    from core.logging import configure_logging

    stream = io.StringIO()
    configure_logging(stream=stream)

    logger = logging.getLogger("test_error")
    logger.error("erro de teste")

    output = stream.getvalue().strip()
    record = json.loads(output)

    assert record["level"] == "ERROR"
    assert record["message"] == "erro de teste"
