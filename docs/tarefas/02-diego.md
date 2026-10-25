# Diego de Souza — Leitura do CSV e gerador de extratos sintéticos

| | |
|---|---|
| **Issues** | #2 (U2 leitura), #11 (fichas de banco), #4 (U7 gerador de fixtures) |
| **Branch** | `feature/2-leitura`, criada a partir da `entrega` |
| **Começa quando** | O Gustavo avisar que a `entrega` existe (passo 0) |
| **Antes de começar** | Ler [`00-LEIA-PRIMEIRO.md`](00-LEIA-PRIMEIRO.md) e [`CONTRATO.md`](CONTRATO.md) |

## O que é a sua parte

Você escreve a porta de entrada do sistema. Ela recebe os bytes do arquivo CSV, aplica a
ficha do banco (delimitador, encoding, nome das colunas) e entrega cada linha recortada como
`LinhaCrua`. Você ainda **não valida** data nem valor: isso é do Felipe.

Você também escreve o gerador de extratos **inventados**. Ele será usado na demonstração e
nos testes de volume.

As três fichas (`app/fichas/*.json`) já vêm prontas na base. Use essas fichas e não altere
nenhuma delas.

## Arquivos seus (só você cria e edita)

- `app/leitura.py`
- `gerador/__init__.py`, `gerador/gerar.py`
- `tests/test_leitura.py`, `tests/test_gerador.py`
- `docs/prompts/diego.md`

**Não toque em mais nada.** Em especial, não altere `app/models.py`, `app/erros.py`,
`app/fichas/*.json` nem `tests/conftest.py`. Se achar que falta algo neles, avise o Gustavo.

## Passo a passo

```bash
git fetch origin
git switch -c feature/2-leitura origin/entrega
# salve em docs/tarefas/ os 3 arquivos que você recebeu no privado:
# 00-LEIA-PRIMEIRO.md, CONTRATO.md e o seu arquivo (a pasta é ignorada pelo git)
python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt
```

## Prompt para a IA

```text
Você está no repositório statement-analyzer, na branch feature/2-leitura. Leia CLAUDE.md,
docs/SPEC.md, docs/tarefas/00-LEIA-PRIMEIRO.md e docs/tarefas/CONTRATO.md (Parte A
inteira e as seções "app/leitura.py" e "gerador/" da Parte B).

Tarefa: implementar a leitura de CSV pela ficha do banco (U2, Issues #2 e #11) e o
gerador de extratos sintéticos (U7, Issue #4).

Regras desta tarefa:
- Você só pode criar/editar: app/leitura.py, gerador/__init__.py, gerador/gerar.py,
  tests/test_leitura.py, tests/test_gerador.py. Não crie nem altere nenhum outro arquivo.
- app/models.py, app/erros.py, app/fichas/*.json e tests/conftest.py são congelados. Use
  as classes e exceções que já existem. Se precisar de algo que não existe, PARE e me
  diga o que falta.
- As assinaturas públicas são exatamente as do CONTRATO.md. Implemente as 7 regras de
  ler() e as regras de carregar_ficha() descritas lá, sem inventar comportamento.
- app/leitura.py não pode importar fastapi nem acessar banco de dados. ler() é um
  gerador e decodifica linha a linha (uma linha com encoding inválido vira LinhaCrua com
  erro=ENCODING_INVALIDO, e a leitura continua).
- Nunca logue o conteúdo das linhas (RNF06).
- Gerador: random.Random(semente), mesma semente = mesmos bytes; valores gerados como
  int em centavos e só formatados como texto na saída (nenhum float); descrições de uma
  lista fixa e fictícia, incluindo gastos repetidos (3+ vezes, valores próximos);
  linhas inválidas opcionais (data inexistente, três casas decimais, linha truncada).
  CLI com argparse: --banco --linhas --semente --invalidas --saida. Use
  app.leitura.carregar_ficha para obter a ficha. Nenhum dado bancário real.

Testes (só nos seus arquivos; fixtures locais, não no conftest):
- tests/test_leitura.py: carregar as 3 fichas; BancoDesconhecido para nome inexistente
  e para "../x"; listar_fichas; ler um CSV de cada banco montado no próprio teste
  (banco-a em latin-1 com "Histórico" no cabeçalho); \r\n e \n; BOM; linhas em branco
  puladas sem perder a numeração; ArquivoVazio (b"", só cabeçalho, só linhas em branco);
  EncodingInvalido no cabeçalho; byte inválido numa linha do meio → ENCODING_INVALIDO
  só naquela linha e as seguintes continuam; LINHA_TRUNCADA (menos e mais células);
  cabeçalho sem uma coluna da ficha → COLUNA_AUSENTE em todas as linhas; célula entre
  aspas contendo o delimitador; campos sem strip.
- tests/test_gerador.py: mesma semente → bytes idênticos; semente diferente → bytes
  diferentes; para cada uma das 3 fichas, o CSV gerado passa por ler() sem nenhum erro
  quando invalidas=0, com o número de linhas pedido; com invalidas=N, exatamente N
  linhas defeituosas. (Não valide data/valor com app.regras: esse módulo é de outra
  pessoa e ainda não existe na sua branch. Para contar as linhas inválidas, use o
  próprio gerador, por exemplo devolvendo ou registrando as posições.)
- Toda função de teste tem docstring citando a regra (RF01, RNF05, RN05...) ou o item do
  CONTRATO.md que verifica.

Ao terminar, rode: pytest tests/test_leitura.py tests/test_gerador.py -q. Não rode a
suíte inteira: os módulos dos outros ainda não estão nesta branch. Depois rode
python -m gerador.gerar --banco banco-a --linhas 50 --semente 1 --invalidas 3 --saida dados/teste.csv
e mostre as 5 primeiras linhas. Proponha commits pequenos no padrão do CLAUDE.md
(ex.: "Implement: leitura de CSV aplicando a ficha do banco"). Não faça push.
```

## Prompt de revisão (antes de abrir o PR)

```text
Revise app/leitura.py e gerador/gerar.py contra docs/tarefas/CONTRATO.md, item por item
(as 7 regras de ler, carregar_ficha, gerador). Liste cada regra, diga onde ela está
implementada e qual teste a cobre. Aponte qualquer regra sem teste, qualquer uso de float
em valor e qualquer arquivo alterado fora da minha lista (git diff --name-only
origin/entrega). Corrija só o que estiver nos meus arquivos.
```

## Abrir o PR

```bash
git push -u origin feature/2-leitura
gh pr create --base entrega --title "Implement: leitura de CSV e gerador sintético"
```

Na descrição: `Closes #2`, `Closes #11`, `Closes #4` e as quatro seções do
`00-LEIA-PRIMEIRO.md`.

## Pronto quando

- [ ] `pytest tests/test_leitura.py tests/test_gerador.py -q` está verde
- [ ] `git diff --name-only origin/entrega` mostra só os seus arquivos
- [ ] `docs/prompts/diego.md` está preenchido
