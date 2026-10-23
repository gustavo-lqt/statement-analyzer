"""Testes de unidade de app/leitura.py (U2): fichas de banco e leitura do CSV.

Todo CSV é montado dentro do próprio teste, com dados inventados (RNF05).
"""

from __future__ import annotations

import json

import pytest

from app import leitura
from app.erros import BancoDesconhecido
from app.leitura import carregar_ficha, listar_fichas
from app.models import ConvencaoSinal, FichaBanco

FICHA_VALIDA = {
    "nome": "banco-teste",
    "delimitador": ";",
    "encoding": "utf-8",
    "formato_data": "dd/mm/aaaa",
    "separador_decimal": ",",
    "separador_milhar": ".",
    "convencao_sinal": "NEGATIVO_SAIDA",
    "colunas": {"data": "Data", "descricao": "Histórico", "valor": "Valor"},
}


def _sem(campo: str) -> dict:
    dados = dict(FICHA_VALIDA)
    del dados[campo]
    return dados


def _com(**mudancas: object) -> dict:
    return {**FICHA_VALIDA, **mudancas}


FICHAS_MALFORMADAS = {
    "sem um campo": _sem("separador_milhar"),
    "formato_data fora da lista": _com(formato_data="mm/dd/aaaa"),
    "encoding fora da lista": _com(encoding="utf-16"),
    "convencao desconhecida": _com(convencao_sinal="SINAL_INVERTIDO"),
    "colunas sem valor": _com(colunas={"data": "Data", "descricao": "Histórico"}),
    "COLUNA_DC sem dc": _com(convencao_sinal="COLUNA_DC"),
    "COLUNAS_SEPARADAS sem debito": _com(
        convencao_sinal="COLUNAS_SEPARADAS",
        colunas={"data": "Data", "descricao": "Histórico", "credito": "Crédito"},
    ),
}


@pytest.fixture
def pasta_fichas(tmp_path, monkeypatch):
    """Troca app/fichas por uma pasta temporária vazia."""
    monkeypatch.setattr(leitura, "PASTA_FICHAS", tmp_path)
    return tmp_path


def _gravar_ficha(pasta, nome: str, dados: dict) -> None:
    texto = json.dumps(dados, ensure_ascii=False)
    (pasta / f"{nome}.json").write_text(texto, encoding="utf-8")


# --- carregar_ficha / listar_fichas -------------------------------------------------------


@pytest.mark.parametrize(
    ("nome", "convencao", "encoding", "formato_data", "delimitador"),
    [
        ("banco-a", ConvencaoSinal.NEGATIVO_SAIDA, "latin-1", "dd/mm/aaaa", ";"),
        ("banco-b", ConvencaoSinal.COLUNA_DC, "utf-8", "aaaa-mm-dd", ","),
        ("banco-c", ConvencaoSinal.COLUNAS_SEPARADAS, "utf-8", "dd-mm-aaaa", ";"),
    ],
)
def test_carregar_ficha_devolve_cada_banco(nome, convencao, encoding, formato_data, delimitador):
    """RF07, D1 / CONTRATO carregar_ficha: lê app/fichas/<nome>.json e converte
    convencao_sinal para ConvencaoSinal."""
    ficha = carregar_ficha(nome)

    assert ficha.nome == nome
    assert ficha.convencao_sinal is convencao
    assert ficha.encoding == encoding
    assert ficha.formato_data == formato_data
    assert ficha.delimitador == delimitador


def test_carregar_ficha_banco_a_igual_a_spec():
    """SPEC §6.1 / CONTRATO carregar_ficha: a banco-a é exatamente a ficha de exemplo da SPEC."""
    assert carregar_ficha("banco-a") == FichaBanco(
        nome="banco-a",
        delimitador=";",
        encoding="latin-1",
        formato_data="dd/mm/aaaa",
        separador_decimal=",",
        separador_milhar=".",
        convencao_sinal=ConvencaoSinal.NEGATIVO_SAIDA,
        colunas={"data": "Data", "descricao": "Histórico", "valor": "Valor"},
    )


def test_carregar_ficha_le_o_json_em_utf8():
    """CONTRATO carregar_ficha: o JSON é lido em UTF-8, então os nomes acentuados da banco-c
    chegam intactos (sem depender do encoding padrão do sistema)."""
    assert carregar_ficha("banco-c").colunas == {
        "data": "Data Lançamento",
        "descricao": "Descrição",
        "credito": "Crédito",
        "debito": "Débito",
    }


