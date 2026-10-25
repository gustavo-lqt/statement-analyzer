# Contrato da Entrega 2

Este documento detalha a SPEC até o nível de código, para que cinco pessoas implementem
partes diferentes ao mesmo tempo e tudo se encaixe no merge. **Vale tanto quanto a
`docs/SPEC.md`.** Onde a SPEC é ambígua, a decisão está aqui e é registrada na SPEC §8 pelo
Gustavo no passo 0.

- **Parte A** — arquivos da base compartilhada. O Gustavo cria esses arquivos no passo 0,
  copiando o conteúdo daqui, e depois eles ficam congelados.
- **Parte B** — interface pública de cada módulo. Cada dono copia o esqueleto do seu módulo
  como ponto de partida e implementa os corpos. **Os nomes, parâmetros e tipos de retorno
  não mudam.**

---

## Decisões que fecham as ambiguidades da SPEC

| # | Decisão | Onde estava a dúvida |
|:---:|---|---|
| D1 | Os três bancos são as fichas sintéticas `banco-a`, `banco-b` e `banco-c` (abaixo). Juntas, elas cobrem as três convenções de sinal, os três formatos de data e os dois encodings. | SPEC §9 — "quais três bancos" |
| D2 | A semana de `por-semana` vai de **segunda a domingo**. Semanas parciais nas pontas entram, recortadas ao período do extrato. | SPEC §9 |
| D3 | O saldo inicial continua opcional. Quando não é informado, é gravado como `NULL` (a coluna perde o `NOT NULL DEFAULT 0`). As consultas usam 0 nesse caso, e `dias-no-negativo` devolve `saldo_inicial_assumido: true`. | Sem isso não dá para saber depois se o saldo foi "assumido" (RN07) |
| D4 | A tolerância de 10% da RN09 continua, com o algoritmo exato descrito em `repetidos`. | SPEC §9 |
| D5 | `maior-entrada` e `maior-despesa` sem nenhum lançamento do tipo pedido devolvem `200` com corpo `null`. | SPEC não dizia |
| D6 | `GET /extratos/{id}` pagina com `limite` (padrão 100, de 1 a 1000) e `offset` (padrão 0). | SPEC dizia só "paginados" |
| D7 | As oito consultas entram já na Entrega 2: as funções são puras e baratas, e isso adianta a Entrega 3. | — |

---

# Parte A — Base compartilhada (passo 0 do Gustavo)

### `app/__init__.py`

```python
"""Statement Analyzer — ver docs/SPEC.md."""
```

### `app/models.py`

```python
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
```

### `app/erros.py`

```python
"""Exceções de domínio. CONTRATO CONGELADO da Entrega 2 (ver docs/SPEC.md §8).

Não conhecem HTTP (ADR-001): carregam só o código do erro (SPEC §6.6) e a RN violada.
Quem decide o status HTTP é app/api.py.
"""

from __future__ import annotations


class ErroDominio(Exception):
    codigo: str = "ERRO_DOMINIO"
    regra: str | None = None

    def __init__(self, mensagem: str) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem


class ArquivoVazio(ErroDominio):
    codigo = "ARQUIVO_VAZIO"


class EncodingInvalido(ErroDominio):
    codigo = "ENCODING_INVALIDO"


class NenhumaLinhaValida(ErroDominio):
    codigo = "NENHUMA_LINHA_VALIDA"
    regra = "RN06"


class BancoDesconhecido(ErroDominio):
    codigo = "BANCO_DESCONHECIDO"


class ExtratoNaoEncontrado(ErroDominio):
    codigo = "EXTRATO_NAO_ENCONTRADO"


class ParametroInvalido(ErroDominio):
    codigo = "PARAMETRO_INVALIDO"
```

### `app/fichas/banco-a.json` (salvar em UTF-8)

```json
{
  "nome": "banco-a",
  "delimitador": ";",
  "encoding": "latin-1",
  "formato_data": "dd/mm/aaaa",
  "separador_decimal": ",",
  "separador_milhar": ".",
  "convencao_sinal": "NEGATIVO_SAIDA",
  "colunas": { "data": "Data", "descricao": "Histórico", "valor": "Valor" }
}
```

### `app/fichas/banco-b.json`

```json
{
  "nome": "banco-b",
  "delimitador": ",",
  "encoding": "utf-8",
  "formato_data": "aaaa-mm-dd",
  "separador_decimal": ".",
  "separador_milhar": "",
  "convencao_sinal": "COLUNA_DC",
  "colunas": { "data": "date", "descricao": "description", "valor": "amount", "dc": "type" }
}
```

