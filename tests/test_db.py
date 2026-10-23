"""Testes do acesso SQLite (SPEC §7, ADR-004)."""

from datetime import date
import sqlite3

import pytest

from app import db
from app.models import (
    Lancamento,
    MotivoRecusa,
    Recusa,
    ResultadoLeitura,
)


@pytest.fixture
def connection() -> sqlite3.Connection:
    """Cria banco isolado em memória para cada teste (ADR-004)."""
    conn = db.conectar(":memory:")
    yield conn
    conn.close()


def _resultado(
    lancamentos: list[Lancamento] | None = None,
    recusas: list[Recusa] | None = None,
) -> ResultadoLeitura:
    return ResultadoLeitura(
        lancamentos=lancamentos or [],
        recusas=recusas or [],
    )


def _salvar(
    conn: sqlite3.Connection,
    resultado: ResultadoLeitura | None = None,
    saldo_inicial_centavos: int | None = 12500,
):
    return db.salvar_extrato(
        conn,
        "extrato-sintetico.csv",
        "banco-teste",
        "2026-10-22T12:30:00-03:00",
        saldo_inicial_centavos,
        resultado or _resultado(),
    )


def test_conectar_cria_schema_e_ativa_chaves_estrangeiras(
    connection: sqlite3.Connection,
) -> None:
    """Verifica schema idempotente e FK ativa (SPEC §7, ADR-004)."""
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = ?", ("table",)
        )
    }
    indexes = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = ?", ("index",)
        )
    }

    assert {"extrato", "lancamento", "recusa"} <= tables
    assert "idx_lancamento_extrato_data" in indexes
    assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    connection.executescript(db.SCHEMA)


def test_conectar_cria_pasta_pai_de_arquivo(tmp_path) -> None:
    """Verifica criação do diretório do banco (ADR-004)."""
    db_path = tmp_path / "nao-existe" / "statement.db"

    conn = db.conectar(str(db_path))
    try:
        assert db_path.parent.is_dir()
        assert conn.execute(
            "SELECT name FROM sqlite_master WHERE type = ? AND name = ?",
            ("table", "extrato"),
        ).fetchone() is not None
    finally:
        conn.close()


def test_salvar_extrato_preserva_contadores_datas_e_valores_inteiros(
    connection: sqlite3.Connection,
) -> None:
    """Verifica persistência, conversão de datas e inteiros (RF04, RF05, D3)."""
    grande = 987654321012345
    resultado = _resultado(
        [
            Lancamento(date(2026, 10, 3), -2350, "COMPRA FICTICIA"),
            Lancamento(date(2026, 10, 1), grande, "CREDITO FICTICIO"),
        ],
        [Recusa(7, MotivoRecusa.DATA_INVALIDA, "data-ficticia;valor")],
    )

    extrato = _salvar(connection, resultado)
    lancamentos = db.listar_lancamentos(connection, extrato.id)
    recusas = db.listar_recusas(connection, extrato.id)

    assert extrato.id == 1
    assert (extrato.total_linhas, extrato.aceitos, extrato.rejeitados) == (3, 2, 1)
    assert [item.data for item in lancamentos] == [date(2026, 10, 1), date(2026, 10, 3)]
    assert [item.valor_centavos for item in lancamentos] == [grande, -2350]
    assert all(type(item.valor_centavos) is int for item in lancamentos)
    assert all(item.id is not None and item.extrato_id == extrato.id for item in lancamentos)
    assert recusas == [Recusa(7, MotivoRecusa.DATA_INVALIDA, "data-ficticia;valor")]


def test_salvar_extrato_preserva_saldo_inicial_null(
    connection: sqlite3.Connection,
) -> None:
    """Verifica NULL para saldo não informado conforme D3."""
    saved = _salvar(connection, saldo_inicial_centavos=None)

    row = connection.execute(
        "SELECT saldo_inicial_centavos FROM extrato WHERE id = ?", (saved.id,)
    ).fetchone()
    loaded = db.obter_extrato(connection, saved.id)

    assert row[0] is None
    assert loaded is not None
    assert loaded.saldo_inicial_centavos is None


