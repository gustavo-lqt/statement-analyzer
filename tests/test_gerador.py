"""Testes de unidade do gerador de extratos sintéticos (U7, Issue #4).

A saída do gerador é lida com app.leitura.ler. Data e valor são conferidos aqui mesmo, com
datetime e aritmética de inteiros: app.regras é de outra unidade e não está nesta branch.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import pytest

from app.leitura import carregar_ficha, ler
from app.models import ConvencaoSinal, FichaBanco, LinhaCrua, MotivoRecusa
from gerador.gerar import gerar_csv, gerar_extrato

RAIZ = Path(__file__).resolve().parents[1]
BANCOS = ["banco-a", "banco-b", "banco-c"]
STRPTIME = {"dd/mm/aaaa": "%d/%m/%Y", "aaaa-mm-dd": "%Y-%m-%d", "dd-mm-aaaa": "%d-%m-%Y"}


@pytest.fixture(params=BANCOS)
def ficha(request) -> FichaBanco:
    return carregar_ficha(request.param)


def _ler(conteudo: bytes, ficha: FichaBanco) -> list[LinhaCrua]:
    return list(ler(conteudo, ficha))


def _texto_valor(linha: LinhaCrua, ficha: FichaBanco) -> str:
    if ficha.convencao_sinal is ConvencaoSinal.COLUNAS_SEPARADAS:
        return linha.campos["credito"] or linha.campos["debito"]
    return linha.campos["valor"]


def _data(linha: LinhaCrua, ficha: FichaBanco) -> date | None:
    try:
        return datetime.strptime(linha.campos["data"], STRPTIME[ficha.formato_data]).date()
    except ValueError:
        return None


def _defeito_observado(linha: LinhaCrua, ficha: FichaBanco) -> MotivoRecusa | None:
    """Recusa que a linha causaria, olhando só o texto que o gerador escreveu."""
    if linha.erro is not None:
        return linha.erro
    if _data(linha, ficha) is None:
        return MotivoRecusa.DATA_INVALIDA
    _, _, decimais = _texto_valor(linha, ficha).partition(ficha.separador_decimal)
    if len(decimais) > 2:
        return MotivoRecusa.PRECISAO_INVALIDA
    return None


def _centavos(linha: LinhaCrua, ficha: FichaBanco) -> int:
    """Valor com sinal (RN03), convertido só com inteiros, para conferir o gerador."""
    texto = _texto_valor(linha, ficha)
    negativo = texto.startswith("-")
    inteiro, _, decimais = texto.removeprefix("-").partition(ficha.separador_decimal)
    if ficha.separador_milhar:
        inteiro = inteiro.replace(ficha.separador_milhar, "")
    valor = int(inteiro) * 100 + int(decimais)
    saida = negativo or linha.campos.get("dc") == "D" or bool(linha.campos.get("debito"))
    return -valor if saida else valor


# --- determinismo ---------------------------------------------------------------------------


def test_mesma_semente_gera_bytes_identicos(ficha):
    """RNF05 / CONTRATO gerador: a mesma semente gera os mesmos bytes."""
    assert gerar_csv(ficha, 300, 42, invalidas=5) == gerar_csv(ficha, 300, 42, invalidas=5)


@pytest.mark.parametrize("hash_seed", ["1", "2"])
def test_mesma_semente_gera_bytes_identicos_em_outro_processo(hash_seed):
    """RNF05 / CONTRATO gerador: os bytes não dependem do processo (nem da aleatorização de
    hash do Python), então a fixture gerada hoje é a mesma gerada amanhã."""
    codigo = (
        "import sys; from app.leitura import carregar_ficha; from gerador.gerar import gerar_csv; "
        "sys.stdout.buffer.write(gerar_csv(carregar_ficha('banco-c'), 200, 7, 4))"
    )
    ambiente = {**os.environ, "PYTHONHASHSEED": hash_seed}

    resultado = subprocess.run(
        [sys.executable, "-c", codigo], cwd=RAIZ, env=ambiente, capture_output=True, check=True
    )

    assert resultado.stdout == gerar_csv(carregar_ficha("banco-c"), 200, 7, 4)


def test_semente_diferente_gera_bytes_diferentes(ficha):
    """RNF05 / CONTRATO gerador: os dados vêm de random.Random(semente)."""
    assert gerar_csv(ficha, 50, 1) != gerar_csv(ficha, 50, 2)


# --- formato da ficha -----------------------------------------------------------------------


def test_csv_sem_invalidas_passa_por_ler_sem_erro(ficha):
    """RF01, RF07 / CONTRATO gerador: com invalidas=0, o CSV passa por ler() sem nenhum erro,
    com o número de linhas pedido, datas existentes e no máximo duas casas decimais."""
    linhas = _ler(gerar_csv(ficha, 200, 42), ficha)

    assert len(linhas) == 200
    assert [linha.numero for linha in linhas] == list(range(2, 202))
    assert [linha for linha in linhas if _defeito_observado(linha, ficha)] == []


@pytest.mark.parametrize(
    "banco, encoding, cabecalho",
    [
        ("banco-a", "latin-1", "Data;Histórico;Valor"),
        ("banco-b", "utf-8", "date,description,amount,type"),
        ("banco-c", "utf-8", "Data Lançamento;Descrição;Crédito;Débito"),
    ],
)
def test_cabecalho_e_encoding_da_ficha(banco, encoding, cabecalho):
    """CONTRATO gerador: cabeçalho com os nomes de coluna da ficha, no encoding da ficha."""
    conteudo = gerar_csv(carregar_ficha(banco), 10, 1)

    assert conteudo.splitlines()[0] == cabecalho.encode(encoding)


def test_datas_em_setembro_de_2026_em_ordem_crescente(ficha):
    """CONTRATO gerador: as datas ficam em setembro de 2026 e saem em ordem crescente."""
    datas = [_data(linha, ficha) for linha in _ler(gerar_csv(ficha, 300, 11), ficha)]

    assert all(d.year == 2026 and d.month == 9 for d in datas)
    assert datas == sorted(datas)


def test_valores_banco_a_negativo_e_saida():
    """RN03 / CONTRATO gerador: na ficha NEGATIVO_SAIDA a saída tem "-" e a entrada não; milhar
    com "." e decimal com ","."""
    ficha = carregar_ficha("banco-a")
    valores = [linha.campos["valor"] for linha in _ler(gerar_csv(ficha, 300, 5), ficha)]

    assert all(re.fullmatch(r"-?\d{1,3}(\.\d{3})*,\d{2}", valor) for valor in valores)
    assert any(valor.startswith("-") for valor in valores)
    assert any(not valor.startswith("-") for valor in valores)


def test_valores_banco_b_sem_sinal_com_coluna_dc():
    """RN03 / CONTRATO gerador: na ficha COLUNA_DC o valor vem sem sinal e sem milhar, e o
    sentido vem em "dc" (D ou C)."""
    ficha = carregar_ficha("banco-b")
    linhas = _ler(gerar_csv(ficha, 300, 5), ficha)

    assert all(re.fullmatch(r"\d+\.\d{2}", linha.campos["valor"]) for linha in linhas)
    assert {linha.campos["dc"] for linha in linhas} == {"C", "D"}


def test_valores_banco_c_em_credito_ou_debito():
    """RN03 / CONTRATO gerador: na ficha COLUNAS_SEPARADAS exatamente uma das colunas,
    crédito ou débito, vem preenchida, sem sinal."""
    ficha = carregar_ficha("banco-c")
    linhas = _ler(gerar_csv(ficha, 300, 5), ficha)
    preenchidas = [(linha.campos["credito"], linha.campos["debito"]) for linha in linhas]

    assert all(bool(credito) != bool(debito) for credito, debito in preenchidas)
    assert all(re.fullmatch(r"\d{1,3}(\.\d{3})*,\d{2}", credito or debito) for credito, debito in preenchidas)
    assert any(credito for credito, _ in preenchidas)
    assert any(debito for _, debito in preenchidas)


def test_salario_entra_e_compra_no_mercado_sai(ficha):
    """RN03 / CONTRATO gerador: em qualquer convenção de sinal, SALARIO é entrada (positivo) e
    PAG*MERC CENTRAL é saída (negativo)."""
    sinais = {
        (linha.campos["descricao"], _centavos(linha, ficha) > 0)
        for linha in _ler(gerar_csv(ficha, 300, 5), ficha)
        if linha.campos["descricao"] in ("SALARIO", "PAG*MERC CENTRAL")
    }

    assert sinais == {("SALARIO", True), ("PAG*MERC CENTRAL", False)}


def test_inclui_gasto_repetido_com_valores_proximos(ficha):
    """RN09 / CONTRATO gerador: alguma despesa se repete 3+ vezes com todos os valores a no
    máximo 10% da média do grupo, para a consulta repetidos ter o que mostrar."""
    grupos: dict[str, list[int]] = {}
    for linha in _ler(gerar_csv(ficha, 100, 42), ficha):
        valor = _centavos(linha, ficha)
        if valor < 0:
            grupos.setdefault(linha.campos["descricao"], []).append(valor)

    repetidos = [
        descricao
        for descricao, valores in grupos.items()
        if len(valores) >= 3
        and all(10 * abs(v * len(valores) - sum(valores)) <= abs(sum(valores)) for v in valores)
    ]

    assert repetidos


# --- linhas inválidas -----------------------------------------------------------------------


@pytest.mark.parametrize("linhas, invalidas", [(100, 10), (20, 20), (20, 0)])
def test_invalidas_gera_exatamente_n_linhas_defeituosas(ficha, linhas, invalidas):
    """RN05 / CONTRATO gerador: com invalidas=N, exatamente N linhas têm defeito, nas posições e
    com os tipos que o próprio gerador registra; as demais são válidas."""
    extrato = gerar_extrato(ficha, linhas, 7, invalidas)
    lidas = _ler(extrato.conteudo, ficha)
    observados = {
        linha.numero: _defeito_observado(linha, ficha)
        for linha in lidas
        if _defeito_observado(linha, ficha) is not None
    }

    assert len(lidas) == linhas
    assert len(extrato.defeitos) == invalidas
    assert observados == extrato.defeitos
    assert gerar_csv(ficha, linhas, 7, invalidas) == extrato.conteudo


def test_defeitos_cobrem_os_tres_tipos():
    """CONTRATO gerador: o defeito sorteado é data inexistente, valor com três casas ou linha
    truncada."""
    extrato = gerar_extrato(carregar_ficha("banco-b"), 100, 3, invalidas=30)

    assert set(extrato.defeitos.values()) == {
        MotivoRecusa.DATA_INVALIDA,
        MotivoRecusa.PRECISAO_INVALIDA,
        MotivoRecusa.LINHA_TRUNCADA,
    }


def test_posicoes_dos_defeitos_vem_da_semente():
    """CONTRATO gerador: as posições das linhas inválidas também são escolhidas pela semente."""
    ficha = carregar_ficha("banco-a")

    assert gerar_extrato(ficha, 100, 1, 5).defeitos.keys() != gerar_extrato(ficha, 100, 2, 5).defeitos.keys()


@pytest.mark.parametrize("linhas, invalidas", [(10, 11), (10, -1), (-1, 0)])
def test_parametros_invalidos_levantam_value_error(linhas, invalidas):
    """CONTRATO gerador: invalidas fora de 0..linhas, ou linhas negativo, não gera nada."""
    with pytest.raises(ValueError):
        gerar_csv(carregar_ficha("banco-a"), linhas, 1, invalidas)