### `app/fichas/banco-c.json`

```json
{
  "nome": "banco-c",
  "delimitador": ";",
  "encoding": "utf-8",
  "formato_data": "dd-mm-aaaa",
  "separador_decimal": ",",
  "separador_milhar": ".",
  "convencao_sinal": "COLUNAS_SEPARADAS",
  "colunas": { "data": "Data Lançamento", "descricao": "Descrição",
               "credito": "Crédito", "debito": "Débito" }
}
```

Exemplos de arquivo (para os testes):

```text
banco-a (latin-1)                 banco-b (utf-8)                     banco-c (utf-8)
Data;Histórico;Valor              date,description,amount,type        Data Lançamento;Descrição;Crédito;Débito
01/09/2026;SALARIO;5.800,00       2026-09-01,SALARIO,5800.00,C        01-09-2026;SALARIO;5.800,00;
03/09/2026;PAG*MERC CENTRAL;-92,40 2026-09-03,PAG*MERC CENTRAL,92.40,D 03-09-2026;PAG*MERC CENTRAL;;92,40
```

### `requirements.txt`

```text
fastapi==0.115.6
uvicorn==0.34.0
python-multipart==0.0.20
httpx==0.28.1
pytest==8.3.4
pytest-cov==6.0.0
```

### `pytest.ini`

```ini
[pytest]
testpaths = tests
pythonpath = .
addopts = -ra
```

### `tests/conftest.py`

```python
"""Fixtures compartilhadas. Congelado na Entrega 2: cada integrante declara as próprias
fixtures dentro do seu arquivo de teste, para não haver conflito de merge."""
```

---

# Parte B — Interface de cada módulo

## `app/leitura.py` — dono: Diego

Proibido importar FastAPI ou acessar o banco.

```python
from collections.abc import Iterator
from pathlib import Path
from app.models import FichaBanco, LinhaCrua

PASTA_FICHAS = Path(__file__).parent / "fichas"

def carregar_ficha(nome: str) -> FichaBanco: ...
def listar_fichas() -> list[str]: ...
def ler(conteudo: bytes, ficha: FichaBanco) -> Iterator[LinhaCrua]: ...
```

**`carregar_ficha(nome)`**
- Lê `app/fichas/<nome>.json` (em UTF-8) e devolve a `FichaBanco` com `convencao_sinal`
  convertido para `ConvencaoSinal`.
