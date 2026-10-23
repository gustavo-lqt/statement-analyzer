"""U4 — Motor puro de análise (SPEC §6.5, RN07–RN10). Sem HTTP e sem I/O."""

from __future__ import annotations

import unicodedata
from collections import defaultdict
from collections.abc import Sequence
from datetime import date

from app.models import Lancamento, Periodo, Resumo, Saldo


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


def _totais_por_data(lancamentos: Sequence[Lancamento]) -> dict[date, int]:
    totais: dict[date, int] = defaultdict(int)
    for lancamento in lancamentos:
        totais[lancamento.data] += lancamento.valor_centavos
    return totais


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


def saldo(lancamentos: Sequence[Lancamento], saldo_inicial: int) -> Saldo:
    """Consulta saldo (RF09, RN08): saldo por bloco de dia, mínimo e se ficou negativo."""
    if not lancamentos:
        return Saldo(
            saldo_inicial_centavos=saldo_inicial,
            saldo_final_centavos=saldo_inicial,
            ficou_negativo=saldo_inicial < 0,
            saldo_minimo_centavos=saldo_inicial,
            data_saldo_minimo=None,
        )

    totais = _totais_por_data(lancamentos)
    corrente = saldo_inicial
    minimo: int | None = None
    data_minimo: date | None = None
    for dia in sorted(totais):
        corrente += totais[dia]
        if minimo is None or corrente < minimo:
            minimo = corrente
            data_minimo = dia

    saldo_final = saldo_inicial + sum(
        lancamento.valor_centavos for lancamento in lancamentos
    )
    return Saldo(
        saldo_inicial_centavos=saldo_inicial,
        saldo_final_centavos=saldo_final,
        ficou_negativo=minimo is not None and minimo < 0,
        saldo_minimo_centavos=minimo if minimo is not None else saldo_inicial,
        data_saldo_minimo=data_minimo,
    )
