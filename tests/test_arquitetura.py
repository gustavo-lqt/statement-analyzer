"""Guarda de arquitetura (Issue #7, SPEC §7, RNF02).

Analisa o código-fonte de app/ com ``ast``, sem importar os módulos: o motor puro
(leitura, regras, consultas) não conhece HTTP, SQLite nem a persistência, e todo SQL
vive em app/db.py.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

# Exige a forma de um comando SQL, para não confundir com "DELETE /extratos/{id}".
COMANDO_SQL = re.compile(
    r"\b(?:CREATE\s+(?:UNIQUE\s+)?(?:TABLE|INDEX)|INSERT\s+INTO|SELECT\s+.+?\s+FROM|DELETE\s+FROM)\b",
    re.IGNORECASE | re.DOTALL,
)


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


def strings_sql(fonte: str) -> list[str]:
    """Devolve as strings de ``fonte`` (exceto docstrings) que contêm um comando SQL.

    Uma f-string é avaliada inteira, com cada ``{...}`` trocado por ``{}``, para pegar SQL
    montado em pedaços.
    """
    arvore = ast.parse(fonte)
    ignorados: set[int] = set()
    for no in ast.walk(arvore):
        if isinstance(no, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            primeiro = no.body[0] if no.body else None
            if isinstance(primeiro, ast.Expr) and isinstance(primeiro.value, ast.Constant):
                ignorados.add(id(primeiro.value))
        elif isinstance(no, ast.JoinedStr):
            ignorados.update(id(parte) for parte in no.values)

    textos: list[str] = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.JoinedStr):
            textos.append(
                "".join(
                    parte.value if isinstance(parte, ast.Constant) else "{}"
                    for parte in no.values
                )
            )
        elif (
            isinstance(no, ast.Constant)
            and isinstance(no.value, str)
            and id(no) not in ignorados
        ):
            textos.append(no.value)
    return [texto for texto in textos if COMANDO_SQL.search(texto)]


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


# --- O detector de SQL ------------------------------------------------------------


def test_strings_sql_detecta_os_quatro_comandos() -> None:
    """SPEC §7: CREATE, INSERT, SELECT e DELETE em string contam como SQL."""
    fonte = (
        'a = "CREATE TABLE extrato (id INTEGER)"\n'
        'b = "INSERT INTO extrato VALUES (1)"\n'
        'c = "SELECT id FROM extrato"\n'
        'd = "DELETE FROM extrato WHERE id = ?"\n'
    )

    assert len(strings_sql(fonte)) == 4


def test_strings_sql_ignora_maiusculas_e_quebras_de_linha() -> None:
    """SPEC §7 (borda): SQL em minúsculas e em string de várias linhas também conta."""
    fonte = 'q = """\n    select id\n    from extrato\n"""\n'

    assert len(strings_sql(fonte)) == 1


def test_strings_sql_detecta_sql_dentro_de_f_string() -> None:
    """SPEC §7 (borda): SQL montado com f-string também é SQL."""
    fonte = 'q = f"DELETE FROM lancamento WHERE extrato_id = {i}"\n'

    assert len(strings_sql(fonte)) == 1


def test_strings_sql_ignora_metodo_http_e_docstring() -> None:
    """SPEC §7 (borda): "DELETE /extratos/{id}" é rota HTTP e docstring não é código."""
    fonte = (
        '"""Módulo que faz SELECT id FROM extrato só na documentação."""\n'
        '@app.delete("/extratos/{id}")\n'
        "def apagar():\n"
        '    """Trata DELETE /extratos/{id}."""\n'
        '    return "selecione um arquivo"\n'
    )

    assert strings_sql(fonte) == []


# --- As guardas, aplicadas ao código de app/ --------------------------------------

PASTA_APP = Path(__file__).resolve().parent.parent / "app"

MOTOR_PURO = ("leitura", "regras", "consultas")

# Prefixos proibidos no motor puro: HTTP, SQLite e as camadas de fora (SPEC §7).
IMPORTS_PROIBIDOS = ("fastapi", "starlette", "sqlite3", "app.db", "app.api")


def _fonte_do_modulo(nome: str) -> str:
    caminho = PASTA_APP / f"{nome}.py"
    if not caminho.exists():
        pytest.skip(f"app/{nome}.py ainda não está nesta branch (entra pela entrega)")
    return caminho.read_text(encoding="utf-8")


def _proibido(modulo: str) -> bool:
    return any(modulo == p or modulo.startswith(f"{p}.") for p in IMPORTS_PROIBIDOS)


@pytest.mark.parametrize("nome", MOTOR_PURO)
def test_motor_puro_nao_importa_http_sqlite_nem_camadas_externas(nome: str) -> None:
    """RNF02, SPEC §7: leitura, regras e consultas não importam fastapi, starlette,
    sqlite3, app.db nem app.api."""
    importados = modulos_importados(_fonte_do_modulo(nome))

    assert sorted(m for m in importados if _proibido(m)) == []


def test_somente_db_contem_sql() -> None:
    """SPEC §7, CLAUDE.md: nenhum arquivo de app/ além de app/db.py contém SQL."""
    violacoes = {
        str(caminho.relative_to(PASTA_APP)): sql
        for caminho in sorted(PASTA_APP.rglob("*.py"))
        if caminho != PASTA_APP / "db.py"
        if (sql := strings_sql(caminho.read_text(encoding="utf-8")))
    }

    assert violacoes == {}
