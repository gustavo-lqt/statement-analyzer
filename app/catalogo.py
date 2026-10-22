from __future__ import annotations

import json
from pathlib import Path

from app.models import FichaBanco


_FORMATS = {"dd/mm/aaaa", "aaaa-mm-dd", "dd-mm-aaaa"}
_ENCODINGS = {"utf-8", "latin-1"}
_SIGN_CONVENTIONS = {"NEGATIVO_SAIDA", "COLUNA_DC", "COLUNAS_SEPARADAS"}


def _parse_ficha(path: Path) -> FichaBanco:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "nome",
        "delimitador",
        "encoding",
        "formato_data",
        "separador_decimal",
        "separador_milhar",
        "convencao_sinal",
        "colunas",
    }
    if not isinstance(data, dict) or required - data.keys():
        raise ValueError(f"Ficha inválida: {path.name}")
    if data["formato_data"] not in _FORMATS:
        raise ValueError(f"Formato de data inválido na ficha {path.name}")
    if data["encoding"] not in _ENCODINGS:
        raise ValueError(f"Encoding inválido na ficha {path.name}")
    if data["convencao_sinal"] not in _SIGN_CONVENTIONS:
        raise ValueError(f"Convenção de sinal inválida na ficha {path.name}")
    if not isinstance(data["colunas"], dict):
        raise ValueError(f"Colunas inválidas na ficha {path.name}")

    convention_columns = {
        "NEGATIVO_SAIDA": {"valor"},
        "COLUNA_DC": {"valor", "tipo"},
        "COLUNAS_SEPARADAS": {"credito", "debito"},
    }[data["convencao_sinal"]]
    required_columns = {"data", "descricao"} | convention_columns
    if not required_columns <= data["colunas"].keys():
        raise ValueError(f"Colunas obrigatórias ausentes na ficha {path.name}")

    return FichaBanco(
        nome=data["nome"],
        delimitador=data["delimitador"],
        encoding=data["encoding"],
        formato_data=data["formato_data"],
        separador_decimal=data["separador_decimal"],
        separador_milhar=data["separador_milhar"],
        convencao_sinal=data["convencao_sinal"],
        colunas=data["colunas"],
    )


def carregar_fichas(directory: Path | None = None) -> dict[str, FichaBanco]:
    ficha_directory = directory or Path(__file__).parent / "fichas"
    paths = sorted(ficha_directory.glob("*.json"))
    loaded = [_parse_ficha(path) for path in paths]
    fichas = {ficha.nome: ficha for ficha in loaded}
    if len(fichas) != len(loaded):
        raise ValueError("Há nomes de ficha duplicados.")
    return fichas