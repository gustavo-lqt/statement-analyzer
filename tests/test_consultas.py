"""Testes de unidade do motor de análise (SPEC §4 RN07–RN10, §6.5, CONTRATO D2–D5)."""

from datetime import date

import pytest

from app.consultas import (
    dias_no_negativo,
    maior_despesa,
    maior_entrada,
    normalizar_descricao,
    por_semana,
    repetidos,
    resumo,
    saldo,
    top_despesas,
)
from app.erros import ParametroInvalido
from app.models import Lancamento, Periodo, PeriodoNegativo, Semana


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


# --- maior_entrada / maior_despesa (RF10, RN10, D5) ---


def test_maior_entrada_unica() -> None:
    """RN10: devolve o positivo de maior valor quando ele é único."""
    lancamentos = [_l(3, 1000), _l(4, 580000, "SALARIO FICTICIO"), _l(5, -900000)]
    assert maior_entrada(lancamentos) == _l(4, 580000, "SALARIO FICTICIO")


def test_maior_entrada_empate_escolhe_data_mais_antiga() -> None:
    """RN10: empate de valor na maior entrada resolve pela data mais antiga, em qualquer ordem."""
    lancamentos = [_l(20, 5000, "PIX B"), _l(7, 5000, "PIX A"), _l(25, 100)]
    assert maior_entrada(lancamentos) == _l(7, 5000, "PIX A")
    assert maior_entrada(list(reversed(lancamentos))) == _l(7, 5000, "PIX A")


def test_maior_entrada_mesma_data_e_valor_fica_o_primeiro_da_lista() -> None:
    """RN10 (contrato): empate também na data → o primeiro na ordem da lista."""
    lancamentos = [_l(7, 5000, "PIX A"), _l(7, 5000, "PIX B")]
    assert maior_entrada(lancamentos).descricao == "PIX A"


def test_maior_entrada_sem_entradas_devolve_none() -> None:
    """D5: sem nenhum positivo (zero não é entrada) → None."""
    assert maior_entrada([_l(1, -100), _l(2, 0)]) is None
    assert maior_entrada([]) is None


def test_maior_despesa_unica() -> None:
    """RN10: devolve o negativo de maior valor absoluto quando ele é único."""
    lancamentos = [_l(3, -1000), _l(18, -134000, "TRANSF PIX ENVIADA"), _l(5, 900000)]
    assert maior_despesa(lancamentos) == _l(18, -134000, "TRANSF PIX ENVIADA")


def test_maior_despesa_empate_escolhe_data_mais_antiga() -> None:
    """RN10: empate de valor na maior despesa resolve pela data mais antiga, em qualquer ordem."""
    lancamentos = [_l(22, -7000, "LOJA B"), _l(9, -7000, "LOJA A"), _l(2, -10)]
    assert maior_despesa(lancamentos) == _l(9, -7000, "LOJA A")
    assert maior_despesa(list(reversed(lancamentos))) == _l(9, -7000, "LOJA A")


def test_maior_despesa_mesma_data_e_valor_fica_o_primeiro_da_lista() -> None:
    """RN10 (contrato): empate também na data → o primeiro na ordem da lista."""
    lancamentos = [_l(9, -7000, "LOJA A"), _l(9, -7000, "LOJA B")]
    assert maior_despesa(lancamentos).descricao == "LOJA A"


def test_maior_despesa_sem_despesas_devolve_none() -> None:
    """D5: sem nenhum negativo (zero não é saída) → None."""
    assert maior_despesa([_l(1, 100), _l(2, 0)]) is None
    assert maior_despesa([]) is None


# --- top_despesas (RF11, RN10) ---


def test_top_despesas_ordem_mais_negativa_primeiro() -> None:
    """RF11: as n despesas mais negativas, da maior para a menor em valor absoluto."""
    lancamentos = [_l(1, -100), _l(2, -900), _l(3, 5000), _l(4, -500), _l(5, -300)]
    resultado = top_despesas(lancamentos, 3)
    assert [item.valor_centavos for item in resultado] == [-900, -500, -300]


