"""U2 — Leitura do CSV aplicando a ficha do banco (SPEC §7, RF01, RF07, ADR-002).

Abre as fichas de app/fichas/ e recorta cada linha do arquivo em ``LinhaCrua``. Não valida
data nem valor (isso é de app/regras.py). Não importa FastAPI nem acessa o banco (ADR-001) e
nunca registra o conteúdo das linhas em log (RNF06).
"""

from __future__ import annotations

import codecs
import csv
import io
import json
from collections.abc import Iterator
from dataclasses import fields
from pathlib import Path

from app.erros import ArquivoVazio, BancoDesconhecido, EncodingInvalido
from app.models import (
    COLUNAS_POR_CONVENCAO,
    ENCODINGS,
    FORMATOS_DATA,
    ConvencaoSinal,
    FichaBanco,
    LinhaCrua,
    MotivoRecusa,
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


def ler(conteudo: bytes, ficha: FichaBanco) -> Iterator[LinhaCrua]:
    """Recorta cada linha de dados do CSV pela ficha do banco (RF01, RN05, RNF04).

    É um gerador que decodifica uma linha por vez: ArquivoVazio e EncodingInvalido só
    aparecem quando a iteração começa. Linha ruim sai com ``erro`` preenchido e a leitura
    continua (RN05).
    """
    if conteudo.startswith(codecs.BOM_UTF8):
        conteudo = conteudo[len(codecs.BOM_UTF8):]
    linhas = _linhas_preenchidas(conteudo)
    primeira = next(linhas, None)
    if primeira is None:
        raise ArquivoVazio("O arquivo está vazio.")
    cabecalho = _decodificar_cabecalho(primeira[1], ficha)
    indices = _indices_das_colunas(cabecalho, ficha)
    sem_dados = True
    for numero, bruta in linhas:
        sem_dados = False
        yield _recortar(numero, bruta, ficha, len(cabecalho), indices)
    if sem_dados:
        raise ArquivoVazio("O arquivo não tem nenhuma linha de dados.")


def _linhas_preenchidas(conteudo: bytes) -> Iterator[tuple[int, bytes]]:
    """Linhas físicas que não estão em branco, numeradas a partir de 1, sem \\n ou \\r\\n."""
    for numero, bruta in enumerate(io.BytesIO(conteudo), start=1):
        bruta = bruta.removesuffix(b"\n").removesuffix(b"\r")
        if bruta.strip():
            yield numero, bruta


def _decodificar_cabecalho(bruta: bytes, ficha: FichaBanco) -> list[str]:
    try:
        texto = bruta.decode(ficha.encoding)
    except UnicodeDecodeError:
        raise EncodingInvalido(f"O cabeçalho do arquivo não está em {ficha.encoding}.") from None
    # Cabeçalho que o csv não separa não tem as colunas da ficha: as linhas saem COLUNA_AUSENTE.
    return _celulas(texto, ficha.delimitador) or []


def _indices_das_colunas(cabecalho: list[str], ficha: FichaBanco) -> dict[str, int] | None:
    """Posição de cada chave lógica no cabeçalho, ou None se falta alguma coluna da ficha."""
    if any(nome not in cabecalho for nome in ficha.colunas.values()):
        return None
    return {chave: cabecalho.index(nome) for chave, nome in ficha.colunas.items()}


def _recortar(
    numero: int,
    bruta: bytes,
    ficha: FichaBanco,
    total_celulas: int,
    indices: dict[str, int] | None,
) -> LinhaCrua:
    """Decodifica a linha e recorta as células; a primeira falha define o erro (RN05)."""
    try:
        texto = bruta.decode(ficha.encoding)
    except UnicodeDecodeError:
        texto = bruta.decode(ficha.encoding, errors="replace")
        return LinhaCrua(numero, {}, texto, MotivoRecusa.ENCODING_INVALIDO)
    if indices is None:
        return LinhaCrua(numero, {}, texto, MotivoRecusa.COLUNA_AUSENTE)
    celulas = _celulas(texto, ficha.delimitador)
    if celulas is None or len(celulas) != total_celulas:
        return LinhaCrua(numero, {}, texto, MotivoRecusa.LINHA_TRUNCADA)
    return LinhaCrua(numero, {chave: celulas[i] for chave, i in indices.items()}, texto)


def _celulas(texto: str, delimitador: str) -> list[str] | None:
    """Separa as células com o módulo csv, respeitando aspas duplas.

    Devolve None quando o csv não consegue separar a linha, como num \\r solto fora de aspas:
    é uma quebra de linha corrompida, e a linha é recusada sem derrubar a leitura (RN05,
    SPEC §8 v1.3).
    """
    try:
        return next(csv.reader([texto], delimiter=delimitador))
    except csv.Error:
        return None


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
