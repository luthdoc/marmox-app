"""
Testes para o middleware de request logging.
Verifica que cada requisição gera log INFO com método, path e status.
"""
import io
import json
import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.logging import configure_logging


@pytest.fixture()
def app_with_middleware() -> FastAPI:
    from core.middleware import RequestLoggingMiddleware

    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/ping")
    def ping():
        return {"pong": True}

    return app


def test_request_generates_info_log(app_with_middleware: FastAPI):
    """Requisição bem-sucedida deve gerar log INFO com method, path e status_code."""
    stream = io.StringIO()
    configure_logging(stream=stream)

    client = TestClient(app_with_middleware, raise_server_exceptions=False)
    client.get("/ping")

    logs = [json.loads(line) for line in stream.getvalue().strip().splitlines() if line]
    request_log = next((l for l in logs if l.get("path") == "/ping"), None)

    assert request_log is not None, "Nenhum log com path=/ping encontrado"
    assert request_log["level"] == "INFO"
    assert request_log["method"] == "GET"
    assert request_log["status_code"] == 200


def test_request_log_contains_duration(app_with_middleware: FastAPI):
    """Log de requisição deve conter campo duration_ms."""
    stream = io.StringIO()
    configure_logging(stream=stream)

    client = TestClient(app_with_middleware, raise_server_exceptions=False)
    client.get("/ping")

    logs = [json.loads(line) for line in stream.getvalue().strip().splitlines() if line]
    request_log = next((l for l in logs if l.get("path") == "/ping"), None)

    assert request_log is not None
    assert "duration_ms" in request_log