def test_carregar_ficha_inexistente_levanta_banco_desconhecido():
    """CONTRATO carregar_ficha / SPEC §6.6: ficha que não existe → BancoDesconhecido."""
    with pytest.raises(BancoDesconhecido) as erro:
        carregar_ficha("banco-z")

    assert "banco-z" in erro.value.mensagem


@pytest.mark.parametrize(
    "nome", ["../x", "..\\x", "a/b", "a\\b", "..", "../fichas/banco-a", "..\\fichas\\banco-a"]
)
def test_carregar_ficha_nome_que_sai_da_pasta_levanta_banco_desconhecido(nome):
    """CONTRATO carregar_ficha: nome com "/", "\\" ou ".." gera BancoDesconhecido, mesmo quando
    o caminho resultante aponta para uma ficha que existe."""
    with pytest.raises(BancoDesconhecido):
        carregar_ficha(nome)


def test_carregar_ficha_nome_com_ponto_ponto_levanta_mesmo_se_o_arquivo_existe(pasta_fichas):
    """CONTRATO carregar_ficha: ".." no nome gera BancoDesconhecido, sem olhar o disco."""
    _gravar_ficha(pasta_fichas, "x..y", FICHA_VALIDA)

    with pytest.raises(BancoDesconhecido):
        carregar_ficha("x..y")


def test_carregar_ficha_nome_com_outra_caixa_levanta_banco_desconhecido():
    """CONTRATO carregar_ficha: "BANCO-A" não é uma ficha registrada, inclusive no Windows,
    onde o sistema de arquivos ignora caixa e abriria banco-a.json."""
    with pytest.raises(BancoDesconhecido):
        carregar_ficha("BANCO-A")


def test_carregar_ficha_valida_numa_pasta_de_fichas_qualquer(pasta_fichas):
    """CONTRATO carregar_ficha: uma ficha bem formada carrega (controle dos testes de ficha
    malformada, que usam a mesma pasta temporária)."""
    _gravar_ficha(pasta_fichas, "banco-teste", FICHA_VALIDA)

    ficha = carregar_ficha("banco-teste")

    assert ficha.nome == "banco-teste"
    assert ficha.convencao_sinal is ConvencaoSinal.NEGATIVO_SAIDA


def test_carregar_ficha_ignora_campo_extra(pasta_fichas):
    """CONTRATO carregar_ficha: campo a mais não está entre os casos de ficha malformada."""
    _gravar_ficha(pasta_fichas, "banco-teste", _com(observacao="exportado pelo internet banking"))

    assert carregar_ficha("banco-teste").nome == "banco-teste"


@pytest.mark.parametrize("dados", FICHAS_MALFORMADAS.values(), ids=FICHAS_MALFORMADAS.keys())
def test_carregar_ficha_malformada_levanta_value_error(pasta_fichas, dados):
    """CONTRATO carregar_ficha: ficha malformada (campo faltando, formato_data, encoding ou
    convenção fora da lista, colunas sem as chaves da convenção) → ValueError."""
    _gravar_ficha(pasta_fichas, "quebrada", dados)

    with pytest.raises(ValueError):
        carregar_ficha("quebrada")


@pytest.mark.parametrize("texto", ["{ isto não é json", "[]"], ids=["json invalido", "lista"])
def test_carregar_ficha_que_nao_e_objeto_json_levanta_value_error(pasta_fichas, texto):
    """CONTRATO carregar_ficha: arquivo de ficha que não é um objeto JSON → ValueError."""
    (pasta_fichas / "quebrada.json").write_text(texto, encoding="utf-8")

    with pytest.raises(ValueError):
        carregar_ficha("quebrada")


def test_listar_fichas_devolve_as_tres_em_ordem_alfabetica():
    """CONTRATO listar_fichas / D1: ["banco-a", "banco-b", "banco-c"]."""
    assert listar_fichas() == ["banco-a", "banco-b", "banco-c"]


def test_listar_fichas_so_considera_arquivos_json(pasta_fichas):
    """CONTRATO listar_fichas: nomes das fichas .json da pasta, em ordem alfabética."""
    for nome in ("zeta", "alfa", "meio"):
        _gravar_ficha(pasta_fichas, nome, FICHA_VALIDA)
    (pasta_fichas / "leia-me.txt").write_text("não é ficha", encoding="utf-8")

    assert listar_fichas() == ["alfa", "meio", "zeta"]
