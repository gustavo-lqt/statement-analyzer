"""Testes de unidade de app/leitura.py (U2): fichas de banco e leitura do CSV.

Todo CSV é montado dentro do próprio teste, com dados inventados (RNF05).
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
import tracemalloc
from pathlib import Path

import pytest

from app import leitura
from app.erros import ArquivoVazio, BancoDesconhecido, EncodingInvalido
from app.leitura import carregar_ficha, ler, listar_fichas
from app.models import ConvencaoSinal, FichaBanco, LinhaCrua, MotivoRecusa

RAIZ = Path(__file__).resolve().parents[1]

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


@pytest.fixture
def banco_a() -> FichaBanco:
    return carregar_ficha("banco-a")


@pytest.fixture
def banco_b() -> FichaBanco:
    return carregar_ficha("banco-b")


@pytest.fixture
def banco_c() -> FichaBanco:
    return carregar_ficha("banco-c")


def _ler(conteudo: bytes, ficha: FichaBanco) -> list[LinhaCrua]:
    return list(ler(conteudo, ficha))


def _recusada(numero: int, conteudo: str, motivo: MotivoRecusa) -> LinhaCrua:
    return LinhaCrua(numero=numero, campos={}, conteudo=conteudo, erro=motivo)


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


# --- ler -----------------------------------------------------------------------------------

CABECALHO_B = b"date,description,amount,type"
SALARIO_B = LinhaCrua(
    numero=2,
    campos={"data": "2026-09-01", "descricao": "SALARIO", "valor": "5800.00", "dc": "C"},
    conteudo="2026-09-01,SALARIO,5800.00,C",
)
MERCADO_B = LinhaCrua(
    numero=3,
    campos={"data": "2026-09-03", "descricao": "PAG*MERC CENTRAL", "valor": "92.40", "dc": "D"},
    conteudo="2026-09-03,PAG*MERC CENTRAL,92.40,D",
)


def test_ler_e_um_gerador(banco_b):
    """CONTRATO ler: é um gerador, então as exceções só aparecem quando a iteração começa."""
    linhas = ler(b"", banco_b)

    with pytest.raises(ArquivoVazio):
        next(linhas)


def test_ler_banco_a_em_latin1(banco_a):
    """RF01, RF07 / CONTRATO ler, regra 7: banco-a é lida em latin-1, com "Histórico" no
    cabeçalho; cada linha sai com os campos da ficha e o número da linha física."""
    conteudo = (
        "Data;Histórico;Valor\r\n"
        "01/09/2026;SALARIO;5.800,00\r\n"
        "03/09/2026;PAG*MERC CENTRAL;-92,40\r\n"
        "04/09/2026;PADARIA PÃO QUENTE;-8,50\r\n"
    ).encode("latin-1")

    assert _ler(conteudo, banco_a) == [
        LinhaCrua(
            numero=2,
            campos={"data": "01/09/2026", "descricao": "SALARIO", "valor": "5.800,00"},
            conteudo="01/09/2026;SALARIO;5.800,00",
        ),
        LinhaCrua(
            numero=3,
            campos={"data": "03/09/2026", "descricao": "PAG*MERC CENTRAL", "valor": "-92,40"},
            conteudo="03/09/2026;PAG*MERC CENTRAL;-92,40",
        ),
        LinhaCrua(
            numero=4,
            campos={"data": "04/09/2026", "descricao": "PADARIA PÃO QUENTE", "valor": "-8,50"},
            conteudo="04/09/2026;PADARIA PÃO QUENTE;-8,50",
        ),
    ]


def test_ler_banco_b_com_coluna_dc(banco_b):
    """RF01, RF07 / CONTRATO ler, regra 7: banco-b (utf-8, vírgula) entrega também a chave "dc"."""
    conteudo = (
        b"date,description,amount,type\n"
        b"2026-09-01,SALARIO,5800.00,C\n"
        b"2026-09-03,PAG*MERC CENTRAL,92.40,D\n"
    )

    assert _ler(conteudo, banco_b) == [SALARIO_B, MERCADO_B]


def test_ler_banco_c_com_colunas_separadas(banco_c):
    """RF01, RF07 / CONTRATO ler, regra 7: banco-c (utf-8, cabeçalho acentuado) entrega crédito e
    débito; a célula vazia chega como texto vazio."""
    conteudo = (
        "Data Lançamento;Descrição;Crédito;Débito\n"
        "01-09-2026;SALARIO;5.800,00;\n"
        "03-09-2026;PAG*MERC CENTRAL;;92,40\n"
    ).encode("utf-8")

    assert _ler(conteudo, banco_c) == [
        LinhaCrua(
            numero=2,
            campos={"data": "01-09-2026", "descricao": "SALARIO", "credito": "5.800,00", "debito": ""},
            conteudo="01-09-2026;SALARIO;5.800,00;",
        ),
        LinhaCrua(
            numero=3,
            campos={"data": "03-09-2026", "descricao": "PAG*MERC CENTRAL", "credito": "", "debito": "92,40"},
            conteudo="03-09-2026;PAG*MERC CENTRAL;;92,40",
        ),
    ]


@pytest.mark.parametrize(
    "quebra_cabecalho, quebra_dados",
    [(b"\n", b"\n"), (b"\r\n", b"\r\n"), (b"\r\n", b"\n")],
    ids=["lf", "crlf", "misturado"],
)
def test_ler_aceita_crlf_e_lf(banco_b, quebra_cabecalho, quebra_dados):
    """CONTRATO ler, regra 1: a quebra pode ser \\n ou \\r\\n, e conteudo/campos saem sem ela."""
    conteudo = (
        CABECALHO_B + quebra_cabecalho
        + b"2026-09-01,SALARIO,5800.00,C" + quebra_dados
        + b"2026-09-03,PAG*MERC CENTRAL,92.40,D" + quebra_dados
    )

    assert _ler(conteudo, banco_b) == [SALARIO_B, MERCADO_B]


def test_ler_arquivo_terminando_em_cr_sem_lf(banco_b):
    """CONTRATO ler, regra 1 / RN05: um \\r final sem \\n não vira célula nem derruba a leitura."""
    conteudo = CABECALHO_B + b"\r\n2026-09-01,SALARIO,5800.00,C\r"

    assert _ler(conteudo, banco_b) == [SALARIO_B]


@pytest.mark.parametrize(
    "ficha_nome, conteudo, esperado",
    [
        (
            "banco-c",
            "﻿Data Lançamento;Descrição;Crédito;Débito\n01-09-2026;SALARIO;5.800,00;\n".encode(),
            {"data": "01-09-2026", "descricao": "SALARIO", "credito": "5.800,00", "debito": ""},
        ),
        (
            "banco-a",
            b"\xef\xbb\xbf" + "Data;Histórico;Valor\n01/09/2026;SALARIO;5.800,00\n".encode("latin-1"),
            {"data": "01/09/2026", "descricao": "SALARIO", "valor": "5.800,00"},
        ),
    ],
    ids=["utf-8", "latin-1"],
)
def test_ler_descarta_bom(ficha_nome, conteudo, esperado):
    """CONTRATO ler, regra 2: o BOM UTF-8 no início é descartado, então a primeira coluna do
    cabeçalho é reconhecida (sem BOM grudado no nome)."""
    [linha] = _ler(conteudo, carregar_ficha(ficha_nome))

    assert linha.erro is None
    assert linha.campos == esperado


def test_ler_pula_linhas_em_branco_sem_perder_a_numeracao(banco_b):
    """CONTRATO ler, regras 1 e 2 / LinhaCrua.numero: linhas em branco (ou só com espaços),
    antes ou depois do cabeçalho, são puladas mas contam no número da linha física."""
    conteudo = (
        b"\n"                                       # 1
        b"   \n"                                    # 2
        b"date,description,amount,type\n"           # 3 cabeçalho
        b"2026-09-01,SALARIO,5800.00,C\n"           # 4
        b"\t \n"                                    # 5
        b"\r\n"                                     # 6
        b"2026-09-03,PAG*MERC CENTRAL,92.40,D\n"    # 7
        b"\n"                                       # 8
    )

    linhas = _ler(conteudo, banco_b)

    assert [linha.numero for linha in linhas] == [4, 7]
    assert [linha.campos["descricao"] for linha in linhas] == ["SALARIO", "PAG*MERC CENTRAL"]


@pytest.mark.parametrize(
    "conteudo",
    [
        b"",
        CABECALHO_B,
        CABECALHO_B + b"\r\n",
        CABECALHO_B + b"\n\n   \n\t\n",
        b"\n \n\t\r\n",
        b"\xef\xbb\xbf",
    ],
    ids=["sem bytes", "so cabecalho", "so cabecalho com quebra", "cabecalho e brancas", "so brancas", "so bom"],
)
def test_ler_arquivo_sem_linha_de_dados_levanta_arquivo_vazio(banco_b, conteudo):
    """CONTRATO ler, regra 2 / SPEC §6.3: arquivo sem bytes, só com linhas em branco ou só com o
    cabeçalho → ArquivoVazio."""
    with pytest.raises(ArquivoVazio):
        _ler(conteudo, banco_b)


def test_ler_cabecalho_que_nao_decodifica_levanta_encoding_invalido(banco_c):
    """CONTRATO ler, regra 2 / SPEC §6.3: arquivo da banco-c salvo em latin-1 (ficha diz utf-8)
    tem cabeçalho que não decodifica → EncodingInvalido."""
    conteudo = (
        "Data Lançamento;Descrição;Crédito;Débito\n01-09-2026;SALARIO;5.800,00;\n"
    ).encode("latin-1")

    with pytest.raises(EncodingInvalido):
        _ler(conteudo, banco_c)


def test_ler_byte_invalido_no_meio_so_afeta_aquela_linha(banco_c):
    """CONTRATO ler, regra 3 / RN05: a linha que não decodifica sai com ENCODING_INVALIDO,
    campos vazios e conteudo com o caractere de substituição; as seguintes continuam."""
    conteudo = (
        "Data Lançamento;Descrição;Crédito;Débito\n01-09-2026;SALARIO;5.800,00;\n".encode()
        + b"02-09-2026;PADARIA P\xc3O QUENTE;;8,50\n"
        + b"03-09-2026;PAG*MERC CENTRAL;;92,40\n"
    )

    linhas = _ler(conteudo, banco_c)

    assert [linha.numero for linha in linhas] == [2, 3, 4]
    assert linhas[1] == _recusada(
        3, "02-09-2026;PADARIA P�O QUENTE;;8,50", MotivoRecusa.ENCODING_INVALIDO
    )
    assert linhas[0].erro is None
    assert linhas[2].erro is None
    assert linhas[2].campos["debito"] == "92,40"


@pytest.mark.parametrize(
    "linha_ruim",
    ["05/09/2026;TRANSF PIX ENVIADA", "05/09/2026;TRANSF PIX ENVIADA;-10,00;sobrando"],
    ids=["menos celulas", "mais celulas"],
)
def test_ler_linha_com_numero_de_celulas_diferente_e_truncada(banco_a, linha_ruim):
    """CONTRATO ler, regra 5 / RN05: menos ou mais células que o cabeçalho → LINHA_TRUNCADA, e a
    leitura continua."""
    conteudo = (
        f"Data;Histórico;Valor\n{linha_ruim}\n06/09/2026;IFD*IFOOD;-42,10\n".encode("latin-1")
    )

    linhas = _ler(conteudo, banco_a)

    assert linhas[0] == _recusada(2, linha_ruim, MotivoRecusa.LINHA_TRUNCADA)
    assert linhas[1].numero == 3
    assert linhas[1].erro is None


def test_ler_cabecalho_sem_coluna_da_ficha_recusa_todas_as_linhas(banco_a):
    """CONTRATO ler, regra 6: cabeçalho sem a coluna "Histórico" → toda linha de dados sai com
    COLUNA_AUSENTE, inclusive a que também teria o número errado de células."""
    conteudo = (
        "Data;Descricao;Valor\n01/09/2026;SALARIO;5.800,00\n03/09/2026;PAG*MERC CENTRAL\n"
    ).encode("latin-1")

    assert _ler(conteudo, banco_a) == [
        _recusada(2, "01/09/2026;SALARIO;5.800,00", MotivoRecusa.COLUNA_AUSENTE),
        _recusada(3, "03/09/2026;PAG*MERC CENTRAL", MotivoRecusa.COLUNA_AUSENTE),
    ]


def test_ler_linha_que_nao_decodifica_continua_encoding_invalido_sem_coluna(banco_c):
    """CONTRATO ler, regras 3 e 6: com coluna ausente no cabeçalho, a linha que nem decodifica
    continua ENCODING_INVALIDO (a decodificação vem antes do recorte)."""
    conteudo = "Data;Descrição;Crédito;Débito\n".encode() + b"02-09-2026;P\xc3O;;8,50\n"

    assert _ler(conteudo, banco_c) == [
        _recusada(2, "02-09-2026;P�O;;8,50", MotivoRecusa.ENCODING_INVALIDO)
    ]


def test_ler_ignora_colunas_extras_e_a_ordem_do_cabecalho(banco_a):
    """CONTRATO ler, regras 6 e 7: colunas extras são ignoradas e cada campo vem da coluna com o
    nome declarado na ficha, em qualquer posição."""
    conteudo = (
        "Saldo;Valor;Data;Histórico;Agência\n100,00;-92,40;03/09/2026;PAG*MERC CENTRAL;0001\n"
    ).encode("latin-1")

    [linha] = _ler(conteudo, banco_a)

    assert linha.erro is None
    assert linha.campos == {"data": "03/09/2026", "descricao": "PAG*MERC CENTRAL", "valor": "-92,40"}


def test_ler_celula_entre_aspas_pode_conter_o_delimitador(banco_b):
    """CONTRATO ler, regra 4: as células são separadas pelo módulo csv, respeitando aspas
    duplas; conteudo continua sendo a linha original."""
    conteudo = (
        CABECALHO_B
        + b'\n2026-09-03,"PAG*LOJA CENTRO, FILIAL 2",92.40,D'
        + b'\n2026-09-04,"MERCADO ""BOM PRECO""",15.00,D\n'
    )

    linhas = _ler(conteudo, banco_b)

    assert [linha.campos["descricao"] for linha in linhas] == [
        "PAG*LOJA CENTRO, FILIAL 2",
        'MERCADO "BOM PRECO"',
    ]
    assert [linha.erro for linha in linhas] == [None, None]
    assert linhas[0].conteudo == '2026-09-03,"PAG*LOJA CENTRO, FILIAL 2",92.40,D'


