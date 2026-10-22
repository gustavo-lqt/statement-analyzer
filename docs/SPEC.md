# Especificação Técnica — Statement Analyzer (v1.1)

> **Fonte da verdade do projeto.** Este documento é lido pelo agente de IA que implementa e
> pelo harness que valida. Código que contraria esta especificação está errado. Especificação
> que os testes revelarem ambígua é corrigida aqui e registrada na seção 8.

| | |
|---|---|
| **Projeto** | Statement Analyzer |
| **Disciplina** | Bootcamp III — Turma B — CEUB — 2026/2 |
| **Repositório** | [statement-analyzer](https://github.com/gustavo-lqt/statement-analyzer) |
| **Stack** | Python 3.12 · FastAPI · SQLite · pytest · Docker |
| **Versão** | v1.1 — 11/09/2026 |

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

## 2. Escopo da Entrega 1

Fundação do projeto: repositório governado, especificação técnica e trabalho dividido. Nada
de implementação.

**Entregue nesta etapa:**

- Repositório público, com todos os integrantes como colaboradores
- Fluxo de branches `main` / `develop` / `feature/*`, com a `main` protegida por regra ativa
  (Pull Request obrigatório, uma aprovação, sem lista de bypass)
- README com visão geral, guia de execução e as decisões de arquitetura (ADRs)
- Esta especificação técnica
- Arquivo de contexto do agente de IA (`CLAUDE.md`)
- Issues abertas a partir da decomposição da §7, com responsável atribuído, organizadas no
  quadro do GitHub Projects

**Fora de escopo nesta entrega:** implementação de qualquer unidade, ambiente containerizado,
harness de testes, API HTTP, persistência e consultas.

> Conforme orientação do professor na Oficina Prática I (22/08), a Entrega Inicial pode ser
> entregue incompleta e complementada até a Entrega Intermediária (17/10). A equipe optou por
> consolidar a fundação nesta etapa e iniciar a implementação na janela seguinte.

**Fora de escopo em toda a v1.0.0:** categorização de gastos, metas e orçamento, comparação
com despesas planejadas, Open Finance, múltiplas moedas, autenticação e multiusuário,
interface web além do mínimo para demonstração.

**Evolução prevista:** leitura de arquivos OFX; análise cruzando vários extratos da mesma
conta (exige o conceito de conta, hoje inexistente no modelo).

---

## 3. Requisitos funcionais

| ID | Requisito | Entrega |
|:---:|---|:---:|
| RF01 | Ler um arquivo CSV aplicando a ficha do banco informada | 2 |
| RF02 | Normalizar cada linha para o modelo canônico de Lançamento | 2 |
| RF03 | Recusar linhas inválidas individualmente, registrando motivo e número da linha | 2 |
| RF04 | Enviar um extrato e persistir lançamentos e recusas | 2 |
| RF05 | Listar extratos e consultar um extrato com seus lançamentos | 2 |
| RF06 | Apagar um extrato, em cascata com lançamentos e recusas | 2 |
| RF07 | Suportar três fichas de banco distintas | 2 |
| RF08 | Consulta `resumo`: entradas, saídas, saldo, média diária, período, quantidade | 2 |
| RF09 | Consulta `saldo`: saldo final, se ficou negativo, saldo mínimo e sua data | 2 |
| RF10 | Consultas `maior-entrada` e `maior-despesa` | 2 |
| RF11 | Consulta `top-despesas`, com N configurável | 2 |
| RF12 | Consulta `por-semana` | 3 |
| RF13 | Consulta `dias-no-negativo` | 3 |
| RF14 | Consulta `repetidos` | 3 |

---

## 4. Regras de negócio

Cada regra é verificável e é citada na docstring do teste que a valida.

| ID | Regra |
|:---:|---|
| **RN01** | A data é interpretada pelo formato **declarado na ficha do banco**, nunca inferido. Formatos aceitos: `dd/mm/aaaa`, `aaaa-mm-dd`, `dd-mm-aaaa`. Data que não casa com o formato declarado, ou sintaticamente válida mas inexistente (`31/02/2026`), recusa a linha. Armazenada sempre como `AAAA-MM-DD`. |
| **RN02** | O valor é armazenado como **inteiro em centavos**. Separador decimal e de milhar vêm da ficha; o de milhar é removido antes da conversão. Com vírgula decimal, `1.234,56` → `123456`. Ponto flutuante não é usado em nenhum ponto do fluxo monetário. |
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
| RNF07 | Cobertura mínima de 80% em `app/regras.py` e `app/consultas.py` (verificado na Entrega 3) |

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
`saldo_inicial_centavos` (opcional, RN07).

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

### 6.6 Formato único de erro (RNF01)

```json
{ "erro": "BANCO_DESCONHECIDO", "mensagem": "A ficha 'banco-z' não está registrada.", "regra": null }
```

O campo `regra` traz o identificador da RN violada quando o erro nasce de uma regra de
negócio (ex.: `"RN06"`); é `null` quando o erro é de protocolo.

---

## 7. Decomposição em unidades

Princípio: **dependências apontam para dentro.** A camada HTTP conhece o motor; o motor não
conhece HTTP.

```
[ U5 api (FastAPI) ] → traduz HTTP → [ U2/U3/U4 motor puro ] → usa → [ U1 models ]
        ↑ testes de integração (test_api.py)      ↑ testes de unidade (test_regras.py, test_consultas.py)
```

| # | Unidade | Arquivo | Responsabilidade | Entrega |
|:---:|---|---|---|:---:|
| U1 | models | `app/models.py` | Entidades: `Extrato`, `Lancamento`, `Recusa`, `FichaBanco` | 2 |
| U2 | leitura | `app/leitura.py` | Abre o arquivo e aplica a ficha; produz linhas cruas. Sem HTTP | 2 |
| U3 | regras | `app/regras.py` | Motor puro de normalização e validação (RN01–RN06). Sem HTTP, sem I/O | 2 |
| U4 | consultas | `app/consultas.py` | As oito consultas (RN07–RN10). Recebe lista de lançamentos, devolve agregados | 2 e 3 |
| U5 | api | `app/api.py` | Camada FastAPI fina; traduz HTTP ⇄ motor e erros para o formato §6.6 | 2 |
| U6 | db | `app/db.py` | Tabelas e acesso SQLite | 2 |
| U7 | harness | `tests/` + `gerador/` | Fixtures sintéticas com semente e suíte de testes | 2 |

Cada unidade vira uma Issue no GitHub, com o responsável definido lá. A atribuição não é
duplicada neste documento: a Issue é a fonte da divisão, e a autoria dos commits e dos Pull
Requests é a comprovação.

### Interface pública do motor

```python
# app/leitura.py
ler(conteudo: bytes, ficha: FichaBanco) -> Iterator[LinhaCrua]
#   levanta: ArquivoVazio | EncodingInvalido

# app/regras.py — motor puro de normalização
normalizar(linha: LinhaCrua, ficha: FichaBanco) -> Lancamento | Recusa
#   aplica RN01..RN04; devolve Recusa em vez de levantar (RN05)
processar(linhas: Iterable[LinhaCrua], ficha: FichaBanco) -> ResultadoLeitura
#   levanta: NenhumaLinhaValida (RN06)

# app/consultas.py — motor puro de análise
resumo(lancamentos) -> Resumo
saldo(lancamentos, saldo_inicial: int) -> Saldo
maior_entrada(lancamentos) -> Lancamento | None      # desempate por RN10
maior_despesa(lancamentos) -> Lancamento | None      # desempate por RN10
top_despesas(lancamentos, n: int) -> list[Lancamento]
por_semana(lancamentos) -> list[Semana]
dias_no_negativo(lancamentos, saldo_inicial: int) -> DiasNoNegativo   # RN07, RN08
repetidos(lancamentos) -> list[GrupoRepetido]                          # RN09
```

### Modelo de dados

```sql
CREATE TABLE extrato (
    id INTEGER PRIMARY KEY, nome_arquivo TEXT NOT NULL, banco TEXT NOT NULL,
    criado_em TEXT NOT NULL, saldo_inicial_centavos INTEGER NOT NULL DEFAULT 0,
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
| RN01 | Data no formato da ficha converte | `31/02/2026`; data vazia; formato diferente do declarado | `tests/test_regras.py` |
| RN02 | `1.234,56` → `123456` | valor vazio; só separador; negativo entre parênteses | `tests/test_regras.py` |
| RN03 | Saída chega negativa | ficha `COLUNA_DC`; ficha `COLUNAS_SEPARADAS` | `tests/test_regras.py` |
| RN04 | Duas casas passam | três casas recusa `PRECISAO_INVALIDA`; duas casas com zero à direita passa | `tests/test_regras.py` |
| RN05 | Arquivo com 3 linhas ruins lê as demais | linha truncada no fim do arquivo; encoding errado no meio | `tests/test_regras.py` |
| RN06 | Arquivo válido produz resultado | arquivo só com linhas ruins levanta `NenhumaLinhaValida`; arquivo vazio | `tests/test_regras.py` |
| RN07 | Saldo inicial informado é usado | ausente marca `saldo_inicial_assumido` | `tests/test_consultas.py` |
| RN08 | Saldo corrente por data crescente | dois lançamentos no mesmo dia cruzando o zero; conta que nunca fica negativa | `tests/test_consultas.py` |
| RN09 | Três cobranças iguais formam grupo | duas ocorrências não formam; valor 11% acima fica fora; exatamente 10% entra | `tests/test_consultas.py` |
| RN10 | Maior despesa única | empate resolve pela data mais antiga | `tests/test_consultas.py` |
| §6.3 | `POST /extratos` devolve 201 com o contrato | `422 NENHUMA_LINHA_VALIDA` no formato único | `tests/test_api.py` |

---

## 8. Registro de refinamentos

> Este registro é o requisito "Refinamento por Feedback". Cada ajuste vindo de teste ou de
> revisão entra aqui com o motivo e a referência ao PR.

| Versão | O que mudou | Motivo | PR |
|:---:|---|---|:---:|
| v1.0 → v1.1 | A consulta `recorrentes` (cobranças que se repetem **todos os meses**) virou `repetidos` (gastos que se repetem **dentro do período**), e ganhou a RN09 com limiar de 3 ocorrências e tolerância de 10% | Revisão do grupo apontou que um extrato exportado cobre normalmente **um mês**, então a consulta original não teria dados suficientes para existir. Análise entre meses foi movida para "evolução prevista", pois exige o conceito de conta | #«n» |
| v1.0 → v1.1 | A consulta `por-mes` virou `por-semana` | Mesmo motivo: num extrato de um mês, o agrupamento mensal devolvia uma única linha, sem informação útil | #«n» |
| v1.0 → v1.1 | RN08 passou a definir explicitamente o tratamento de lançamentos na mesma data | O cálculo de `dias-no-negativo` era ambíguo quando dois lançamentos do mesmo dia cruzavam o zero em ordens diferentes — o extrato não garante ordem interna do dia | #«n» |
| v1.0 → v1.1 | O escopo da Entrega 1 (§2) deixou de incluir a implementação do motor de leitura e normalização e o harness; passou a cobrir repositório governado, documentação e divisão de tarefas. RF01–RF03 e as unidades U1, U2, U3 e U7 foram remanejadas para a Entrega 2 | Orientação do professor na Oficina Prática I (22/08): a Entrega Inicial pode ser entregue incompleta e complementada até 17/10. A equipe priorizou consolidar governança e especificação antes de começar a codificar | — |
| | | | |

---

## 9. Decisões em aberto

- A tolerância de 10% da RN09 é adequada? Assinaturas têm valor fixo, delivery varia muito.
- `saldo_inicial` deveria ser obrigatório? Sem ele, `dias-no-negativo` responde algo relativo
  que pode enganar quem lê rápido, mesmo com o campo `saldo_inicial_assumido`.
- A semana de `por-semana` começa no domingo ou na segunda, e semanas parciais no início e no
  fim do período entram ou são descartadas?
- Quais três bancos, definidos a partir dos extratos que os integrantes conseguirem exportar.
