"""U1 — Entidades do domínio (SPEC §6.2 e §7). CONTRATO CONGELADO da Entrega 2 (ver docs/SPEC.md §8).

- Dinheiro é sempre ``int`` em centavos (RN02). Nunca ``float``.
- Datas em memória são ``datetime.date``; viram ``"AAAA-MM-DD"`` só na borda (db e JSON).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum


class MotivoRecusa(StrEnum):
    """Motivos de recusa de linha (SPEC §4)."""

    DATA_INVALIDA = "DATA_INVALIDA"
    VALOR_INVALIDO = "VALOR_INVALIDO"
    PRECISAO_INVALIDA = "PRECISAO_INVALIDA"
    COLUNA_AUSENTE = "COLUNA_AUSENTE"
    LINHA_TRUNCADA = "LINHA_TRUNCADA"
    ENCODING_INVALIDO = "ENCODING_INVALIDO"


class ConvencaoSinal(StrEnum):
    """Como o banco indica saída e entrada (SPEC §6.1, RN03)."""

    NEGATIVO_SAIDA = "NEGATIVO_SAIDA"
    COLUNA_DC = "COLUNA_DC"
    COLUNAS_SEPARADAS = "COLUNAS_SEPARADAS"


# Chaves lógicas obrigatórias em FichaBanco.colunas para cada convenção de sinal.
# O valor de cada chave na ficha é o nome da coluna no cabeçalho do CSV do banco.
COLUNAS_POR_CONVENCAO: dict[ConvencaoSinal, tuple[str, ...]] = {
    ConvencaoSinal.NEGATIVO_SAIDA: ("data", "descricao", "valor"),
    ConvencaoSinal.COLUNA_DC: ("data", "descricao", "valor", "dc"),
    ConvencaoSinal.COLUNAS_SEPARADAS: ("data", "descricao", "credito", "debito"),
}

FORMATOS_DATA: tuple[str, ...] = ("dd/mm/aaaa", "aaaa-mm-dd", "dd-mm-aaaa")
ENCODINGS: tuple[str, ...] = ("utf-8", "latin-1")


@dataclass(frozen=True)
class FichaBanco:
    """Formato de exportação de um banco (SPEC §6.1). separador_milhar pode ser ""."""

    nome: str
    delimitador: str
    encoding: str
    formato_data: str
    separador_decimal: str
    separador_milhar: str
    convencao_sinal: ConvencaoSinal
    colunas: dict[str, str]


@dataclass(frozen=True)
class LinhaCrua:
    """Linha de dados do CSV recortada pela ficha, ainda sem validação.

    numero: linha física no arquivo, a partir de 1 (cabeçalho = 1). Linhas em branco são
        puladas mas contam.
    campos: chave lógica ("data", "descricao", "valor", "dc", "credito", "debito") → texto
        cru da célula, sem strip. Vazio quando há erro.
    conteudo: texto bruto da linha, sem a quebra de linha.
    erro: preenchido pela leitura quando a linha nem pôde ser recortada.
    """

    numero: int
    campos: dict[str, str]
    conteudo: str
    erro: MotivoRecusa | None = None


@dataclass(frozen=True)
class Lancamento:
    """Modelo canônico (SPEC §6.2). Saída negativa, entrada positiva (RN03).

    id e extrato_id ficam None até o lançamento ser persistido.
    """

    data: date
    valor_centavos: int
    descricao: str
    id: int | None = None
    extrato_id: int | None = None


@dataclass(frozen=True)
class Recusa:
    """Linha recusada (RN05)."""

    linha: int
    motivo: MotivoRecusa
    conteudo: str


@dataclass
class ResultadoLeitura:
    """Saída de regras.processar: aceitos e recusas, na ordem do arquivo."""

    lancamentos: list[Lancamento] = field(default_factory=list)
    recusas: list[Recusa] = field(default_factory=list)

    @property
    def aceitos(self) -> int:
        return len(self.lancamentos)

    @property
    def rejeitados(self) -> int:
        return len(self.recusas)

    @property
    def total_linhas(self) -> int:
        return self.aceitos + self.rejeitados


@dataclass(frozen=True)
class Extrato:
    """Arquivo enviado e persistido. saldo_inicial_centavos é None quando não informado (D3)."""

    id: int
    nome_arquivo: str
    banco: str
    criado_em: str  # ISO 8601 com fuso, ex.: "2026-09-11T14:32:00-03:00"
    saldo_inicial_centavos: int | None
    total_linhas: int
    aceitos: int
    rejeitados: int


# Resultados das consultas (SPEC §6.5). A API converte para JSON com os mesmos nomes.

@dataclass(frozen=True)
class Periodo:
    de: date
    ate: date


@dataclass(frozen=True)
class Resumo:
    periodo: Periodo | None
    total_lancamentos: int
    entradas_centavos: int
    saidas_centavos: int
    saldo_centavos: int
    media_diaria_gasto_centavos: int


@dataclass(frozen=True)
class Saldo:
    saldo_inicial_centavos: int
    saldo_final_centavos: int
    ficou_negativo: bool
    saldo_minimo_centavos: int
    data_saldo_minimo: date | None


@dataclass(frozen=True)
class Semana:
    de: date
    ate: date
    entradas_centavos: int
    saidas_centavos: int
    saldo_centavos: int


@dataclass(frozen=True)
class PeriodoNegativo:
    de: date
    ate: date
    saldo_minimo_centavos: int


@dataclass(frozen=True)
class DiasNoNegativo:
    saldo_inicial_centavos: int
    saldo_inicial_assumido: bool
    dias_no_negativo: int
    periodos: list[PeriodoNegativo]


@dataclass(frozen=True)
class GrupoRepetido:
    descricao_normalizada: str
    ocorrencias: int
    valor_medio_centavos: int
    total_centavos: int
    datas: list[date]
