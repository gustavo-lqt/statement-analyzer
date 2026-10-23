"""Testes de unidade do motor de análise (SPEC §4 RN07–RN10, §6.5, CONTRATO D2–D5)."""

from datetime import date

from app.consultas import normalizar_descricao, resumo
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