- Arquivo inexistente → `BancoDesconhecido`. Um `nome` com `/`, `\` ou `..` também gera
  `BancoDesconhecido`, para não sair da pasta de fichas.
- Ficha malformada levanta `ValueError`, porque é erro de quem escreveu a ficha. Casos:
  falta um campo, `formato_data` está fora de `FORMATOS_DATA`, `encoding` está fora de
  `ENCODINGS`, a convenção é desconhecida, ou `colunas` não tem as chaves de
  `COLUNAS_POR_CONVENCAO`.

**`listar_fichas()`** → `["banco-a", "banco-b", "banco-c"]`, em ordem alfabética.

**`ler(conteudo, ficha)`** é um **gerador**, então as exceções só aparecem quando a
iteração começa.
1. A quebra de linha pode ser `\n` ou `\r\n`. Linhas em branco (só espaços) são puladas, mas
   continuam contando no `numero`.
2. A primeira linha não vazia é o cabeçalho. O BOM UTF-8 no início é descartado.
   - Arquivo sem bytes, só com linhas em branco ou só com o cabeçalho → `ArquivoVazio`.
   - Cabeçalho que não decodifica com `ficha.encoding` → `EncodingInvalido`.
3. Cada linha é decodificada **individualmente**. Se a decodificação falhar, a linha sai com
   `erro=ENCODING_INVALIDO`, `campos={}` e `conteudo` decodificado com `errors="replace"`, e
   a leitura continua (RN05).
4. As células são separadas com o módulo `csv`, usando `ficha.delimitador` e respeitando as
   aspas duplas padrão.
5. Linha com número de células diferente do cabeçalho → `erro=LINHA_TRUNCADA`.
6. Se o cabeçalho não tiver alguma coluna de `ficha.colunas`, toda linha de dados sai com
   `erro=COLUNA_AUSENTE`. Colunas extras no cabeçalho são ignoradas.
7. Linha válida: `campos` tem uma entrada para cada chave lógica de `ficha.colunas`, com o
   texto cru da célula (sem `strip`).
- `conteudo` é sempre a linha original decodificada, sem o `\r\n`. **Nunca logar
  `conteudo` (RNF06).**

## `gerador/` — dono: Diego

```python
# gerador/__init__.py  (vazio)
# gerador/gerar.py
def gerar_csv(ficha: FichaBanco, linhas: int, semente: int, invalidas: int = 0) -> bytes: ...
def main(argv: list[str] | None = None) -> int: ...   # CLI
```

- `python -m gerador.gerar --banco banco-a --linhas 300 --semente 42 --invalidas 5 --saida dados/extrato-banco-a.csv`
- Gera um CSV **inventado** no formato exato da ficha (cabeçalho, delimitador, encoding,
  formato de data, separadores, convenção de sinal). Usa `random.Random(semente)`: **a mesma
  semente gera os mesmos bytes**.
- As datas ficam dentro de um único mês (setembro de 2026) e saem em ordem crescente.
- As descrições vêm de uma lista fixa e fictícia (ex.: `SALARIO`, `PAG*MERC CENTRAL`,
  `IFD*IFOOD`, `TRANSF PIX ENVIADA`, `STREAMING FILMES`). A lista inclui gastos que se
  repetem três ou mais vezes com valores parecidos, para a consulta `repetidos` ter o que
  mostrar.
- `invalidas` linhas recebem um defeito escolhido pela semente: data inexistente, valor com
  três casas ou linha truncada. As posições dessas linhas também são escolhidas pela semente.
- Os valores são gerados como `int` em centavos e só formatados como texto na saída.
  **Nenhum `float`.**

## `app/regras.py` — dono: Felipe

Proibido importar FastAPI, fazer I/O ou acessar o banco.

```python
from collections.abc import Iterable
from datetime import date
from app.models import FichaBanco, Lancamento, LinhaCrua, Recusa, ResultadoLeitura

def converter_data(texto: str, formato: str) -> date | None: ...
def converter_valor(texto: str, separador_decimal: str, separador_milhar: str) -> int | str: ...
def normalizar(linha: LinhaCrua, ficha: FichaBanco) -> Lancamento | Recusa: ...
def processar(linhas: Iterable[LinhaCrua], ficha: FichaBanco) -> ResultadoLeitura: ...
```

**`converter_data` (RN01)**
- Interpreta o texto exatamente no formato da ficha. Dia e mês com **dois dígitos**, ano
  com quatro: `1/9/2026` não casa com `dd/mm/aaaa`.
- Espaços nas pontas são ignorados.
- Devolve `None` quando:
  - o texto está vazio;
  - não casa com o formato;
  - a data não existe (`31/02/2026`).
- Nunca tenta outro formato.

**`converter_valor` (RN02, RN04)** devolve o `int` em centavos ou o **nome do motivo**
(`"VALOR_INVALIDO"` / `"PRECISAO_INVALIDA"`). Não usa `float` em nenhum momento.
- Espaços nas pontas são ignorados. Texto vazio → `"VALOR_INVALIDO"`.
- Sinal: `-` no início, ou valor entre parênteses como `(1.234,56)`, é negativo. `+` no
  início é aceito.
- Remove todas as ocorrências de `separador_milhar` (quando não é `""`). O que sobra precisa
  ser: dígitos, opcionalmente seguidos de `separador_decimal` e mais dígitos.
- Qualquer outra coisa → `"VALOR_INVALIDO"`. Exemplos: `"R$ 10"`, `","`, `"1,"`, `",50"`,
  letras.
- Exemplos válidos:
  - `"1234"` → 123400
  - `"12,5"` → 1250
  - `"1.234,56"` → 123456
  - `"12,30"` → 1230
  - `"-92,40"` → -9240
- Três ou mais casas decimais (mesmo com zero à direita, como `"12,340"`) →
  `"PRECISAO_INVALIDA"`. **Não arredonda.**

**`normalizar` (RN01–RN05)** **nunca levanta exceção** por dado ruim: devolve `Recusa`, com
`linha=linha.numero` e `conteudo=linha.conteudo`. O primeiro problema encontrado define o
motivo, nesta ordem:
1. `linha.erro` preenchido → recusa com esse motivo.
2. A data falha → `DATA_INVALIDA`.
3. Valor, segundo a convenção de sinal (RN03: a saída sai sempre negativa). Se a conversão
   falhar, o motivo é o que `converter_valor` devolveu.
   - `NEGATIVO_SAIDA`: o valor fica com o sinal que vier.
   - `COLUNA_DC`:
     - o valor precisa vir sem sinal (negativo → `VALOR_INVALIDO`);
     - `dc` é lido sem espaços e em maiúsculas: `"D"` vira negativo e `"C"` vira positivo;
     - qualquer outro `dc` → `VALOR_INVALIDO`.
   - `COLUNAS_SEPARADAS`:
     - exatamente uma das colunas, `credito` ou `debito`, tem que estar preenchida (as duas
       vazias ou as duas preenchidas → `VALOR_INVALIDO`);
     - o valor precisa vir sem sinal (negativo → `VALOR_INVALIDO`);
     - débito vira negativo e crédito vira positivo.
4. Descrição: `campos["descricao"].strip()`. Se ficar vazia → `COLUNA_AUSENTE`.
- O lançamento aceito sai com `id=None` e `extrato_id=None`, e guarda a descrição original
  com `strip`.

**`processar` (RN05, RN06)**
- Chama `normalizar` em cada linha, mantendo a ordem do arquivo.
- Exceções vindas do iterável (`ArquivoVazio`, `EncodingInvalido`) **não são capturadas**.
- Se nenhuma linha for aceita → `NenhumaLinhaValida`.

## `app/consultas.py` — dono: Italo

Proibido importar FastAPI, fazer I/O ou acessar o banco.

```python
from collections.abc import Sequence
from app.models import DiasNoNegativo, GrupoRepetido, Lancamento, Resumo, Saldo, Semana

