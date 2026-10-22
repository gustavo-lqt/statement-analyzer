from __future__ import annotations

import csv
import random
from io import StringIO

from app.models import FichaBanco


def _format_amount(cents: int, decimal_separator: str, thousands_separator: str | None) -> str:
    whole, fraction = divmod(abs(cents), 100)
    whole_text = str(whole)
    if thousands_separator:
        groups: list[str] = []
        while whole_text:
            groups.append(whole_text[-3:])
            whole_text = whole_text[:-3]
        whole_text = thousands_separator.join(reversed(groups))
    return f"{whole_text}{decimal_separator}{fraction:02d}"


def gerar_csv_sintetico(ficha: FichaBanco, seed: int = 20261022, quantidade: int = 30) -> bytes:
    """Gera CSV reprodutível com dados fictícios, sem persistir dados financeiros reais."""
    if quantidade < 1:
        raise ValueError("quantidade deve ser maior que zero")
    generator = random.Random(seed)
    output = StringIO(newline="")
    writer = csv.writer(output, delimiter=ficha.delimitador, lineterminator="\n")
    canonical_columns = list(ficha.colunas)
    writer.writerow([ficha.colunas[name] for name in canonical_columns])

    for index in range(quantidade):
        transaction_day = generator.randint(1, 28)
        day = date_for_format(transaction_day, ficha.formato_data)
        description = f"LANCAMENTO SINTETICO {index + 1:03d}"
        cents = generator.randint(100, 500_000)
        is_expense = generator.choice((True, False))
        amount = _format_amount(cents, ficha.separador_decimal, ficha.separador_milhar)

        values = {"data": day, "descricao": description}
        if ficha.convencao_sinal == "NEGATIVO_SAIDA":
            values["valor"] = f"-{amount}" if is_expense else amount
        elif ficha.convencao_sinal == "COLUNA_DC":
            values["valor"] = amount
            values["tipo"] = "D" if is_expense else "C"
        elif ficha.convencao_sinal == "COLUNAS_SEPARADAS":
            values["credito"] = "" if is_expense else amount
            values["debito"] = amount if is_expense else ""
        writer.writerow([values.get(name, "") for name in canonical_columns])

    return output.getvalue().encode(ficha.encoding)


def date_for_format(day: int, declared_format: str) -> str:
    if declared_format == "dd/mm/aaaa":
        return f"{day:02d}/09/2026"
    if declared_format == "aaaa-mm-dd":
        return f"2026-09-{day:02d}"
    if declared_format == "dd-mm-aaaa":
        return f"{day:02d}-09-2026"
    raise ValueError(f"Formato de data não suportado: {declared_format}")