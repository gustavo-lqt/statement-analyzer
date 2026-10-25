# João Caio Dutra Gontijo — Persistência SQLite e Docker

| | |
|---|---|
| **Issues** | #8 (U6 persistência), #6 (ambiente Docker), #5 (harness: comando único da suíte) |
| **Branch** | `feature/8-db-docker`, criada a partir da `entrega` |
| **Começa quando** | O Gustavo avisar que a `entrega` existe (passo 0) |
| **Antes de começar** | Ler [`00-LEIA-PRIMEIRO.md`](00-LEIA-PRIMEIRO.md) e [`CONTRATO.md`](CONTRATO.md) |

## O que é a sua parte

Você tem duas partes.

1. **`app/db.py`:** é o único lugar do projeto com SQL. Ele grava um extrato com os seus
   lançamentos e recusas (tudo ou nada, numa transação), lista, busca e apaga em cascata.
   A API do Gustavo chama as suas funções exatamente como estão no contrato.
2. **O ambiente Docker:**
   - `docker compose up api` sobe a API;
   - `docker compose run --rm tests` roda a suíte inteira. É o comando único exigido pela
     RNF03 e o que o professor vai executar.

Você não depende de ninguém. Os seus testes criam os `ResultadoLeitura` e os `Lancamento` à
mão.

## Arquivos seus (só você cria e edita)

- `app/db.py`
- `tests/test_db.py`
- `Dockerfile`, `.dockerignore`, `docker-compose.yml`
- `docs/prompts/joao-caio.md`

**Não toque em mais nada.** Em especial, não altere `requirements.txt`, `app/models.py`,
`app/erros.py` nem `tests/conftest.py`. Se precisar de outra dependência, avise o Gustavo:
dependência nova exige um ADR.

## Passo a passo

```bash
git fetch origin
git switch -c feature/8-db-docker origin/entrega
# salve em docs/tarefas/ os 3 arquivos que você recebeu no privado:
# 00-LEIA-PRIMEIRO.md, CONTRATO.md e o seu arquivo (a pasta é ignorada pelo git)
python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt
```

É preciso ter o Docker Desktop instalado e rodando.

## Prompt para a IA

