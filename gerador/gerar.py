"""U7 — Gerador de extratos CSV inventados, no formato exato de cada ficha (Issue #4).

    python -m gerador.gerar --banco banco-a --linhas 300 --semente 42 --invalidas 5 \\
        --saida dados/extrato-banco-a.csv

Tudo sai de um único ``random.Random(semente)``: a mesma semente gera os mesmos bytes
(RNF05). Os valores são ``int`` em centavos e só viram texto na formatação, sem ``float``
(RN02). Nenhum dado bancário real: as descrições vêm de uma lista fixa e fictícia.
"""

from __future__ import annotations

import argparse
import csv
import io
import random
from dataclasses import dataclass
from pathlib import Path

from app.leitura import carregar_ficha, listar_fichas
from app.models import COLUNAS_POR_CONVENCAO, ConvencaoSinal, FichaBanco, MotivoRecusa

ANO = 2026
MES = 9
DIAS_NO_MES = 30
DIA_INEXISTENTE = 31  # 31 de setembro: casa com o formato da ficha, mas não existe (RN01)


@dataclass(frozen=True)
class _Modelo:
    """Um tipo de lançamento inventado; o valor é sorteado entre minimo e maximo centavos."""

    descricao: str
    minimo: int
    maximo: int
    entrada: bool
    peso: int


# IFD*IFOOD, PADARIA PÃO QUENTE e STREAMING FILMES variam no máximo ~5% em torno da média e
# aparecem com frequência: são os gastos repetidos que a consulta repetidos (RN09) encontra.
_MODELOS = (
    _Modelo("SALARIO", 480000, 620000, entrada=True, peso=2),
    _Modelo("TRANSF PIX RECEBIDA", 2000, 80000, entrada=True, peso=6),
    _Modelo("ESTORNO COMPRA", 500, 15000, entrada=True, peso=2),
    _Modelo("PAG*MERC CENTRAL", 1500, 45000, entrada=False, peso=14),
    _Modelo("IFD*IFOOD", 4000, 4400, entrada=False, peso=12),
    _Modelo("PADARIA PÃO QUENTE", 800, 880, entrada=False, peso=10),
    _Modelo("STREAMING FILMES", 3990, 3990, entrada=False, peso=4),
    _Modelo("TRANSF PIX ENVIADA", 1000, 150000, entrada=False, peso=10),
    _Modelo("APP TRANSPORTE", 1200, 3500, entrada=False, peso=8),
    _Modelo("POSTO ESTRELA", 8000, 25000, entrada=False, peso=5),
    _Modelo("CONTA ENERGIA", 12000, 22000, entrada=False, peso=2),
    _Modelo("TARIFA PACOTE SERVICOS", 3450, 3450, entrada=False, peso=2),
)
# Sorteio ponderado só com inteiros: cada modelo aparece ``peso`` vezes.
_SORTEIO = tuple(modelo for modelo in _MODELOS for _ in range(modelo.peso))
_DEFEITOS = (
    MotivoRecusa.DATA_INVALIDA,
    MotivoRecusa.PRECISAO_INVALIDA,
    MotivoRecusa.LINHA_TRUNCADA,
)


@dataclass(frozen=True)
class ExtratoGerado:
    """CSV gerado e o defeito injetado em cada linha física (cabeçalho = 1).

    O valor de ``defeitos`` é o motivo de recusa que a linha deve causar.
    """

    conteudo: bytes
    defeitos: dict[int, MotivoRecusa]


def gerar_csv(ficha: FichaBanco, linhas: int, semente: int, invalidas: int = 0) -> bytes:
    """CSV inventado no formato exato da ficha; a mesma semente gera os mesmos bytes (RNF05)."""
    return gerar_extrato(ficha, linhas, semente, invalidas).conteudo


