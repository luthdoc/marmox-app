"""
Smoke tests para main.py.

Para rodar:
    pip install httpx pytest
    pytest tests/test_main.py
"""
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_root_returns_ok():
    """GET / deve retornar status ok e nome do serviço."""
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "marmax-api"
