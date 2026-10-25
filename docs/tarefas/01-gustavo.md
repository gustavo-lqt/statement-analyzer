# Gustavo Lourenço — Base compartilhada, API e integração

| | |
|---|---|
| **Issues** | #1 (U1 models), #9 (U5 API), #7 (guarda de arquitetura) |
| **Branch da base** | `entrega`, criada a partir da `main` |
| **Branch da API** | `feature/9-api`, criada a partir da `entrega` |
| **Antes de começar** | Ler [`00-LEIA-PRIMEIRO.md`](00-LEIA-PRIMEIRO.md) e [`CONTRATO.md`](CONTRATO.md) |

Você tem três papéis:
1. **Passo 0:** criar a base que destrava todo mundo. **Faça isso antes de todos.**
2. Implementar a API e o teste de arquitetura, em paralelo com os outros.
3. Integrar: revisar, fazer o merge dos PRs e entregar.

---

## Passo 0 — Base compartilhada (cerca de 1 hora, bloqueia o grupo)

### Arquivos que você cria

Todos copiados da **Parte A** do `CONTRATO.md`:
- `app/__init__.py`, `app/models.py`, `app/erros.py`
- `app/fichas/banco-a.json`, `app/fichas/banco-b.json`, `app/fichas/banco-c.json`
- `requirements.txt`, `pytest.ini`, `tests/conftest.py`
- remover `app/.gitkeep` e `tests/.gitkeep`

Atualize também a `docs/SPEC.md` para v1.2:
- registre as decisões D1–D7 do `CONTRATO.md` na §8;
- marque como resolvidas as dúvidas da §9;
- tire o `NOT NULL DEFAULT 0` de `saldo_inicial_centavos` no modelo de dados (§7).

### Prompt para a IA (passo 0)

```text
Você está no repositório statement-analyzer. Leia CLAUDE.md, docs/SPEC.md,
docs/tarefas/00-LEIA-PRIMEIRO.md e docs/tarefas/CONTRATO.md antes de qualquer coisa.

Tarefa: criar a base compartilhada da Entrega 2 (passo 0), sem implementar nenhuma lógica.

1. Crie exatamente os arquivos da "Parte A" do CONTRATO.md, com o conteúdo idêntico ao que
   está lá: app/__init__.py, app/models.py, app/erros.py, app/fichas/banco-a.json,
   app/fichas/banco-b.json, app/fichas/banco-c.json, requirements.txt, pytest.ini,
   tests/conftest.py. Salve tudo em UTF-8. Apague app/.gitkeep e tests/.gitkeep.
2. Não crie leitura.py, regras.py, consultas.py, db.py, api.py, Docker nem testes: cada um
   desses tem outro dono.
3. Atualize docs/SPEC.md para v1.2:
   - registre na §8 uma linha para cada decisão D1–D7 do CONTRATO.md (motivo: detalhar o
     contrato para permitir trabalho paralelo; PR: deixe "#«n»");
   - na §9, marque as dúvidas resolvidas, apontando a decisão correspondente;
   - no modelo de dados da §7, deixe saldo_inicial_centavos como "INTEGER" (aceita NULL).
   Não mude mais nada na SPEC.
4. Verifique: python -c "import app.models, app.erros; import json, pathlib;
   [json.loads(p.read_text(encoding='utf-8')) for p in pathlib.Path('app/fichas').glob('*.json')]"
5. Mostre o git status e proponha a mensagem de commit no padrão do CLAUDE.md
   (ex.: "Chore: base compartilhada da Entrega 2"). Não faça push.
```

### Depois do prompt

```bash
git switch main && git pull
git switch -c entrega
# (rode o prompt acima e revise o diff)
git add app requirements.txt pytest.ini tests/conftest.py docs/SPEC.md .gitignore
git commit -m "Chore: base compartilhada da Entrega 2"
git push -u origin entrega
```

Depois:
- **Avise o grupo que a `entrega` existe.** Mande no privado de cada integrante três
  arquivos: `00-LEIA-PRIMEIRO.md`, `CONTRATO.md` e o arquivo dele. A partir daí, os cinco
  trabalham em paralelo.
- A pasta `docs/tarefas/` fica só na sua máquina: o `.gitignore` commitado acima garante que
  ela nunca entre no repositório.
- No GitHub: atribua as Issues conforme a tabela do `00-LEIA-PRIMEIRO.md`.
- Ative a proteção da `main` (hoje ela **não** está protegida): PR obrigatório e uma
  aprovação.
- Feche o PR #13 (`develop → main`) sem merge.

---

## Passo 1 — API HTTP e teste de arquitetura (em paralelo com o grupo)

### Arquivos seus (só você cria e edita)

- `app/api.py`
- `tests/test_api.py`
- `tests/test_arquitetura.py`
- `docs/prompts/gustavo.md`

**Não toque** em `leitura.py`, `regras.py`, `consultas.py`, `db.py`, `gerador/`, Docker nem
nos arquivos congelados.

Enquanto os módulos dos outros não estão na `entrega`, os seus testes de API vão falhar
com `ImportError`. Isso é esperado. Escreva a API e os testes contra o contrato. Para
executar, rode `git merge origin/entrega` na sua branch depois que os PRs dos outros
entrarem.

### Prompt para a IA

