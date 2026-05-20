from fastapi import FastAPI

app = FastAPI(title="Marmax API", version="0.1.0")


@app.get("/")
def root() -> dict:
    """Rota raiz — placeholder para health-check da Epic 1."""
    return {"status": "ok", "service": "marmax-api"}
