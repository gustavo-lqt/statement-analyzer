"""U2 — Leitura do CSV aplicando a ficha do banco (SPEC §7, RF01, RF07, ADR-002).

Abre as fichas de app/fichas/ e recorta cada linha do arquivo em ``LinhaCrua``. Não valida
data nem valor (isso é de app/regras.py). Não importa FastAPI nem acessa o banco (ADR-001) e
nunca registra o conteúdo das linhas em log (RNF06).
"""

from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

from app.erros import BancoDesconhecido
from app.models import (
    COLUNAS_POR_CONVENCAO,
    ENCODINGS,
    FORMATOS_DATA,
    ConvencaoSinal,
    FichaBanco,
)

PASTA_FICHAS = Path(__file__).parent / "fichas"

_CAMPOS_FICHA = tuple(campo.name for campo in fields(FichaBanco))


def carregar_ficha(nome: str) -> FichaBanco:
    """Lê app/fichas/<nome>.json, em UTF-8, e devolve a ficha do banco (RF07, ADR-002).

    Levanta BancoDesconhecido se a ficha não está registrada ou se o nome tem "/", "\\" ou
    "..". Levanta ValueError se a ficha está malformada: é erro de quem escreveu a ficha.
    """
    if "/" in nome or "\\" in nome or ".." in nome or nome not in listar_fichas():
        raise BancoDesconhecido(f"A ficha '{nome}' não está registrada.")
    caminho = PASTA_FICHAS / f"{nome}.json"
    return _montar_ficha(json.loads(caminho.read_text(encoding="utf-8")), caminho.name)


def listar_fichas() -> list[str]:
    """Nomes das fichas registradas em app/fichas, em ordem alfabética (RF07)."""
    return sorted(caminho.stem for caminho in PASTA_FICHAS.glob("*.json"))


def _montar_ficha(dados: object, origem: str) -> FichaBanco:
    """Valida o JSON da ficha contra o vocabulário de app/models.py (SPEC §6.1)."""
    if not isinstance(dados, dict):
        raise ValueError(f"Ficha {origem}: o conteúdo precisa ser um objeto JSON.")
    faltando = [campo for campo in _CAMPOS_FICHA if campo not in dados]
    if faltando:
        raise ValueError(f"Ficha {origem}: faltam os campos {', '.join(faltando)}.")
    if dados["formato_data"] not in FORMATOS_DATA:
        raise ValueError(f"Ficha {origem}: formato_data deve ser um de {FORMATOS_DATA}.")
    if dados["encoding"] not in ENCODINGS:
        raise ValueError(f"Ficha {origem}: encoding deve ser um de {ENCODINGS}.")
    try:
        convencao = ConvencaoSinal(dados["convencao_sinal"])
    except ValueError:
        raise ValueError(f"Ficha {origem}: convencao_sinal desconhecida.") from None
    colunas = dados["colunas"]
    if not isinstance(colunas, dict):
        raise ValueError(f"Ficha {origem}: colunas precisa ser um objeto JSON.")
    faltando = [chave for chave in COLUNAS_POR_CONVENCAO[convencao] if chave not in colunas]
    if faltando:
        raise ValueError(f"Ficha {origem}: colunas sem as chaves {', '.join(faltando)}.")
    valores = {campo: dados[campo] for campo in _CAMPOS_FICHA}
    return FichaBanco(**{**valores, "convencao_sinal": convencao, "colunas": dict(colunas)})