```text
Você está no repositório statement-analyzer, na branch feature/8-db-docker. Leia
CLAUDE.md, docs/SPEC.md (§5 RNF03, §7 "Modelo de dados", ADR-004 e ADR-006 no README),
docs/tarefas/00-LEIA-PRIMEIRO.md e docs/tarefas/CONTRATO.md (decisão D3, Parte A e as
seções "app/db.py" e "Docker" da Parte B).

Tarefa: implementar a persistência em SQLite (U6, Issue #8) e o ambiente Docker com o
comando único da suíte (Issues #6 e #5).

Regras desta tarefa:
- Você só pode criar/editar: app/db.py, tests/test_db.py, Dockerfile, .dockerignore,
  docker-compose.yml. Não crie nem altere nenhum outro arquivo (nem requirements.txt).
- app/models.py e app/erros.py são congelados. Devolva exatamente Extrato, Lancamento e
  Recusa de lá. Se precisar de algo que não existe, PARE e me diga o que falta.
- As assinaturas e o comportamento de app/db.py são exatamente os do CONTRATO.md.
  Schema = o da SPEC §7 com IF NOT EXISTS e saldo_inicial_centavos aceitando NULL (D3).
- Use só sqlite3 da biblioteca padrão, com parâmetros "?" em toda query (nunca formate SQL
  com f-string). PRAGMA foreign_keys = ON em toda conexão. check_same_thread=False.
- salvar_extrato grava extrato + lançamentos + recusas numa única transação (executemany
  para os lançamentos); se qualquer insert falhar, faz rollback e a exceção sobe.
- Datas: date.isoformat() ao gravar; date.fromisoformat() ao ler. Dinheiro é int.
- db.py não importa fastapi nem app.regras/app.consultas/app.leitura/app.api.
- Nunca logue descrição de lançamento (RNF06).

Docker:
- Dockerfile: python:3.12-slim, WORKDIR /code, instala requirements.txt numa camada
  separada (cache), copia app/, gerador/, tests/, pytest.ini. Variáveis
  PYTHONDONTWRITEBYTECODE=1 e PYTHONUNBUFFERED=1. Use COPY de pastas que podem ainda não
  existir na sua branch (gerador/) de forma que o build não quebre: por exemplo, copiar o
  projeto inteiro com "COPY . ." e deixar o .dockerignore filtrar.
- .dockerignore: .git, .venv, venv, dados, __pycache__, .pytest_cache, *.db, htmlcov.
- docker-compose.yml: serviço "api" (uvicorn app.api:app --host 0.0.0.0 --port 8000,
  porta 8000:8000, volume ./dados:/code/dados, STATEMENT_DB=/code/dados/statement.db) e
  serviço "tests" (pytest -q --cov=app.regras --cov=app.consultas
  --cov-report=term-missing), ambos com build da mesma imagem.

Testes em tests/test_db.py (fixture local com conectar(":memory:") nova em cada teste;
ResultadoLeitura/Lancamento/Recusa montados à mão, com dados inventados):
- conectar cria as 3 tabelas e o índice; foreign_keys está ligado; conectar num arquivo
  em pasta inexistente (use tmp_path) cria a pasta; chamar o schema duas vezes não falha.
- salvar_extrato devolve Extrato com id e contadores certos; saldo_inicial None é gravado
  como NULL e volta None; datas voltam como date; valores voltam como int idênticos
  (inclusive negativos e grandes).
- Transação: force uma falha no meio (ex.: um Lancamento com descricao=None viola NOT
  NULL) e verifique que nenhuma linha de nenhuma tabela ficou gravada.
- listar_extratos em ordem de id; obter_extrato inexistente → None.
- listar_lancamentos ordenado por data e depois id (insira fora de ordem); limite e
  offset; limite=None traz todos; extrato inexistente → [].
- listar_recusas ordenado por linha, com linha/motivo/conteudo corretos (motivo como
  MotivoRecusa).
- apagar_extrato: True e cascata (lançamentos e recusas somem); de novo → False; apagar
  um extrato não afeta os outros.
- Toda função de teste tem docstring citando o requisito (RF04, RF05, RF06, ADR-004...).

Ao terminar:
1. pytest tests/test_db.py -q
2. docker compose build
3. docker compose run --rm tests pytest tests/test_db.py -q  (só os seus testes: os
   módulos dos outros ainda não estão nesta branch, e app/api.py ainda é de outra
   pessoa, então NÃO tente subir o serviço api agora nem crie um api.py provisório)
Mostre as saídas. Proponha commits pequenos no padrão do CLAUDE.md
(ex.: "Implement: persistência SQLite com gravação transacional",
"Chore: ambiente Docker com serviços api e tests"). Não faça push.
```

## Prompt de revisão (antes de abrir o PR)

```text
Revise app/db.py contra docs/tarefas/CONTRATO.md ("app/db.py") e a SPEC §7. Confira:
toda query usa parâmetros "?"; não existe SQL montado com f-string ou %; foreign_keys
ligado; a transação de salvar_extrato é atômica (aponte o teste que prova); as datas e o
NULL do saldo fazem a ida e volta corretamente. Revise o Dockerfile e o compose contra o
contrato. Confira com git diff --name-only origin/entrega que só os meus arquivos
mudaram. Corrija só o que estiver nos meus arquivos.
```

## Abrir o PR

```bash
git push -u origin feature/8-db-docker
gh pr create --base entrega --title "Implement: persistência SQLite e ambiente Docker"
```

Na descrição: `Closes #8`, `Closes #6`, `Closes #5` e as quatro seções do
`00-LEIA-PRIMEIRO.md`.

## Depois do merge de todos (junto com o Gustavo)

Quando a `entrega` tiver todos os módulos, rode `docker compose run --rm tests` e
`docker compose up api` para confirmar que o ambiente funciona com o sistema inteiro. Se
algo do Docker falhar, a correção é sua, numa branch `feature/6-ajuste-docker`.

## Pronto quando

- [ ] `pytest tests/test_db.py -q` está verde
- [ ] `docker compose build` funciona e `docker compose run --rm tests pytest tests/test_db.py -q` passa
- [ ] `grep -n 'f"\|%s' app/db.py` não mostra SQL montado com formatação
- [ ] `git diff --name-only origin/entrega` mostra só os seus arquivos
- [ ] `docs/prompts/joao-caio.md` está preenchido
