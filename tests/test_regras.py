"""Testes do motor puro de normalização e validação (RN01–RN06)."""

from collections.abc import Iterable
from datetime import date

import pytest

from app.erros import ArquivoVazio, NenhumaLinhaValida
from app.models import (
    ConvencaoSinal,
    FichaBanco,
    LinhaCrua,
    MotivoRecusa,
)
from app.regras import converter_data, converter_valor, normalizar, processar


def ficha(
    *,
    formato_data: str = "dd/mm/aaaa",
    convencao: ConvencaoSinal = ConvencaoSinal.NEGATIVO_SAIDA,
    decimal: str = ",",
    milhar: str = ".",
) -> FichaBanco:
    colunas = {
        ConvencaoSinal.NEGATIVO_SAIDA: {"data": "Data", "descricao": "Descrição", "valor": "Valor"},
        ConvencaoSinal.COLUNA_DC: {
            "data": "Data",
            "descricao": "Descrição",
            "valor": "Valor",
            "dc": "D/C",
        },
        ConvencaoSinal.COLUNAS_SEPARADAS: {
            "data": "Data",
            "descricao": "Descrição",
            "credito": "Crédito",
            "debito": "Débito",
        },
    }[convencao]
    return FichaBanco(
        nome="teste",
        delimitador=";",
        encoding="utf-8",
        formato_data=formato_data,
        separador_decimal=decimal,
        separador_milhar=milhar,
        convencao_sinal=convencao,
        colunas=colunas,
    )


def linha(campos: dict[str, str], *, numero: int = 2, erro: MotivoRecusa | None = None) -> LinhaCrua:
    return LinhaCrua(numero=numero, campos=campos, conteudo=";".join(campos.values()), erro=erro)


def linha_valor(valor: str, *, numero: int = 2, descricao: str = "  Salário  ") -> LinhaCrua:
    return linha({"data": "01/09/2026", "descricao": descricao, "valor": valor}, numero=numero)


def test_converter_data_aplica_os_tres_formatos():
    """RN01: a data segue estritamente o formato declarado pela ficha."""
    assert converter_data("01/09/2026", "dd/mm/aaaa") == date(2026, 9, 1)
    assert converter_data("2026-09-01", "aaaa-mm-dd") == date(2026, 9, 1)
    assert converter_data("01-09-2026", "dd-mm-aaaa") == date(2026, 9, 1)


@pytest.mark.parametrize(
    "texto",
    ["31/02/2026", "29/02/2026", "", "1/9/2026", " 01/09/2026 "],
)
def test_converter_data_recusa_formato_ou_data_invalida(texto: str):
    """RN01: formato, calendário e espaços inválidos não são adivinhados."""
    if texto == " 01/09/2026 ":
        assert converter_data(texto, "dd/mm/aaaa") == date(2026, 9, 1)
    else:
        assert converter_data(texto, "dd/mm/aaaa") is None


def test_converter_data_aceita_bissexto_valido():
    """RN01: 29/02/2028 é uma data de calendário válida."""
    assert converter_data("29/02/2028", "dd/mm/aaaa") == date(2028, 2, 29)


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("1.234,56", 123456),
        ("1234", 123400),
        ("12,5", 1250),
        ("(1.234,56)", -123456),
        ("-92,40", -9240),
        ("+10,00", 1000),
        ("", None),
        (",", None),
        ("R$ 10", None),
        (",50", None),
        ("1,", None),
    ],
)
def test_converter_valor_em_centavos(texto: str, esperado: int | None):
    """RN02 e RN04: valores válidos viram centavos sem float e inválidos recusam."""
    if esperado is None:
        assert converter_valor(texto, ",", ".") == "VALOR_INVALIDO"
    else:
        assert converter_valor(texto, ",", ".") == esperado


def test_converter_valor_banco_com_ponto_decimal_sem_milhar():
    """RN02: a ficha pode declarar ponto decimal e nenhum separador de milhar."""
    assert converter_valor("1234.50", ".", "") == 123450


def test_converter_valor_recusa_espacos_internos_em_parenteses():
    """RN02: somente espaços nas pontas do valor são ignorados."""
    assert converter_valor("( 1,00 )", ",", ".") == "VALOR_INVALIDO"


@pytest.mark.parametrize("texto", ["1²", "²", "١٢,٣٠", "12,٣٠"])
def test_converter_valor_recusa_digitos_unicode(texto: str):
    """RN02: valores com dígitos não ASCII são recusados."""
    assert converter_valor(texto, ",", ".") == "VALOR_INVALIDO"


def test_converter_data_recusa_digitos_unicode():
    """RN01: datas com dígitos não ASCII são recusadas."""
    assert converter_data("٠١/٠٩/٢٠٢٦", "dd/mm/aaaa") is None


@pytest.mark.parametrize("texto", ["12,340", "1,999"])
def test_converter_valor_recusa_precisao_excedente(texto: str):
    """RN04: três casas decimais recusam sem arredondamento."""
    assert converter_valor(texto, ",", ".") == "PRECISAO_INVALIDA"


def test_normalizar_aplica_sinal_negativo_saida_e_descricao():
    """RN02 e RN03: saída negativa e descrição aparada no modelo canônico."""
    resultado = normalizar(linha_valor("-92,40"), ficha())
    assert resultado.valor_centavos == -9240
    assert resultado.descricao == "Salário"


