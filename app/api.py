"""U5 — Camada HTTP (SPEC §6.3 a §6.6, ADR-001, CONTRATO.md "app/api.py").

Camada fina: valida os parâmetros HTTP, chama o motor (leitura → regras → db, ou db →
consultas) e converte o resultado para JSON. Nenhuma regra de negócio e nenhum SQL aqui.
Todo erro sai no formato único {"erro", "mensagem", "regra"} (SPEC §6.6).

Nunca registra descrição nem conteúdo de lançamento em log (RNF06).
"""

from __future__ import annotations

import logging
import os
import sqlite3
from dataclasses import asdict
from datetime import datetime
from functools import cache
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, Form, Query, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app import consultas, db, leitura, regras
from app.erros import (
    ArquivoVazio,
    BancoDesconhecido,
    EncodingInvalido,
    ErroDominio,
    ExtratoNaoEncontrado,
    NenhumaLinhaValida,
    ParametroInvalido,
)
from app.models import Extrato, Lancamento

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Statement Analyzer",
    version="1.2",
    description="Lê extratos bancários em CSV pela ficha do banco e responde consultas "
    "de análise sobre os lançamentos. Ver docs/SPEC.md.",
)

# Status HTTP de cada exceção de domínio (CONTRATO.md, tabela de erros).
STATUS_POR_ERRO: dict[type[ErroDominio], int] = {
    BancoDesconhecido: 400,
    ArquivoVazio: 422,
    EncodingInvalido: 422,
    NenhumaLinhaValida: 422,
    ParametroInvalido: 422,
    ExtratoNaoEncontrado: 404,
}


class ErroProtocolo(Exception):
    """Erro da própria camada HTTP, que não nasce de uma regra de negócio (regra = null)."""

    def __init__(self, status: int, codigo: str, mensagem: str) -> None:
        super().__init__(mensagem)
        self.status = status
        self.codigo = codigo
        self.mensagem = mensagem


@cache
def obter_conexao() -> sqlite3.Connection:
    """Abre a conexão uma única vez, no caminho de STATEMENT_DB. Os testes a substituem."""
    return db.conectar(os.environ.get("STATEMENT_DB", "dados/statement.db"))


Conexao = Annotated[sqlite3.Connection, Depends(obter_conexao)]


# --- Formato único de erro (SPEC §6.6) --------------------------------------------


def _resposta_erro(status: int, erro: str, mensagem: str, regra: str | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status, content={"erro": erro, "mensagem": mensagem, "regra": regra}
    )


@app.exception_handler(ErroDominio)
async def _tratar_erro_dominio(request: Request, exc: ErroDominio) -> JSONResponse:
    status = next(
        (STATUS_POR_ERRO[tipo] for tipo in type(exc).__mro__ if tipo in STATUS_POR_ERRO), 422
    )
    return _resposta_erro(status, exc.codigo, exc.mensagem, exc.regra)


@app.exception_handler(ErroProtocolo)
async def _tratar_erro_protocolo(request: Request, exc: ErroProtocolo) -> JSONResponse:
    return _resposta_erro(exc.status, exc.codigo, exc.mensagem)