def test_ler_nao_aplica_strip_nos_campos(banco_a):
    """CONTRATO ler, regra 7 / LinhaCrua.campos: o texto da célula chega cru, sem strip."""
    conteudo = "Data;Histórico;Valor\n  01/09/2026 ; SALARIO  ;5.800,00 \n".encode("latin-1")

    [linha] = _ler(conteudo, banco_a)

    assert linha.campos == {"data": "  01/09/2026 ", "descricao": " SALARIO  ", "valor": "5.800,00 "}
    assert linha.conteudo == "  01/09/2026 ; SALARIO  ;5.800,00 "


# --- restrições do módulo ---------------------------------------------------------------------


def test_leitura_nao_importa_fastapi_nem_sqlite3():
    """CONTRATO app/leitura.py / ADR-001: o módulo não importa FastAPI nem acessa o banco;
    importá-lo num processo limpo não carrega fastapi nem sqlite3."""
    codigo = (
        "import sys, app.leitura; "
        "print(sorted(m for m in ('fastapi', 'sqlite3') if m in sys.modules))"
    )

    resultado = subprocess.run(
        [sys.executable, "-c", codigo], cwd=RAIZ, capture_output=True, text=True, check=True
    )

    assert resultado.stdout.strip() == "[]"


def test_ler_nao_registra_o_conteudo_das_linhas(banco_c, caplog, capsys):
    """RNF06 / CONTRATO ler: o conteúdo das linhas nunca vai para log, stdout ou stderr, seja a
    linha válida, com encoding inválido ou truncada."""
    conteudo = (
        "Data Lançamento;Descrição;Crédito;Débito\n01-09-2026;LOJA SIGILOSA;5.800,00;\n".encode()
        + b"02-09-2026;LOJA SIGILOSA P\xc3O;;8,50\n"
        + b"03-09-2026;LOJA SIGILOSA\n"
    )

    with caplog.at_level(logging.DEBUG):
        linhas = _ler(conteudo, banco_c)

    impresso = capsys.readouterr()
    assert [linha.erro for linha in linhas] == [
        None,
        MotivoRecusa.ENCODING_INVALIDO,
        MotivoRecusa.LINHA_TRUNCADA,
    ]
    assert "SIGILOSA" not in caplog.text
    assert "SIGILOSA" not in impresso.out + impresso.err


def test_ler_100_mil_linhas_dentro_do_prazo(banco_a):
    """RNF04: um arquivo de 100.000 linhas é lido em menos de 60 s."""
    conteudo = "Data;Histórico;Valor\n".encode("latin-1") + b"03/09/2026;PAG*MERC CENTRAL;-92,40\n" * 100_000

    inicio = time.perf_counter()
    total = sum(1 for _ in ler(conteudo, banco_a))
    duracao = time.perf_counter() - inicio

    assert total == 100_000
    assert duracao < 60


def test_ler_em_streaming_nao_acumula_o_arquivo_na_memoria(banco_a):
    """RNF04: leitura em streaming; o pico de memória durante a iteração fica muito abaixo do
    tamanho do arquivo (guardar todas as linhas passaria de 100% dele)."""
    conteudo = "Data;Histórico;Valor\n".encode("latin-1") + b"03/09/2026;PAG*MERC CENTRAL;-92,40\n" * 20_000

    tracemalloc.start()
    try:
        for _ in ler(conteudo, banco_a):
            pass
        _, pico = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert pico < len(conteudo) // 10