def test_top_despesas_desempate_por_data_e_ordem_da_lista() -> None:
    """RF11/RN10: empate de valor → data mais antiga; mesma data → ordem da lista."""
    lancamentos = [
        _l(15, -400, "C"),
        _l(10, -400, "B1"),
        _l(10, -400, "B2"),
        _l(3, -50, "D"),
    ]
    resultado = top_despesas(lancamentos, 3)
    assert [item.descricao for item in resultado] == ["B1", "B2", "C"]


def test_top_despesas_n_maior_que_total_devolve_todas() -> None:
    """RF11: com menos de n despesas, devolve todas (entradas e zero ficam fora)."""
    lancamentos = [_l(1, -100), _l(2, -200), _l(3, 700), _l(4, 0)]
    resultado = top_despesas(lancamentos, 10)
    assert [item.valor_centavos for item in resultado] == [-200, -100]


@pytest.mark.parametrize("n", [0, -1, 101])
def test_top_despesas_n_fora_da_faixa_levanta(n: int) -> None:
    """RF11: n < 1 ou n > 100 → ParametroInvalido."""
    with pytest.raises(ParametroInvalido):
        top_despesas([_l(1, -100)], n)


@pytest.mark.parametrize("n", [1, 100])
def test_top_despesas_n_nas_fronteiras_e_aceito(n: int) -> None:
    """RF11: n = 1 e n = 100 são as fronteiras aceitas."""
    lancamentos = [_l(1, -100), _l(2, -200)]
    resultado = top_despesas(lancamentos, n)
    assert resultado[0].valor_centavos == -200
    assert len(resultado) == min(n, 2)


def test_top_despesas_lista_vazia() -> None:
    """RF11: lista vazia devolve [] sem levantar."""
    assert top_despesas([], 5) == []


# --- por_semana (RF12, D2) ---


def test_por_semana_recorta_pontas_e_inclui_semanas_vazias() -> None:
    """D2: 2026-09-01 (terça) abre semana até 06; semanas do meio vazias entram zeradas; a última é parcial."""
    lancamentos = [
        _l(30, -100, "ULTIMO DIA"),
        _l(3, -92400, "MERCADO"),
        _l(1, 580000, "SALARIO FICTICIO"),
        _l(16, -500, "PADARIA"),
        _l(17, 200, "PIX RECEBIDO"),
    ]
    assert por_semana(lancamentos) == [
        Semana(date(2026, 9, 1), date(2026, 9, 6), 580000, -92400, 487600),
        Semana(date(2026, 9, 7), date(2026, 9, 13), 0, 0, 0),
        Semana(date(2026, 9, 14), date(2026, 9, 20), 200, -500, -300),
        Semana(date(2026, 9, 21), date(2026, 9, 27), 0, 0, 0),
        Semana(date(2026, 9, 28), date(2026, 9, 30), 0, -100, -100),
    ]


def test_por_semana_saldo_nao_e_acumulado() -> None:
    """D2: o saldo da semana é só entradas + saídas daquela semana."""
    resultado = por_semana([_l(7, 1000), _l(14, -300)])
    assert [semana.saldo_centavos for semana in resultado] == [1000, -300]


def test_por_semana_um_unico_dia() -> None:
    """D2: período de um dia (um domingo) vira uma semana recortada de um dia só."""
    assert por_semana([_l(13, -50)]) == [
        Semana(date(2026, 9, 13), date(2026, 9, 13), 0, -50, -50)
    ]


def test_por_semana_lista_vazia() -> None:
    """D2: lista vazia → []."""
    assert por_semana([]) == []


# --- dias_no_negativo (RF13, RN07, RN08) ---


def test_dias_no_negativo_exemplo_da_spec() -> None:
    """RN07/RN08: saldo inicial informado; negativo de 14 a 17 → 4 dias, mínimo -31200; dias sem lançamento herdam."""
    lancamentos = [
        _l(18, 50000, "SALARIO FICTICIO"),
        _l(10, -5000, "FARMACIA"),
        _l(16, -6200, "MERCADO"),
        _l(14, -40000, "ALUGUEL FICTICIO"),
    ]
    resultado = dias_no_negativo(lancamentos, saldo_inicial=20000)
    assert resultado.saldo_inicial_centavos == 20000
    assert resultado.saldo_inicial_assumido is False
    assert resultado.dias_no_negativo == 4
    assert resultado.periodos == [
        PeriodoNegativo(date(2026, 9, 14), date(2026, 9, 17), -31200)
    ]


