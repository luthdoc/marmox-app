"""
Testes para os arquivos de configuração de deploy no Railway.
Verifica existência e conteúdo do Procfile e runtime.txt.
"""
import os
from pathlib import Path

# Diretório raiz do backend (um nível acima de tests/)
BACKEND_ROOT = Path(__file__).parent.parent


def test_procfile_exists():
    """backend/Procfile deve existir no repositório."""
    procfile = BACKEND_ROOT / "Procfile"
    assert procfile.exists(), "Procfile não encontrado em backend/Procfile"


def test_procfile_contains_web_command():
    """Procfile deve conter comando web com uvicorn usando $PORT dinâmico."""
    procfile = BACKEND_ROOT / "Procfile"
    content = procfile.read_text(encoding="utf-8").strip()
    assert content == "web: uvicorn main:app --host 0.0.0.0 --port $PORT", (
        f"Conteúdo do Procfile incorreto: '{content}'"
    )


def test_procfile_uses_dynamic_port():
    """Procfile não deve conter porta fixa 8000 — deve usar $PORT."""
    procfile = BACKEND_ROOT / "Procfile"
    content = procfile.read_text(encoding="utf-8")
    assert "--port 8000" not in content, (
        "Procfile não deve conter porta fixa 8000; use $PORT"
    )
    assert "$PORT" in content, "Procfile deve usar $PORT para a porta"


def test_runtime_txt_exists():
    """backend/runtime.txt deve existir no repositório."""
    runtime = BACKEND_ROOT / "runtime.txt"
    assert runtime.exists(), "runtime.txt não encontrado em backend/runtime.txt"


def test_runtime_txt_specifies_python_312():
    """runtime.txt deve especificar Python 3.12."""
    runtime = BACKEND_ROOT / "runtime.txt"
    content = runtime.read_text(encoding="utf-8").strip()
    assert content.startswith("python-3.12"), (
        f"runtime.txt deve especificar python-3.12, encontrado: '{content}'"
    )
