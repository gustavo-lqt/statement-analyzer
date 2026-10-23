"""Testes de unidade do motor de análise (SPEC §4 RN07–RN10, §6.5, CONTRATO D2–D5)."""

from datetime import date

import pytest

from app.consultas import (
    maior_despesa,
    maior_entrada,
    normalizar_descricao,
    resumo,
    saldo,
    top_despesas,
)
from app.erros import ParametroInvalido
from app.models import Lancamento, Periodo


def _l(dia: int, valor: int, descricao: str = "LOJA TESTE") -> Lancamento:
    return Lancamento(data=date(2026, 9, dia), valor_centavos=valor, descricao=descricao)


# --- normalizar_descricao (SPEC §4) ---


def test_normalizar_descricao_tira_acentos() -> None:
    """SPEC §4: acentos saem da descrição normalizada (São → SAO)."""
    assert normalizar_descricao("São Paulo") == "SAO PAULO"


def test_normalizar_descricao_cedilha() -> None:
    """SPEC §4: Ç vira C."""
    assert normalizar_descricao("açaí") == "ACAI"
    assert normalizar_descricao("PEÇA") == "PECA"


def test_normalizar_descricao_pontuacao() -> None:
    """SPEC §4: pontuação é removida (IFD*iFood)."""
    assert normalizar_descricao("IFD*iFood  São Paulo") == "IFDIFOOD SAO PAULO"


def test_normalizar_descricao_espacos_repetidos() -> None:
    """SPEC §4: espaços consecutivos colapsam e as pontas são removidas."""
    assert normalizar_descricao("  LOJA    CENTRAL  ") == "LOJA CENTRAL"


def test_normalizar_descricao_caixa() -> None:
    """SPEC §4: a descrição normalizada fica em caixa alta."""
    assert normalizar_descricao("streaming filmes") == "STREAMING FILMES"


# --- resumo (RF08) ---


def test_resumo_media_do_exemplo_da_spec() -> None:
    """RF08: saídas -423410 em 30 dias (1 a 30 de setembro) truncam para -14113."""
    lancamentos = [
        _l(1, 580000, "SALARIO FICTICIO"),
        _l(30, -423410, "PAG MERCADO CENTRAL"),
    ]
    resultado = resumo(lancamentos)
    assert resultado.periodo == Periodo(de=date(2026, 9, 1), ate=date(2026, 9, 30))
    assert resultado.total_lancamentos == 2
    assert resultado.entradas_centavos == 580000
    assert resultado.saidas_centavos == -423410
    assert resultado.saldo_centavos == 156590
    assert resultado.media_diaria_gasto_centavos == -14113


def test_resumo_um_unico_dia() -> None:
    """RF08: período de um dia usa denominador 1 na média."""
    resultado = resumo([_l(10, -1500, "CAFE FICTICIO")])
    assert resultado.periodo == Periodo(de=date(2026, 9, 10), ate=date(2026, 9, 10))
    assert resultado.saidas_centavos == -1500
    assert resultado.media_diaria_gasto_centavos == -1500
    assert resultado.total_lancamentos == 1


def test_resumo_lista_vazia() -> None:
    """RF08: lista vazia devolve periodo None e todos os totais iguais a 0."""
    resultado = resumo([])
    assert resultado.periodo is None
    assert resultado.total_lancamentos == 0
    assert resultado.entradas_centavos == 0
    assert resultado.saidas_centavos == 0
    assert resultado.saldo_centavos == 0
    assert resultado.media_diaria_gasto_centavos == 0


def test_resumo_valor_zero_nao_e_entrada_nem_saida() -> None:
    """RF08: valor zero conta no total de lançamentos, mas não em entradas nem saídas."""
    resultado = resumo([_l(5, 0, "AJUSTE ZERADO")])
    assert resultado.total_lancamentos == 1
    assert resultado.entradas_centavos == 0
    assert resultado.saidas_centavos == 0
    assert resultado.saldo_centavos == 0
    assert resultado.media_diaria_gasto_centavos == 0


# --- saldo (RF09, RN08) ---


def test_saldo_corrente_por_data_com_lista_embaralhada() -> None:
    """RN08: o saldo corrente ordena por data crescente mesmo com a lista embaralhada."""
    lancamentos = [_l(20, -30), _l(5, 100), _l(10, -20)]
    resultado = saldo(lancamentos, saldo_inicial=0)
    assert resultado.saldo_final_centavos == 50
    assert resultado.data_saldo_minimo == date(2026, 9, 20)
    assert resultado.saldo_minimo_centavos == 50
    assert resultado.ficou_negativo is False


def test_saldo_bloco_do_dia_nao_observa_intermediario() -> None:
    """RN08: +100 e -150 no mesmo dia com saldo 0 terminam em -50; o intermediário não conta."""
    lancamentos = [_l(8, 100, "CREDITO DIA"), _l(8, -150, "DEBITO DIA")]
    resultado = saldo(lancamentos, saldo_inicial=0)
    assert resultado.saldo_final_centavos == -50
    assert resultado.saldo_minimo_centavos == -50
    assert resultado.data_saldo_minimo == date(2026, 9, 8)
    assert resultado.ficou_negativo is True


def test_saldo_conta_que_nunca_fica_negativa() -> None:
    """RN08: conta só com saldos de fim de dia ≥ 0 não marca ficou_negativo."""
    resultado = saldo([_l(1, 200), _l(2, -50), _l(3, -10)], saldo_inicial=0)
    assert resultado.ficou_negativo is False
    assert resultado.saldo_minimo_centavos == 140
    assert resultado.saldo_final_centavos == 140


def test_saldo_exatamente_zero_nao_e_negativo() -> None:
    """RN08: saldo de fim de dia igual a zero não é negativo."""
    resultado = saldo([_l(1, 80), _l(2, -80)], saldo_inicial=0)
    assert resultado.saldo_minimo_centavos == 0
    assert resultado.ficou_negativo is False
    assert resultado.data_saldo_minimo == date(2026, 9, 2)


def test_saldo_empate_de_minimo_escolhe_dia_mais_antigo() -> None:
    """RN08: empate no saldo mínimo resolve pelo dia mais antigo."""
    resultado = saldo([_l(12, -40), _l(18, 40), _l(22, -40)], saldo_inicial=0)
    assert resultado.saldo_minimo_centavos == -40
    assert resultado.data_saldo_minimo == date(2026, 9, 12)


def test_saldo_lista_vazia() -> None:
    """RF09: lista vazia devolve final e mínimo iguais ao inicial e data_saldo_minimo None."""
    resultado = saldo([], saldo_inicial=20000)
    assert resultado.saldo_inicial_centavos == 20000
    assert resultado.saldo_final_centavos == 20000
    assert resultado.saldo_minimo_centavos == 20000
    assert resultado.data_saldo_minimo is None
    assert resultado.ficou_negativo is False


def test_saldo_lista_vazia_inicial_negativo() -> None:
    """RF09: lista vazia com saldo inicial negativo marca ficou_negativo."""
    resultado = saldo([], saldo_inicial=-1)
    assert resultado.ficou_negativo is True
