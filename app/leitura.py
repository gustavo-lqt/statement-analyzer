from __future__ import annotations

import csv
from io import BytesIO, TextIOWrapper
from typing import Iterator

from app.models import ArquivoVazio, EncodingInvalido, FichaBanco, LinhaCrua


class _LinhasCapturadas:
    def __init__(self, stream: TextIOWrapper) -> None:
        self.stream = stream
        self.current_record: list[str] = []

    def __iter__(self) -> _LinhasCapturadas:
        return self

    def __next__(self) -> str:
        line = next(self.stream)
        self.current_record.append(line)
        return line

    def take_record(self) -> str:
        record = "".join(self.current_record).rstrip("\r\n")
        self.current_record.clear()
        return record


def ler(conteudo: bytes, ficha: FichaBanco) -> Iterator[LinhaCrua]:
    """Aplica a ficha ao CSV e produz linhas cruas sem importar HTTP (RF01, RNF02)."""
    if not conteudo:
        raise ArquivoVazio()

    def records() -> Iterator[LinhaCrua]:
        text_stream = TextIOWrapper(
            BytesIO(conteudo), encoding=ficha.encoding, errors="strict", newline=""
        )
        source = _LinhasCapturadas(text_stream)
        reader = csv.reader(source, delimiter=ficha.delimitador, strict=True)
        try:
            header = next(reader)
        except StopIteration as error:
            raise ArquivoVazio() from error
        except UnicodeDecodeError as error:
            raise EncodingInvalido() from error
        header = [column.strip() for column in header]
        header_line_count = reader.line_num

        while True:
            start_line = header_line_count + 1
            source.current_record.clear()
            try:
                values = next(reader)
            except StopIteration:
                return
            except UnicodeDecodeError as error:
                raise EncodingInvalido() from error
            except csv.Error:
                raw = source.take_record()
                header_line_count = max(reader.line_num, header_line_count + 1)
                yield LinhaCrua(start_line, raw, {}, "LINHA_TRUNCADA")
                continue

            raw = source.take_record()
            header_line_count = reader.line_num
            if not values:
                continue

            fields: dict[str, str] = {}
            for canonical_name, column_name in ficha.colunas.items():
                try:
                    column_index = header.index(column_name)
                except ValueError:
                    continue
                if column_index < len(values):
                    fields[canonical_name] = values[column_index]

            row_error = "LINHA_TRUNCADA" if len(values) != len(header) else None
            yield LinhaCrua(start_line, raw, fields, row_error)

    return records()