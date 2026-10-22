from __future__ import annotations

from app.leitura import ler
from app.regras import processar
from gerador.fixtures import gerar_csv_sintetico


def test_fixtures_sao_deterministicas_e_compativeis_com_todas_as_fichas(fichas):
    """Verifica RNF05: fixtures sintéticas com semente fixa passam pelo leitor das três fichas."""
    for ficha in fichas.values():
        first = gerar_csv_sintetico(ficha, seed=17, quantidade=12)
        second = gerar_csv_sintetico(ficha, seed=17, quantidade=12)
        result = processar(ler(first, ficha), ficha)
        assert first == second
        assert result.total_linhas == 12
        assert len(result.lancamentos) == 12
        assert all("SINTETICO" in item.descricao for item in result.lancamentos)


def test_gerador_recusa_quantidade_vazia(fichas):
    """Verifica que o gerador não produz CSV de fixture sem nenhuma linha configurada."""
    try:
        gerar_csv_sintetico(fichas["banco-a"], quantidade=0)
    except ValueError as error:
        assert "quantidade" in str(error)
    else:
        raise AssertionError("quantidade zero deveria ser inválida")