def normalizar_descricao(texto: str) -> str: ...
def resumo(lancamentos: Sequence[Lancamento]) -> Resumo: ...
def saldo(lancamentos: Sequence[Lancamento], saldo_inicial: int) -> Saldo: ...
def maior_entrada(lancamentos: Sequence[Lancamento]) -> Lancamento | None: ...
def maior_despesa(lancamentos: Sequence[Lancamento]) -> Lancamento | None: ...
def top_despesas(lancamentos: Sequence[Lancamento], n: int) -> list[Lancamento]: ...
def por_semana(lancamentos: Sequence[Lancamento]) -> list[Semana]: ...
def dias_no_negativo(lancamentos: Sequence[Lancamento], saldo_inicial: int | None) -> DiasNoNegativo: ...
def repetidos(lancamentos: Sequence[Lancamento]) -> list[GrupoRepetido]: ...
```

Regras gerais:
- A lista pode chegar em qualquer ordem, e o resultado não pode depender dela, a não ser
  onde estiver escrito "ordem da lista" como último desempate.
- Nenhum `float`: divisões truncam em direção a zero usando só inteiros
  (`-423410 / 30` → `-14113`).
- Entrada é `valor > 0` e saída (despesa, gasto) é `valor < 0`. Valor zero conta no total
  de lançamentos, mas não é nem entrada nem saída.
- Lista vazia nunca levanta exceção.

**`normalizar_descricao` (SPEC §4)**
- Converte para caixa alta e tira os acentos (`Ç` → `C`).
- Remove todo caractere que não é letra, dígito ou espaço.
- Colapsa espaços repetidos e aplica `strip`.
- Exemplo: `"IFD*iFood  São Paulo"` → `"IFDIFOOD SAO PAULO"`.

**`resumo` (RF08)**
- `periodo` vai da menor à maior data.
- `entradas_centavos` é a soma dos positivos; `saidas_centavos`, a soma dos negativos
  (≤ 0); `saldo_centavos` = entradas + saídas.
- `media_diaria_gasto_centavos` = saídas ÷ número de dias do período, contando as duas
  pontas (1 a 30 de setembro dá 30 dias), truncado em direção a zero.
- Lista vazia → `periodo=None` e todos os números iguais a 0.

**`saldo` (RF09, RN08)**
- O saldo corrente é calculado por data crescente. Lançamentos da mesma data formam um
  bloco, e só o saldo **ao fim do dia** conta.
- `saldo_final_centavos` = saldo inicial + a soma de todos os valores.
- `saldo_minimo_centavos` é o menor saldo de fim de dia entre os dias com lançamento;
  `data_saldo_minimo` é esse dia (em caso de empate, o mais antigo). O saldo inicial **não**
  entra como candidato a mínimo.
- `ficou_negativo` = mínimo `< 0`. Saldo exatamente zero não é negativo.
- Lista vazia → saldo final e mínimo iguais ao saldo inicial, `data_saldo_minimo=None` e
  `ficou_negativo = saldo_inicial < 0`.

**`maior_entrada` / `maior_despesa` (RF10, RN10)**
- Devolvem o positivo de maior valor / o negativo de maior valor absoluto.
- Empate → data mais antiga; se a data também empatar, o primeiro na ordem da lista.
- Se não houver nenhum lançamento do tipo pedido → `None`.

**`top_despesas` (RF11)**
- Devolve as `n` despesas mais negativas, com o mesmo desempate de `maior_despesa`.
- Se houver menos de `n` despesas, devolve todas.
- `n < 1` ou `n > 100` → `ParametroInvalido`.

**`por_semana` (RF12, D2)**
- Semanas de segunda a domingo, da data do primeiro lançamento até a do último.
- As semanas parciais das pontas são recortadas ao período. Exemplo: 2026-09-01 é uma
  terça, então a primeira semana vai de 2026-09-01 a 2026-09-06.
- Semana sem lançamento no meio do período entra com todos os valores 0.
- O `saldo_centavos` da semana é entradas + saídas **daquela semana** (não é acumulado).
- Ordem cronológica. Lista vazia → `[]`.

**`dias_no_negativo` (RF13, RN07, RN08)**
- `saldo_inicial is None` → usa 0 e marca `saldo_inicial_assumido=True`.
- Percorre **todos os dias do calendário**, da primeira à última data. Um dia sem
  lançamento herda o saldo do dia anterior. O dia é negativo se o saldo ao fim dele for
  `< 0`.
- `periodos` lista cada sequência máxima de dias negativos consecutivos, com o menor saldo
  dentro dela. Exemplo da SPEC: de 14 a 17 de setembro = 4 dias.
- Lista vazia → 0 dias e `[]`.

**`repetidos` (RF14, RN09)**: só despesas entram. É feito numa única passada:
1. Agrupe as despesas por `normalizar_descricao(descricao)`.
2. Num grupo com `k` despesas e soma `S`, mantenha as despesas de valor `v` em que
   `10 * abs(v * k - S) <= abs(S)`. **Exatamente 10% entra.** A média não é recalculada
   depois do filtro.
3. Só reporte o grupo se sobrarem **3 ou mais** despesas.
4. Para as despesas que ficaram, calcule:
   - `ocorrencias`;
   - `total_centavos`;
   - `valor_medio_centavos` (total ÷ ocorrências, truncado em direção a zero);
   - `datas`, em ordem crescente e com repetições.
- Ordem da resposta:
  1. mais ocorrências primeiro;
  2. depois, `total_centavos` mais negativo;
  3. depois, `descricao_normalizada` em ordem alfabética.

## `app/db.py` — dono: João Caio

É o único módulo com SQL. Não importa FastAPI.

```python
import sqlite3
from app.models import Extrato, Lancamento, Recusa, ResultadoLeitura

