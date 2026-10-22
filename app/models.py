from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class FichaBanco:
    nome: str
    delimitador: str
    encoding: str
    formato_data: str
    separador_decimal: str
    separador_milhar: str | None
    convencao_sinal: str
    colunas: dict[str, str]


@dataclass(frozen=True, slots=True)
class LinhaCrua:
    numero_linha: int
    conteudo_bruto: str
    campos: dict[str, str]
    motivo_recusa: str | None = None


@dataclass(frozen=True, slots=True)
class Lancamento:
    data: str
    valor_centavos: int
    descricao: str
    descricao_normalizada: str
    id: int | None = None
    extrato_id: int | None = None


@dataclass(frozen=True, slots=True)
class Recusa:
    numero_linha: int
    motivo: str
    conteudo_bruto: str


@dataclass(frozen=True, slots=True)
class ResultadoLeitura:
    lancamentos: list[Lancamento]
    recusas: list[Recusa]
    total_linhas: int


@dataclass(frozen=True, slots=True)
class Extrato:
    id: int
    nome_arquivo: str
    banco: str
    criado_em: str
    saldo_inicial_centavos: int
    saldo_inicial_assumido: bool
    total_linhas: int
    aceitos: int
    rejeitados: int
    lancamentos: list[Lancamento]
    recusas: list[Recusa]


@dataclass(frozen=True, slots=True)
class Resumo:
    extrato_id: int | None
    periodo_de: str | None
    periodo_ate: str | None
    total_lancamentos: int
    entradas_centavos: int
    saidas_centavos: int
    saldo_centavos: int
    media_diaria_gasto_centavos: int


@dataclass(frozen=True, slots=True)
class Saldo:
    saldo_inicial_centavos: int
    saldo_final_centavos: int
    ficou_negativo: bool
    saldo_minimo_centavos: int
    data_saldo_minimo: str | None


@dataclass(frozen=True, slots=True)
class Semana:
    de: str
    ate: str
    entradas_centavos: int
    saidas_centavos: int
    saldo_centavos: int


@dataclass(frozen=True, slots=True)
class PeriodoNegativo:
    de: str
    ate: str
    saldo_minimo_centavos: int


@dataclass(frozen=True, slots=True)
class DiasNoNegativo:
    saldo_inicial_centavos: int
    saldo_inicial_assumido: bool
    dias_no_negativo: int
    periodos: list[PeriodoNegativo]


@dataclass(frozen=True, slots=True)
class GrupoRepetido:
    descricao_normalizada: str
    ocorrencias: int
    valor_medio_centavos: int
    total_centavos: int
    datas: list[str]


class ErroDominio(Exception):
    def __init__(self, codigo: str, mensagem: str, regra: str | None = None) -> None:
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem
        self.regra = regra


class ArquivoVazio(ErroDominio):
    def __init__(self) -> None:
        super().__init__("ARQUIVO_VAZIO", "O arquivo enviado está vazio.")


class EncodingInvalido(ErroDominio):
    def __init__(self) -> None:
        super().__init__("ENCODING_INVALIDO", "O arquivo não corresponde ao encoding da ficha.")


class NenhumaLinhaValida(ErroDominio):
    def __init__(self) -> None:
        super().__init__(
            "NENHUMA_LINHA_VALIDA",
            "Nenhuma linha válida foi encontrada; o extrato não foi criado.",
            "RN06",
        )


class RecursoNaoEncontrado(ErroDominio):
    def __init__(self) -> None:
        super().__init__("EXTRATO_NAO_ENCONTRADO", "O extrato solicitado não foi encontrado.")


class ParametroInvalido(ErroDominio):
    def __init__(self, mensagem: str) -> None:
        super().__init__("PARAMETRO_INVALIDO", mensagem)


JsonObject = dict[str, Any]