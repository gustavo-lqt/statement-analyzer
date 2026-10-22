from __future__ import annotations

import pytest

from app.db import Database
from app.models import (
    Lancamento,
    Recusa,
    RecursoNaoEncontrado,
    ResultadoLeitura,
)


def _result() -> ResultadoLeitura:
    return ResultadoLeitura(
        [
            Lancamento("2026-09-01", -1234, "SYNTHETIC ONE", "SYNTHETIC ONE"),
            Lancamento("2026-09-02", 500, "SYNTHETIC TWO", "SYNTHETIC TWO"),
        ],
        [Recusa(4, "DATA_INVALIDA", "synthetic invalid row")],
        3,
    )


def _save(database: Database, *, assumed: bool = True) -> int:
    return database.criar_extrato(
        "synthetic.csv",
        "banco-a",
        "2026-10-22T12:00:00+00:00",
        0,
        assumed,
        _result(),
    )


def test_criacao_persiste_extrato_lancamentos_e_recusas(tmp_path):
    """Verifica RF04 e RN05 na gravação atômica do extrato e recusas."""
    database = Database(tmp_path / "synthetic.sqlite3")
    extract_id = _save(database)
    extract = database.obter_extrato(extract_id)
    database.close()
    assert extract.total_linhas == 3
    assert extract.aceitos == 2
    assert extract.rejeitados == 1
    assert extract.saldo_inicial_assumido is True
    assert extract.recusas[0].motivo == "DATA_INVALIDA"


def test_detalhes_paginam_lancamentos(tmp_path):
    """Verifica RF05 para paginação sem perder o total do extrato."""
    database = Database(tmp_path / "synthetic.sqlite3")
    extract_id = _save(database)
    first_page = database.obter_extrato(extract_id, limit=1, offset=0)
    second_page = database.obter_extrato(extract_id, limit=1, offset=1)
    database.close()
    assert first_page.total_linhas == second_page.total_linhas == 3
    assert first_page.lancamentos[0].data == "2026-09-01"
    assert second_page.lancamentos[0].data == "2026-09-02"


def test_listagem_e_exclusao_cascata(tmp_path):
    """Verifica RF05 e RF06 na listagem e exclusão dos dados associados."""
    database = Database(tmp_path / "synthetic.sqlite3")
    extract_id = _save(database)
    assert len(database.listar_extratos()) == 1
    assert database.excluir_extrato(extract_id) is True
    assert database.listar_extratos() == []
    with pytest.raises(RecursoNaoEncontrado):
        database.listar_lancamentos(extract_id)
    database.close()


def test_excluir_id_inexistente_retorna_false(tmp_path):
    """Verifica RF06 para exclusão de identificador que não existe."""
    database = Database(tmp_path / "synthetic.sqlite3")
    assert database.excluir_extrato(987654) is False
    database.close()


def test_saldo_zero_informado_nao_e_marcado_como_assumido(tmp_path):
    """Verifica RN07 distinguindo zero explícito de saldo inicial omitido."""
    database = Database(tmp_path / "synthetic.sqlite3")
    extract_id = _save(database, assumed=False)
    assert database.obter_extrato(extract_id).saldo_inicial_assumido is False
    database.close()