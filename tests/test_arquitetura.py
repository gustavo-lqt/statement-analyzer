"""Guarda de arquitetura (Issue #7, SPEC §7, RNF02).

Analisa o código-fonte de app/ com ``ast``, sem importar os módulos: o motor puro
(leitura, regras, consultas) não conhece HTTP, SQLite nem a persistência, e todo SQL
vive em app/db.py.
"""

from __future__ import annotations

import ast


def modulos_importados(fonte: str, pacote: str = "app") -> set[str]:
    """Devolve os nomes absolutos de todos os módulos importados em ``fonte``.

    ``fonte`` é tratado como um módulo que está direto dentro de ``pacote``, então um import
    relativo (``from . import db``) é resolvido para ``pacote.db``.
    """
    modulos: set[str] = set()
    for no in ast.walk(ast.parse(fonte)):
        if isinstance(no, ast.Import):
            modulos.update(alias.name for alias in no.names)
        elif isinstance(no, ast.ImportFrom):
            if no.level:
                modulo = f"{pacote}.{no.module}" if no.module else pacote
            else:
                modulo = no.module or ""
            modulos.add(modulo)
            # `from app import db` importa o submódulo app.db.
            if modulo.split(".")[0] == pacote:
                modulos.update(f"{modulo}.{alias.name}" for alias in no.names)
    return modulos


# --- O analisador de imports ------------------------------------------------------


def test_modulos_importados_detecta_import_simples() -> None:
    """RNF02: `import fastapi` e `import sqlite3` aparecem como importados."""
    fonte = "import fastapi\nimport sqlite3 as s\n"

    assert modulos_importados(fonte) == {"fastapi", "sqlite3"}


def test_modulos_importados_detecta_from_import_de_submodulo() -> None:
    """RNF02: `from starlette.responses import X` conta como importar starlette.responses."""
    fonte = "from starlette.responses import JSONResponse\n"

    assert modulos_importados(fonte) == {"starlette.responses"}


def test_modulos_importados_detecta_modulo_importado_do_pacote() -> None:
    """SPEC §7: `from app import db` importa app.db, não só app."""
    fonte = "from app import db, models\n"

    assert {"app.db", "app.models"} <= modulos_importados(fonte)


def test_modulos_importados_resolve_import_relativo() -> None:
    """SPEC §7: `from . import db` e `from .api import x` dentro de app/ contam como app.db e app.api."""
    fonte = "from . import db\nfrom .api import app\n"

    assert {"app.db", "app.api"} <= modulos_importados(fonte)


def test_modulos_importados_ignora_import_dentro_de_string() -> None:
    """RNF02 (borda): texto que só menciona `import fastapi` não é um import."""
    fonte = '"""Este módulo não faz import fastapi."""\nimport datetime\n'

    assert modulos_importados(fonte) == {"datetime"}
