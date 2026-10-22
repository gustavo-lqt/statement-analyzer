from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Iterable

from app.models import (
    FichaBanco,
    Lancamento,
    LinhaCrua,
    NenhumaLinhaValida,
    Recusa,
    ResultadoLeitura,
)


_DATE_FORMATS = {
    "dd/mm/aaaa": "%d/%m/%Y",
    "aaaa-mm-dd": "%Y-%m-%d",
    "dd-mm-aaaa": "%d-%m-%Y",
}


def normalizar_descricao(descricao: str) -> str:
    normalized = unicodedata.normalize("NFKD", descricao.upper())
    without_accents = "".join(character for character in normalized if not unicodedata.combining(character))
    alphanumeric = re.sub(r"[^A-Z0-9]+", " ", without_accents)
    return " ".join(alphanumeric.split())


def _parse_date(value: str, declared_format: str) -> str | None:
    format_string = _DATE_FORMATS.get(declared_format)
    if format_string is None:
        return None
    try:
        parsed = datetime.strptime(value.strip(), format_string).date()
    except ValueError:
        return None
    return parsed.isoformat()


def _parse_cents(value: str, ficha: FichaBanco, *, absolute: bool = False) -> int | None:
    text = value.strip()
    if not text:
        return None

    is_parenthesized = text.startswith("(") and text.endswith(")")
    if is_parenthesized:
        text = text[1:-1].strip()
    sign = -1 if is_parenthesized else 1
    if text.startswith(("+", "-")):
        if text[0] == "-":
            sign *= -1
        text = text[1:]

    decimal_separator = ficha.separador_decimal
    if not decimal_separator or text.count(decimal_separator) > 1:
        return None
    if decimal_separator in text:
        whole, fractional = text.split(decimal_separator, maxsplit=1)
    else:
        whole, fractional = text, ""
    thousands_separator = ficha.separador_milhar
    if thousands_separator and thousands_separator in whole:
        groups = whole.split(thousands_separator)
        if not (1 <= len(groups[0]) <= 3 and groups[0].isdigit()):
            return None
        if any(len(group) != 3 or not group.isdigit() for group in groups[1:]):
            return None
        whole = "".join(groups)

    if not whole or not whole.isdigit() or (fractional and not fractional.isdigit()):
        return None
    if len(fractional) > 2:
        return None

    cents = int(whole) * 100 + int(fractional.ljust(2, "0") or "0")
    if absolute:
        return cents
    return sign * cents


def _has_excess_precision(value: str, ficha: FichaBanco) -> bool:
    text = value.strip().strip("()")
    if text.startswith(("+", "-")):
        text = text[1:]
    decimal_separator = ficha.separador_decimal
    if not decimal_separator or text.count(decimal_separator) != 1:
        return False
    _whole, fractional = text.split(decimal_separator, maxsplit=1)
    return fractional.isdigit() and len(fractional) >= 3


def _row_value(linha: LinhaCrua, ficha: FichaBanco, canonical_name: str) -> str | None:
    if canonical_name not in ficha.colunas:
        return None
    return linha.campos.get(canonical_name)


def normalizar(linha: LinhaCrua, ficha: FichaBanco) -> Lancamento | Recusa:
    """Aplica RN01–RN05: interpreta pela ficha, usa centavos e recusa a linha inválida."""
    if linha.motivo_recusa is not None:
        return Recusa(linha.numero_linha, linha.motivo_recusa, linha.conteudo_bruto)

    date_value = _row_value(linha, ficha, "data")
    description = _row_value(linha, ficha, "descricao")
    if date_value is None or description is None:
        return Recusa(linha.numero_linha, "COLUNA_AUSENTE", linha.conteudo_bruto)

    required_value_columns = {
        "NEGATIVO_SAIDA": {"valor"},
        "COLUNA_DC": {"valor", "tipo"},
        "COLUNAS_SEPARADAS": {"credito", "debito"},
    }.get(ficha.convencao_sinal, set())
    if not required_value_columns <= ficha.colunas.keys():
        return Recusa(linha.numero_linha, "COLUNA_AUSENTE", linha.conteudo_bruto)
    if any(_row_value(linha, ficha, name) is None for name in required_value_columns):
        return Recusa(linha.numero_linha, "COLUNA_AUSENTE", linha.conteudo_bruto)

    normalized_date = _parse_date(date_value, ficha.formato_data)
    if normalized_date is None:
        return Recusa(linha.numero_linha, "DATA_INVALIDA", linha.conteudo_bruto)

    precision_values: list[str] = []
    if ficha.convencao_sinal in {"NEGATIVO_SAIDA", "COLUNA_DC"}:
        precision_values.append(_row_value(linha, ficha, "valor") or "")
    elif ficha.convencao_sinal == "COLUNAS_SEPARADAS":
        precision_values.extend(
            _row_value(linha, ficha, name) or "" for name in ("credito", "debito")
        )
    if any(_has_excess_precision(value, ficha) for value in precision_values):
        return Recusa(linha.numero_linha, "PRECISAO_INVALIDA", linha.conteudo_bruto)

    if ficha.convencao_sinal == "NEGATIVO_SAIDA":
        raw_value = _row_value(linha, ficha, "valor")
        cents = _parse_cents(raw_value or "", ficha)
    elif ficha.convencao_sinal == "COLUNA_DC":
        raw_value = _row_value(linha, ficha, "valor")
        kind = _row_value(linha, ficha, "tipo")
        cents = _parse_cents(raw_value or "", ficha, absolute=True)
        if kind == "D" and cents is not None:
            cents = -cents
        elif kind != "C":
            cents = None
    elif ficha.convencao_sinal == "COLUNAS_SEPARADAS":
        credit = _row_value(linha, ficha, "credito")
        debit = _row_value(linha, ficha, "debito")
        credit_value = (credit or "").strip()
        debit_value = (debit or "").strip()
        if bool(credit_value) == bool(debit_value):
            cents = None
        elif credit_value:
            cents = _parse_cents(credit_value, ficha, absolute=True)
        else:
            parsed_debit = _parse_cents(debit_value, ficha, absolute=True)
            cents = -parsed_debit if parsed_debit is not None else None
    else:
        cents = None

    if cents is None:
        return Recusa(linha.numero_linha, "VALOR_INVALIDO", linha.conteudo_bruto)

    normalized_description = normalizar_descricao(description)
    return Lancamento(
        data=normalized_date,
        valor_centavos=cents,
        descricao=description.strip(),
        descricao_normalizada=normalized_description,
    )


def processar(linhas: Iterable[LinhaCrua], ficha: FichaBanco) -> ResultadoLeitura:
    """Aplica RN05 por linha e RN06 quando nenhuma linha produz lançamento válido."""
    lancamentos: list[Lancamento] = []
    recusas: list[Recusa] = []
    total_linhas = 0
    for linha in linhas:
        total_linhas += 1
        resultado = normalizar(linha, ficha)
        if isinstance(resultado, Recusa):
            recusas.append(resultado)
        else:
            lancamentos.append(resultado)
    if not lancamentos:
        raise NenhumaLinhaValida()
    return ResultadoLeitura(lancamentos, recusas, total_linhas)