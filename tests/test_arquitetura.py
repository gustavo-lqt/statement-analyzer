from __future__ import annotations

import ast
from pathlib import Path


def _import_roots(source: str) -> set[str]:
    tree = ast.parse(source)
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_motores_nao_dependem_de_http_persistencia_ou_rede():
    """Verifica RNF02: regras e consultas permanecem puras, sem HTTP, I/O ou banco."""
    repository = Path(__file__).parents[1]
    forbidden = {"fastapi", "sqlite3", "requests", "urllib", "socket", "pathlib"}
    for module_name in ("regras.py", "consultas.py"):
        roots = _import_roots((repository / "app" / module_name).read_text(encoding="utf-8"))
        assert roots.isdisjoint(forbidden), f"{module_name} importa {roots & forbidden}"


def test_sqlite_so_e_importado_na_camda_de_persistencia():
    """Verifica o limite arquitetural de que SQL e SQLite ficam em app/db.py."""
    repository = Path(__file__).parents[1]
    for module_path in (repository / "app").glob("*.py"):
        if module_path.name != "db.py":
            assert "sqlite3" not in _import_roots(module_path.read_text(encoding="utf-8"))