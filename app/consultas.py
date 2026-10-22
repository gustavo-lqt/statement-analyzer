from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Iterable

from app.models import (
    DiasNoNegativo,
    GrupoRepetido,
    Lancamento,
    ParametroInvalido,
    PeriodoNegativo,
    Resumo,
    Saldo,
    Semana,
)


def _date_key(lancamento: Lancamento) -> date:
    return date.fromisoformat(lancamento.data)


def _ordered(lancamentos: Iterable[Lancamento]) -> list[Lancamento]:
    return sorted(
        lancamentos,
        key=lambda item: (
            item.data,
            item.descricao_normalizada,
            item.valor_centavos,
            item.descricao,
            item.id or 0,
        ),
    )


def resumo(lancamentos: Iterable[Lancamento], extrato_id: int | None = None) -> Resumo:
    """Aplica RN02 e calcula agregados de entradas, saídas e período do extrato."""
    items = list(lancamentos)
    if not items:
        return Resumo(extrato_id, None, None, 0, 0, 0, 0, 0)

    first_date = min(item.data for item in items)
    last_date = max(item.data for item in items)
    entries = sum(item.valor_centavos for item in items if item.valor_centavos > 0)
    expenses = sum(item.valor_centavos for item in items if item.valor_centavos < 0)
    days = (date.fromisoformat(last_date) - date.fromisoformat(first_date)).days + 1
    average_daily_expense = -(abs(expenses) // days) if days else 0
    return Resumo(
        extrato_id,
        first_date,
        last_date,
        len(items),
        entries,
        expenses,
        entries + expenses,
        average_daily_expense,
    )


def saldo(lancamentos: Iterable[Lancamento], saldo_inicial: int = 0) -> Saldo:
    """Aplica RN07 e RN08 calculando o saldo ao final de cada bloco de data."""
    grouped: dict[str, int] = defaultdict(int)
    for item in lancamentos:
        grouped[item.data] += item.valor_centavos

    current = saldo_inicial
    minimum = saldo_inicial
    minimum_date: str | None = None
    went_negative = saldo_inicial < 0
    for transaction_date in sorted(grouped):
        current += grouped[transaction_date]
        if current < 0:
            went_negative = True
        if current < minimum:
            minimum = current
            minimum_date = transaction_date
    return Saldo(saldo_inicial, current, went_negative, minimum, minimum_date)


def maior_entrada(lancamentos: Iterable[Lancamento]) -> Lancamento | None:
    """Aplica RN10 à entrada positiva de maior valor, escolhendo a data mais antiga no empate."""
    candidates = (item for item in lancamentos if item.valor_centavos > 0)
    return min(
        candidates,
        key=lambda item: (-item.valor_centavos, item.data, item.descricao_normalizada, item.descricao),
        default=None,
    )


def maior_despesa(lancamentos: Iterable[Lancamento]) -> Lancamento | None:
    """Aplica RN10 à saída negativa de maior magnitude, escolhendo a data mais antiga no empate."""
    candidates = (item for item in lancamentos if item.valor_centavos < 0)
    return min(
        candidates,
        key=lambda item: (item.valor_centavos, item.data, item.descricao_normalizada, item.descricao),
        default=None,
    )


def top_despesas(lancamentos: Iterable[Lancamento], n: int = 10) -> list[Lancamento]:
    """Aplica RN02 ordenando despesas por magnitude e desempate determinístico por data."""
    if n < 1:
        raise ParametroInvalido("O parâmetro n deve ser maior que zero.")
    expenses = (item for item in lancamentos if item.valor_centavos < 0)
    return sorted(
        expenses,
        key=lambda item: (item.valor_centavos, item.data, item.descricao_normalizada, item.descricao),
    )[:n]


def por_semana(lancamentos: Iterable[Lancamento]) -> list[Semana]:
    """Agrupa por segunda-feira a domingo, incluindo semanas parciais conforme RF12."""
    items = _ordered(lancamentos)
    if not items:
        return []

    period_start = _date_key(items[0])
    period_end = _date_key(items[-1])
    groups: dict[date, list[Lancamento]] = defaultdict(list)
    for item in items:
        transaction_date = _date_key(item)
        week_start = transaction_date - timedelta(days=transaction_date.weekday())
        groups[week_start].append(item)

    weeks: list[Semana] = []
    for week_start, week_items in sorted(groups.items()):
        week_end = week_start + timedelta(days=6)
        entries = sum(item.valor_centavos for item in week_items if item.valor_centavos > 0)
        expenses = sum(item.valor_centavos for item in week_items if item.valor_centavos < 0)
        weeks.append(
            Semana(
                max(week_start, period_start).isoformat(),
                min(week_end, period_end).isoformat(),
                entries,
                expenses,
                entries + expenses,
            )
        )
    return weeks


def dias_no_negativo(
    lancamentos: Iterable[Lancamento],
    saldo_inicial: int = 0,
    saldo_inicial_assumido: bool = False,
) -> DiasNoNegativo:
    """Aplica RN07 e RN08; avalia cada dia civil até o último lançamento."""
    items = _ordered(lancamentos)
    if not items:
        return DiasNoNegativo(saldo_inicial, saldo_inicial_assumido, 0, [])

    daily_totals: dict[date, int] = defaultdict(int)
    for item in items:
        daily_totals[_date_key(item)] += item.valor_centavos

    first_date = _date_key(items[0])
    last_date = _date_key(items[-1])
    current = saldo_inicial
    negative_days = 0
    periods: list[PeriodoNegativo] = []
    active_start: date | None = None
    active_end: date | None = None
    active_minimum = 0
    current_date = first_date
    while current_date <= last_date:
        current += daily_totals[current_date]
        if current < 0:
            negative_days += 1
            if active_start is None:
                active_start = current_date
                active_minimum = current
            else:
                active_minimum = min(active_minimum, current)
            active_end = current_date
        elif active_start is not None and active_end is not None:
            periods.append(
                PeriodoNegativo(active_start.isoformat(), active_end.isoformat(), active_minimum)
            )
            active_start = None
            active_end = None
        current_date += timedelta(days=1)

    if active_start is not None and active_end is not None:
        periods.append(PeriodoNegativo(active_start.isoformat(), active_end.isoformat(), active_minimum))

    return DiasNoNegativo(saldo_inicial, saldo_inicial_assumido, negative_days, periods)


def repetidos(lancamentos: Iterable[Lancamento]) -> list[GrupoRepetido]:
    """Aplica RN09 usando comparação inteira para o limite de 10% e mínimo de 3 ocorrências."""
    groups: dict[str, list[Lancamento]] = defaultdict(list)
    for item in lancamentos:
        if item.valor_centavos < 0 and item.descricao_normalizada:
            groups[item.descricao_normalizada].append(item)

    repeated: list[GrupoRepetido] = []
    for description, group in groups.items():
        ordered_group = _ordered(group)
        if len(ordered_group) < 3:
            continue
        total = sum(item.valor_centavos for item in ordered_group)
        if 10 * max(abs(item.valor_centavos * len(ordered_group) - total) for item in ordered_group) > abs(total):
            continue
        average = abs(total) // len(ordered_group)
        if total < 0:
            average = -average
        repeated.append(
            GrupoRepetido(
                description,
                len(ordered_group),
                average,
                total,
                [item.data for item in ordered_group],
            )
        )
    return sorted(repeated, key=lambda group: (-abs(group.total_centavos), group.descricao_normalizada))