SCHEMA: str   # o da SPEC §7, com IF NOT EXISTS e saldo_inicial_centavos aceitando NULL (D3)

def conectar(caminho: str = ":memory:") -> sqlite3.Connection: ...
def salvar_extrato(conn, nome_arquivo: str, banco: str, criado_em: str,
                   saldo_inicial_centavos: int | None, resultado: ResultadoLeitura) -> Extrato: ...
def listar_extratos(conn) -> list[Extrato]: ...
def obter_extrato(conn, extrato_id: int) -> Extrato | None: ...
def listar_lancamentos(conn, extrato_id: int, limite: int | None = None, offset: int = 0) -> list[Lancamento]: ...
def listar_recusas(conn, extrato_id: int) -> list[Recusa]: ...
def apagar_extrato(conn, extrato_id: int) -> bool: ...
```

- `conectar`:
  - liga `PRAGMA foreign_keys = ON`;
  - usa `check_same_thread=False`;
  - cria o schema;
  - se o caminho for um arquivo, cria a pasta pai.
- `salvar_extrato`:
  - grava o extrato, os lançamentos e as recusas **numa única transação**; se algo falhar,
    faz rollback e a exceção sobe;
  - devolve o `Extrato` com `id`, com os contadores tirados do `resultado`.
- As datas são gravadas como `"AAAA-MM-DD"` e voltam como `date`.
- `listar_extratos` ordena por `id`.
- `listar_lancamentos`:
  - ordena por `data` e depois por `id`;
  - devolve os lançamentos com `id` e `extrato_id` preenchidos;
  - com `limite=None`, devolve todos.
- `listar_recusas` ordena por número da linha. As colunas `numero_linha` e
  `conteudo_bruto` viram `Recusa.linha` e `Recusa.conteudo`.
- Extrato inexistente: `obter_extrato` → `None`, as listagens → `[]` e `apagar_extrato` →
  `False`.
- `apagar_extrato` apaga em cascata (RF06).

## Docker — dono: João Caio

- `Dockerfile` com `python:3.12-slim` e diretório de trabalho `/code`:
  1. instala o `requirements.txt`;
  2. copia `app/`, `gerador/`, `tests/` e `pytest.ini`.
- `.dockerignore` sem `.git`, `.venv`, `dados/` nem `__pycache__`.
- `docker-compose.yml` com dois serviços:
  - `api`: `uvicorn app.api:app --host 0.0.0.0 --port 8000`, porta `8000:8000`, volume
    `./dados:/code/dados` e `STATEMENT_DB=/code/dados/statement.db`.
  - `tests`: `pytest -q --cov=app.regras --cov=app.consultas --cov-report=term-missing`.

## `app/api.py` — dono: Gustavo

Camada fina, sem regra de negócio.

- O objeto se chama `app`.
- A conexão vem da dependência `obter_conexao()`, que abre `db.conectar(os.environ.get("STATEMENT_DB", "dados/statement.db"))` uma única vez. Os testes a substituem
  com `app.dependency_overrides[obter_conexao]` usando `":memory:"`.
- Todas as datas saem em JSON como `"AAAA-MM-DD"`.

| Rota | Faz | Resposta |
|---|---|---|
| `POST /extratos` | multipart: `arquivo`, `banco` e `saldo_inicial_centavos` (inteiro, opcional). Encadeia `leitura.carregar_ficha` → `leitura.ler` → `regras.processar` → `db.salvar_extrato`. `criado_em` = agora, com fuso. | `201` com o JSON da SPEC §6.3 (`recusas` com `linha`, `motivo`, `conteudo`) |
| `GET /extratos` | `db.listar_extratos` | `200`, uma lista de extratos sem lançamentos |
| `GET /extratos/{id}` | extrato + `lancamentos` paginados (D6) + `limite` + `offset` | `200` / `404` |
| `DELETE /extratos/{id}` | `db.apagar_extrato` | `204` / `404` |
| `GET /extratos/{id}/resumo` | `consultas.resumo`; acrescenta `extrato_id` | `200` |
| `GET /extratos/{id}/saldo` | `consultas.saldo(l, saldo_inicial or 0)` | `200` |
| `GET /extratos/{id}/maior-entrada` e `/maior-despesa` | `{data, valor_centavos, descricao}` ou `null` (D5) | `200` |
| `GET /extratos/{id}/top-despesas?n=10` | `{"n": n, "despesas": [...]}` | `200` / `422` |
| `GET /extratos/{id}/por-semana` | `{"semanas": [...]}` | `200` |
| `GET /extratos/{id}/dias-no-negativo` | `consultas.dias_no_negativo(l, extrato.saldo_inicial_centavos)` | `200` |
| `GET /extratos/{id}/repetidos` | `{"repetidos": [...]}` | `200` |

Erros, sempre no formato `{"erro", "mensagem", "regra"}` da SPEC §6.6:

| Situação | Status | `erro` |
|---|:---:|---|
| `arquivo` não enviado | 400 | `ARQUIVO_AUSENTE` |
| `BancoDesconhecido` | 400 | `BANCO_DESCONHECIDO` |
| `ArquivoVazio` / `EncodingInvalido` | 422 | `ARQUIVO_VAZIO` / `ENCODING_INVALIDO` |
| `NenhumaLinhaValida` | 422 | `NENHUMA_LINHA_VALIDA` (`regra: "RN06"`) |
| `ExtratoNaoEncontrado` / id inexistente | 404 | `EXTRATO_NAO_ENCONTRADO` |
| `ParametroInvalido` ou validação do FastAPI | 422 | `PARAMETRO_INVALIDO` |
| exceção inesperada | 500 | `ERRO_INTERNO` (sem detalhes, sem descrição de lançamento) |
