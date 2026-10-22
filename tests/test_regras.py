from __future__ import annotations

import pytest

from app.models import FichaBanco, Lancamento, NenhumaLinhaValida, Recusa
from app.regras import normalizar, normalizar_descricao, processar


def test_data_e_valor_sao_normalizados_pela_ficha(ficha, linha_factory):
    """Verifica RN01, RN02 e RN03 para data declarada e saída em centavos."""
    result = normalizar(
        linha_factory(
            {"data": "15/09/2026", "descricao": "Café Sintético", "valor": "-1.234,56"}
        ),
        ficha,
    )
    assert isinstance(result, Lancamento)
    assert result.data == "2026-09-15"
    assert result.valor_centavos == -123456
    assert result.descricao_normalizada == "CAFE SINTETICO"


@pytest.mark.parametrize(
    ("date_format", "date_value", "expected"),
    [
        ("dd/mm/aaaa", "15/09/2026", "2026-09-15"),
        ("aaaa-mm-dd", "2026-09-15", "2026-09-15"),
        ("dd-mm-aaaa", "15-09-2026", "2026-09-15"),
    ],
)
def test_formatos_de_data_suportados(ficha, linha_factory, date_format, date_value, expected):
    """Verifica RN01 nos três formatos declarados pela ficha."""
    configured = FichaBanco(
        ficha.nome,
        ficha.delimitador,
        ficha.encoding,
        date_format,
        ficha.separador_decimal,
        ficha.separador_milhar,
        ficha.convencao_sinal,
        ficha.colunas,
    )
    result = normalizar(
        linha_factory({"data": date_value, "descricao": "X", "valor": "1,00"}), configured
    )
    assert isinstance(result, Lancamento)
    assert result.data == expected


@pytest.mark.parametrize("invalid_date", ["31/02/2026", "2026-09-15", ""])
def test_data_invalida_recusa_a_linha(ficha, linha_factory, invalid_date):
    """Verifica RN01 para datas inexistentes, formato divergente e valor vazio."""
    result = normalizar(
        linha_factory({"data": invalid_date, "descricao": "X", "valor": "1,00"}), ficha
    )
    assert isinstance(result, Recusa)
    assert result.motivo == "DATA_INVALIDA"


def test_precisao_de_duas_casas_e_aceita(ficha, linha_factory):
    """Verifica RN04 no limite inclusivo de exatamente duas casas decimais."""
    result = normalizar(
        linha_factory({"data": "01/09/2026", "descricao": "X", "valor": "1,20"}), ficha
    )
    assert isinstance(result, Lancamento)
    assert result.valor_centavos == 120


def test_tres_casas_decimais_sao_recusadas_sem_arredondar(ficha, linha_factory):
    """Verifica RN04 para precisão excedente sem arredondamento silencioso."""
    result = normalizar(
        linha_factory({"data": "01/09/2026", "descricao": "X", "valor": "1,234"}), ficha
    )
    assert isinstance(result, Recusa)
    assert result.motivo == "PRECISAO_INVALIDA"


@pytest.mark.parametrize("raw_value", ["", "abc", "1,2,3", "12.34,56"])
def test_valor_malformado_e_recusado(ficha, linha_factory, raw_value):
    """Verifica RN02 para valor vazio e separadores numéricos inválidos."""
    result = normalizar(
        linha_factory({"data": "01/09/2026", "descricao": "X", "valor": raw_value}), ficha
    )
    assert isinstance(result, Recusa)
    assert result.motivo == "VALOR_INVALIDO"


def test_coluna_configurada_ausente_e_recusada(ficha, linha_factory):
    """Verifica RN05 e COLUNA_AUSENTE quando o CSV não contém a coluna de valor."""
    result = normalizar(linha_factory({"data": "01/09/2026", "descricao": "X"}), ficha)
    assert isinstance(result, Recusa)
    assert result.motivo == "COLUNA_AUSENTE"


