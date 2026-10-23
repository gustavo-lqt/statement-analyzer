# Registro do uso de IA — João Caio

## Prompt principal

> Leia `CLAUDE.md`, a RNF03 e o modelo de dados da `docs/SPEC.md`, os ADRs 004 e 006
> do `README.md` e o contrato da Entrega 2. Implemente a persistência SQLite em
> `app/db.py`, os testes em `tests/test_db.py` e o ambiente Docker em `Dockerfile`,
> `.dockerignore` e `docker-compose.yml`, sem alterar outros arquivos.
>
> Siga as assinaturas do contrato; use apenas `sqlite3`, parâmetros SQL `?`, chaves
> estrangeiras ativas e uma transação atômica para salvar extrato, lançamentos e recusas.
> Preserve datas como ISO na persistência, valores monetários como inteiros e saldo
> inicial ausente como `NULL`. Teste as operações e o rollback. Configure os serviços
> `api` e `tests` conforme o contrato.

## Erros da IA e correções

- Inicialmente procurei os documentos do contrato em `docs/tarefas/`, embora eles
  estivessem em `docs/`; corrigi o caminho e li os documentos disponíveis antes de
  continuar.
- A primeira pasta de trabalho não tinha metadados Git. Em vez de tentar criar commits
  nela, clonei o repositório a partir da branch `entrega`, criei `feature/8-db-docker`
  e transferi somente os cinco arquivos permitidos antes de commitar.
- O comando `pytest` direto não estava no `PATH`; usei `python -m pytest`, que executou
  os nove testes com sucesso.
- O Docker Desktop Engine não estava acessível durante a validação. A configuração do
  Compose foi validada, mas a construção e execução dos testes dentro do Docker ficaram
  pendentes.
- O pull request foi inicialmente criado com destino `main`. O branch de destino do PR
  foi corrigido para `entrega`.

## Revisão manual

Conferi o contrato do módulo SQLite, os parâmetros das consultas, o rollback, a
conversão de datas e `NULL`, o escopo dos arquivos, e validei os testes locais e a
sintaxe do Docker Compose.
