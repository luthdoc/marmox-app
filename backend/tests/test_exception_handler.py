"""
Testes para o exception handler global.
Verifica que erros não tratados retornam 500 com body estruturado.
"""
import io
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.logging import configure_logging


def _make_app_with_handler() -> FastAPI:
    from core.exception_handler import register_exception_handlers

    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    def boom():
        raise RuntimeError("erro inesperado")

    return app


def test_unhandled_exception_returns_500():
    """Exceção não tratada deve retornar HTTP 500."""
    client = TestClient(_make_app_with_handler(), raise_server_exceptions=False)
    response = client.get("/boom")
    assert response.status_code == 500


def test_unhandled_exception_body_is_structured():
    """Body do 500 deve ser {'error': 'internal_server_error'}."""
    client = TestClient(_make_app_with_handler(), raise_server_exceptions=False)
    response = client.get("/boom")
    assert response.json() == {"error": "internal_server_error"}


def test_unhandled_exception_generates_error_log():
    """Exceção não tratada deve gerar log ERROR com stack trace."""
    stream = io.StringIO()
    configure_logging(stream=stream)

    client = TestClient(_make_app_with_handler(), raise_server_exceptions=False)
    client.get("/boom")

    logs = [json.loads(line) for line in stream.getvalue().strip().splitlines() if line]
    error_logs = [l for l in logs if l.get("level") == "ERROR"]

    assert len(error_logs) >= 1
    assert any("exc_info" in l or "RuntimeError" in l.get("message", "") for l in error_logs)