def gerar_extrato(
    ficha: FichaBanco, linhas: int, semente: int, invalidas: int = 0
) -> ExtratoGerado:
    """Gera o CSV e registra em que linhas foi injetado cada defeito (RNF05, RN05).

    Datas de setembro de 2026 em ordem crescente; valores em centavos (RN02). Depois de sortear
    os lançamentos, sorteia ``invalidas`` posições e um defeito para cada uma: data inexistente
    (RN01), valor com três casas decimais (RN04) ou linha truncada.
    """
    if linhas < 0 or not 0 <= invalidas <= linhas:
        raise ValueError("Use linhas >= 0 e invalidas entre 0 e linhas.")
    rng = random.Random(semente)
    dias = sorted(rng.randint(1, DIAS_NO_MES) for _ in range(linhas))
    lancamentos = []
    for dia in dias:
        modelo = rng.choice(_SORTEIO)
        lancamentos.append((dia, modelo, rng.randint(modelo.minimo, modelo.maximo)))
    defeitos = {i: rng.choice(_DEFEITOS) for i in sorted(rng.sample(range(linhas), invalidas))}

    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=ficha.delimitador, lineterminator="\r\n")
    chaves = COLUNAS_POR_CONVENCAO[ficha.convencao_sinal]
    escritor.writerow([ficha.colunas[chave] for chave in chaves])
    for i, (dia, modelo, centavos) in enumerate(lancamentos):
        defeito = defeitos.get(i)
        if defeito is MotivoRecusa.DATA_INVALIDA:
            dia = DIA_INEXISTENTE
        if defeito is MotivoRecusa.PRECISAO_INVALIDA:
            numero = _formatar_numero(centavos * 10 + rng.randrange(10), 3, ficha)
        else:
            numero = _formatar_numero(centavos, 2, ficha)
        campos = {
            "data": _formatar_data(dia, ficha.formato_data),
            "descricao": modelo.descricao,
            **_campos_de_valor(numero, modelo.entrada, ficha.convencao_sinal),
        }
        celulas = [campos[chave] for chave in chaves]
        if defeito is MotivoRecusa.LINHA_TRUNCADA:
            celulas.pop()
        escritor.writerow(celulas)

    return ExtratoGerado(
        conteudo=saida.getvalue().encode(ficha.encoding),
        defeitos={i + 2: defeito for i, defeito in defeitos.items()},
    )


def _formatar_data(dia: int, formato: str) -> str:
    """Dia de setembro de 2026 no formato da ficha, montado como texto para aceitar o dia 31."""
    return formato.replace("dd", f"{dia:02d}").replace("mm", f"{MES:02d}").replace("aaaa", str(ANO))


def _formatar_numero(quantidade: int, casas: int, ficha: FichaBanco) -> str:
    """Número sem sinal com ``casas`` decimais e os separadores da ficha, só com inteiros."""
    inteiro, fracao = divmod(quantidade, 10**casas)
    milhar = f"{inteiro:,}".replace(",", ficha.separador_milhar)
    return f"{milhar}{ficha.separador_decimal}{fracao:0{casas}d}"


def _campos_de_valor(numero: str, entrada: bool, convencao: ConvencaoSinal) -> dict[str, str]:
    """Escreve o valor na convenção de sinal da ficha (RN03)."""
    if convencao is ConvencaoSinal.NEGATIVO_SAIDA:
        return {"valor": numero if entrada else f"-{numero}"}
    if convencao is ConvencaoSinal.COLUNA_DC:
        return {"valor": numero, "dc": "C" if entrada else "D"}
    return {"credito": numero if entrada else "", "debito": "" if entrada else numero}


def main(argv: list[str] | None = None) -> int:
    """CLI: grava em --saida um extrato inventado no formato da ficha --banco (Issue #4).

    Imprime só a contagem e o caminho, nunca o conteúdo das linhas (RNF06).
    """
    parser = argparse.ArgumentParser(
        prog="python -m gerador.gerar",
        description="Gera um extrato CSV inventado no formato da ficha do banco.",
    )
    parser.add_argument("--banco", required=True, choices=listar_fichas(), help="ficha em app/fichas")
    parser.add_argument("--linhas", required=True, type=int, help="quantidade de lançamentos")
    parser.add_argument("--semente", required=True, type=int, help="mesma semente, mesmos bytes")
    parser.add_argument("--invalidas", type=int, default=0, help="linhas com defeito (padrão: 0)")
    parser.add_argument("--saida", required=True, type=Path, help="arquivo CSV a gravar")
    args = parser.parse_args(argv)
    try:
        conteudo = gerar_csv(carregar_ficha(args.banco), args.linhas, args.semente, args.invalidas)
    except ValueError as erro:
        parser.error(str(erro))
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_bytes(conteudo)
    print(f"{args.linhas} linhas ({args.invalidas} inválidas) gravadas em {args.saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
