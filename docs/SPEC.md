# Especificação Técnica — Statement Analyzer (v1.5, as-built)

> **Fonte da verdade do projeto.** Este documento é lido pelo agente de IA que implementa e
> pelo harness que valida. Código que contraria esta especificação está errado. Especificação
> que os testes revelarem ambígua é corrigida aqui e registrada na seção 8.
>
> **As-built:** a partir da v1.5, este documento descreve o sistema exatamente como foi
> entregue na release `v1.0.0`: arquitetura, rotas, contratos e interfaces públicas.

| | |
|---|---|
| **Projeto** | Statement Analyzer |
| **Disciplina** | Bootcamp III — Turma B — CEUB — 2026/2 |
| **Repositório** | [statement-analyzer](https://github.com/gustavo-lqt/statement-analyzer) |
| **Stack** | Python 3.12 · FastAPI · SQLite · pytest · Docker |
| **Versão** | v1.5 (as-built) — 25/10/2026 · descreve a release `v1.0.0` |

---

## 1. Problema

A pessoa recebe do banco um arquivo com tudo que entrou e saiu da conta no mês. O arquivo é
longo, as descrições são geradas por máquina (`PAG*MERC CENTRAL 03/09`, `IFD*IFOOD`) e não há
nenhum resumo. Na prática ninguém lê o próprio extrato, e perguntas simples ficam sem
resposta: quanto saiu no total, qual foi o maior gasto, a conta ficou negativa em algum
momento, o que está sendo cobrado repetidamente.

Agrava o problema não existir formato único de exportação: cada banco escreve a data, o valor
decimal, o sinal de saída e os nomes das colunas de um jeito. Qualquer ferramenta precisa
resolver isso antes de fazer qualquer coisa útil.

**Solução proposta:** uma API que recebe o arquivo, identifica o formato pela ficha do banco,
normaliza cada lançamento para um modelo único, armazena, e responde consultas de análise
sobre aquele extrato.

Não é sistema de controle financeiro: sem categorização, orçamento ou planejamento. Entra um
arquivo, saem respostas sobre ele.

---

## 2. Escopo entregue (v1.0.0)

Sistema completo, entregue de uma vez na Entrega 3 (§3 e §7).

**Produto:**

- Leitura de extratos CSV pela ficha do banco, com três fichas (`banco-a`, `banco-b`,
  `banco-c`) que cobrem as três convenções de sinal, os três formatos de data e os dois
  encodings (RF01, RF07)
- Normalização para o modelo canônico e recusa individual de linhas inválidas (RN01–RN06)
- Persistência em SQLite de extratos, lançamentos e recusas, com exclusão em cascata
- As oito consultas de análise (RN07–RN10)
- API HTTP em FastAPI, com documentação interativa em `/docs` e formato único de erro
- Gerador de extratos sintéticos com semente fixa e harness de testes
- Ambiente Docker com dois serviços: `api` e `tests`

**Governança:**

- Repositório público, com todos os integrantes como colaboradores
- Fluxo de branches `main` / `entrega` / `feature/<issue>-<nome>`: cada integrante trabalha
  numa feature branch, que entra na `entrega` por Pull Request; a `entrega` entra na `main`
  por Pull Request
- `main` e `entrega` protegidas, inclusive para administradores: Pull Request obrigatório,
  uma aprovação, o último push aprovado por outra pessoa, conversas resolvidas, sem force
  push e sem exclusão
- Uma Issue por unidade (§7), com responsável, fechada pelo Pull Request que a entrega

**Documentação:** README (instalação, execução, arquitetura e ADRs), esta especificação,
`CLAUDE.md` (contexto do agente de IA), `docs/prompts/` (registro de uso de IA de cada
integrante), `docs/tarefas/` (planejamento da divisão do trabalho), `docs/RELATORIO.md`
(relatório técnico-ético) e `logs_testes.txt` (execução da suíte no Docker).

**Fora de escopo em toda a v1.0.0:** categorização de gastos, metas e orçamento, comparação
com despesas planejadas, Open Finance, múltiplas moedas, autenticação e multiusuário,
interface web além do mínimo para demonstração.

**Evolução prevista:** leitura de arquivos OFX; análise cruzando vários extratos da mesma
conta (exige o conceito de conta, hoje inexistente no modelo).

---

## 3. Requisitos funcionais

| ID | Requisito | Entrega |
|:---:|---|:---:|
| RF01 | Ler um arquivo CSV aplicando a ficha do banco informada | 3 |
| RF02 | Normalizar cada linha para o modelo canônico de Lançamento | 3 |
| RF03 | Recusar linhas inválidas individualmente, registrando motivo e número da linha | 3 |
| RF04 | Enviar um extrato e persistir lançamentos e recusas | 3 |
| RF05 | Listar extratos e consultar um extrato com seus lançamentos | 3 |
| RF06 | Apagar um extrato, em cascata com lançamentos e recusas | 3 |
| RF07 | Suportar três fichas de banco distintas | 3 |
| RF08 | Consulta `resumo`: entradas, saídas, saldo, média diária, período, quantidade | 3 |
| RF09 | Consulta `saldo`: saldo final, se ficou negativo, saldo mínimo e sua data | 3 |
| RF10 | Consultas `maior-entrada` e `maior-despesa` | 3 |
| RF11 | Consulta `top-despesas`, com N configurável | 3 |
| RF12 | Consulta `por-semana` | 3 |
| RF13 | Consulta `dias-no-negativo` | 3 |
| RF14 | Consulta `repetidos` | 3 |

---

## 4. Regras de negócio

Cada regra é verificável e é citada na docstring do teste que a valida.

| ID | Regra |
|:---:|---|
| **RN01** | A data é interpretada pelo formato **declarado na ficha do banco**, nunca inferido. Formatos aceitos: `dd/mm/aaaa`, `aaaa-mm-dd`, `dd-mm-aaaa`, só com os dígitos `0`–`9`. Data que não casa com o formato declarado, ou sintaticamente válida mas inexistente (`31/02/2026`), recusa a linha. Armazenada sempre como `AAAA-MM-DD`. |
| **RN02** | O valor é armazenado como **inteiro em centavos**. Separador decimal e de milhar vêm da ficha; o de milhar é removido antes da conversão. Só os dígitos `0`–`9` são aceitos; qualquer outro recusa a linha (`VALOR_INVALIDO`). Com vírgula decimal, `1.234,56` → `123456`. Ponto flutuante não é usado em nenhum ponto do fluxo monetário. |
| **RN03** | Saída é negativa e entrada é positiva, **sempre**. Fichas `COLUNA_DC` e `COLUNAS_SEPARADAS` são convertidas na leitura; nenhuma unidade posterior conhece a convenção do banco. |
| **RN04** | Valor com três ou mais casas decimais **recusa a linha** (`PRECISAO_INVALIDA`). Não arredonda: arredondar em silêncio é perda de informação em sistema de conferência. |
| **RN05** | Linha inválida **não aborta a leitura**. É recusada com número da linha, motivo e conteúdo bruto, e o processamento continua. Um arquivo com recusas é uma leitura bem-sucedida. |
| **RN06** | Arquivo em que **todas** as linhas foram recusadas devolve erro `NENHUMA_LINHA_VALIDA` e **nenhum extrato é criado**. |
| **RN07** | O saldo inicial é opcional no envio; ausente vale zero. Quando ausente, a resposta de `dias-no-negativo` traz `saldo_inicial_assumido: true`. |
| **RN08** | Para o saldo corrente, os lançamentos são ordenados por data crescente e os de mesma data formam um bloco: o saldo do dia é o saldo **após todos eles**. Um dia é negativo se o saldo ao fim do dia for negativo — o extrato não garante ordem interna do dia. |
| **RN09** | Dois lançamentos são repetições do mesmo gasto quando a descrição normalizada é idêntica e o valor difere em no máximo **10%** do valor médio do grupo. Um grupo só é reportado com **três ou mais ocorrências** no período. |
| **RN10** | Empate em `maior-entrada` ou `maior-despesa` resolve pelo lançamento de **data mais antiga**, para a resposta ser determinística. |

**Motivos de recusa:** `DATA_INVALIDA` · `VALOR_INVALIDO` · `PRECISAO_INVALIDA` ·
`COLUNA_AUSENTE` · `LINHA_TRUNCADA` · `ENCODING_INVALIDO`

Só `\n` e `\r\n` quebram linha. Um `\r` solto fora de aspas é quebra de linha corrompida:
a linha sai `LINHA_TRUNCADA`; no cabeçalho, as linhas de dados saem `COLUNA_AUSENTE`.

**Descrição normalizada** (usada em RN09): original em caixa alta, sem acentos, com espaços
consecutivos colapsados e sem pontuação.

---

## 5. Requisitos não funcionais

| ID | Requisito |
|:---:|---|
| RNF01 | Respostas da API em JSON; erros seguem formato único (ver §6.6) |
| RNF02 | Regras de negócio isoladas da camada HTTP — `app/regras.py` e `app/consultas.py` não importam FastAPI nem fazem I/O, e são testáveis sem subir servidor |
| RNF03 | Suíte executável com um único comando, dentro do Docker: `docker compose run --rm tests` |
| RNF04 | Ler arquivo de 100.000 linhas em até 60 s, em máquina de 2 vCPU e 4 GB, com leitura em streaming (memória não cresce proporcional ao arquivo) |
| RNF05 | Nenhum extrato bancário real no repositório: toda fixture é gerada sinteticamente, com semente fixa |
| RNF06 | Logs não registram descrição de lançamento em texto claro |
| RNF07 | Cobertura mínima de 80% em `app/regras.py` e `app/consultas.py` (verificado na entrega) |

---

## 6. Contratos de entrada e saída

### 6.1 Ficha de banco — `app/fichas/*.json`

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

`formato_data`: `dd/mm/aaaa` | `aaaa-mm-dd` | `dd-mm-aaaa` ·
`convencao_sinal`: `NEGATIVO_SAIDA` | `COLUNA_DC` | `COLUNAS_SEPARADAS` ·
`encoding`: `utf-8` | `latin-1`

### 6.2 Modelo canônico — Lançamento

```json
{ "id": 933, "extrato_id": 1, "data": "2026-09-18",
  "valor_centavos": -134000, "descricao": "TRANSF PIX ENVIADA" }
```

### 6.3 `POST /extratos`

Entrada `multipart/form-data`: `arquivo` (obrigatório), `banco` (obrigatório),
`saldo_inicial_centavos` (opcional, inteiro, RN07).

Saída `201`:
```json
{ "id": 1, "nome_arquivo": "extrato-setembro.csv", "banco": "banco-a",
  "criado_em": "2026-09-11T14:32:00-03:00", "saldo_inicial_centavos": 20000,
  "total_linhas": 342, "aceitos": 340, "rejeitados": 2,
  "recusas": [ { "linha": 87, "motivo": "DATA_INVALIDA", "conteudo": "31/02/2026;PAG*..." } ] }
```
Erros: `400 ARQUIVO_AUSENTE` | `400 BANCO_DESCONHECIDO` | `422 ARQUIVO_VAZIO` |
`422 NENHUMA_LINHA_VALIDA` (RN06) | `422 ENCODING_INVALIDO`

### 6.4 Gestão de extratos

```
GET    /extratos                → 200 (lista, sem lançamentos)
GET    /extratos/{id}           → 200 (com lançamentos paginados) | 404
DELETE /extratos/{id}           → 204 (cascata) | 404
```

`GET /extratos/{id}` aceita `limite` (padrão 100, de 1 a 1000) e `offset` (padrão 0, a partir
de 0). Fora da faixa → `422 PARAMETRO_INVALIDO`. A resposta traz os campos do extrato (como
na §6.3, sem `recusas`), mais `lancamentos` (no modelo da §6.2), `limite` e `offset`.

### 6.5 Consultas — `GET /extratos/{id}/<consulta>`

```json
// resumo
{ "extrato_id": 1, "periodo": { "de": "2026-09-01", "ate": "2026-09-30" },
  "total_lancamentos": 340, "entradas_centavos": 580000, "saidas_centavos": -423410,
  "saldo_centavos": 156590, "media_diaria_gasto_centavos": -14113 }

// saldo
{ "saldo_inicial_centavos": 20000, "saldo_final_centavos": 176590,
  "ficou_negativo": true, "saldo_minimo_centavos": -31200,
  "data_saldo_minimo": "2026-09-16" }

// maior-entrada | maior-despesa
{ "data": "2026-09-18", "valor_centavos": -134000, "descricao": "TRANSF PIX ENVIADA" }

// top-despesas?n=10
{ "n": 10, "despesas": [ { "data": "...", "valor_centavos": -134000, "descricao": "..." } ] }

// por-semana
{ "semanas": [ { "de": "2026-09-01", "ate": "2026-09-06", "entradas_centavos": 580000,
                 "saidas_centavos": -92400, "saldo_centavos": 487600 } ] }

// dias-no-negativo
{ "saldo_inicial_centavos": 20000, "saldo_inicial_assumido": false,
  "dias_no_negativo": 4,
  "periodos": [ { "de": "2026-09-14", "ate": "2026-09-17", "saldo_minimo_centavos": -31200 } ] }

// repetidos
{ "repetidos": [ { "descricao_normalizada": "IFD IFOOD", "ocorrencias": 9,
                   "valor_medio_centavos": -4210, "total_centavos": -37890,
                   "datas": ["2026-09-02", "2026-09-05", "2026-09-09"] } ] }
```

Erros de consulta: `404 EXTRATO_NAO_ENCONTRADO` | `422 PARAMETRO_INVALIDO`

`top-despesas` aceita `n` de 1 a 100 (padrão 10). `maior-entrada` e `maior-despesa` devolvem
`200` com corpo `null` quando não há lançamento do tipo pedido (D5). Sem saldo inicial
informado, `saldo` usa 0 e `dias-no-negativo` marca `saldo_inicial_assumido: true` (D3).

### 6.6 Formato único de erro (RNF01)

```json
{ "erro": "BANCO_DESCONHECIDO", "mensagem": "A ficha 'banco-z' não está registrada.", "regra": null }
```

O campo `regra` traz o identificador da RN violada quando o erro nasce de uma regra de
negócio (ex.: `"RN06"`); é `null` quando o erro é de protocolo.

Todos os erros da API, sem exceção:

| Status | `erro` | Quando |
|:---:|---|---|
| 400 | `ARQUIVO_AUSENTE` | `POST /extratos` sem o campo `arquivo` |
| 400 | `BANCO_DESCONHECIDO` | ficha não registrada em `app/fichas/` |
| 404 | `EXTRATO_NAO_ENCONTRADO` | id de extrato inexistente |
| 404 | `ROTA_INEXISTENTE` | rota que não existe |
| 405 | `METODO_NAO_PERMITIDO` | método que a rota não aceita (com o cabeçalho `Allow`) |
| 422 | `ARQUIVO_VAZIO` | arquivo sem nenhuma linha de dados |
| 422 | `ENCODING_INVALIDO` | cabeçalho fora do encoding da ficha |
| 422 | `NENHUMA_LINHA_VALIDA` | todas as linhas recusadas (`regra: "RN06"`) |
| 422 | `PARAMETRO_INVALIDO` | parâmetro fora do tipo ou da faixa; o valor enviado não é ecoado |
| 500 | `ERRO_INTERNO` | erro inesperado; a resposta e o log não trazem a mensagem original (RNF06) |

### 6.7 Configuração

| Variável | Padrão | Uso |
|---|---|---|
| `STATEMENT_DB` | `dados/statement.db` | Caminho do arquivo SQLite. No Docker, `/code/dados/statement.db`, numa pasta montada como volume |

A API escuta na porta `8000`. A conexão é aberta uma vez, pela dependência
`obter_conexao()` de `app/api.py`; os testes a substituem por um banco em memória.

---

## 7. Decomposição em unidades

Princípio: **dependências apontam para dentro.** A camada HTTP conhece o motor; o motor não
conhece HTTP.

```
[ U5 api (FastAPI) ] → traduz HTTP → [ U2/U3/U4 motor puro ] → usa → [ U1 models ]
        │                                                              ↑
        └──────────────→ [ U6 db (SQLite) ] ───────────────────────────┘
        ↑ testes de integração (test_api.py)      ↑ testes de unidade (test_leitura.py,
                                                     test_regras.py, test_consultas.py, test_db.py)
```

`tests/test_arquitetura.py` verifica essas dependências no código-fonte: o motor não importa
FastAPI, Starlette, `sqlite3`, `app.db` nem `app.api`, e nenhum arquivo de `app/` além de
`app/db.py` contém SQL.

| # | Unidade | Arquivo | Responsabilidade | Entrega |
|:---:|---|---|---|:---:|
| U1 | models | `app/models.py` | Entidades: `Extrato`, `Lancamento`, `Recusa`, `FichaBanco` | 3 |
| U2 | leitura | `app/leitura.py` | Abre o arquivo e aplica a ficha; produz linhas cruas. Sem HTTP | 3 |
| U3 | regras | `app/regras.py` | Motor puro de normalização e validação (RN01–RN06). Sem HTTP, sem I/O | 3 |
| U4 | consultas | `app/consultas.py` | As oito consultas (RN07–RN10). Recebe lista de lançamentos, devolve agregados | 3 |
| U5 | api | `app/api.py` | Camada FastAPI fina; traduz HTTP ⇄ motor e erros para o formato §6.6 | 3 |
| U6 | db | `app/db.py` | Tabelas e acesso SQLite | 3 |
| U7 | harness | `tests/` + `gerador/` | Fixtures sintéticas com semente e suíte de testes | 3 |

Cada unidade vira uma Issue no GitHub, com o responsável definido lá. A atribuição não é
duplicada neste documento: a Issue é a fonte da divisão, e a autoria dos commits e dos Pull
Requests é a comprovação.

### Interfaces públicas

```python
# app/leitura.py — U2
carregar_ficha(nome: str) -> FichaBanco          # levanta: BancoDesconhecido
listar_fichas() -> list[str]                     # em ordem alfabética
ler(conteudo: bytes, ficha: FichaBanco) -> Iterator[LinhaCrua]
#   gerador, em streaming; levanta: ArquivoVazio | EncodingInvalido

# app/regras.py — U3, motor puro de normalização
converter_data(texto: str, formato: str) -> date | None                        # RN01
converter_valor(texto: str, separador_decimal: str, separador_milhar: str) -> int | str
#   centavos, ou o motivo de recusa (VALOR_INVALIDO | PRECISAO_INVALIDA)        # RN02, RN04
normalizar(linha: LinhaCrua, ficha: FichaBanco) -> Lancamento | Recusa
#   aplica RN01..RN04; devolve Recusa em vez de levantar (RN05)
processar(linhas: Iterable[LinhaCrua], ficha: FichaBanco) -> ResultadoLeitura
#   levanta: NenhumaLinhaValida (RN06)

# app/consultas.py — U4, motor puro de análise
normalizar_descricao(texto: str) -> str                                         # RN09
resumo(lancamentos) -> Resumo
saldo(lancamentos, saldo_inicial: int) -> Saldo                                 # RN08
maior_entrada(lancamentos) -> Lancamento | None      # desempate por RN10
maior_despesa(lancamentos) -> Lancamento | None      # desempate por RN10
top_despesas(lancamentos, n: int) -> list[Lancamento]   # levanta: ParametroInvalido
por_semana(lancamentos) -> list[Semana]                                         # D2
dias_no_negativo(lancamentos, saldo_inicial: int | None) -> DiasNoNegativo   # RN07, RN08 (None = assumido, D3)
repetidos(lancamentos) -> list[GrupoRepetido]                                   # RN09

# app/db.py — U6, único módulo com SQL
conectar(caminho: str = ":memory:") -> sqlite3.Connection
salvar_extrato(conn, nome_arquivo, banco, criado_em, saldo_inicial_centavos, resultado) -> Extrato
#   uma transação: extrato, lançamentos e recusas entram juntos ou nada entra
listar_extratos(conn) -> list[Extrato]
obter_extrato(conn, extrato_id: int) -> Extrato | None
listar_lancamentos(conn, extrato_id: int, limite: int | None = None, offset: int = 0) -> list[Lancamento]
listar_recusas(conn, extrato_id: int) -> list[Recusa]
apagar_extrato(conn, extrato_id: int) -> bool                                   # cascata

# gerador/gerar.py — U7
gerar_csv(ficha: FichaBanco, linhas: int, semente: int, invalidas: int = 0) -> bytes
#   CLI: python -m gerador.gerar --banco --linhas --semente [--invalidas] --saida
```

Entidades (`app/models.py`): `FichaBanco`, `LinhaCrua`, `Lancamento`, `Recusa`,
`ResultadoLeitura`, `Extrato`, `Resumo`, `Periodo`, `Saldo`, `Semana`, `DiasNoNegativo`,
`PeriodoNegativo` e `GrupoRepetido`, mais os enums `MotivoRecusa` e `ConvencaoSinal`.
Exceções (`app/erros.py`): `ErroDominio` e as subclasses `ArquivoVazio`, `EncodingInvalido`,
`NenhumaLinhaValida`, `BancoDesconhecido`, `ExtratoNaoEncontrado` e `ParametroInvalido`.

### Modelo de dados

```sql
CREATE TABLE extrato (
    id INTEGER PRIMARY KEY, nome_arquivo TEXT NOT NULL, banco TEXT NOT NULL,
    criado_em TEXT NOT NULL, saldo_inicial_centavos INTEGER,
    total_linhas INTEGER NOT NULL, aceitos INTEGER NOT NULL, rejeitados INTEGER NOT NULL);

CREATE TABLE lancamento (
    id INTEGER PRIMARY KEY,
    extrato_id INTEGER NOT NULL REFERENCES extrato(id) ON DELETE CASCADE,
    data TEXT NOT NULL, valor_centavos INTEGER NOT NULL, descricao TEXT NOT NULL);

CREATE TABLE recusa (
    id INTEGER PRIMARY KEY,
    extrato_id INTEGER NOT NULL REFERENCES extrato(id) ON DELETE CASCADE,
    numero_linha INTEGER NOT NULL, motivo TEXT NOT NULL, conteudo_bruto TEXT NOT NULL);

CREATE INDEX idx_lancamento_extrato_data ON lancamento(extrato_id, data);
```

### Rastreabilidade regra → teste

| Regra | Cenário principal | Casos de borda | Arquivo |
|:---:|---|---|---|
| RN01 | Data no formato da ficha converte | `31/02/2026`; data vazia; formato diferente do declarado; dígitos não ASCII | `tests/test_regras.py` |
| RN02 | `1.234,56` → `123456` | valor vazio; só separador; negativo entre parênteses; `1²` e dígitos não ASCII | `tests/test_regras.py` |
| RN03 | Saída chega negativa | ficha `COLUNA_DC`; ficha `COLUNAS_SEPARADAS` | `tests/test_regras.py` |
| RN04 | Duas casas passam | três casas recusa `PRECISAO_INVALIDA`; duas casas com zero à direita passa | `tests/test_regras.py` |
| RN05 | Arquivo com 3 linhas ruins lê as demais | linha truncada no fim do arquivo; encoding errado no meio; `\r` solto fora de aspas | `tests/test_regras.py`, `tests/test_leitura.py` |
| RN06 | Arquivo válido produz resultado | arquivo só com linhas ruins levanta `NenhumaLinhaValida`; arquivo vazio | `tests/test_regras.py` |
| RN07 | Saldo inicial informado é usado | ausente marca `saldo_inicial_assumido` | `tests/test_consultas.py` |
| RN08 | Saldo corrente por data crescente | dois lançamentos no mesmo dia cruzando o zero; conta que nunca fica negativa | `tests/test_consultas.py` |
| RN09 | Três cobranças iguais formam grupo | duas ocorrências não formam; valor 11% acima fica fora; exatamente 10% entra | `tests/test_consultas.py` |
| RN10 | Maior despesa única | empate resolve pela data mais antiga | `tests/test_consultas.py` |
| §6.3 | `POST /extratos` devolve 201 com o contrato | `422 NENHUMA_LINHA_VALIDA` no formato único | `tests/test_api.py` |
| §6.6 | Todo erro sai no formato único | 404 de rota inexistente; 405; 500 sem detalhes | `tests/test_api.py` |
| ADR-001 | O motor não importa HTTP nem banco | SQL fora de `app/db.py` | `tests/test_arquitetura.py` |

---

## 8. Registro de refinamentos

> Este registro é o requisito "Refinamento por Feedback". Cada ajuste vindo de teste ou de
> revisão entra aqui com o motivo e a referência ao PR.
>
> Quando a SPEC mudou por commit direto, sem PR, a coluna traz o commit (`1b58f3a` é a
> estrutura inicial e `5ec5f1b` é a base da Entrega 2), seguido dos PRs que implementaram a
> decisão.

| Versão | O que mudou | Motivo | PR |
|:---:|---|---|:---:|
| v1.0 → v1.1 | A consulta `recorrentes` (cobranças que se repetem **todos os meses**) virou `repetidos` (gastos que se repetem **dentro do período**), e ganhou a RN09 com limiar de 3 ocorrências e tolerância de 10% | Revisão do grupo apontou que um extrato exportado cobre normalmente **um mês**, então a consulta original não teria dados suficientes para existir. Análise entre meses foi movida para "evolução prevista", pois exige o conceito de conta | `1b58f3a` |
| v1.0 → v1.1 | A consulta `por-mes` virou `por-semana` | Mesmo motivo: num extrato de um mês, o agrupamento mensal devolvia uma única linha, sem informação útil | `1b58f3a` |
| v1.0 → v1.1 | RN08 passou a definir explicitamente o tratamento de lançamentos na mesma data | O cálculo de `dias-no-negativo` era ambíguo quando dois lançamentos do mesmo dia cruzavam o zero em ordens diferentes — o extrato não garante ordem interna do dia | `1b58f3a` |
| v1.0 → v1.1 | O escopo da Entrega 1 (§2) deixou de incluir a implementação do motor de leitura e normalização e o harness; passou a cobrir repositório governado, documentação e divisão de tarefas. RF01–RF03 e as unidades U1, U2, U3 e U7 foram remanejadas para a Entrega 2 | Orientação do professor na Oficina Prática I (22/08): a Entrega Inicial pode ser entregue incompleta e complementada até 17/10. A equipe priorizou consolidar governança e especificação antes de começar a codificar | — |
| v1.1 → v1.2 | Os três bancos são as fichas sintéticas `banco-a`, `banco-b` e `banco-c`, que juntas cobrem as três convenções de sinal, os três formatos de data e os dois encodings (D1) | Detalhar o contrato para permitir trabalho paralelo | `5ec5f1b` · #16 |
| v1.1 → v1.2 | A semana de `por-semana` vai de segunda a domingo; semanas parciais nas pontas entram, recortadas ao período do extrato (D2) | Detalhar o contrato para permitir trabalho paralelo | `5ec5f1b` · #17 |
| v1.1 → v1.2 | O saldo inicial continua opcional; quando não informado é gravado como `NULL` (a coluna `saldo_inicial_centavos` perde o `NOT NULL DEFAULT 0`). As consultas usam 0 nesse caso, e `dias-no-negativo` devolve `saldo_inicial_assumido: true` (D3) | Detalhar o contrato para permitir trabalho paralelo | `5ec5f1b` · #15, #17, #19 |
| v1.1 → v1.2 | A tolerância de 10% da RN09 é mantida, com o algoritmo exato de `repetidos` definido no contrato da Entrega 2 (D4) | Detalhar o contrato para permitir trabalho paralelo | `5ec5f1b` · #17 |
| v1.1 → v1.2 | `maior-entrada` e `maior-despesa` sem nenhum lançamento do tipo pedido devolvem `200` com corpo `null` (D5) | Detalhar o contrato para permitir trabalho paralelo | `5ec5f1b` · #17, #19 |
| v1.1 → v1.2 | `GET /extratos/{id}` pagina com `limite` (padrão 100, de 1 a 1000) e `offset` (padrão 0) (D6) | Detalhar o contrato para permitir trabalho paralelo | `5ec5f1b` · #15, #19 |
| v1.1 → v1.2 | As oito consultas entram já na Entrega 2 (D7) | Detalhar o contrato para permitir trabalho paralelo | `5ec5f1b` · #17, #19 |
| v1.2 → v1.3 | RN01 e RN02 aceitam só os dígitos `0`–`9`; qualquer outro dígito recusa a linha | Revisão do PR #18 mostrou que `str.isdigit()` aceita `²` e dígitos de outros alfabetos: `"1²"` derrubava o envio com 500 (contra a RN05) e `"١٢,٣٠"` virava 1230 (contra "recusar, não adivinhar") | #18 |
| v1.2 → v1.3 | Um `\r` solto fora de aspas recusa a linha como `LINHA_TRUNCADA`; no cabeçalho, as linhas de dados saem `COLUNA_AUSENTE` (§4) | Revisão do PR #16 apontou que o módulo `csv` levantava erro nesse caso e derrubava a leitura do arquivo inteiro, contra a RN05 | #19 |
| v1.3 → v1.4 | Todo o escopo (RF01–RF14 e as unidades U1–U7) é entregue de uma vez, na Entrega 3; as tabelas da §3 e da §7 deixam de dividir os requisitos entre as Entregas 2 e 3 | Com as consultas adiantadas (D7), o sistema ficou completo de uma vez, e a divisão entre entregas deixou de corresponder ao que foi entregue | — |
| v1.4 → v1.5 | Rota inexistente (`404 ROTA_INEXISTENTE`) e método não aceito (`405 METODO_NAO_PERMITIDO`) passam a sair no formato único de erro (§6.6) | Saíam no formato padrão do FastAPI (`{"detail": ...}`), o que contrariava a RNF01 | — |
| v1.4 → v1.5 | A SPEC passa a ser *as-built*: §2 com o escopo entregue e o fluxo de branches real (`main`/`entrega`/`feature/*`), §6 com a tabela completa de erros, a paginação e a configuração (§6.7), §7 com as interfaces públicas de todos os módulos | Fechamento da release `v1.0.0`: a especificação precisa descrever exatamente o que foi entregue | — |

---

## 9. Decisões em aberto

- ~~A tolerância de 10% da RN09 é adequada? Assinaturas têm valor fixo, delivery varia muito.~~ **Resolvida em v1.2 (D4):** a tolerância de 10% é mantida.
- ~~`saldo_inicial` deveria ser obrigatório? Sem ele, `dias-no-negativo` responde algo relativo
  que pode enganar quem lê rápido, mesmo com o campo `saldo_inicial_assumido`.~~ **Resolvida em v1.2 (D3):** continua
  opcional; ausente é gravado como `NULL` e `dias-no-negativo` marca `saldo_inicial_assumido: true`.
- ~~A semana de `por-semana` começa no domingo ou na segunda, e semanas parciais no início e no
  fim do período entram ou são descartadas?~~ **Resolvida em v1.2 (D2):** segunda a domingo;
  semanas parciais entram, recortadas ao período.
- ~~Quais três bancos, definidos a partir dos extratos que os integrantes conseguirem exportar.~~
  **Resolvida em v1.2 (D1):** fichas sintéticas `banco-a`, `banco-b` e `banco-c`.

Nenhuma decisão fica em aberto na release `v1.0.0`.