def test_dias_no_negativo_saldo_inicial_none_assume_zero() -> None:
    """RN07/D3: saldo_inicial None → usa 0 e marca saldo_inicial_assumido."""
    resultado = dias_no_negativo([_l(5, -10)], saldo_inicial=None)
    assert resultado.saldo_inicial_centavos == 0
    assert resultado.saldo_inicial_assumido is True
    assert resultado.dias_no_negativo == 1


def test_dias_no_negativo_zero_explicito_nao_e_assumido() -> None:
    """RN07: saldo inicial 0 informado não é assumido."""
    resultado = dias_no_negativo([_l(5, -10)], saldo_inicial=0)
    assert resultado.saldo_inicial_assumido is False


def test_dias_no_negativo_dois_periodos_e_saldo_zero_nao_conta() -> None:
    """RN08: dois períodos separados; o dia em que o saldo chega exatamente a zero não é negativo."""
    lancamentos = [_l(2, -10), _l(3, 20), _l(5, -30), _l(7, 20)]
    resultado = dias_no_negativo(lancamentos, saldo_inicial=0)
    assert resultado.dias_no_negativo == 3
    assert resultado.periodos == [
        PeriodoNegativo(date(2026, 9, 2), date(2026, 9, 2), -10),
        PeriodoNegativo(date(2026, 9, 5), date(2026, 9, 6), -20),
    ]


def test_dias_no_negativo_bloco_do_dia_cruzando_zero() -> None:
    """RN08: +100 e -150 no mesmo dia com saldo 0 → o dia termina em -50 e conta."""
    lancamentos = [_l(8, -150, "DEBITO DIA"), _l(8, 100, "CREDITO DIA")]
    resultado = dias_no_negativo(lancamentos, saldo_inicial=0)
    assert resultado.dias_no_negativo == 1
    assert resultado.periodos == [
        PeriodoNegativo(date(2026, 9, 8), date(2026, 9, 8), -50)
    ]


def test_dias_no_negativo_intermediario_negativo_no_dia_nao_conta() -> None:
    """RN08: -150 e +200 no mesmo dia com saldo 0 → o intermediário -150 não torna o dia negativo."""
    resultado = dias_no_negativo([_l(8, -150), _l(8, 200)], saldo_inicial=0)
    assert resultado.dias_no_negativo == 0
    assert resultado.periodos == []


def test_dias_no_negativo_lista_vazia() -> None:
    """RF13: lista vazia → 0 dias e [], mesmo com saldo inicial negativo."""
    resultado = dias_no_negativo([], saldo_inicial=-500)
    assert resultado.saldo_inicial_centavos == -500
    assert resultado.dias_no_negativo == 0
    assert resultado.periodos == []


# --- repetidos (RF14, RN09, D4) ---


def test_repetidos_tres_iguais_formam_grupo() -> None:
    """RN09: três despesas de mesma descrição e valor formam um grupo."""
    lancamentos = [
        _l(9, -4210, "IFD*IFOOD"),
        _l(2, -4210, "IFD*IFOOD"),
        _l(5, -4210, "IFD*IFOOD"),
    ]
    [grupo] = repetidos(lancamentos)
    assert grupo.descricao_normalizada == "IFDIFOOD"
    assert grupo.ocorrencias == 3
    assert grupo.valor_medio_centavos == -4210
    assert grupo.total_centavos == -12630
    assert grupo.datas == [date(2026, 9, 2), date(2026, 9, 5), date(2026, 9, 9)]


def test_repetidos_duas_ocorrencias_nao_formam_grupo() -> None:
    """RN09: duas ocorrências não bastam."""
    assert repetidos([_l(1, -999, "STREAMING"), _l(15, -999, "STREAMING")]) == []


def test_repetidos_exatamente_dez_por_cento_entra() -> None:
    """RN09/D4: média -10000; -11000 e -9000 estão a exatamente 10% e entram."""
    lancamentos = [
        _l(1, -11000, "ACADEMIA"),
        _l(2, -10000, "ACADEMIA"),
        _l(3, -9000, "ACADEMIA"),
    ]
    [grupo] = repetidos(lancamentos)
    assert grupo.ocorrencias == 3
    assert grupo.total_centavos == -30000


