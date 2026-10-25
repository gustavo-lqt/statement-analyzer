# Entrega 2 — Divisão do trabalho

Todos leem este arquivo primeiro. Depois, cada integrante abre **o seu** arquivo:

| Integrante | Arquivo | Parte do sistema | Issues |
|---|---|---|---|
| Gustavo Lourenço | [`01-gustavo.md`](01-gustavo.md) | Base compartilhada (passo 0) + API HTTP + teste de arquitetura + integração | #1, #9, #7 |
| Diego de Souza | [`02-diego.md`](02-diego.md) | Leitura do CSV pela ficha + gerador de extratos sintéticos | #2, #11, #4 |
| Felipe Marinho | [`03-felipe.md`](03-felipe.md) | Motor de normalização (RN01–RN06) | #12, #3 |
| Italo Henrique | [`04-italo.md`](04-italo.md) | As oito consultas de análise (RN07–RN10) | #10 |
| João Caio | [`05-joao-caio.md`](05-joao-caio.md) | Persistência SQLite + Docker | #8, #6, #5 |

O contrato que todos seguem (classes, assinaturas, comportamento exato) está em
[`CONTRATO.md`](CONTRATO.md). **Ele vale tanto quanto a SPEC.** Os nomes de quem faz o quê
podem ser trocados à vontade: o que importa é que cada parte tenha um único dono.

### Onde salvar estes arquivos

Estas instruções **não vão para o repositório**. A pasta `docs/tarefas/` está no
`.gitignore`, e essa linha já chega a todos pelo commit do passo 0. Ninguém precisa editar o
`.gitignore`; se cada um editasse, daria conflito.

Depois de criar a sua branch (ver "Comandos Git"), salve na pasta `docs/tarefas/` do seu
clone os três arquivos que recebeu no privado:
- `00-LEIA-PRIMEIRO.md`
- `CONTRATO.md`
- o seu arquivo

Os prompts mandam a IA ler esses arquivos nesse caminho.

Confira com `git status`: os arquivos **não** devem aparecer na lista. Se aparecerem, a sua
branch não partiu da `entrega`.

---

## Por que dá para trabalhar em paralelo sem conflito

1. **Cada arquivo tem um único dono.** Você só cria e edita os arquivos listados no seu `.md`.
   Se dois integrantes nunca tocam o mesmo arquivo, o Git nunca gera conflito no merge.
2. **O contrato é fechado antes de qualquer um começar.** O Gustavo faz o *passo 0*: um
   commit pequeno na branch `entrega` com as classes (`app/models.py`), as exceções
   (`app/erros.py`), as três fichas de banco e as dependências. Todos partem desse commit e
   programam contra as mesmas classes e assinaturas, mesmo sem o código dos outros pronto.
3. **Cada um testa só a própria parte.** Cada integrante tem o próprio arquivo de teste e
   monta os próprios dados de teste dentro dele. Ninguém depende do código de outro para
   ver os testes passando na sua branch.
4. **Arquivos congelados:** `app/models.py`, `app/erros.py`, `app/fichas/*.json`,
   `requirements.txt`, `pytest.ini`, `tests/conftest.py`, `docs/SPEC.md`, `CLAUDE.md` e
   `.gitignore`.
   Ninguém altera esses arquivos numa branch de feature. Se achar que falta algo, **avise no
   grupo e abra uma Issue**. O Gustavo decide e faz a mudança na `entrega`, e todos
   atualizam a sua branch (ver "Atualizar sua branch" abaixo).

---

## Branches

```
main                      ← só recebe a entrega pronta, via PR
└── entrega             ← branch de integração (o Gustavo cria no passo 0)
    ├── feature/9-api              (Gustavo)
    ├── feature/2-leitura          (Diego)
    ├── feature/12-regras          (Felipe)
    ├── feature/10-consultas       (Italo)
    └── feature/8-db-docker        (João Caio)
```

A `develop` não é usada nesta entrega.

## Ordem

| Etapa | Quem | O quê |
|---|---|---|
| 0 | Gustavo | Cria a `entrega` com a base compartilhada e avisa o grupo. Leva cerca de 1 hora. |
| 1 | **Os cinco, ao mesmo tempo** | Cada um cria a sua branch a partir da `entrega` e implementa a sua parte |
| 2 | Cada um | Abre o PR da sua branch **para a `entrega`** (nunca para a `main`) |
| 3 | Outro integrante | Revisa e aprova o PR. O Gustavo faz o merge. A ordem dos merges não importa. |
| 4 | Gustavo | Por último, faz o merge da API, roda a suíte inteira no Docker e abre o PR `entrega → main` |

---

## Comandos Git (iguais para todos; troque o nome da branch)

```bash
# começar (depois que o Gustavo avisar que a entrega existe)
git fetch origin
git switch -c feature/2-leitura origin/entrega
# salve em docs/tarefas/ os arquivos recebidos no privado (ver "Onde salvar estes arquivos")

# instalar dependências (Python 3.12)
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt

# trabalhar e salvar
git add <seus arquivos>          # nunca use "git add ." sem conferir o git status
git commit -m "Implement: ..."
git push -u origin feature/2-leitura

# abrir o PR para a entrega
gh pr create --base entrega
```

### Atualizar sua branch (se o Gustavo avisar que a base mudou)

```bash
git fetch origin
git merge origin/entrega
```

Como ninguém mexe nos arquivos dos outros, esse merge não gera conflito.

---

## Regras para todos (e para a IA de todos)

- O arquivo de contexto do agente é o `CLAUDE.md` da raiz. A IA deve ler `CLAUDE.md`,
  `docs/SPEC.md` e `docs/tarefas/CONTRATO.md` antes de escrever código. O prompt de cada um
  já pede isso.
- **Exceção ao `CLAUDE.md` nesta entrega:** a regra "só conclua com a suíte inteira verde no
  Docker" vale na integração (etapa 4). Na sua branch, rode **só os seus testes**
  (`pytest tests/test_<seu>.py -q`), porque as partes dos outros ainda não existem nela.
- Dinheiro é sempre `int` em centavos. **Nunca `float`.**
- Nenhum dado bancário real, nem nos testes. Os dados de teste são inventados.
- Toda função de teste tem docstring citando a regra (RNxx) ou o contrato que verifica.
  Cada regra precisa de um teste do cenário principal **e** de casos de borda.
- Mensagem de commit: `Verbo: descrição em português` (ver tabela no `CLAUDE.md`).
- **Registro do uso de IA (obrigatório para o README):** cada um cria
  `docs/prompts/<seu-nome>.md` com os prompts que usou, o que a IA errou e o que você
  corrigiu à mão. Esse arquivo também é só seu.

## Descrição do PR (quatro seções, exigidas pelo `CLAUDE.md`)

```markdown
## O que faz
...
Closes #n

## Como foi feito (colaboração com IA)
Ferramenta usada, prompt principal (ou link para docs/prompts/<nome>.md) e o que precisou
de correção manual.

## Como validar
pytest tests/test_<arquivo>.py -q

## Impacto na SPEC
Nenhum / descreva.
```

## Checklist antes de abrir o PR

- [ ] `git diff --name-only origin/entrega` mostra **só** arquivos que são seus
- [ ] `pytest tests/test_<seu>.py -q` está verde
- [ ] Nenhum `float` em valor monetário (`grep -n float app/<seu>.py`)
- [ ] As assinaturas públicas estão idênticas às do `CONTRATO.md`
- [ ] `docs/prompts/<seu-nome>.md` está preenchido
