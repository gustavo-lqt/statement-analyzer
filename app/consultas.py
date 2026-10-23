"""U4 — Motor puro de análise (SPEC §6.5, RN07–RN10). Sem HTTP e sem I/O."""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence
from datetime import date

from app.models import Lancamento, Periodo, Resumo


def _divisao_para_zero(numerador: int, denominador: int) -> int:
    """Divide inteiros truncando em direção a zero (não usa float)."""
    quociente = abs(numerador) // denominador
    if numerador < 0:
        return -quociente
    return quociente


def _somas(lancamentos: Sequence[Lancamento]) -> tuple[int, int]:
    entradas = 0
    saidas = 0
    for lancamento in lancamentos:
        valor = lancamento.valor_centavos
        if valor > 0:
            entradas += valor
        elif valor < 0:
            saidas += valor
    return entradas, saidas


def normalizar_descricao(texto: str) -> str:
    """Aplica a descrição normalizada da SPEC §4 (usada em RN09)."""
    decomposto = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(ch for ch in decomposto if not unicodedata.combining(ch))
    filtrado = "".join(
        ch for ch in sem_acento.upper() if ch.isalnum() or ch == " "
    )
    return " ".join(filtrado.split())


def resumo(lancamentos: Sequence[Lancamento]) -> Resumo:
    """Consulta resumo (RF08): totais, saldo e média diária de gasto no período."""
    if not lancamentos:
        return Resumo(
            periodo=None,
            total_lancamentos=0,
            entradas_centavos=0,
            saidas_centavos=0,
            saldo_centavos=0,
            media_diaria_gasto_centavos=0,
        )

    datas = [lancamento.data for lancamento in lancamentos]
    inicio = min(datas)
    fim = max(datas)
    entradas, saidas = _somas(lancamentos)
    dias = (fim - inicio).days + 1
    return Resumo(
        periodo=Periodo(de=inicio, ate=fim),
        total_lancamentos=len(lancamentos),
        entradas_centavos=entradas,
        saidas_centavos=saidas,
        saldo_centavos=entradas + saidas,
        media_diaria_gasto_centavos=_divisao_para_zero(saidas, dias),
    )
