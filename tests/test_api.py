from __future__ import annotations

from fastapi.testclient import TestClient


def _csv(*rows: str) -> str:
    return "\n".join(("Data;Historico;Valor", *rows, ""))


def test_post_cria_extrato_com_lancamentos_e_recusas(client):
    """Verifica RF04 e RN05: resposta 201 inclui aceitos e recusas por linha."""
    response = client.post(
        "/extratos",
        data={"banco": "banco-a", "saldo_inicial_centavos": "200"},
        files={
            "arquivo": (
                "synthetic.csv",
                _csv("01/09/2026;ITEM SINTETICO;12,34", "31/02/2026;LINHA RUIM;1,00"),
                "text/csv",
            )
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["aceitos"] == 1
    assert body["rejeitados"] == 1
    assert body["recusas"][0]["motivo"] == "DATA_INVALIDA"


def test_post_sem_arquivo_retorna_erro_uniforme(client):
    """Verifica §6.3 e RNF01 para arquivo obrigatório ausente."""
    response = client.post("/extratos", data={"banco": "banco-a"})
    assert response.status_code == 400
    assert response.json()["erro"] == "ARQUIVO_AUSENTE"
    assert set(response.json()) == {"erro", "mensagem", "regra"}


def test_post_com_banco_desconhecido_retorna_erro_uniforme(client):
    """Verifica §6.3 e RNF01 para ficha bancária inexistente."""
    response = client.post(
        "/extratos",
        data={"banco": "inexistente"},
        files={"arquivo": ("synthetic.csv", _csv("01/09/2026;X;1,00"), "text/csv")},
    )
    assert response.status_code == 400
    assert response.json()["erro"] == "BANCO_DESCONHECIDO"
    assert response.json()["regra"] is None


def test_post_de_arquivo_vazio_retorna_422(client):
    """Verifica §6.3 para upload sem bytes, sem criar registro no banco."""
    response = client.post(
        "/extratos",
        data={"banco": "banco-a"},
        files={"arquivo": ("empty.csv", b"", "text/csv")},
    )
    assert response.status_code == 422
    assert response.json()["erro"] == "ARQUIVO_VAZIO"
    assert client.get("/extratos").json() == []


def test_post_com_todas_as_linhas_invalidas_nao_persiste(client):
    """Verifica RN06 e o formato único de erro para arquivo sem linha aceita."""
    response = client.post(
        "/extratos",
        data={"banco": "banco-a"},
        files={
            "arquivo": (
                "invalid.csv",
                _csv("31/02/2026;INVALIDA;1,00"),
                "text/csv",
            )
        },
    )
    assert response.status_code == 422
    assert response.json()["erro"] == "NENHUMA_LINHA_VALIDA"
    assert response.json()["regra"] == "RN06"
    assert client.get("/extratos").json() == []


def test_listagem_detalhes_paginacao_e_consultas(client):
    """Verifica RF05 e contratos de resumo, maiores, top, semana e repetidos."""
    response = client.post(
        "/extratos",
        data={"banco": "banco-a", "saldo_inicial_centavos": "100000"},
        files={
            "arquivo": (
                "synthetic.csv",
                _csv(
                    "01/09/2026;ASSINATURA SINTETICA;-10,00",
                    "02/09/2026;ASSINATURA SINTETICA;-10,00",
                    "03/09/2026;ASSINATURA SINTETICA;-11,00",
                    "08/09/2026;ENTRADA SINTETICA;30,00",
                ),
                "text/csv",
            )
        },
    )
    extract_id = response.json()["id"]
    assert client.get("/extratos").json()[0]["id"] == extract_id
    details = client.get(f"/extratos/{extract_id}", params={"limit": 2, "offset": 1}).json()
    assert len(details["lancamentos"]) == 2

    summary = client.get(f"/extratos/{extract_id}/resumo").json()
    assert summary["entradas_centavos"] == 3000
    assert summary["saidas_centavos"] == -3100
    assert client.get(f"/extratos/{extract_id}/maior-entrada").json()["valor_centavos"] == 3000
    assert client.get(f"/extratos/{extract_id}/maior-despesa").json()["valor_centavos"] == -1100
    assert len(client.get(f"/extratos/{extract_id}/top-despesas?n=2").json()["despesas"]) == 2
    assert len(client.get(f"/extratos/{extract_id}/por-semana").json()["semanas"]) == 2
    assert client.get(f"/extratos/{extract_id}/repetidos").json()["repetidos"][0]["ocorrencias"] == 3


def test_consulta_dias_negativos_e_distingue_saldo_assumido(client):
    """Verifica RN07 na resposta quando o saldo inicial foi omitido."""
    response = client.post(
        "/extratos",
        data={"banco": "banco-a"},
        files={
            "arquivo": (
                "synthetic.csv",
                _csv("01/09/2026;SAIDA SINTETICA;-1,00"),
                "text/csv",
            )
        },
    )
    extract_id = response.json()["id"]
    result = client.get(f"/extratos/{extract_id}/dias-no-negativo").json()
    assert result["saldo_inicial_assumido"] is True
    assert result["dias_no_negativo"] == 1


def test_parametro_invalido_usa_formato_de_erro_unico(client):
    """Verifica RNF01 para parâmetro fora dos limites de paginação/consulta."""
    response = client.get("/extratos/1/top-despesas?n=0")
    assert response.status_code == 422
    assert response.json()["erro"] == "PARAMETRO_INVALIDO"
    assert set(response.json()) == {"erro", "mensagem", "regra"}


def test_exclusao_em_cascata_e_not_found(client):
    """Verifica RF06 e o contrato 404 para extrato removido ou inexistente."""
    created = client.post(
        "/extratos",
        data={"banco": "banco-a"},
        files={"arquivo": ("synthetic.csv", _csv("01/09/2026;ITEM;1,00"), "text/csv")},
    ).json()
    extract_id = created["id"]
    assert client.delete(f"/extratos/{extract_id}").status_code == 204
    missing = client.get(f"/extratos/{extract_id}")
    assert missing.status_code == 404
    assert missing.json()["erro"] == "EXTRATO_NAO_ENCONTRADO"


def test_erro_interno_nao_vaza_detalhes_e_usa_formato_unico(client):
    """Verifica RNF01 para exceção inesperada sem expor detalhe interno ao cliente."""
    def fail_listing():
        raise RuntimeError("synthetic internal detail")

    client.app.state.database.listar_extratos = fail_listing
    response = TestClient(client.app, raise_server_exceptions=False).get("/extratos")

    assert response.status_code == 500
    assert response.json() == {
        "erro": "ERRO_INTERNO",
        "mensagem": "Erro interno ao processar a solicitação.",
        "regra": None,
    }
    assert "synthetic internal detail" not in response.text