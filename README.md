<div align="center">

# Statement Analyzer

**Envie um extrato bancário. Faça perguntas sobre ele.**

![Etapa](https://img.shields.io/badge/etapa-02%20e%2003%20%E2%80%94%20documentacao-1F4E79)
![Status](https://img.shields.io/badge/status-em%20desenvolvimento-C08A2E)
![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)

</div>

Especificação técnica completa: **[`docs/SPEC.md`](docs/SPEC.md)**

> **Estado As-Built (22/10/2026):** este repositório contém a documentação de produto e a
> estrutura inicial. A API, a persistência, as fichas bancárias, o ambiente Docker e os testes
> ainda não estão implementados. As rotas e consultas abaixo são contratos especificados, não
> funcionalidades disponíveis para execução. Consulte [`ERROS.md`](ERROS.md) para o estado de
> validação.

---

## O projeto

O banco registra tudo que entrou e saiu da conta, mas entrega isso como um arquivo longo, com
descrições geradas por máquina (`PAG*MERC CENTRAL 03/09`) e sem nenhum resumo. Na prática
ninguém lê o próprio extrato, e perguntas simples ficam sem resposta.

Pior: não existe formato único de exportação — cada banco escreve data, valor decimal, sinal
de saída e nomes de coluna de um jeito.

**O Statement Analyzer resolve as duas coisas.** Você envia o arquivo, ele entende o formato
do banco pela ficha declarada, normaliza os lançamentos para um modelo único e passa a
responder consultas sobre eles.

Arquitetura **prevista**:

```mermaid
flowchart LR
    A["Arquivo CSV<br/>do banco"] --> B["Leitura<br/><small>aplica a ficha do banco</small>"]
    B --> C{"Linha<br/>válida?"}
    C -->|sim| D["Normalização<br/><small>data, valor, sinal</small>"]
    C -->|não| E["Recusa<br/><small>motivo + nº da linha</small>"]
    D --> F[("SQLite")]
    E --> F
    F --> G["Consultas"]

    style A fill:#DEE8F1,stroke:#1F4E79,color:#13181B
    style D fill:#DEE8F1,stroke:#1F4E79,color:#13181B
    style E fill:#F3E0DC,stroke:#9E382B,color:#13181B
    style G fill:#DEE8F1,stroke:#1F4E79,color:#13181B
```

Uma linha com defeito **não derruba o arquivo**: é recusada individualmente, com motivo e
número da linha, e a leitura continua (RN05).

---

## Funcionalidades

Contratos HTTP **especificados, ainda não implementados**:

| Método | Rota | Descrição |
|:---|:---|:---|
| `POST` | `/extratos` | Envia o arquivo e devolve o resultado da leitura |
| `GET` | `/extratos` | Lista os extratos enviados |
| `GET` | `/extratos/{id}` | Detalhes do extrato e seus lançamentos |
| `DELETE` | `/extratos/{id}` | Apaga o extrato, seus lançamentos e suas recusas |

### Consultas

| Rota | Responde |
|:---|:---|
| `GET /extratos/{id}/resumo` | Entradas, saídas, saldo, média diária e período |
| `GET /extratos/{id}/saldo` | Saldo final, se ficou negativo, saldo mínimo e sua data |
| `GET /extratos/{id}/maior-entrada` | O maior valor que entrou |
| `GET /extratos/{id}/maior-despesa` | O maior valor que saiu |
| `GET /extratos/{id}/top-despesas?n=10` | As N maiores saídas |
| `GET /extratos/{id}/por-semana` | Entradas, saídas e saldo por semana |
| `GET /extratos/{id}/dias-no-negativo` | Quantos dias no vermelho, e quais |
| `GET /extratos/{id}/repetidos` | Gastos que se repetem no período |

### Fora do escopo da v1.0.0

Categorização de gastos · metas e orçamento · comparação com despesas planejadas ·
Open Finance · múltiplas moedas · login e múltiplos usuários · interface web além do mínimo
para demonstração.

---

## Execução e validação

Ainda não há uma aplicação executável neste repositório: faltam os módulos em `app/`, as
dependências e o arquivo `docker-compose.yml`. Por isso, os comandos abaixo são o destino de
execução definido pelo projeto, não comandos validados no estado atual.

```bash
git clone https://github.com/gustavo-lqt/statement-analyzer.git
cd statement-analyzer

docker compose up api
docker compose run --rm tests
```

Quando a API for implementada, sua documentação interativa deverá estar em
`http://localhost:8000/docs`. Não foi possível executar Pytest nem produzir cobertura nesta
revisão, pois não existem testes ou código Python no repositório.

---

## Colaboração com IA

**Ferramenta:** a equipe pode avaliar Claude Code, Codex CLI, Cursor e Antigravity segundo
disponibilidade, integração ao fluxo e controles de privacidade. Este repositório não registra
uma comparação empírica nem a ferramenta usada para produzir a implementação. A análise e os
limites estão em [`docs/RELATORIO_IA.md`](docs/RELATORIO_IA.md). O agente deve seguir
[`CLAUDE.md`](CLAUDE.md) e a fonte da verdade, `docs/SPEC.md`.

**Uso pretendido no fluxo SDD:** a especificação é escrita primeiro pela equipe; o agente
propõe alterações a partir dela; testes e revisão humana verificam o resultado. Ambiguidades
confirmadas devem voltar como refinamento na `docs/SPEC.md` §8. Esta rotina ainda não foi
demonstrada por uma suíte neste repositório.

**Prompts relevantes** ficam versionados em [`docs/prompts/`](docs/prompts/).

---

## Decisões arquiteturais (ADRs)

### ADR-001 — Regras de negócio isoladas da camada HTTP

**Contexto:** precisamos testar as regras rapidamente e poder trocar a camada de apresentação
nas próximas entregas. Testes que sobem servidor são lentos e frágeis.
**Decisão:** motor puro em `app/regras.py` e `app/consultas.py`, proibidos de importar FastAPI
ou fazer I/O; `app/api.py` apenas traduz HTTP.
**Consequências:** 80% dos testes rodam em milissegundos, sem rede. Em troca, exige disciplina
de revisão para nenhuma dependência de HTTP vazar para dentro do motor.

### ADR-002 — Fichas de banco declarativas em JSON

**Contexto:** três bancos na v1.0.0, cada um com colunas, separadores, encoding e convenção de
sinal diferentes — e mais bancos depois. Condicionais no núcleo tornariam cada banco novo um
risco para os já existentes.
**Decisão:** o formato de cada banco é um arquivo JSON em `app/fichas/`, consumido por um
leitor único.
**Consequências:** adicionar um banco é adicionar dado, não código, e os testes dos bancos
existentes seguem válidos. Formatos que não caibam no vocabulário da ficha exigirão estender o
esquema.

### ADR-003 — Valores monetários em centavos inteiros

**Contexto:** ponto flutuante introduz erro de arredondamento (`0.1 + 0.2 = 0.30000000000000004`),
inaceitável em sistema cujo propósito é conferência.
**Decisão:** inteiro em centavos em todo o fluxo, do parser ao JSON de resposta.
**Consequências:** soma e comparação exatas, e SQLite armazena inteiros nativamente. A
formatação para exibição fica na borda, a cargo do cliente da API.

### ADR-004 — Persistência em SQLite

**Contexto:** o sistema é monousuário por escopo e o volume é de milhares de linhas. Postgres
somaria um serviço ao compose, espera de readiness e limpeza de tabelas entre testes.
**Decisão:** SQLite em arquivo, com banco em memória nos testes.
**Consequências:** um serviço a menos e testes rápidos e isolados. Se o sistema virar
multiusuário será preciso migrar — o acesso a dados está isolado em `app/db.py` para tornar
isso viável.

### ADR-005 — Recusar a linha em vez de adivinhar o formato

**Contexto:** `03/04/2026` pode ser 3 de abril ou 4 de março; valor com três casas decimais
pode ser erro de exportação ou precisão real. Uma heurística acertaria em alguns arquivos e
erraria em silêncio em outros.
**Decisão:** recusar a linha, registrando motivo e número, sempre que o dado não casar com a
ficha declarada.
**Consequências:** o sistema falha de forma visível e auditável em vez de produzir números
errados — aceitável porque o propósito é conferência. O custo é exigir ficha correta antes da
primeira leitura.

### ADR-006 — Docker como ambiente de referência, não de desenvolvimento

**Contexto:** cinco integrantes em sistemas operacionais diferentes, e o projeto depende de
encoding, locale e interpretação de data — exatamente o que varia entre máquinas.
**Decisão:** desenvolvimento local com dependências travadas; Docker obrigatório antes de
abrir PR e na entrega.
**Consequências:** ciclo rápido no dia a dia e reprodutibilidade verificável na entrega. Exige
manter as duas definições de dependência em sincronia.

---

## Evidências de execução

Log da última execução da suíte: [`logs_testes.txt`](logs_testes.txt), gerado com

```bash
docker compose run --rm tests | tee logs_testes.txt
```

---

## Equipe

| Integrante | RA |
|---|:---|
| Diego de Souza | 22352472 |
| Felipe Marinho | 22353607 |
| Gustavo Lourenço | 22350665 |
| Italo Henrique Lins Carneiro | 22350066 |
| João Caio Dutra Gontijo | 22352975 |

A divisão de tarefas está nas [Issues](../../issues), com responsável atribuído em cada uma.
As unidades do sistema estão descritas em [`docs/SPEC.md`](docs/SPEC.md) §7.

---

<div align="center">

Projeto acadêmico — **Bootcamp III**, Turma B<br>
Centro Universitário de Brasília (CEUB) — 2026/2<br>

</div>
