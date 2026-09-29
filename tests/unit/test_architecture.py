"""Guard the architectural boundaries this refactor establishes."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "backend"


def test_services_do_not_import_storage_or_http_adapters():
    for path in (ROOT / "service").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert not module.startswith(
                    (
                        "sqlalchemy",
                        "fastapi",
                        "backend.models",
                        "backend.repositories",
                        "backend.db",
                    )
                ), (path, module)


def test_repositories_do_not_own_transactions_or_http_errors():
    for path in (ROOT / "repositories").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {"commit", "rollback", "begin"}, (
                    path,
                    node.lineno,
                )
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("fastapi"), path
