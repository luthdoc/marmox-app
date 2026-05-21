"""
Teste de integração do app principal.
Verifica que o main.py monta todos os componentes corretamente.
"""
from fastapi.testclient import TestClient


def test_health_endpoint_available_from_main_app():
    """GET /health deve estar disponível no app principal."""
    from main import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_unhandled_error_returns_500_from_main_app():
    """App principal deve tratar exceções não tratadas com 500 estruturado."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient as TC
    from main import app

    # injeta rota que vai explodir
    @app.get("/test-boom")
    def test_boom():
        raise RuntimeError("boom de integração")

    client = TC(app, raise_server_exceptions=False)
    response = client.get("/test-boom")
    assert response.status_code == 500
    assert response.json() == {"error": "internal_server_error"}

    # remove rota de teste
    app.routes[:] = [r for r in app.routes if getattr(r, "path", "") != "/test-boom"]
