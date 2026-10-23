"""Persistência SQLite do Statement Analyzer (SPEC §7, ADR-004)."""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from app.models import Extrato, Lancamento, MotivoRecusa, Recusa, ResultadoLeitura

SCHEMA = """
CREATE TABLE IF NOT EXISTS extrato (
    id INTEGER PRIMARY KEY, nome_arquivo TEXT NOT NULL, banco TEXT NOT NULL,
    criado_em TEXT NOT NULL, saldo_inicial_centavos INTEGER,
    total_linhas INTEGER NOT NULL, aceitos INTEGER NOT NULL, rejeitados INTEGER NOT NULL);

CREATE TABLE IF NOT EXISTS lancamento (
    id INTEGER PRIMARY KEY,
    extrato_id INTEGER NOT NULL REFERENCES extrato(id) ON DELETE CASCADE,
    data TEXT NOT NULL, valor_centavos INTEGER NOT NULL, descricao TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS recusa (
    id INTEGER PRIMARY KEY,
    extrato_id INTEGER NOT NULL REFERENCES extrato(id) ON DELETE CASCADE,
    numero_linha INTEGER NOT NULL, motivo TEXT NOT NULL, conteudo_bruto TEXT NOT NULL);

CREATE INDEX IF NOT EXISTS idx_lancamento_extrato_data
    ON lancamento(extrato_id, data);
"""


def conectar(caminho: str = ":memory:") -> sqlite3.Connection:
    """Abre o banco, ativa chaves estrangeiras e prepara o schema (ADR-004)."""
    if caminho != ":memory:":
        parent = Path(caminho).parent
        if str(parent) not in ("", "."):
            parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(caminho, check_same_thread=False)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA)
    except Exception:
        conn.close()
        raise
    return conn


def salvar_extrato(
    conn: sqlite3.Connection,
    nome_arquivo: str,
    banco: str,
    criado_em: str,
    saldo_inicial_centavos: int | None,
    resultado: ResultadoLeitura,
) -> Extrato:
    """Grava extrato, lançamentos e recusas atomicamente (RF04, RF05, D3)."""
    with conn:
        cursor = conn.execute(
            """
            INSERT INTO extrato (
                nome_arquivo, banco, criado_em, saldo_inicial_centavos,
                total_linhas, aceitos, rejeitados
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nome_arquivo,
                banco,
                criado_em,
                saldo_inicial_centavos,
                resultado.total_linhas,
                resultado.aceitos,
                resultado.rejeitados,
            ),
        )
        extrato_id = cursor.lastrowid
        conn.executemany(
            """
            INSERT INTO lancamento (
                extrato_id, data, valor_centavos, descricao
            ) VALUES (?, ?, ?, ?)
            """,
            [
                (
                    extrato_id,
                    lancamento.data.isoformat(),
                    lancamento.valor_centavos,
                    lancamento.descricao,
                )
                for lancamento in resultado.lancamentos
            ],
        )
        conn.executemany(
            """
            INSERT INTO recusa (
                extrato_id, numero_linha, motivo, conteudo_bruto
            ) VALUES (?, ?, ?, ?)
            """,
            [
                (extrato_id, recusa.linha, recusa.motivo.value, recusa.conteudo)
                for recusa in resultado.recusas
            ],
        )

    return Extrato(
        id=extrato_id,
        nome_arquivo=nome_arquivo,
        banco=banco,
        criado_em=criado_em,
        saldo_inicial_centavos=saldo_inicial_centavos,
        total_linhas=resultado.total_linhas,
        aceitos=resultado.aceitos,
        rejeitados=resultado.rejeitados,
    )


def _extrato_from_row(row: sqlite3.Row) -> Extrato:
    return Extrato(
        id=row["id"],
        nome_arquivo=row["nome_arquivo"],
        banco=row["banco"],
        criado_em=row["criado_em"],
        saldo_inicial_centavos=row["saldo_inicial_centavos"],
        total_linhas=row["total_linhas"],
        aceitos=row["aceitos"],
        rejeitados=row["rejeitados"],
    )


def listar_extratos(conn: sqlite3.Connection) -> list[Extrato]:
    """Lista extratos por id (RF04)."""
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM extrato ORDER BY id"
    ).fetchall()
    return [_extrato_from_row(row) for row in rows]


def obter_extrato(conn: sqlite3.Connection, extrato_id: int) -> Extrato | None:
    """Busca um extrato ou devolve None se não existir (RF04)."""
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM extrato WHERE id = ?", (extrato_id,)
    ).fetchone()
    return _extrato_from_row(row) if row is not None else None


def listar_lancamentos(
    conn: sqlite3.Connection,
    extrato_id: int,
    limite: int | None = None,
    offset: int = 0,
) -> list[Lancamento]:
    """Lista lançamentos por data e id, opcionalmente paginados (RF05)."""
    conn.row_factory = sqlite3.Row
    query = """
        SELECT id, extrato_id, data, valor_centavos, descricao
        FROM lancamento
        WHERE extrato_id = ?
        ORDER BY data, id
    """
    params: tuple[int, ...]
    if limite is None:
        params = (extrato_id,)
    else:
        query += " LIMIT ? OFFSET ?"
        params = (extrato_id, limite, offset)

    rows = conn.execute(query, params).fetchall()
    return [
        Lancamento(
            data=date.fromisoformat(row["data"]),
            valor_centavos=row["valor_centavos"],
            descricao=row["descricao"],
            id=row["id"],
            extrato_id=row["extrato_id"],
        )
        for row in rows
    ]


def listar_recusas(conn: sqlite3.Connection, extrato_id: int) -> list[Recusa]:
    """Lista recusas por número da linha (RF05)."""
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT numero_linha, motivo, conteudo_bruto
        FROM recusa
        WHERE extrato_id = ?
        ORDER BY numero_linha
        """,
        (extrato_id,),
    ).fetchall()
    return [
        Recusa(
            linha=row["numero_linha"],
            motivo=MotivoRecusa(row["motivo"]),
            conteudo=row["conteudo_bruto"],
        )
        for row in rows
    ]


def apagar_extrato(conn: sqlite3.Connection, extrato_id: int) -> bool:
    """Apaga um extrato e seus dados dependentes em cascata (RF06)."""
    with conn:
        cursor = conn.execute("DELETE FROM extrato WHERE id = ?", (extrato_id,))
    return cursor.rowcount > 0