@pytest.mark.parametrize(
    ("marcador", "esperado"),
    [("D", -9240), ("C", 9240), ("d ", -9240)],
)
def test_normalizar_coluna_dc_converte_entrada_e_saida(marcador: str, esperado: int):
    """RN03: D/C aceita marcadores com normalização de caixa e espaços."""
    banco = ficha(
        convencao=ConvencaoSinal.COLUNA_DC,
        formato_data="aaaa-mm-dd",
        milhar="",
        decimal=".",
    )
    resultado = normalizar(
        linha({"data": "2026-09-01", "descricao": "Compra", "valor": "92.40", "dc": marcador}),
        banco,
    )
    assert resultado.valor_centavos == esperado


def test_normalizar_coluna_dc_recusa_marcador_desconhecido():
    """RN03: marcador D/C fora de D ou C é VALOR_INVALIDO."""
    banco = ficha(convencao=ConvencaoSinal.COLUNA_DC, formato_data="aaaa-mm-dd")
    resultado = normalizar(
        linha({"data": "2026-09-01", "descricao": "Compra", "valor": "92.40", "dc": "X"}),
        banco,
    )
    assert resultado.motivo is MotivoRecusa.VALOR_INVALIDO


@pytest.mark.parametrize(
    ("campos", "esperado"),
    [
        ({"data": "01-09-2026", "descricao": "Entrada", "credito": "10,00", "debito": ""}, 1000),
        ({"data": "01-09-2026", "descricao": "Saída", "credito": "", "debito": "10,00"}, -1000),
    ],
)
def test_normalizar_colunas_separadas_aplica_sinal(campos: dict[str, str], esperado: int):
    """RN03: crédito entra positivo e débito sai negativo."""
    resultado = normalizar(linha(campos), ficha(convencao=ConvencaoSinal.COLUNAS_SEPARADAS, formato_data="dd-mm-aaaa"))
    assert resultado.valor_centavos == esperado


def test_normalizar_colunas_separadas_recusa_ambos_preenchidos():
    """RN03: crédito e débito preenchidos simultaneamente são inválidos."""
    resultado = normalizar(
        linha({"data": "01-09-2026", "descricao": "Ambos", "credito": "1,00", "debito": "2,00"}),
        ficha(convencao=ConvencaoSinal.COLUNAS_SEPARADAS, formato_data="dd-mm-aaaa"),
    )
    assert resultado.motivo is MotivoRecusa.VALOR_INVALIDO


def test_normalizar_respeita_ordem_data_antes_do_valor():
    """RN05: data inválida vence valor inválido na ordem contratual."""
    resultado = normalizar(
        linha({"data": "31/02/2026", "descricao": "X", "valor": "12,340"}),
        ficha(),
    )
    assert resultado.motivo is MotivoRecusa.DATA_INVALIDA


def test_normalizar_recusa_valor_com_digito_unicode():
    """RN05: valor com dígito não ASCII vira VALOR_INVALIDO sem levantar exceção."""
    resultado = normalizar(linha_valor("1²"), ficha())
    assert resultado.motivo is MotivoRecusa.VALOR_INVALIDO


@pytest.mark.parametrize("motivo", [MotivoRecusa.ENCODING_INVALIDO, MotivoRecusa.LINHA_TRUNCADA])
def test_normalizar_preserva_erro_da_leitura(motivo: MotivoRecusa):
    """RN05: erros já detectados pela leitura viram recusas com os mesmos dados."""
    original = LinhaCrua(9, {}, "linha bruta", motivo)
    resultado = normalizar(original, ficha())
    assert (resultado.linha, resultado.motivo, resultado.conteudo) == (9, motivo, "linha bruta")


def test_normalizar_recusa_descricao_vazia():
    """Contrato: descrição ausente recebe COLUNA_AUSENTE."""
    resultado = normalizar(linha_valor("10,00", descricao="   "), ficha())
    assert resultado.motivo is MotivoRecusa.COLUNA_AUSENTE


def test_processar_preserva_ordem_e_continua_apos_recusas():
    """RN05: recusas no meio não interrompem os lançamentos válidos."""
    linhas = [
        linha_valor("1,00", numero=2),
        LinhaCrua(3, {}, "ruim", MotivoRecusa.LINHA_TRUNCADA),
        linha_valor("2,00", numero=4),
        linha_valor("3,00", numero=5),
    ]
    resultado = processar(linhas, ficha())
    assert [item.valor_centavos for item in resultado.lancamentos] == [100, 200, 300]
    assert [item.linha for item in resultado.recusas] == [3]


def test_processar_continua_apos_valor_com_digito_unicode():
    """RN05: valor com dígito não ASCII é recusado sem abortar o lote."""
    resultado = processar([linha_valor("1,00"), linha_valor("1²", numero=3)], ficha())
    assert resultado.aceitos == 1
    assert resultado.rejeitados == 1
    assert resultado.recusas[0].motivo is MotivoRecusa.VALOR_INVALIDO


def test_processar_todas_ruins_levanta_nenhuma_linha_valida():
    """RN06: lote sem nenhum lançamento válido levanta o erro de domínio."""
    with pytest.raises(NenhumaLinhaValida):
        processar([linha_valor("R$ 10")], ficha())


def test_processar_iteravel_vazio_levanta_nenhuma_linha_valida():
    """RN06: iterável vazio também não cria resultado válido."""
    with pytest.raises(NenhumaLinhaValida):
        processar([], ficha())


def test_processar_preserva_excecao_do_iteravel():
    """RN06: exceção da fonte não é capturada pelo motor."""
    def linhas() -> Iterable[LinhaCrua]:
        yield linha_valor("1,00")
        raise ArquivoVazio("arquivo vazio")

    with pytest.raises(ArquivoVazio, match="arquivo vazio"):
        processar(linhas(), ficha())