def test_salvar_extrato_faz_rollback_de_todas_as_tabelas_em_falha(
    connection: sqlite3.Connection,
) -> None:
    """Verifica transação atômica ao violar NOT NULL (RF04, RF05)."""
    resultado = _resultado(
        [
            Lancamento(date(2026, 10, 1), -100, "DESCRICAO FICTICIA"),
            Lancamento(date(2026, 10, 2), -200, None),  # type: ignore[arg-type]
        ],
        [Recusa(4, MotivoRecusa.VALOR_INVALIDO, "linha-ficticia")],
    )

    with pytest.raises(sqlite3.IntegrityError):
        _salvar(connection, resultado)

    assert connection.execute("SELECT COUNT(*) FROM extrato").fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM lancamento").fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM recusa").fetchone()[0] == 0


def test_listar_e_obter_extratos_ordenam_por_id_e_tratam_ausencia(
    connection: sqlite3.Connection,
) -> None:
    """Verifica listagem ordenada e busca de extrato inexistente (RF04)."""
    first = _salvar(connection)
    second = _salvar(connection)

    assert [item.id for item in db.listar_extratos(connection)] == [
        first.id,
        second.id,
    ]
    assert db.obter_extrato(connection, second.id) == second
    assert db.obter_extrato(connection, 999) is None


def test_listar_lancamentos_ordena_pagina_e_devolve_lista_vazia(
    connection: sqlite3.Connection,
) -> None:
    """Verifica ordenação, paginação e ausência de lançamentos (RF05)."""
    resultado = _resultado(
        [
            Lancamento(date(2026, 10, 3), -300, "TERCEIRO FICTICIO"),
            Lancamento(date(2026, 10, 1), -100, "PRIMEIRO FICTICIO"),
            Lancamento(date(2026, 10, 1), -200, "SEGUNDO FICTICIO"),
        ]
    )
    extrato = _salvar(connection, resultado)
    all_items = db.listar_lancamentos(connection, extrato.id, limite=None)

    assert [item.descricao for item in all_items] == [
        "PRIMEIRO FICTICIO",
        "SEGUNDO FICTICIO",
        "TERCEIRO FICTICIO",
    ]
    assert db.listar_lancamentos(connection, extrato.id, limite=1, offset=1) == [
        all_items[1]
    ]
    assert db.listar_lancamentos(connection, extrato.id, limite=2, offset=1) == all_items[1:]
    assert db.listar_lancamentos(connection, 999) == []


def test_listar_recusas_ordena_e_reconstroi_motivo_enum(
    connection: sqlite3.Connection,
) -> None:
    """Verifica ordenação e reconstrução das recusas (RF05)."""
    resultado = _resultado(
        recusas=[
            Recusa(9, MotivoRecusa.VALOR_INVALIDO, "conteudo-ficticio-9"),
            Recusa(3, MotivoRecusa.DATA_INVALIDA, "conteudo-ficticio-3"),
        ]
    )
    extrato = _salvar(connection, resultado)

    assert db.listar_recusas(connection, extrato.id) == [
        Recusa(3, MotivoRecusa.DATA_INVALIDA, "conteudo-ficticio-3"),
        Recusa(9, MotivoRecusa.VALOR_INVALIDO, "conteudo-ficticio-9"),
    ]
    assert db.listar_recusas(connection, 999) == []


def test_apagar_extrato_remove_dependencias_e_preserva_outros(
    connection: sqlite3.Connection,
) -> None:
    """Verifica exclusão em cascata e isolamento entre extratos (RF06)."""
    result_with_data = _resultado(
        [Lancamento(date(2026, 10, 1), -100, "ITEM FICTICIO")],
        [Recusa(5, MotivoRecusa.DATA_INVALIDA, "linha-ficticia")],
    )
    deleted = _salvar(connection, result_with_data)
    remaining = _salvar(connection, result_with_data)

    assert db.apagar_extrato(connection, deleted.id) is True
    assert db.apagar_extrato(connection, deleted.id) is False
    assert db.obter_extrato(connection, deleted.id) is None
    assert db.listar_lancamentos(connection, deleted.id) == []
    assert db.listar_recusas(connection, deleted.id) == []
    assert db.obter_extrato(connection, remaining.id) == remaining
    assert len(db.listar_lancamentos(connection, remaining.id)) == 1
    assert len(db.listar_recusas(connection, remaining.id)) == 1
