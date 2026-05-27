#!/usr/bin/env python3
"""
check_metrics.py -- metricas objetivas de qualidade para o agente de QA.

Uso:
  python scripts/check_metrics.py          # saida human-readable
  python scripts/check_metrics.py --json   # saida JSON para consumo pelo QA agent

Metricas produzidas:
  C1  -- funcoes com mais de 20 linhas de logica (corpo, excluindo def, docstring, blanks)
  C4  -- complexidade ciclomatica por funcao (via radon)
  T1  -- ratio total linhas-de-teste / total linhas-de-logica de producao (projeto inteiro)

Dependencia: radon (em requirements-dev.txt)
"""
from __future__ import annotations

import ast
import json
import sys
from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# Configuracao
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent.parent  # backend/
PROD_DIRS = ["routers", "services", "core", "schemas"]
# db/ e infra (setup do cliente Supabase) -- sem logica de negocio propria, isento de T1/C1
INFRA_DIRS = ["db"]
TEST_DIR = ROOT / "tests"
LOGIC_LINE_LIMIT = 20
CC_LIMIT = 5
T1_BLOCK_THRESHOLD = 0.9   # ratio < 0.9 -> bloqueio
T1_WARN_THRESHOLD = 1.0    # ratio < 1.0 -> observacao (nao bloqueia)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_logic_line(line: str) -> bool:
    """Retorna True se a linha conta como logica de negocio."""
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith("#"):
        return False
    if stripped in ('"""', "'''", "pass", "@dataclass"):
        return False
    return True


def _count_lines(path: Path) -> int:
    """Conta linhas de logica em um arquivo inteiro."""
    try:
        source = path.read_text(encoding="utf-8")
        return sum(1 for line in source.splitlines() if _is_logic_line(line))
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# C1 -- funcoes > 20 linhas de logica (usando AST para evitar contar
#        assinaturas multi-linha e docstrings como logica)
# ---------------------------------------------------------------------------

@dataclass
class C1Violation:
    file: str
    function: str
    lines: int


def _count_function_body_lines(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    source_lines: list[str],
) -> int:
    """
    Conta linhas de logica no CORPO da funcao.

    Usa informacao do AST para:
    - Pular a linha(s) da assinatura "def ..."  (node.lineno ate body[0].lineno)
    - Pular a docstring inicial, se presente
    - Contar apenas linhas reais de logica
    """
    body = node.body
    if not body:
        return 0

    # Determina onde o corpo logico comeca (apos docstring opcional)
    first_body_idx = 0
    if (
        isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        first_body_idx = 1  # pula docstring

    if first_body_idx >= len(body):
        return 0

    # Linhas do corpo logico: do inicio do primeiro statement nao-docstring
    # ate o fim da funcao (1-indexed no AST, 0-indexed nas listas)
    start = body[first_body_idx].lineno - 1
    end = node.end_lineno  # end_lineno e inclusivo (1-indexed) -> exclusive slice
    func_body_lines = source_lines[start:end]

    return sum(1 for line in func_body_lines if _is_logic_line(line))


def check_c1(prod_files: list[Path]) -> list[C1Violation]:
    violations: list[C1Violation] = []
    for path in prod_files:
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, OSError):
            continue

        source_lines = source.splitlines()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            count = _count_function_body_lines(node, source_lines)
            if count > LOGIC_LINE_LIMIT:
                violations.append(C1Violation(
                    file=str(path.relative_to(ROOT)),
                    function=node.name,
                    lines=count,
                ))
    return violations


# ---------------------------------------------------------------------------
# C4 -- complexidade ciclomatica via radon
# ---------------------------------------------------------------------------

@dataclass
class C4Violation:
    file: str
    function: str
    complexity: int


def check_c4(prod_files: list[Path]) -> list[C4Violation]:
    try:
        from radon.complexity import cc_visit
    except ImportError:
        print(
            "AVISO: radon nao instalado -- C4 ignorado. "
            "Execute: pip install radon",
            file=sys.stderr,
        )
        return []

    violations: list[C4Violation] = []
    for path in prod_files:
        try:
            source = path.read_text(encoding="utf-8")
            results = cc_visit(source)
        except Exception:
            continue
        for block in results:
            if block.complexity > CC_LIMIT:
                violations.append(C4Violation(
                    file=str(path.relative_to(ROOT)),
                    function=block.name,
                    complexity=block.complexity,
                ))
    return violations


# ---------------------------------------------------------------------------
# T1 -- ratio total de linhas de teste / total de logica de producao
#
# Estrategia: nivel de projeto, nao por modulo.
# Razao: um arquivo de teste pode cobrir multiplos modulos (ex: test_webhook.py
# cobre tanto routers/webhook.py quanto services/webhook_service.py). Heuristicas
# de mapeamento arquivo-a-arquivo produzem falsos negatives. O ratio do projeto
# captura a cobertura real sem ambiguidade.
# ---------------------------------------------------------------------------

