from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    """Retorna status do serviço para monitoramento."""
    return {"status": "ok", "version": "0.1.0"}
