from __future__ import annotations

import pytest

from app.consultas import (
    dias_no_negativo,
    maior_despesa,
    maior_entrada,
    por_semana,
    repetidos,
    resumo,
    saldo,
    top_despesas,
)
from app.models import ParametroInvalido


def test_resumo_de_lista_vazia():
    """Verifica o contrato de resumo para extrato sem lançamentos."""
    result = resumo([])
    assert result.total_lancamentos == 0
    assert result.periodo_de is None
    assert result.saldo_centavos == 0


def test_resumo_soma_centavos_e_divide_pelos_dias_inclusivos(lancamento_factory):
    """Verifica RN02 e o período inclusivo usado na média diária de gastos."""
    items = [
        lancamento_factory("2026-09-01", 580000),
        lancamento_factory("2026-09-30", -423410),
    ]
    result = resumo(items, extrato_id=7)
    assert result.extrato_id == 7
    assert result.entradas_centavos == 580000
    assert result.saidas_centavos == -423410
    assert result.saldo_centavos == 156590
    assert result.media_diaria_gasto_centavos == -14113


def test_saldo_agrupa_lancamentos_da_mesma_data(lancamento_factory):
    """Verifica RN08: saldo e negatividade são avaliados após o bloco diário completo."""
    items = [
        lancamento_factory("2026-09-01", -500),
        lancamento_factory("2026-09-01", 500),
        lancamento_factory("2026-09-02", -100),
    ]
    result = saldo(items)
    assert result.saldo_final_centavos == -100
    assert result.ficou_negativo is True
    assert result.saldo_minimo_centavos == -100
    assert result.data_saldo_minimo == "2026-09-02"


def test_saldo_inicial_negativo_e_detectado(lancamento_factory):
    """Verifica RN07 para saldo inicial negativo mesmo sem lançamentos."""
    result = saldo([], saldo_inicial=-50)
    assert result.ficou_negativo is True
    assert result.saldo_minimo_centavos == -50


def test_maior_entrada_desempata_pela_data_mais_antiga(lancamento_factory):
    """Verifica RN10 para empate na maior entrada."""
    items = [
        lancamento_factory("2026-09-03", 900),
        lancamento_factory("2026-09-01", 900),
        lancamento_factory("2026-09-02", 800),
    ]
    assert maior_entrada(items).data == "2026-09-01"


def test_maior_despesa_desempata_pela_data_mais_antiga(lancamento_factory):
    """Verifica RN10 para empate na maior despesa."""
    items = [
        lancamento_factory("2026-09-03", -900),
        lancamento_factory("2026-09-01", -900),
        lancamento_factory("2026-09-02", -800),
    ]
    assert maior_despesa(items).data == "2026-09-01"


def test_maiores_movimentacoes_ignoram_sinal_oposto(lancamento_factory):
    """Verifica as consultas de maior entrada e despesa quando o respectivo sinal não existe."""
    items = [lancamento_factory(amount=10), lancamento_factory(amount=0)]
    assert maior_despesa(items) is None
    assert maior_entrada([]) is None


def test_top_despesas_ordena_por_magnitude_e_limita_n(lancamento_factory):
    """Verifica a ordenação de despesas e o limite configurável da consulta."""
    items = [
        lancamento_factory("2026-09-03", -500),
        lancamento_factory("2026-09-01", -900),
        lancamento_factory("2026-09-02", -800),
        lancamento_factory("2026-09-01", 1000),
    ]
    result = top_despesas(items, 2)
    assert [item.valor_centavos for item in result] == [-900, -800]


def test_top_despesas_rejeita_limite_nao_positivo():
    """Verifica PARAMETRO_INVALIDO para quantidade N menor que um."""
    with pytest.raises(ParametroInvalido):
        top_despesas([], 0)


def test_por_semana_inclui_semanas_parciais_de_segunda_a_domingo(lancamento_factory):
    """Verifica RF12 para semana parcial no começo e no fim do período do extrato."""
    items = [
        lancamento_factory("2026-09-01", 1000),
        lancamento_factory("2026-09-06", -200),
        lancamento_factory("2026-09-08", -300),
    ]
    weeks = por_semana(items)
    assert [(item.de, item.ate) for item in weeks] == [
        ("2026-09-01", "2026-09-06"),
        ("2026-09-07", "2026-09-08"),
    ]
    assert weeks[0].saldo_centavos == 800


def test_por_semana_sem_lancamentos_retorna_lista_vazia():
    """Verifica RF12 para extrato vazio."""
    assert por_semana([]) == []


def test_dias_negativos_conta_dias_sem_movimentacao_e_separa_periodos(lancamento_factory):
    """Verifica RN08 para dias civis negativos consecutivos e períodos interrompidos."""
    items = [
        lancamento_factory("2026-09-01", -100),
        lancamento_factory("2026-09-03", 200),
        lancamento_factory("2026-09-04", -250),
        lancamento_factory("2026-09-05", 250),
    ]
    result = dias_no_negativo(items, 0, saldo_inicial_assumido=True)
    assert result.dias_no_negativo == 3
    assert result.saldo_inicial_assumido is True
    assert [(item.de, item.ate, item.saldo_minimo_centavos) for item in result.periodos] == [
        ("2026-09-01", "2026-09-02", -100),
        ("2026-09-04", "2026-09-04", -150),
    ]


def test_dias_negativos_com_saldo_inicial_informado():
    """Verifica RN07 quando nenhum lançamento foi informado e o saldo é explícito."""
    result = dias_no_negativo([], -200, saldo_inicial_assumido=False)
    assert result.saldo_inicial_centavos == -200
    assert result.saldo_inicial_assumido is False
    assert result.dias_no_negativo == 0


def test_repetidos_aceita_exatamente_dez_porcento(lancamento_factory):
    """Verifica RN09 no limite inclusivo de 10% e exatamente três ocorrências."""
    items = [
        lancamento_factory("2026-09-01", -9000, "Synthetic Market", "SYNTHETIC MARKET"),
        lancamento_factory("2026-09-02", -10000, "Synthetic Market", "SYNTHETIC MARKET"),
        lancamento_factory("2026-09-03", -11000, "Synthetic Market", "SYNTHETIC MARKET"),
    ]
    result = repetidos(items)
    assert len(result) == 1
    assert result[0].ocorrencias == 3
    assert result[0].valor_medio_centavos == -10000


def test_repetidos_rejeita_diferenca_acima_de_dez_porcento(lancamento_factory):
    """Verifica RN09 para grupo cuja diferença ultrapassa exatamente o limiar permitido."""
    items = [
        lancamento_factory(amount=-8900, description="S", normalized="S"),
        lancamento_factory(amount=-10000, description="S", normalized="S"),
        lancamento_factory(amount=-11100, description="S", normalized="S"),
    ]
    assert repetidos(items) == []


def test_repetidos_exige_tres_despesas_da_mesma_descricao(lancamento_factory):
    """Verifica RN09 para duas ocorrências, entradas e descrição normalizada vazia."""
    items = [
        lancamento_factory(amount=-100, normalized="SAME"),
        lancamento_factory(amount=-100, normalized="SAME"),
        lancamento_factory(amount=100, normalized="SAME"),
        lancamento_factory(amount=-100, normalized=""),
    ]
    assert repetidos(items) == []