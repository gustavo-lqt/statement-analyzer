# Changelog

## [v1.0.0] — 25/10/2026

Primeira versão estável: o sistema completo especificado na [`docs/SPEC.md`](docs/SPEC.md)
(v1.5, as-built).

### Funcionalidades

- `POST /extratos`: lê um extrato CSV pela ficha do banco (`banco-a`, `banco-b` ou
  `banco-c`), normaliza os lançamentos e recusa individualmente as linhas inválidas, com
  número da linha e motivo (RN01–RN06).
- `GET /extratos`, `GET /extratos/{id}` (com paginação) e `DELETE /extratos/{id}` (em
  cascata).
- As oito consultas: `resumo`, `saldo`, `maior-entrada`, `maior-despesa`, `top-despesas`,
  `por-semana`, `dias-no-negativo` e `repetidos` (RN07–RN10).
- Formato único de erro em todas as respostas, inclusive 404, 405 e 500 (RNF01).
- Gerador de extratos sintéticos com semente fixa: `python -m gerador.gerar`.
- Docker: `docker compose up api` e `docker compose run --rm tests`.

### Qualidade

- 282 testes automatizados, 100% aprovados ([`logs_testes.txt`](logs_testes.txt)).
- 99% de cobertura em `app/` e `gerador/`; 95% em `app/regras.py` e 100% em
  `app/consultas.py` (a RNF07 pede 80%).
- Guarda de arquitetura: o motor não importa HTTP nem banco, e só `app/db.py` tem SQL.

### Correções feitas na revisão

- Dígitos não ASCII (`"1²"`) derrubavam o envio com 500; agora a linha é recusada (#18).
- Um `\r` solto fora de aspas derrubava a leitura; agora a linha é recusada (#19).
- Rota inexistente e método não aceito agora saem no formato único de erro.

### Documentação

- README com instalação, configuração, execução, arquitetura e ADRs.
- SPEC as-built, com o registro de refinamentos (§8).
- [`docs/RELATORIO.md`](docs/RELATORIO.md): relatório técnico-ético e de encerramento.
- [`docs/prompts/`](docs/prompts/): registro de uso de IA de cada integrante.
