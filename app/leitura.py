from __future__ import annotations

import csv
from io import BytesIO
from typing import Iterator

from app.models import ArquivoVazio, EncodingInvalido, FichaBanco, LinhaCrua


class _LinhasCapturadas:
    def __init__(self, content: bytes, encoding: str) -> None:
        self.stream = content
        self.encoding = encoding
        self.current_record: list[str] = []
        self.record_has_invalid_encoding = False

    def __iter__(self) -> _LinhasCapturadas:
        return self

    def __next__(self) -> str:
        raw_line = self.stream.readline()
        if not raw_line:
            raise StopIteration
        try:
            line = raw_line.decode(self.encoding)
        except UnicodeDecodeError:
            line = raw_line.decode(self.encoding, errors="replace")
            self.record_has_invalid_encoding = True
        self.current_record.append(line)
        return line

    def take_record(self) -> tuple[str, bool]:
        record = "".join(self.current_record).rstrip("\r\n")
        has_invalid_encoding = self.record_has_invalid_encoding
        self.current_record.clear()
        self.record_has_invalid_encoding = False
        return record, has_invalid_encoding


def ler(conteudo: bytes, ficha: FichaBanco) -> Iterator[LinhaCrua]:
    """Aplica a ficha ao CSV e produz linhas cruas sem importar HTTP (RF01, RNF02)."""
    if not conteudo:
        raise ArquivoVazio()

    def records() -> Iterator[LinhaCrua]:
        source = _LinhasCapturadas(BytesIO(conteudo), ficha.encoding)
        reader = csv.reader(source, delimiter=ficha.delimitador, strict=True)
        try:
            header = next(reader)
        except StopIteration as error:
            raise ArquivoVazio() from error
        _header_raw, header_has_invalid_encoding = source.take_record()
        if header_has_invalid_encoding:
            raise EncodingInvalido()
        header = [column.strip() for column in header]
        header_line_count = reader.line_num

        while True:
            start_line = header_line_count + 1
            source.current_record.clear()
            try:
                values = next(reader)
            except StopIteration:
                return
            except csv.Error:
                raw, has_invalid_encoding = source.take_record()
                header_line_count = max(reader.line_num, header_line_count + 1)
                reason = "ENCODING_INVALIDO" if has_invalid_encoding else "LINHA_TRUNCADA"
                yield LinhaCrua(start_line, raw, {}, reason)
                continue

            raw, has_invalid_encoding = source.take_record()
            header_line_count = reader.line_num
            if has_invalid_encoding:
                yield LinhaCrua(start_line, raw, {}, "ENCODING_INVALIDO")
                continue
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