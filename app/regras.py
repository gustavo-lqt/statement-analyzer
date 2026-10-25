"""U3 — motor puro de normalização e validação (RN01–RN06)."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
import re

from app.erros import NenhumaLinhaValida
from app.models import (
    ConvencaoSinal,
    FichaBanco,
    Lancamento,
    LinhaCrua,
    MotivoRecusa,
    Recusa,
    ResultadoLeitura,
)


def converter_data(texto: str, formato: str) -> date | None:
    """Aplica RN01: interpreta uma data somente no formato declarado."""
    padroes = {
        "dd/mm/aaaa": r"^(?P<dia>[0-9]{2})/(?P<mes>[0-9]{2})/(?P<ano>[0-9]{4})$",
        "aaaa-mm-dd": r"^(?P<ano>[0-9]{4})-(?P<mes>[0-9]{2})-(?P<dia>[0-9]{2})$",
        "dd-mm-aaaa": r"^(?P<dia>[0-9]{2})-(?P<mes>[0-9]{2})-(?P<ano>[0-9]{4})$",
    }
    texto = texto.strip()
    padrao = padroes.get(formato)
    if not texto or padrao is None:
        return None
    correspondencia = re.fullmatch(padrao, texto)
    if correspondencia is None:
        return None
    try:
        partes = {nome: int(valor) for nome, valor in correspondencia.groupdict().items()}
        return date(partes["ano"], partes["mes"], partes["dia"])
    except ValueError:
        return None


def converter_valor(
    texto: str,
    separador_decimal: str,
    separador_milhar: str,
) -> int | str:
    """Aplica RN02 e RN04: converte texto monetário para centavos inteiros."""
    texto = texto.strip()
    if not texto:
        return MotivoRecusa.VALOR_INVALIDO.value

    negativo = False
    if texto.startswith("(") or texto.endswith(")"):
        if not (texto.startswith("(") and texto.endswith(")")):
            return MotivoRecusa.VALOR_INVALIDO.value
        negativo = True
        texto = texto[1:-1]
    elif texto[:1] in "+-":
        negativo = texto[0] == "-"
        texto = texto[1:]

    if not texto or texto[:1] in "+-" or "(" in texto or ")" in texto:
        return MotivoRecusa.VALOR_INVALIDO.value
    if separador_milhar:
        texto = texto.replace(separador_milhar, "")

    partes = texto.split(separador_decimal)
    if len(partes) > 2:
        return MotivoRecusa.VALOR_INVALIDO.value
    inteiro = partes[0]
    decimal = partes[1] if len(partes) == 2 else ""
    if (
        not (inteiro.isascii() and inteiro.isdigit())
        or (
            len(partes) == 2
            and not (decimal.isascii() and decimal.isdigit())
        )
    ):
        return MotivoRecusa.VALOR_INVALIDO.value
    if len(decimal) >= 3:
        return MotivoRecusa.PRECISAO_INVALIDA.value

    centavos = int(inteiro) * 100
    if decimal:
        centavos += int(decimal.ljust(2, "0"))
    return -centavos if negativo else centavos


def _recusa(linha: LinhaCrua, motivo: MotivoRecusa) -> Recusa:
    return Recusa(linha=linha.numero, motivo=motivo, conteudo=linha.conteudo)


def _valor_com_sinal_explicito(texto: str) -> bool:
    texto = texto.strip()
    return texto.startswith(("-", "+", "(")) or texto.endswith(")")


def _converter_valor_da_ficha(texto: str, ficha: FichaBanco) -> int | MotivoRecusa:
    resultado = converter_valor(texto, ficha.separador_decimal, ficha.separador_milhar)
    if isinstance(resultado, str):
        return MotivoRecusa(resultado)
    return resultado


def normalizar(linha: LinhaCrua, ficha: FichaBanco) -> Lancamento | Recusa:
    """Aplica RN01–RN05: normaliza uma linha ou devolve sua recusa."""
    if linha.erro is not None:
        return _recusa(linha, linha.erro)

    campos = linha.campos
    data_convertida = converter_data(campos.get("data", ""), ficha.formato_data)
    if data_convertida is None:
        return _recusa(linha, MotivoRecusa.DATA_INVALIDA)

    if ficha.convencao_sinal is ConvencaoSinal.NEGATIVO_SAIDA:
        valor = _converter_valor_da_ficha(campos.get("valor", ""), ficha)
        if isinstance(valor, MotivoRecusa):
            return _recusa(linha, valor)
    elif ficha.convencao_sinal is ConvencaoSinal.COLUNA_DC:
        texto_valor = campos.get("valor", "")
        marcador = campos.get("dc", "").strip().upper()
        if _valor_com_sinal_explicito(texto_valor) or marcador not in {"D", "C"}:
            return _recusa(linha, MotivoRecusa.VALOR_INVALIDO)
        valor = _converter_valor_da_ficha(texto_valor, ficha)
        if isinstance(valor, MotivoRecusa):
            return _recusa(linha, valor)
        if marcador == "D":
            valor = -valor
    else:
        credito = campos.get("credito", "").strip()
        debito = campos.get("debito", "").strip()
        if bool(credito) == bool(debito):
            return _recusa(linha, MotivoRecusa.VALOR_INVALIDO)
        texto_valor = credito or debito
        if _valor_com_sinal_explicito(texto_valor):
            return _recusa(linha, MotivoRecusa.VALOR_INVALIDO)
        valor = _converter_valor_da_ficha(texto_valor, ficha)
        if isinstance(valor, MotivoRecusa):
            return _recusa(linha, valor)
        if debito:
            valor = -valor

    descricao = campos.get("descricao", "").strip()
    if not descricao:
        return _recusa(linha, MotivoRecusa.COLUNA_AUSENTE)
    return Lancamento(data=data_convertida, valor_centavos=valor, descricao=descricao)


def processar(linhas: Iterable[LinhaCrua], ficha: FichaBanco) -> ResultadoLeitura:
    """Aplica RN05 e RN06: processa o lote e recusa o arquivo sem aceitos."""
    resultado = ResultadoLeitura()
    for linha in linhas:
        normalizado = normalizar(linha, ficha)
        if isinstance(normalizado, Recusa):
            resultado.recusas.append(normalizado)
        else:
            resultado.lancamentos.append(normalizado)
    if not resultado.lancamentos:
        raise NenhumaLinhaValida("Nenhuma linha válida foi encontrada.")
    return resultado
