"""U4 — Motor puro de análise (SPEC §6.5, RN07–RN10). Sem HTTP e sem I/O."""

from __future__ import annotations

import unicodedata
from collections import defaultdict
from collections.abc import Sequence
from datetime import date, timedelta

from app.erros import ParametroInvalido
from app.models import (
    DiasNoNegativo,
    GrupoRepetido,
    Lancamento,
    Periodo,
    PeriodoNegativo,
    Resumo,
    Saldo,
    Semana,
)


def _divisao_para_zero(numerador: int, denominador: int) -> int:
    """Divide inteiros truncando em direção a zero, só com aritmética inteira (RN02)."""
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


def maior_entrada(lancamentos: Sequence[Lancamento]) -> Lancamento | None:
    """Consulta maior-entrada (RF10, RN10): maior positivo; empate pela data mais antiga."""
    vencedor: Lancamento | None = None
    for lancamento in lancamentos:
        if lancamento.valor_centavos <= 0:
            continue
        if vencedor is None:
            vencedor = lancamento
            continue
        if lancamento.valor_centavos > vencedor.valor_centavos:
            vencedor = lancamento
        elif (
            lancamento.valor_centavos == vencedor.valor_centavos
            and lancamento.data < vencedor.data
        ):
            vencedor = lancamento
    return vencedor


def maior_despesa(lancamentos: Sequence[Lancamento]) -> Lancamento | None:
    """Consulta maior-despesa (RF10, RN10): mais negativa; empate pela data mais antiga."""
    vencedor: Lancamento | None = None
    for lancamento in lancamentos:
        if lancamento.valor_centavos >= 0:
            continue
        if vencedor is None:
            vencedor = lancamento
            continue
        if lancamento.valor_centavos < vencedor.valor_centavos:
            vencedor = lancamento
        elif (
            lancamento.valor_centavos == vencedor.valor_centavos
            and lancamento.data < vencedor.data
        ):
            vencedor = lancamento
    return vencedor


def top_despesas(lancamentos: Sequence[Lancamento], n: int) -> list[Lancamento]:
    """Consulta top-despesas (RF11, RN10): as n saídas mais negativas, com o mesmo desempate."""
    if n < 1 or n > 100:
        raise ParametroInvalido("n deve estar entre 1 e 100.")

    despesas = [
        (indice, lancamento)
        for indice, lancamento in enumerate(lancamentos)
        if lancamento.valor_centavos < 0
    ]
    despesas.sort(key=lambda item: (item[1].valor_centavos, item[1].data, item[0]))
    return [lancamento for _, lancamento in despesas[:n]]


def por_semana(lancamentos: Sequence[Lancamento]) -> list[Semana]:
    """Consulta por-semana (RF12, D2): semanas de segunda a domingo recortadas ao período."""
    if not lancamentos:
        return []

    inicio = min(lancamento.data for lancamento in lancamentos)
    fim = max(lancamento.data for lancamento in lancamentos)
    semanas: list[Semana] = []
    de = inicio
    while de <= fim:
        ate = min(de + timedelta(days=6 - de.weekday()), fim)
        da_semana = [
            lancamento for lancamento in lancamentos if de <= lancamento.data <= ate
        ]
        entradas, saidas = _somas(da_semana)
        semanas.append(
            Semana(
                de=de,
                ate=ate,
                entradas_centavos=entradas,
                saidas_centavos=saidas,
                saldo_centavos=entradas + saidas,
            )
        )
        de = ate + timedelta(days=1)
    return semanas


def dias_no_negativo(
    lancamentos: Sequence[Lancamento], saldo_inicial: int | None
) -> DiasNoNegativo:
    """Consulta dias-no-negativo (RF13, RN07, RN08): dias do calendário com saldo de fim de dia < 0."""
    assumido = saldo_inicial is None
    inicial = 0 if saldo_inicial is None else saldo_inicial
    if not lancamentos:
        return DiasNoNegativo(
            saldo_inicial_centavos=inicial,
            saldo_inicial_assumido=assumido,
            dias_no_negativo=0,
            periodos=[],
        )

    totais = _totais_por_data(lancamentos)
    dia = min(totais)
    fim = max(totais)
    corrente = inicial
    total_dias = 0
    periodos: list[PeriodoNegativo] = []
    aberto: PeriodoNegativo | None = None
    while dia <= fim:
        corrente += totais.get(dia, 0)
        if corrente < 0:
            total_dias += 1
            if aberto is None:
                aberto = PeriodoNegativo(de=dia, ate=dia, saldo_minimo_centavos=corrente)
            else:
                aberto = PeriodoNegativo(
                    de=aberto.de,
                    ate=dia,
                    saldo_minimo_centavos=min(aberto.saldo_minimo_centavos, corrente),
                )
        elif aberto is not None:
            periodos.append(aberto)
            aberto = None
        dia += timedelta(days=1)
    if aberto is not None:
        periodos.append(aberto)

    return DiasNoNegativo(
        saldo_inicial_centavos=inicial,
        saldo_inicial_assumido=assumido,
        dias_no_negativo=total_dias,
        periodos=periodos,
    )


def repetidos(lancamentos: Sequence[Lancamento]) -> list[GrupoRepetido]:
    """Consulta repetidos (RF14, RN09, D4): 3+ despesas de mesma descrição a até 10% da média."""
    grupos: dict[str, list[Lancamento]] = defaultdict(list)
    for lancamento in lancamentos:
        if lancamento.valor_centavos < 0:
            grupos[normalizar_descricao(lancamento.descricao)].append(lancamento)

    resultado: list[GrupoRepetido] = []
    for descricao, despesas in grupos.items():
        k = len(despesas)
        soma = sum(despesa.valor_centavos for despesa in despesas)
        mantidas = [
            despesa
            for despesa in despesas
            if 10 * abs(despesa.valor_centavos * k - soma) <= abs(soma)
        ]
        if len(mantidas) < 3:
            continue
        total = sum(despesa.valor_centavos for despesa in mantidas)
        resultado.append(
            GrupoRepetido(
                descricao_normalizada=descricao,
                ocorrencias=len(mantidas),
                valor_medio_centavos=_divisao_para_zero(total, len(mantidas)),
                total_centavos=total,
                datas=sorted(despesa.data for despesa in mantidas),
            )
        )

    resultado.sort(
        key=lambda grupo: (
            -grupo.ocorrencias,
            grupo.total_centavos,
            grupo.descricao_normalizada,
        )
    )
    return resultado