def test_conversao_dc_usa_credito_positivo_e_debito_negativo(fichas, linha_factory):
    """Verifica RN03 para a convenção COLUNA_DC nos dois sentidos."""
    ficha_dc = fichas["banco-b"]
    credit = normalizar(
        linha_factory({"data": "2026-09-01", "descricao": "X", "valor": "12,34", "tipo": "C"}),
        ficha_dc,
    )
    debit = normalizar(
        linha_factory({"data": "2026-09-01", "descricao": "X", "valor": "12,34", "tipo": "D"}),
        ficha_dc,
    )
    assert isinstance(credit, Lancamento) and credit.valor_centavos == 1234
    assert isinstance(debit, Lancamento) and debit.valor_centavos == -1234


def test_codigo_dc_desconhecido_e_recusado(fichas, linha_factory):
    """Verifica RN03 para código de crédito/débito que não pertence à ficha."""
    result = normalizar(
        linha_factory({"data": "2026-09-01", "descricao": "X", "valor": "1,00", "tipo": "X"}),
        fichas["banco-b"],
    )
    assert isinstance(result, Recusa)
    assert result.motivo == "VALOR_INVALIDO"


def test_colunas_separadas_validam_exatamente_uma_contribuicao(fichas, linha_factory):
    """Verifica RN03 para crédito, débito e as duas combinações inválidas."""
    ficha_separada = fichas["banco-c"]
    credit = normalizar(
        linha_factory({"data": "01-09-2026", "descricao": "X", "credito": "10,00", "debito": ""}),
        ficha_separada,
    )
    debit = normalizar(
        linha_factory({"data": "01-09-2026", "descricao": "X", "credito": "", "debito": "10,00"}),
        ficha_separada,
    )
    both = normalizar(
        linha_factory({"data": "01-09-2026", "descricao": "X", "credito": "1,00", "debito": "1,00"}),
        ficha_separada,
    )
    neither = normalizar(
        linha_factory({"data": "01-09-2026", "descricao": "X", "credito": "", "debito": ""}),
        ficha_separada,
    )
    assert isinstance(credit, Lancamento) and credit.valor_centavos == 1000
    assert isinstance(debit, Lancamento) and debit.valor_centavos == -1000
    assert isinstance(both, Recusa) and both.motivo == "VALOR_INVALIDO"
    assert isinstance(neither, Recusa) and neither.motivo == "VALOR_INVALIDO"


def test_normalizacao_de_descricao_remove_acentos_pontuacao_e_espacos():
    """Verifica a chave textual usada pela RN09 para descrições semanticamente iguais."""
    assert normalizar_descricao("  Café--São   João! ") == "CAFE SAO JOAO"


def test_processar_continua_apos_recusa_e_preserva_conteudo(ficha, linha_factory):
    """Verifica RN05: uma linha inválida não impede a normalização das linhas seguintes."""
    rows = [
        linha_factory({"data": "31/02/2026", "descricao": "X", "valor": "1,00"}, number=2),
        linha_factory({"data": "01/09/2026", "descricao": "OK", "valor": "2,00"}, number=3),
    ]
    result = processar(rows, ficha)
    assert result.total_linhas == 2
    assert len(result.lancamentos) == 1
    assert result.recusas[0].numero_linha == 2
    assert result.recusas[0].conteudo_bruto == "synthetic row"


def test_processar_preserva_recusa_de_linha_truncada(ficha, linha_factory):
    """Verifica RN05 para o marcador LINHA_TRUNCADA produzido pelo leitor."""
    result = processar(
        [linha_factory(number=4, reason="LINHA_TRUNCADA"), linha_factory()], ficha
    )
    assert result.recusas[0].motivo == "LINHA_TRUNCADA"
    assert len(result.lancamentos) == 1


def test_arquivo_sem_linha_valida_nao_produz_extrato(ficha, linha_factory):
    """Verifica RN06 quando todas as linhas foram recusadas."""
    rows = [linha_factory({"data": "31/02/2026", "descricao": "X", "valor": "1,00"})]
    with pytest.raises(NenhumaLinhaValida):
        processar(rows, ficha)