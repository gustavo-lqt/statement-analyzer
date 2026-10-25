"""Contratos HTTP de app/api.py (SPEC §6.3 a §6.6, CONTRATO.md "app/api.py").

Testes de integração com TestClient, sem subir servidor. Cada teste usa um banco SQLite
novo em memória, no lugar de obter_conexao. Os CSVs são montados aqui, com dados
inventados, nos formatos das fichas banco-a, banco-b e banco-c.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import db
from app.api import app, obter_conexao


@pytest.fixture
def cliente() -> Iterator[TestClient]:
    conn = db.conectar(":memory:")
    app.dependency_overrides[obter_conexao] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()
    conn.close()


# --- Montagem dos arquivos --------------------------------------------------------


def csv_banco_a(*linhas: str) -> bytes:
    """banco-a: ';', latin-1, dd/mm/aaaa, NEGATIVO_SAIDA."""
    return "\r\n".join(["Data;Histórico;Valor", *linhas]).encode("latin-1")


def csv_banco_b(*linhas: str) -> bytes:
    """banco-b: ',', utf-8, aaaa-mm-dd, COLUNA_DC."""
    return "\n".join(["date,description,amount,type", *linhas]).encode("utf-8")


def csv_banco_c(*linhas: str) -> bytes:
    """banco-c: ';', utf-8, dd-mm-aaaa, COLUNAS_SEPARADAS."""
    return "\n".join(["Data Lançamento;Descrição;Crédito;Débito", *linhas]).encode("utf-8")


def enviar(
    cliente: TestClient,
    conteudo: bytes,
    banco: str,
    saldo_inicial_centavos: str | None = None,
    nome_arquivo: str = "extrato-setembro.csv",
):
    dados = {"banco": banco}
    if saldo_inicial_centavos is not None:
        dados["saldo_inicial_centavos"] = saldo_inicial_centavos
    return cliente.post(
        "/extratos",
        files={"arquivo": (nome_arquivo, conteudo, "text/csv")},
        data=dados,
    )


# Extrato de referência para as consultas (banco-b). Com saldo inicial 10000:
#   09-01 +580000 → 590000 | 09-02 -4210 → 585790 | 09-05 -4210 → 581580
#   09-09 -4210 → 577370   | 09-10 -600000 → -22630 | 09-12 +30000 → 7370
# Fica negativo em 09-10 e 09-11 (09-11 herda o saldo de 09-10).
EXTRATO_REFERENCIA = csv_banco_b(
    "2026-09-01,SALARIO,5800.00,C",
    "2026-09-02,IFD*IFOOD,42.10,D",
    "2026-09-05,IFD*IFOOD,42.10,D",
    "2026-09-09,IFD*IFOOD,42.10,D",
    "2026-09-10,ALUGUEL APTO,6000.00,D",
    "2026-09-12,TRANSF PIX RECEBIDA,300.00,C",
)


@pytest.fixture
def extrato_id(cliente: TestClient) -> int:
    resposta = enviar(cliente, EXTRATO_REFERENCIA, "banco-b", saldo_inicial_centavos="10000")
    assert resposta.status_code == 201
    return resposta.json()["id"]


def assert_erro(resposta, status: int, erro: str, regra: str | None = None) -> None:
    """Confere o formato único de erro da SPEC §6.6."""
    assert resposta.status_code == status
    corpo = resposta.json()
    assert set(corpo) == {"erro", "mensagem", "regra"}
    assert corpo["erro"] == erro
    assert corpo["regra"] == regra
    assert isinstance(corpo["mensagem"], str) and corpo["mensagem"]


# --- POST /extratos (§6.3) --------------------------------------------------------


def test_post_extrato_devolve_201_com_contrato_completo(cliente: TestClient) -> None:
    """§6.3: POST /extratos devolve 201 com todos os campos do contrato, recusas incluídas."""
    conteudo = csv_banco_a(
        "01/09/2026;SALÁRIO;5.800,00",
        "31/02/2026;PAG*MERC CENTRAL;-92,40",
        "03/09/2026;PAG*MERC CENTRAL;-92,40",
    )

    resposta = enviar(cliente, conteudo, "banco-a", saldo_inicial_centavos="20000")

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert set(corpo) == {
        "id", "nome_arquivo", "banco", "criado_em", "saldo_inicial_centavos",
        "total_linhas", "aceitos", "rejeitados", "recusas",
    }
    assert isinstance(corpo["id"], int)
    assert corpo["nome_arquivo"] == "extrato-setembro.csv"
    assert corpo["banco"] == "banco-a"
    assert datetime.fromisoformat(corpo["criado_em"]).utcoffset() is not None
    assert corpo["saldo_inicial_centavos"] == 20000
    assert (corpo["total_linhas"], corpo["aceitos"], corpo["rejeitados"]) == (3, 2, 1)
    assert corpo["recusas"] == [
        {"linha": 3, "motivo": "DATA_INVALIDA", "conteudo": "31/02/2026;PAG*MERC CENTRAL;-92,40"}
    ]


def test_post_extrato_com_linhas_ruins_aceita_as_demais(cliente: TestClient) -> None:
    """§6.3, RN05: linhas ruins viram recusas na ordem do arquivo e o resto é aceito."""
    conteudo = csv_banco_c(
        "01-09-2026;SALARIO;5.800,00;",
        "31-02-2026;PADARIA;;12,00",
        "03-09-2026;PAG*MERC CENTRAL;;92,405",
        "04-09-2026;FARMACIA",
        "05-09-2026;PAG*MERC CENTRAL;;92,40",
    )

    resposta = enviar(cliente, conteudo, "banco-c")

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert (corpo["total_linhas"], corpo["aceitos"], corpo["rejeitados"]) == (5, 2, 3)
    assert [(r["linha"], r["motivo"]) for r in corpo["recusas"]] == [
        (3, "DATA_INVALIDA"),
        (4, "PRECISAO_INVALIDA"),
        (5, "LINHA_TRUNCADA"),
    ]


@pytest.mark.parametrize(
    "linha_ruim, motivo",
    [
        ("03/09/2026;PAG*MERC\rCENTRAL;-92,40", "LINHA_TRUNCADA"),
        ("03/09/2026;PAG*MERC CENTRAL;-1²", "VALOR_INVALIDO"),
    ],
)
def test_post_extrato_com_caractere_que_quebrava_o_motor_recusa_so_a_linha(
    cliente: TestClient, linha_ruim: str, motivo: str
) -> None:
    """§6.3, RN05: \\r solto fora de aspas (SPEC §8 v1.3) e dígito não ASCII (PR #18) recusam
    só a linha, em vez de derrubar o envio com 500."""
    conteudo = csv_banco_a("01/09/2026;SALARIO;5.800,00", linha_ruim)

    resposta = enviar(cliente, conteudo, "banco-a")

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert (corpo["aceitos"], corpo["rejeitados"]) == (1, 1)
    assert [(r["linha"], r["motivo"]) for r in corpo["recusas"]] == [(3, motivo)]


def test_post_extrato_sem_saldo_inicial_devolve_null(cliente: TestClient) -> None:
    """§6.3, RN07, D3: saldo_inicial_centavos é opcional e sai null quando não informado."""
    resposta = enviar(cliente, EXTRATO_REFERENCIA, "banco-b")

    assert resposta.status_code == 201
    assert resposta.json()["saldo_inicial_centavos"] is None


def test_post_extrato_com_saldo_inicial_nao_inteiro_devolve_422(cliente: TestClient) -> None:
    """§6.6, RN02: saldo_inicial_centavos é inteiro em centavos; "200.50" é PARAMETRO_INVALIDO."""
    resposta = enviar(cliente, EXTRATO_REFERENCIA, "banco-b", saldo_inicial_centavos="200.50")

    assert_erro(resposta, 422, "PARAMETRO_INVALIDO")


def test_post_extrato_so_com_linhas_ruins_devolve_422_rn06(cliente: TestClient) -> None:
    """§6.3, RN06: nenhuma linha válida → 422 NENHUMA_LINHA_VALIDA com regra "RN06"."""
    conteudo = csv_banco_a("31/02/2026;PADARIA;-12,00", "01/09/2026;PADARIA;-12,345")

    resposta = enviar(cliente, conteudo, "banco-a")

    assert_erro(resposta, 422, "NENHUMA_LINHA_VALIDA", regra="RN06")


def test_post_extrato_com_banco_desconhecido_devolve_400(cliente: TestClient) -> None:
    """§6.3, §6.6: ficha inexistente → 400 BANCO_DESCONHECIDO, sem regra."""
    resposta = enviar(cliente, EXTRATO_REFERENCIA, "banco-z")

    assert_erro(resposta, 400, "BANCO_DESCONHECIDO")


def test_post_extrato_sem_arquivo_devolve_400(cliente: TestClient) -> None:
    """§6.3: multipart sem o campo arquivo → 400 ARQUIVO_AUSENTE."""
    resposta = cliente.post("/extratos", data={"banco": "banco-a"})

    assert_erro(resposta, 400, "ARQUIVO_AUSENTE")


def test_post_extrato_com_arquivo_vazio_devolve_422(cliente: TestClient) -> None:
    """§6.3: arquivo sem bytes → 422 ARQUIVO_VAZIO."""
    resposta = enviar(cliente, b"", "banco-a")

    assert_erro(resposta, 422, "ARQUIVO_VAZIO")


def test_post_extrato_so_com_cabecalho_devolve_422(cliente: TestClient) -> None:
    """§6.3 (borda): arquivo só com o cabeçalho também é ARQUIVO_VAZIO."""
    resposta = enviar(cliente, csv_banco_a(), "banco-a")

    assert_erro(resposta, 422, "ARQUIVO_VAZIO")


def test_post_extrato_com_cabecalho_em_encoding_errado_devolve_422(cliente: TestClient) -> None:
    """§6.3: cabeçalho que não decodifica no encoding da ficha → 422 ENCODING_INVALIDO."""
    conteudo = "Data Lançamento;Descrição;Crédito;Débito\n01-09-2026;SALARIO;10,00;".encode(
        "latin-1"
    )

    resposta = enviar(cliente, conteudo, "banco-c")

    assert_erro(resposta, 422, "ENCODING_INVALIDO")


# --- Gestão de extratos (§6.4) ----------------------------------------------------


def test_get_extratos_lista_sem_lancamentos(cliente: TestClient) -> None:
    """§6.4: GET /extratos devolve 200 com a lista de extratos, por id, sem lançamentos."""
    primeiro = enviar(cliente, EXTRATO_REFERENCIA, "banco-b", nome_arquivo="a.csv").json()
    segundo = enviar(cliente, EXTRATO_REFERENCIA, "banco-b", nome_arquivo="b.csv").json()

    resposta = cliente.get("/extratos")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert [e["id"] for e in corpo] == [primeiro["id"], segundo["id"]]
    assert [e["nome_arquivo"] for e in corpo] == ["a.csv", "b.csv"]
    assert set(corpo[0]) == {
        "id", "nome_arquivo", "banco", "criado_em", "saldo_inicial_centavos",
        "total_linhas", "aceitos", "rejeitados",
    }


def test_get_extratos_sem_nenhum_devolve_lista_vazia(cliente: TestClient) -> None:
    """§6.4 (borda): sem extratos, GET /extratos devolve 200 com []."""
    resposta = cliente.get("/extratos")

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_get_extrato_por_id_devolve_lancamentos_com_paginacao_padrao(
    cliente: TestClient, extrato_id: int
) -> None:
    """§6.4, §6.2, D6: GET /extratos/{id} devolve o extrato e os lançamentos no modelo
    canônico, com limite 100 e offset 0 por padrão."""
    resposta = cliente.get(f"/extratos/{extrato_id}")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["id"] == extrato_id
    assert corpo["saldo_inicial_centavos"] == 10000
    assert (corpo["limite"], corpo["offset"]) == (100, 0)
    assert len(corpo["lancamentos"]) == 6
    primeiro = corpo["lancamentos"][0]
    assert set(primeiro) == {"id", "extrato_id", "data", "valor_centavos", "descricao"}
    assert primeiro["extrato_id"] == extrato_id
    assert (primeiro["data"], primeiro["valor_centavos"], primeiro["descricao"]) == (
        "2026-09-01", 580000, "SALARIO"
    )


def test_get_extrato_por_id_pagina_com_limite_e_offset(
    cliente: TestClient, extrato_id: int
) -> None:
    """§6.4, D6: limite e offset recortam os lançamentos, em ordem de data."""
    resposta = cliente.get(f"/extratos/{extrato_id}", params={"limite": 2, "offset": 1})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert (corpo["limite"], corpo["offset"]) == (2, 1)
    assert [l["data"] for l in corpo["lancamentos"]] == ["2026-09-02", "2026-09-05"]


def test_get_extrato_por_id_aceita_limite_maximo(cliente: TestClient, extrato_id: int) -> None:
    """D6 (borda): limite=1000 é o máximo aceito."""
    resposta = cliente.get(f"/extratos/{extrato_id}", params={"limite": 1000})

    assert resposta.status_code == 200
    assert resposta.json()["limite"] == 1000


@pytest.mark.parametrize("params", [{"limite": 0}, {"limite": 1001}, {"offset": -1}])
def test_get_extrato_por_id_com_paginacao_fora_da_faixa_devolve_422(
    cliente: TestClient, extrato_id: int, params: dict[str, int]
) -> None:
    """D6, §6.6 (borda): limite fora de 1..1000 ou offset negativo → 422 PARAMETRO_INVALIDO."""
    resposta = cliente.get(f"/extratos/{extrato_id}", params=params)

    assert_erro(resposta, 422, "PARAMETRO_INVALIDO")


def test_get_extrato_inexistente_devolve_404(cliente: TestClient) -> None:
    """§6.4: GET /extratos/{id} de id inexistente → 404 EXTRATO_NAO_ENCONTRADO."""
    resposta = cliente.get("/extratos/999")

    assert_erro(resposta, 404, "EXTRATO_NAO_ENCONTRADO")


def test_get_extrato_com_id_nao_numerico_devolve_422(cliente: TestClient) -> None:
    """§6.6: a validação do FastAPI também sai no formato único, como PARAMETRO_INVALIDO."""
    resposta = cliente.get("/extratos/abc")

    assert_erro(resposta, 422, "PARAMETRO_INVALIDO")


def test_delete_extrato_devolve_204_e_depois_404(cliente: TestClient, extrato_id: int) -> None:
    """§6.4, RF06: DELETE devolve 204 sem corpo; depois o extrato e as consultas dão 404."""
    resposta = cliente.delete(f"/extratos/{extrato_id}")

    assert resposta.status_code == 204
    assert resposta.content == b""
    assert_erro(cliente.get(f"/extratos/{extrato_id}"), 404, "EXTRATO_NAO_ENCONTRADO")
    assert_erro(cliente.get(f"/extratos/{extrato_id}/resumo"), 404, "EXTRATO_NAO_ENCONTRADO")
    assert cliente.get("/extratos").json() == []


def test_delete_extrato_inexistente_devolve_404(cliente: TestClient) -> None:
    """§6.4 (borda): DELETE de id inexistente → 404 EXTRATO_NAO_ENCONTRADO."""
    resposta = cliente.delete("/extratos/999")

    assert_erro(resposta, 404, "EXTRATO_NAO_ENCONTRADO")


# --- Consultas (§6.5) -------------------------------------------------------------

CONSULTAS = (
    "resumo", "saldo", "maior-entrada", "maior-despesa",
    "top-despesas", "por-semana", "dias-no-negativo", "repetidos",
)


@pytest.mark.parametrize("consulta", CONSULTAS)
def test_consulta_de_extrato_inexistente_devolve_404(cliente: TestClient, consulta: str) -> None:
    """§6.5: toda consulta de id inexistente → 404 EXTRATO_NAO_ENCONTRADO."""
    resposta = cliente.get(f"/extratos/999/{consulta}")

    assert_erro(resposta, 404, "EXTRATO_NAO_ENCONTRADO")


def test_consulta_resumo(cliente: TestClient, extrato_id: int) -> None:
    """§6.5, RF08: resumo com extrato_id, período, totais e média diária truncada."""
    resposta = cliente.get(f"/extratos/{extrato_id}/resumo")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "extrato_id": extrato_id,
        "periodo": {"de": "2026-09-01", "ate": "2026-09-12"},
        "total_lancamentos": 6,
        "entradas_centavos": 610000,
        "saidas_centavos": -612630,
        "saldo_centavos": -2630,
        "media_diaria_gasto_centavos": -51052,
    }


def test_consulta_saldo(cliente: TestClient, extrato_id: int) -> None:
    """§6.5, RF09, RN08: saldo final, mínimo de fim de dia e a data em que ocorreu."""
    resposta = cliente.get(f"/extratos/{extrato_id}/saldo")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "saldo_inicial_centavos": 10000,
        "saldo_final_centavos": 7370,
        "ficou_negativo": True,
        "saldo_minimo_centavos": -22630,
        "data_saldo_minimo": "2026-09-10",
    }


def test_consulta_maior_entrada(cliente: TestClient, extrato_id: int) -> None:
    """§6.5, RF10: maior-entrada devolve {data, valor_centavos, descricao}."""
    resposta = cliente.get(f"/extratos/{extrato_id}/maior-entrada")

    assert resposta.status_code == 200
    assert resposta.json() == {"data": "2026-09-01", "valor_centavos": 580000, "descricao": "SALARIO"}


def test_consulta_maior_despesa(cliente: TestClient, extrato_id: int) -> None:
    """§6.5, RF10: maior-despesa devolve {data, valor_centavos, descricao}."""
    resposta = cliente.get(f"/extratos/{extrato_id}/maior-despesa")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "data": "2026-09-10", "valor_centavos": -600000, "descricao": "ALUGUEL APTO"
    }


def test_consulta_maior_entrada_sem_entradas_devolve_null(cliente: TestClient) -> None:
    """§6.5, D5 (borda): sem nenhuma entrada, maior-entrada devolve 200 com null."""
    conteudo = csv_banco_b("2026-09-02,PADARIA,12.00,D", "2026-09-03,PADARIA,8.00,D")
    extrato = enviar(cliente, conteudo, "banco-b").json()

    resposta = cliente.get(f"/extratos/{extrato['id']}/maior-entrada")

    assert resposta.status_code == 200
    assert resposta.json() is None


def test_consulta_maior_despesa_sem_despesas_devolve_null(cliente: TestClient) -> None:
    """§6.5, D5 (borda): sem nenhuma despesa, maior-despesa devolve 200 com null."""
    conteudo = csv_banco_b("2026-09-01,SALARIO,5800.00,C")
    extrato = enviar(cliente, conteudo, "banco-b").json()

    resposta = cliente.get(f"/extratos/{extrato['id']}/maior-despesa")

    assert resposta.status_code == 200
    assert resposta.json() is None


def test_consulta_top_despesas_com_desempate_pela_data(
    cliente: TestClient, extrato_id: int
) -> None:
    """§6.5, RF11, RN10: top-despesas?n=2 devolve as mais negativas; empate → data mais antiga."""
    resposta = cliente.get(f"/extratos/{extrato_id}/top-despesas", params={"n": 2})

    assert resposta.status_code == 200
    assert resposta.json() == {
        "n": 2,
        "despesas": [
            {"data": "2026-09-10", "valor_centavos": -600000, "descricao": "ALUGUEL APTO"},
            {"data": "2026-09-02", "valor_centavos": -4210, "descricao": "IFD*IFOOD"},
        ],
    }


def test_consulta_top_despesas_usa_n_10_por_padrao(cliente: TestClient, extrato_id: int) -> None:
    """§6.5 (borda): sem n, top-despesas usa n=10 e devolve todas se houver menos."""
    resposta = cliente.get(f"/extratos/{extrato_id}/top-despesas")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["n"] == 10
    assert len(corpo["despesas"]) == 4


@pytest.mark.parametrize("n", [0, 101])
def test_consulta_top_despesas_com_n_fora_da_faixa_devolve_422(
    cliente: TestClient, extrato_id: int, n: int
) -> None:
    """§6.5, §6.6 (borda): n=0 ou n=101 → 422 PARAMETRO_INVALIDO, sem regra."""
    resposta = cliente.get(f"/extratos/{extrato_id}/top-despesas", params={"n": n})

    assert_erro(resposta, 422, "PARAMETRO_INVALIDO")


def test_consulta_por_semana(cliente: TestClient, extrato_id: int) -> None:
    """§6.5, RF12, D2: semanas de segunda a domingo, recortadas ao período do extrato."""
    resposta = cliente.get(f"/extratos/{extrato_id}/por-semana")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "semanas": [
            {"de": "2026-09-01", "ate": "2026-09-06", "entradas_centavos": 580000,
             "saidas_centavos": -8420, "saldo_centavos": 571580},
            {"de": "2026-09-07", "ate": "2026-09-12", "entradas_centavos": 30000,
             "saidas_centavos": -604210, "saldo_centavos": -574210},
        ]
    }


def test_consulta_dias_no_negativo(cliente: TestClient, extrato_id: int) -> None:
    """§6.5, RF13, RN08: dia sem lançamento herda o saldo; 09-10 e 09-11 ficam negativos."""
    resposta = cliente.get(f"/extratos/{extrato_id}/dias-no-negativo")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "saldo_inicial_centavos": 10000,
        "saldo_inicial_assumido": False,
        "dias_no_negativo": 2,
        "periodos": [
            {"de": "2026-09-10", "ate": "2026-09-11", "saldo_minimo_centavos": -22630}
        ],
    }


def test_consulta_dias_no_negativo_sem_saldo_inicial_marca_assumido(
    cliente: TestClient,
) -> None:
    """§6.5, RN07, D3 (borda): saldo inicial ausente → usa 0 e saldo_inicial_assumido true."""
    extrato = enviar(cliente, EXTRATO_REFERENCIA, "banco-b").json()

    resposta = cliente.get(f"/extratos/{extrato['id']}/dias-no-negativo")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["saldo_inicial_centavos"] == 0
    assert corpo["saldo_inicial_assumido"] is True


def test_consulta_saldo_sem_saldo_inicial_usa_zero(cliente: TestClient) -> None:
    """§6.5, RN07, D3 (borda): saldo inicial ausente → saldo parte de 0."""
    extrato = enviar(cliente, EXTRATO_REFERENCIA, "banco-b").json()

    resposta = cliente.get(f"/extratos/{extrato['id']}/saldo")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["saldo_inicial_centavos"] == 0
    assert corpo["saldo_final_centavos"] == -2630


def test_consulta_repetidos(cliente: TestClient, extrato_id: int) -> None:
    """§6.5, RF14, RN09: três despesas iguais formam um grupo pela descrição normalizada."""
    resposta = cliente.get(f"/extratos/{extrato_id}/repetidos")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "repetidos": [
            {"descricao_normalizada": "IFDIFOOD", "ocorrencias": 3,
             "valor_medio_centavos": -4210, "total_centavos": -12630,
             "datas": ["2026-09-02", "2026-09-05", "2026-09-09"]}
        ]
    }


# --- Erro interno e documentação --------------------------------------------------


def test_erro_inesperado_devolve_500_sem_detalhes() -> None:
    """§6.6, RNF06: exceção inesperada → 500 ERRO_INTERNO, sem vazar a mensagem original."""
    conn = db.conectar(":memory:")
    conn.close()
    app.dependency_overrides[obter_conexao] = lambda: conn
    try:
        resposta = TestClient(app, raise_server_exceptions=False).get("/extratos")
    finally:
        app.dependency_overrides.clear()

    assert_erro(resposta, 500, "ERRO_INTERNO")
    assert "closed" not in resposta.text.lower()


def test_documentacao_openapi_acessivel(cliente: TestClient) -> None:
    """Issue #9: a documentação OpenAPI fica em /docs e descreve as rotas."""
    assert cliente.get("/docs").status_code == 200
    caminhos = cliente.get("/openapi.json").json()["paths"]
    assert {"/extratos", "/extratos/{extrato_id}", "/extratos/{extrato_id}/resumo"} <= set(caminhos)
