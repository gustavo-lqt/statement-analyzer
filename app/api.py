from __future__ import annotations

import os
from dataclasses import asdict
from datetime import datetime
from typing import Any

from fastapi import FastAPI, File, Form, Query, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.catalogo import carregar_fichas
from app.consultas import (
    dias_no_negativo,
    maior_despesa,
    maior_entrada,
    por_semana,
    repetidos,
    resumo,
    saldo,
    top_despesas,
)
from app.db import Database
from app.leitura import ler
from app.models import ErroDominio, ParametroInvalido
from app.regras import normalizar


def _lancamento_json(item: Any) -> dict[str, Any]:
    return {
        "id": item.id,
        "extrato_id": item.extrato_id,
        "data": item.data,
        "valor_centavos": item.valor_centavos,
        "descricao": item.descricao,
    }


def _recusa_json(item: Any, *, include_content: bool = True) -> dict[str, Any]:
    result = {"linha": item.numero_linha, "motivo": item.motivo}
    if include_content:
        result["conteudo"] = item.conteudo_bruto
    return result


def _transaction_json(item: Any) -> dict[str, Any]:
    return {"data": item.data, "valor_centavos": item.valor_centavos, "descricao": item.descricao}


def create_app(database_path: str | None = None) -> FastAPI:
    application = FastAPI(title="Statement Analyzer", version="1.0.0")
    application.state.database = Database(
        database_path or os.getenv("DATABASE_PATH", "statement-analyzer.sqlite3")
    )
    application.state.fichas = carregar_fichas()

    @application.exception_handler(ErroDominio)
    async def handle_domain_error(_request: Any, error: ErroDominio) -> JSONResponse:
        status = {
            "EXTRATO_NAO_ENCONTRADO": 404,
            "ARQUIVO_AUSENTE": 400,
            "BANCO_DESCONHECIDO": 400,
            "ARQUIVO_VAZIO": 422,
            "ENCODING_INVALIDO": 422,
            "NENHUMA_LINHA_VALIDA": 422,
            "PARAMETRO_INVALIDO": 422,
        }.get(error.codigo, 422)
        return JSONResponse(
            status_code=status,
            content={"erro": error.codigo, "mensagem": error.mensagem, "regra": error.regra},
        )

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(_request: Any, _error: RequestValidationError) -> JSONResponse:
        error = ParametroInvalido("Um ou mais parâmetros da requisição são inválidos.")
        return JSONResponse(
            status_code=422,
            content={"erro": error.codigo, "mensagem": error.mensagem, "regra": error.regra},
        )

    @application.exception_handler(Exception)
    async def handle_unexpected_error(_request: Any, _error: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "erro": "ERRO_INTERNO",
                "mensagem": "Erro interno ao processar a solicitação.",
                "regra": None,
            },
        )

    @application.post("/extratos", status_code=201)
    async def enviar_extrato(
        arquivo: UploadFile | None = File(default=None),
        banco: str = Form(...),
        saldo_inicial_centavos: int | None = Form(default=None),
    ) -> dict[str, Any]:
        if arquivo is None:
            raise ErroDominio("ARQUIVO_AUSENTE", "O arquivo é obrigatório.")
        ficha = application.state.fichas.get(banco)
        if ficha is None:
            raise ErroDominio("BANCO_DESCONHECIDO", f"A ficha '{banco}' não está registrada.")

        arquivo.file.seek(0)
        initial_balance = saldo_inicial_centavos if saldo_inicial_centavos is not None else 0
        created_at = datetime.now().astimezone().isoformat(timespec="seconds")
        database: Database = application.state.database

        def normalized_rows():
            for raw_line in ler(arquivo.file, ficha):
                yield normalizar(raw_line, ficha)

        extract_id = database.criar_extrato_streaming(
            arquivo.filename or "arquivo.csv",
            banco,
            created_at,
            initial_balance,
            saldo_inicial_centavos is None,
            normalized_rows(),
        )
        saved = database.obter_extrato(extract_id, limit=1, offset=0)
        return {
            "id": saved.id,
            "nome_arquivo": saved.nome_arquivo,
            "banco": saved.banco,
            "criado_em": saved.criado_em,
            "saldo_inicial_centavos": saved.saldo_inicial_centavos,
            "total_linhas": saved.total_linhas,
            "aceitos": saved.aceitos,
            "rejeitados": saved.rejeitados,
            "recusas": [_recusa_json(item) for item in saved.recusas],
        }

    @application.get("/extratos")
    def obter_extratos() -> list[dict[str, Any]]:
        return application.state.database.listar_extratos()

    @application.get("/extratos/{extrato_id}")
    def obter_detalhes_extrato(
        extrato_id: int,
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        extract = application.state.database.obter_extrato(extrato_id, limit, offset)
        return {
            "id": extract.id,
            "nome_arquivo": extract.nome_arquivo,
            "banco": extract.banco,
            "criado_em": extract.criado_em,
            "saldo_inicial_centavos": extract.saldo_inicial_centavos,
            "total_linhas": extract.total_linhas,
            "aceitos": extract.aceitos,
            "rejeitados": extract.rejeitados,
            "lancamentos": [_lancamento_json(item) for item in extract.lancamentos],
            "recusas": [_recusa_json(item, include_content=False) for item in extract.recusas],
            "limit": limit,
            "offset": offset,
        }

    @application.delete("/extratos/{extrato_id}", status_code=204)
    def apagar_extrato(extrato_id: int) -> None:
        if not application.state.database.excluir_extrato(extrato_id):
            raise ErroDominio(
                "EXTRATO_NAO_ENCONTRADO", "O extrato solicitado não foi encontrado."
            )

    def obter_contexto_consulta(extrato_id: int) -> tuple[list[Any], int]:
        database: Database = application.state.database
        extract = database.obter_extrato(extrato_id, limit=1, offset=0)
        return database.listar_lancamentos(extrato_id), extract.saldo_inicial_centavos

    @application.get("/extratos/{extrato_id}/resumo")
    def consultar_resumo(extrato_id: int) -> dict[str, Any]:
        items, _initial = obter_contexto_consulta(extrato_id)
        result = resumo(items, extrato_id)
        return {
            "extrato_id": result.extrato_id,
            "periodo": {"de": result.periodo_de, "ate": result.periodo_ate},
            "total_lancamentos": result.total_lancamentos,
            "entradas_centavos": result.entradas_centavos,
            "saidas_centavos": result.saidas_centavos,
            "saldo_centavos": result.saldo_centavos,
            "media_diaria_gasto_centavos": result.media_diaria_gasto_centavos,
        }

    @application.get("/extratos/{extrato_id}/saldo")
    def consultar_saldo(extrato_id: int) -> dict[str, Any]:
        items, initial = obter_contexto_consulta(extrato_id)
        return asdict(saldo(items, initial))

    @application.get("/extratos/{extrato_id}/maior-entrada")
    def consultar_maior_entrada(extrato_id: int) -> dict[str, Any] | None:
        items, _initial = obter_contexto_consulta(extrato_id)
        result = maior_entrada(items)
        return _transaction_json(result) if result else None

    @application.get("/extratos/{extrato_id}/maior-despesa")
    def consultar_maior_despesa(extrato_id: int) -> dict[str, Any] | None:
        items, _initial = obter_contexto_consulta(extrato_id)
        result = maior_despesa(items)
        return _transaction_json(result) if result else None

    @application.get("/extratos/{extrato_id}/top-despesas")
    def consultar_top_despesas(
        extrato_id: int,
        n: int = Query(default=10, ge=1, le=1000),
    ) -> dict[str, Any]:
        items, _initial = obter_contexto_consulta(extrato_id)
        return {"n": n, "despesas": [_transaction_json(item) for item in top_despesas(items, n)]}

    @application.get("/extratos/{extrato_id}/por-semana")
    def consultar_por_semana(extrato_id: int) -> dict[str, Any]:
        items, _initial = obter_contexto_consulta(extrato_id)
        return {"semanas": [asdict(item) for item in por_semana(items)]}

    @application.get("/extratos/{extrato_id}/dias-no-negativo")
    def consultar_dias_no_negativo(extrato_id: int) -> dict[str, Any]:
        items, initial = obter_contexto_consulta(extrato_id)
        extract = application.state.database.obter_extrato(extrato_id, limit=1, offset=0)
        result = dias_no_negativo(items, initial, extract.saldo_inicial_assumido)
        return asdict(result)

    @application.get("/extratos/{extrato_id}/repetidos")
    def consultar_repetidos(extrato_id: int) -> dict[str, Any]:
        items, _initial = obter_contexto_consulta(extrato_id)
        return {"repetidos": [asdict(item) for item in repetidos(items)]}

    return application


app = create_app()