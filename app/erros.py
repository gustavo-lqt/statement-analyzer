"""Exceções de domínio. CONTRATO CONGELADO da Entrega 2 (ver docs/SPEC.md §8).

Não conhecem HTTP (ADR-001): carregam só o código do erro (SPEC §6.6) e a RN violada.
Quem decide o status HTTP é app/api.py.
"""

from __future__ import annotations


class ErroDominio(Exception):
    codigo: str = "ERRO_DOMINIO"
    regra: str | None = None

    def __init__(self, mensagem: str) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem


class ArquivoVazio(ErroDominio):
    codigo = "ARQUIVO_VAZIO"


class EncodingInvalido(ErroDominio):
    codigo = "ENCODING_INVALIDO"


class NenhumaLinhaValida(ErroDominio):
    codigo = "NENHUMA_LINHA_VALIDA"
    regra = "RN06"


class BancoDesconhecido(ErroDominio):
    codigo = "BANCO_DESCONHECIDO"


class ExtratoNaoEncontrado(ErroDominio):
    codigo = "EXTRATO_NAO_ENCONTRADO"


class ParametroInvalido(ErroDominio):
    codigo = "PARAMETRO_INVALIDO"