```text
Você está no repositório statement-analyzer, na branch feature/9-api. Leia CLAUDE.md,
docs/SPEC.md (§6 inteira), docs/tarefas/00-LEIA-PRIMEIRO.md e docs/tarefas/CONTRATO.md
(seção "app/api.py" e a interface de leitura, regras, consultas e db).

Tarefa: implementar a camada HTTP (U5, Issue #9) e o teste de arquitetura (Issue #7).

Regras desta tarefa:
- Você só pode criar/editar: app/api.py, tests/test_api.py, tests/test_arquitetura.py.
  Não crie nem altere nenhum outro arquivo. app/leitura.py, app/regras.py,
  app/consultas.py e app/db.py estão sendo escritos por outras pessoas agora: importe-os
  e chame exatamente as funções e assinaturas do CONTRATO.md, sem criar versões próprias.
- app/models.py, app/erros.py, as fichas e tests/conftest.py são congelados. Se precisar
  de algo que não existe neles, PARE e me diga o que falta.
- api.py é fino: nenhuma regra de negócio, nenhum SQL, nenhum cálculo de consulta.
  Só faz a validação de parâmetros HTTP, chama o motor e converte para JSON.
- Implemente todas as rotas da tabela do CONTRATO.md, com status e corpos da SPEC §6.
  Todas as datas em JSON são "AAAA-MM-DD". Dinheiro é sempre int.
- Erros sempre no formato {"erro","mensagem","regra"} (SPEC §6.6), conforme a tabela de
  erros do CONTRATO.md. Registre exception handlers para ErroDominio, para a validação do
  FastAPI (RequestValidationError → 422 PARAMETRO_INVALIDO) e para Exception genérica
  (500 ERRO_INTERNO, sem vazar detalhes). "arquivo" ausente → 400 ARQUIVO_AUSENTE.
- Conexão pela dependência obter_conexao(), lendo STATEMENT_DB (padrão
  "dados/statement.db"). Nunca logue descrição de lançamento (RNF06).

Testes:
- tests/test_api.py: use fastapi.testclient.TestClient e substitua obter_conexao com
  app.dependency_overrides por uma conexão db.conectar(":memory:") nova em cada teste
  (fixture local no próprio arquivo, não no conftest). Monte os CSVs dentro do teste,
  com dados inventados, nos formatos das fichas banco-a, banco-b e banco-c.
  Cubra no mínimo: POST 201 com o contrato completo (incluindo recusas); POST com
  algumas linhas ruins; 422 NENHUMA_LINHA_VALIDA com regra "RN06"; 400
  BANCO_DESCONHECIDO; 400 ARQUIVO_AUSENTE; 422 ARQUIVO_VAZIO; GET lista; GET por id
  com paginação; DELETE 204 e depois 404; 404 em consulta de id inexistente; cada uma
  das 8 consultas devolvendo os campos da SPEC §6.5; top-despesas?n=0 → 422; maior-entrada
  sem entradas → null; saldo inicial ausente → dias-no-negativo com
  saldo_inicial_assumido true.
- tests/test_arquitetura.py (Issue #7): verifique, analisando o código-fonte com o módulo
  ast, que app/regras.py, app/consultas.py e app/leitura.py não importam fastapi,
  starlette, sqlite3 nem app.db/app.api, e que nenhum arquivo de app/ além de app/db.py
  contém SQL (CREATE/INSERT/SELECT/DELETE como string).
- Toda função de teste tem docstring citando o contrato (§6.x) ou a regra que verifica.

Ao terminar, rode pytest tests/test_arquitetura.py -q. tests/test_api.py só vai passar
depois que os módulos dos outros forem mergeados; me diga isso explicitamente em vez de
criar stubs. Proponha commits pequenos no padrão do CLAUDE.md. Não faça push.
```

### Prompt de revisão (rode depois de juntar tudo)

```text
Fiz o merge de origin/entrega na minha branch e agora todos os módulos existem. Rode
pytest -q (a suíte inteira). Para cada falha, diga se o problema está em app/api.py
(o meu), em um teste meu, ou em outro módulo. Corrija só o que for meu. Se for de outro
módulo, descreva a divergência em relação ao CONTRATO.md para eu repassar ao dono.
Não altere arquivos de outras pessoas.
```

---

## Passo 2 — Integração (por último)

1. Revise e faça o merge dos PRs dos outros na `entrega`, em qualquer ordem. Para cada PR,
   confira em "Files changed" que ele só toca arquivos do dono.
2. `git merge origin/entrega` na `feature/9-api` e rode o prompt de revisão.
3. Abra o PR `feature/9-api → entrega` e peça a revisão de outro integrante.
4. Na `entrega`, já com tudo dentro:
   - `docker compose run --rm tests | tee logs_testes.txt`
   - `docker compose up api` e teste em `http://localhost:8000/docs` com um arquivo gerado
     por `python -m gerador.gerar`
5. Atualize o `README.md`:
   - troque `<organizacao>` por `gustavo-lqt`;
   - corrija o exemplo de prompt;
   - aponte para `docs/prompts/`.
6. Abra o PR `entrega → main`.

## Pronto quando

- [ ] A `entrega` foi criada com a base e o grupo foi avisado
- [ ] As Issues estão atribuídas, a `main` está protegida e o PR #13 foi fechado
- [ ] `pytest -q` passa inteiro, também no Docker
- [ ] `logs_testes.txt` foi gerado e o README foi atualizado
- [ ] `docs/prompts/gustavo.md` está preenchido
