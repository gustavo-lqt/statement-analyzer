from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterable

from app.models import (
    Extrato,
    Lancamento,
    NenhumaLinhaValida,
    Recusa,
    RecursoNaoEncontrado,
    ResultadoLeitura,
)
from app.regras import normalizar_descricao


class Database:
    def __init__(self, database_path: str | Path = "statement-analyzer.sqlite3") -> None:
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(
            self.database_path,
            check_same_thread=False,
            isolation_level=None,
        )
        self._connection.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock:
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._create_schema()

    def _create_schema(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS extrato (
                id INTEGER PRIMARY KEY,
                nome_arquivo TEXT NOT NULL,
                banco TEXT NOT NULL,
                criado_em TEXT NOT NULL,
                saldo_inicial_centavos INTEGER NOT NULL DEFAULT 0,
                saldo_inicial_assumido INTEGER NOT NULL DEFAULT 1,
                total_linhas INTEGER NOT NULL,
                aceitos INTEGER NOT NULL,
                rejeitados INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS lancamento (
                id INTEGER PRIMARY KEY,
                extrato_id INTEGER NOT NULL REFERENCES extrato(id) ON DELETE CASCADE,
                data TEXT NOT NULL,
                valor_centavos INTEGER NOT NULL,
                descricao TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS recusa (
                id INTEGER PRIMARY KEY,
                extrato_id INTEGER NOT NULL REFERENCES extrato(id) ON DELETE CASCADE,
                numero_linha INTEGER NOT NULL,
                motivo TEXT NOT NULL,
                conteudo_bruto TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_lancamento_extrato_data
                ON lancamento(extrato_id, data);
            """
        )
        extract_columns = {
            row["name"]
            for row in self._connection.execute("PRAGMA table_info(extrato)").fetchall()
        }
        if "saldo_inicial_assumido" not in extract_columns:
            self._connection.execute(
                "ALTER TABLE extrato ADD COLUMN saldo_inicial_assumido INTEGER NOT NULL DEFAULT 1"
            )

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def criar_extrato(
        self,
        nome_arquivo: str,
        banco: str,
        criado_em: str,
        saldo_inicial_centavos: int,
        saldo_inicial_assumido: bool,
        resultado: ResultadoLeitura,
    ) -> int:
        with self._lock:
            cursor = self._connection.cursor()
            try:
                cursor.execute("BEGIN")
                cursor.execute(
                    """INSERT INTO extrato
                    (nome_arquivo, banco, criado_em, saldo_inicial_centavos,
                     saldo_inicial_assumido, total_linhas, aceitos, rejeitados)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        nome_arquivo,
                        banco,
                        criado_em,
                        saldo_inicial_centavos,
                        int(saldo_inicial_assumido),
                        resultado.total_linhas,
                        len(resultado.lancamentos),
                        len(resultado.recusas),
                    ),
                )
                extrato_id = int(cursor.lastrowid)
                cursor.executemany(
                    """INSERT INTO lancamento
                    (extrato_id, data, valor_centavos, descricao)
                    VALUES (?, ?, ?, ?)""",
                    [
                        (extrato_id, item.data, item.valor_centavos, item.descricao)
                        for item in resultado.lancamentos
                    ],
                )
                cursor.executemany(
                    """INSERT INTO recusa
                    (extrato_id, numero_linha, motivo, conteudo_bruto)
                    VALUES (?, ?, ?, ?)""",
                    [
                        (extrato_id, item.numero_linha, item.motivo, item.conteudo_bruto)
                        for item in resultado.recusas
                    ],
                )
                cursor.execute("COMMIT")
                return extrato_id
            except Exception:
                cursor.execute("ROLLBACK")
                raise
            finally:
                cursor.close()

    def criar_extrato_streaming(
        self,
        nome_arquivo: str,
        banco: str,
        criado_em: str,
        saldo_inicial_centavos: int,
        saldo_inicial_assumido: bool,
        results: Iterable[Lancamento | Recusa],
    ) -> int:
        with self._lock:
            cursor = self._connection.cursor()
            try:
                cursor.execute("BEGIN")
                cursor.execute(
                    """INSERT INTO extrato
                    (nome_arquivo, banco, criado_em, saldo_inicial_centavos,
                     saldo_inicial_assumido, total_linhas, aceitos, rejeitados)
                    VALUES (?, ?, ?, ?, ?, 0, 0, 0)""",
                    (
                        nome_arquivo,
                        banco,
                        criado_em,
                        saldo_inicial_centavos,
                        int(saldo_inicial_assumido),
                    ),
                )
                extract_id = int(cursor.lastrowid)
                total = accepted = rejected = 0
                for result in results:
                    total += 1
                    if isinstance(result, Recusa):
                        rejected += 1
                        cursor.execute(
                            """INSERT INTO recusa
                            (extrato_id, numero_linha, motivo, conteudo_bruto)
                            VALUES (?, ?, ?, ?)""",
                            (
                                extract_id,
                                result.numero_linha,
                                result.motivo,
                                result.conteudo_bruto,
                            ),
                        )
                    elif isinstance(result, Lancamento):
                        accepted += 1
                        cursor.execute(
                            """INSERT INTO lancamento
                            (extrato_id, data, valor_centavos, descricao)
                            VALUES (?, ?, ?, ?)""",
                            (extract_id, result.data, result.valor_centavos, result.descricao),
                        )
                    else:
                        raise TypeError("resultado de leitura desconhecido")

                if accepted == 0:
                    raise NenhumaLinhaValida()
                cursor.execute(
                    """UPDATE extrato SET total_linhas = ?, aceitos = ?, rejeitados = ?
                    WHERE id = ?""",
                    (total, accepted, rejected, extract_id),
                )
                cursor.execute("COMMIT")
                return extract_id
            except Exception:
                cursor.execute("ROLLBACK")
                raise
            finally:
                cursor.close()

    def listar_extratos(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM extrato ORDER BY id"
            ).fetchall()
        return [dict(row) for row in rows]

    def obter_extrato(self, extrato_id: int, limit: int = 100, offset: int = 0) -> Extrato:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM extrato WHERE id = ?", (extrato_id,)
            ).fetchone()
            if row is None:
                raise RecursoNaoEncontrado()
            launch_rows = self._connection.execute(
                """SELECT * FROM lancamento WHERE extrato_id = ?
                ORDER BY data, id LIMIT ? OFFSET ?""",
                (extrato_id, limit, offset),
            ).fetchall()
            refusal_rows = self._connection.execute(
                "SELECT * FROM recusa WHERE extrato_id = ? ORDER BY numero_linha",
                (extrato_id,),
            ).fetchall()

        launches = [
            Lancamento(
                data=item["data"],
                valor_centavos=item["valor_centavos"],
                descricao=item["descricao"],
                descricao_normalizada=normalizar_descricao(item["descricao"]),
                id=item["id"],
                extrato_id=item["extrato_id"],
            )
            for item in launch_rows
        ]
        refusals = [
            Recusa(item["numero_linha"], item["motivo"], item["conteudo_bruto"])
            for item in refusal_rows
        ]
        return Extrato(
            row["id"],
            row["nome_arquivo"],
            row["banco"],
            row["criado_em"],
            row["saldo_inicial_centavos"],
            bool(row["saldo_inicial_assumido"]),
            row["total_linhas"],
            row["aceitos"],
            row["rejeitados"],
            launches,
            refusals,
        )

    def listar_lancamentos(self, extrato_id: int) -> list[Lancamento]:
        with self._lock:
            exists = self._connection.execute(
                "SELECT 1 FROM extrato WHERE id = ?", (extrato_id,)
            ).fetchone()
            if exists is None:
                raise RecursoNaoEncontrado()
            rows = self._connection.execute(
                "SELECT * FROM lancamento WHERE extrato_id = ? ORDER BY data, id",
                (extrato_id,),
            ).fetchall()
        return [
            Lancamento(
                data=row["data"],
                valor_centavos=row["valor_centavos"],
                descricao=row["descricao"],
                descricao_normalizada=normalizar_descricao(row["descricao"]),
                id=row["id"],
                extrato_id=row["extrato_id"],
            )
            for row in rows
        ]

    def excluir_extrato(self, extrato_id: int) -> bool:
        with self._lock:
            cursor = self._connection.execute("DELETE FROM extrato WHERE id = ?", (extrato_id,))
            return cursor.rowcount > 0