def test_repetidos_onze_por_cento_fica_fora_sem_recalcular_media() -> None:
    """RN09/D4: média -10000; -11100 (11% acima) sai, e a média não é recalculada depois do filtro."""
    lancamentos = [
        _l(1, -9633, "MERCADO"),
        _l(8, -9633, "MERCADO"),
        _l(15, -9634, "MERCADO"),
        _l(22, -11100, "MERCADO"),
    ]
    [grupo] = repetidos(lancamentos)
    assert grupo.ocorrencias == 3
    assert grupo.total_centavos == -28900
    assert grupo.datas == [date(2026, 9, 1), date(2026, 9, 8), date(2026, 9, 15)]


def test_repetidos_filtro_que_deixa_menos_de_tres_descarta_grupo() -> None:
    """RN09: se após o filtro de 10% sobrarem menos de 3, o grupo não é reportado."""
    lancamentos = [_l(1, -1000, "BANCA"), _l(2, -1000, "BANCA"), _l(3, -5000, "BANCA")]
    assert repetidos(lancamentos) == []


def test_repetidos_descricoes_que_diferem_em_acento_pontuacao_caixa() -> None:
    """RN09/SPEC §4: a comparação usa a descrição normalizada."""
    lancamentos = [
        _l(3, -800, "Padaria São João"),
        _l(4, -800, "PADARIA SAO JOAO"),
        _l(5, -800, "padaria,  são joão."),
    ]
    [grupo] = repetidos(lancamentos)
    assert grupo.descricao_normalizada == "PADARIA SAO JOAO"
    assert grupo.ocorrencias == 3


def test_repetidos_entradas_sao_ignoradas() -> None:
    """RN09: só despesas entram; entradas não contam como ocorrência."""
    lancamentos = [
        _l(1, 500, "PIX RECEBIDO"),
        _l(2, 500, "PIX RECEBIDO"),
        _l(3, 500, "PIX RECEBIDO"),
        _l(4, -300, "PIX RECEBIDO"),
        _l(5, -300, "PIX RECEBIDO"),
    ]
    assert repetidos(lancamentos) == []


def test_repetidos_datas_crescentes_com_repeticao() -> None:
    """D4: datas em ordem crescente, mantendo repetições do mesmo dia."""
    lancamentos = [_l(7, -100, "CAFE"), _l(2, -100, "CAFE"), _l(7, -100, "CAFE")]
    [grupo] = repetidos(lancamentos)
    assert grupo.datas == [date(2026, 9, 2), date(2026, 9, 7), date(2026, 9, 7)]


def test_repetidos_valor_medio_trunca_em_direcao_a_zero() -> None:
    """D4: -3001 ÷ 3 = -1000,33 → -1000 (e não -1001, como daria o // do Python)."""
    lancamentos = [_l(1, -1000, "CAFE"), _l(2, -1000, "CAFE"), _l(3, -1001, "CAFE")]
    [grupo] = repetidos(lancamentos)
    assert grupo.valor_medio_centavos == -1000


def test_repetidos_ordem_da_resposta() -> None:
    """D4: mais ocorrências; depois total mais negativo; depois descrição alfabética — em qualquer ordem de entrada."""
    lancamentos = (
        [_l(d, -100, "QUATRO VEZES") for d in (1, 2, 3, 4)]
        + [_l(d, -1000, "BANCA") for d in (5, 6, 7)]
        + [_l(d, -1000, "ACADEMIA") for d in (8, 9, 10)]
        + [_l(d, -2000, "ZOOLOGICO") for d in (11, 12, 13)]
    )
    esperado = ["QUATRO VEZES", "ZOOLOGICO", "ACADEMIA", "BANCA"]
    assert [g.descricao_normalizada for g in repetidos(lancamentos)] == esperado
    invertida = list(reversed(lancamentos))
    assert [g.descricao_normalizada for g in repetidos(invertida)] == esperado


def test_repetidos_lista_vazia() -> None:
    """RF14: lista vazia → []."""
    assert repetidos([]) == []
