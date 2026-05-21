"""
Testes para o endpoint GET /health.
"""
from fastapi.testclient import TestClient
from fastapi import FastAPI


def _make_app() -> FastAPI:
    from routers.health import router

    app = FastAPI()
    app.include_router(router)
    return app


def test_health_returns_200():
    """GET /health deve retornar HTTP 200."""
    client = TestClient(_make_app())
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_status_ok_and_version():
    """GET /health deve retornar {'status': 'ok', 'version': '0.1.0'}."""
    client = TestClient(_make_app())
    response = client.get("/health")
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0"