@app.exception_handler(RequestValidationError)
async def _tratar_validacao(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Só os nomes dos parâmetros: o valor enviado não é ecoado.
    campos = sorted({".".join(str(parte) for parte in erro["loc"]) for erro in exc.errors()})
    return _resposta_erro(422, "PARAMETRO_INVALIDO", f"Parâmetro inválido: {', '.join(campos)}.")


@app.exception_handler(Exception)
async def _tratar_erro_inesperado(request: Request, exc: Exception) -> JSONResponse:
    # Só o tipo: a mensagem da exceção pode carregar dados do extrato (RNF06).
    logger.error("Erro inesperado em %s %s: %s", request.method, request.url.path, type(exc).__name__)
    return _resposta_erro(500, "ERRO_INTERNO", "Erro interno do servidor.")


# --- Conversão para JSON ----------------------------------------------------------


def _lancamento(lancamento: Lancamento) -> dict[str, Any]:
    """Modelo canônico da SPEC §6.2."""
    return {
        "id": lancamento.id,
        "extrato_id": lancamento.extrato_id,
        "data": lancamento.data,
        "valor_centavos": lancamento.valor_centavos,
        "descricao": lancamento.descricao,
    }


def _movimento(lancamento: Lancamento) -> dict[str, Any]:
    """Lançamento como sai nas consultas (SPEC §6.5): {data, valor_centavos, descricao}."""
    return {
        "data": lancamento.data,
        "valor_centavos": lancamento.valor_centavos,
        "descricao": lancamento.descricao,
    }


def _obter_extrato(conn: sqlite3.Connection, extrato_id: int) -> Extrato:
    extrato = db.obter_extrato(conn, extrato_id)
    if extrato is None:
        raise ExtratoNaoEncontrado(f"O extrato {extrato_id} não existe.")
    return extrato


def _extrato_e_lancamentos(
    conn: sqlite3.Connection, extrato_id: int
) -> tuple[Extrato, list[Lancamento]]:
    extrato = _obter_extrato(conn, extrato_id)
    return extrato, db.listar_lancamentos(conn, extrato_id)


# --- Envio e gestão de extratos (SPEC §6.3 e §6.4) --------------------------------


@app.post("/extratos", status_code=201)
def enviar_extrato(
    conn: Conexao,
    banco: Annotated[str, Form()],
    arquivo: Annotated[UploadFile | None, File()] = None,
    saldo_inicial_centavos: Annotated[int | None, Form()] = None,
) -> dict[str, Any]:
    """Lê o arquivo pela ficha do banco, normaliza e persiste (SPEC §6.3)."""
    if arquivo is None:
        raise ErroProtocolo(400, "ARQUIVO_AUSENTE", "O campo 'arquivo' é obrigatório.")
    ficha = leitura.carregar_ficha(banco)
    resultado = regras.processar(leitura.ler(arquivo.file.read(), ficha), ficha)
    criado_em = datetime.now().astimezone().isoformat(timespec="seconds")
    extrato = db.salvar_extrato(
        conn, arquivo.filename or "", ficha.nome, criado_em, saldo_inicial_centavos, resultado
    )
    return {**asdict(extrato), "recusas": [asdict(recusa) for recusa in resultado.recusas]}


@app.get("/extratos")
def listar_extratos(conn: Conexao) -> list[dict[str, Any]]:
    """Lista os extratos, sem lançamentos (SPEC §6.4)."""
    return [asdict(extrato) for extrato in db.listar_extratos(conn)]


@app.get("/extratos/{extrato_id}")
def obter_extrato(
    conn: Conexao,
    extrato_id: int,
    limite: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """Extrato com os lançamentos paginados (SPEC §6.4, D6)."""
    extrato = _obter_extrato(conn, extrato_id)
    lancamentos = db.listar_lancamentos(conn, extrato_id, limite, offset)
    return {
        **asdict(extrato),
        "lancamentos": [_lancamento(lancamento) for lancamento in lancamentos],
        "limite": limite,
        "offset": offset,
    }


@app.delete("/extratos/{extrato_id}", status_code=204, response_class=Response)
def apagar_extrato(conn: Conexao, extrato_id: int) -> Response:
    """Apaga o extrato em cascata (SPEC §6.4, RF06)."""
    if not db.apagar_extrato(conn, extrato_id):
        raise ExtratoNaoEncontrado(f"O extrato {extrato_id} não existe.")
    return Response(status_code=204)


# --- Consultas (SPEC §6.5) --------------------------------------------------------


@app.get("/extratos/{extrato_id}/resumo")
def consultar_resumo(conn: Conexao, extrato_id: int) -> dict[str, Any]:
    """Resumo do extrato (RF08)."""
    _, lancamentos = _extrato_e_lancamentos(conn, extrato_id)
    return {"extrato_id": extrato_id, **asdict(consultas.resumo(lancamentos))}


@app.get("/extratos/{extrato_id}/saldo")
def consultar_saldo(conn: Conexao, extrato_id: int) -> dict[str, Any]:
    """Saldo corrente (RF09). Saldo inicial ausente entra como 0 (D3)."""
    extrato, lancamentos = _extrato_e_lancamentos(conn, extrato_id)
    return asdict(consultas.saldo(lancamentos, extrato.saldo_inicial_centavos or 0))


@app.get("/extratos/{extrato_id}/maior-entrada")
def consultar_maior_entrada(conn: Conexao, extrato_id: int) -> dict[str, Any] | None:
    """Maior entrada (RF10); null quando não há entradas (D5)."""
    _, lancamentos = _extrato_e_lancamentos(conn, extrato_id)
    lancamento = consultas.maior_entrada(lancamentos)
    return None if lancamento is None else _movimento(lancamento)


@app.get("/extratos/{extrato_id}/maior-despesa")
def consultar_maior_despesa(conn: Conexao, extrato_id: int) -> dict[str, Any] | None:
    """Maior despesa (RF10); null quando não há despesas (D5)."""
    _, lancamentos = _extrato_e_lancamentos(conn, extrato_id)
    lancamento = consultas.maior_despesa(lancamentos)
    return None if lancamento is None else _movimento(lancamento)


@app.get("/extratos/{extrato_id}/top-despesas")
def consultar_top_despesas(conn: Conexao, extrato_id: int, n: int = 10) -> dict[str, Any]:
    """As n maiores despesas (RF11). A faixa de n é validada pelo motor."""
    _, lancamentos = _extrato_e_lancamentos(conn, extrato_id)
    despesas = consultas.top_despesas(lancamentos, n)
    return {"n": n, "despesas": [_movimento(despesa) for despesa in despesas]}


@app.get("/extratos/{extrato_id}/por-semana")
def consultar_por_semana(conn: Conexao, extrato_id: int) -> dict[str, Any]:
    """Totais por semana, de segunda a domingo (RF12, D2)."""
    _, lancamentos = _extrato_e_lancamentos(conn, extrato_id)
    return {"semanas": [asdict(semana) for semana in consultas.por_semana(lancamentos)]}


@app.get("/extratos/{extrato_id}/dias-no-negativo")
def consultar_dias_no_negativo(conn: Conexao, extrato_id: int) -> dict[str, Any]:
    """Dias e períodos no negativo (RF13). O saldo inicial vai como está, até None (D3)."""
    extrato, lancamentos = _extrato_e_lancamentos(conn, extrato_id)
    return asdict(consultas.dias_no_negativo(lancamentos, extrato.saldo_inicial_centavos))


@app.get("/extratos/{extrato_id}/repetidos")
def consultar_repetidos(conn: Conexao, extrato_id: int) -> dict[str, Any]:
    """Gastos repetidos (RF14)."""
    _, lancamentos = _extrato_e_lancamentos(conn, extrato_id)
    return {"repetidos": [asdict(grupo) for grupo in consultas.repetidos(lancamentos)]}