@dataclass
class T1Result:
    total_prod_lines: int
    total_test_lines: int
    ratio: float
    status: str  # "ok" | "warn" | "block"
    prod_breakdown: list[dict]  # info por arquivo de producao
    test_breakdown: list[dict]  # info por arquivo de teste


def check_t1(prod_files: list[Path]) -> T1Result:
    prod_breakdown = []
    total_prod = 0
    for path in prod_files:
        lines = _count_lines(path)
        total_prod += lines
        prod_breakdown.append({
            "file": str(path.relative_to(ROOT)),
            "logic_lines": lines,
        })

    test_files = sorted(TEST_DIR.glob("test_*.py")) if TEST_DIR.exists() else []
    test_breakdown = []
    total_test = 0
    for path in test_files:
        lines = _count_lines(path)
        total_test += lines
        test_breakdown.append({
            "file": str(path.relative_to(ROOT)),
            "logic_lines": lines,
        })

    ratio = round(total_test / total_prod, 2) if total_prod > 0 else 1.0

    if ratio >= T1_WARN_THRESHOLD:
        status = "ok"
    elif ratio >= T1_BLOCK_THRESHOLD:
        status = "warn"
    else:
        status = "block"

    return T1Result(
        total_prod_lines=total_prod,
        total_test_lines=total_test,
        ratio=ratio,
        status=status,
        prod_breakdown=prod_breakdown,
        test_breakdown=test_breakdown,
    )


# ---------------------------------------------------------------------------
# Coleta de arquivos de producao (exclui infra e __init__.py vazios)
# ---------------------------------------------------------------------------

def collect_prod_files() -> list[Path]:
    files: list[Path] = []
    for d in PROD_DIRS:
        p = ROOT / d
        if p.is_dir():
            files.extend(p.rglob("*.py"))
    return [
        f for f in files
        if not (f.name == "__init__.py" and f.stat().st_size <= 100)
    ]


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def main() -> None:
    as_json = "--json" in sys.argv

    prod_files = collect_prod_files()

    c1 = check_c1(prod_files)
    c4 = check_c4(prod_files)
    t1 = check_t1(prod_files)

    passed = len(c1) == 0 and len(c4) == 0 and t1.status != "block"

    if as_json:
        output = {
            "c1_violations": [
                {"file": v.file, "function": v.function, "logic_lines": v.lines}
                for v in c1
            ],
            "c4_violations": [
                {"file": v.file, "function": v.function, "complexity": v.complexity}
                for v in c4
            ],
            "t1": {
                "total_prod_lines": t1.total_prod_lines,
                "total_test_lines": t1.total_test_lines,
                "ratio": t1.ratio,
                "status": t1.status,
                "prod_breakdown": t1.prod_breakdown,
                "test_breakdown": t1.test_breakdown,
            },
            "summary": {
                "c1_count": len(c1),
                "c4_count": len(c4),
                "t1_status": t1.status,
                "passed": passed,
            },
        }
        print(json.dumps(output, indent=2))
    else:
        print("=" * 60)
        print("check_metrics -- Qualidade de codigo (backend)")
        print("=" * 60)

        print(f"\n[C1] Funcoes > {LOGIC_LINE_LIMIT} linhas de logica: {len(c1)}")
        for v in c1:
            print(f"  FAIL {v.file} :: {v.function}() -- {v.lines} linhas")
        if not c1:
            print("  OK Nenhuma violacao")

        print(f"\n[C4] Complexidade ciclomatica > {CC_LIMIT}: {len(c4)}")
        for v in c4:
            print(f"  FAIL {v.file} :: {v.function}() -- CC={v.complexity}")
        if not c4:
            print("  OK Nenhuma violacao")

        print(f"\n[T1] Ratio projeto (teste / producao): {t1.ratio}")
        print(f"     Linhas de producao : {t1.total_prod_lines}")
        print(f"     Linhas de teste    : {t1.total_test_lines}")
        status_label = "OK" if t1.status == "ok" else ("WARN" if t1.status == "warn" else "FAIL")
        print(f"     Status             : {status_label}")

        print("\n" + "=" * 60)
        if passed:
            warns = 1 if t1.status == "warn" else 0
            suffix = f" ({warns} aviso T1 -- nao bloqueia)" if warns else ""
            print(f"APROVADO{suffix}")
        else:
            print(f"BLOQUEADO -- C1:{len(c1)} C4:{len(c4)} T1:{t1.status}")
        print("=" * 60)

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
