# Registro de uso de IA — Diego de Souza

**Parte:** leitura do CSV pela ficha do banco (U2, Issues #2 e #11) e gerador de extratos
sintéticos (U7, Issue #4). **Branch:** `feature/2-leitura`, com PR para a `entrega`.

## Ferramenta

Claude Code (modelo Claude Opus 5.5), pela extensão do VS Code, com o plugin Superpowers. O
plugin conduz um fluxo fixo: plano de implementação, TDD (cada teste visto falhando antes do
código), verificação com evidência e revisão. Antes de escrever código, o agente leu
`CLAUDE.md`, `docs/SPEC.md`, `docs/tarefas/00-LEIA-PRIMEIRO.md` e `docs/tarefas/CONTRATO.md`.

## Prompts usados

### 1. Pedido inicial (resumo)

Implementar os requisitos do `02-diego.md` com o Superpowers, numa branch própria, com os
commits sem a IA como coautora e sem mexer na `main`. Interrompi essa primeira execução ainda
na fase de planejamento e reenviei o pedido com o prompt abaixo, precedido de "Siga todos os
passos do prompt abaixo" e do pedido para criar a branch e fazer os commits nela.

### 2. Prompt de implementação (do `02-diego.md`, na íntegra)

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

### 3. Prompt de revisão (do `02-diego.md`, na íntegra)

Enviado junto com a autorização para fazer o push e abrir o PR.

```text
Revise app/leitura.py e gerador/gerar.py contra docs/tarefas/CONTRATO.md, item por item
(as 7 regras de ler, carregar_ficha, gerador). Liste cada regra, diga onde ela está
implementada e qual teste a cobre. Aponte qualquer regra sem teste, qualquer uso de float
em valor e qualquer arquivo alterado fora da minha lista (git diff --name-only
origin/entrega). Corrija só o que estiver nos meus arquivos.
```

## O que a IA errou ou deixou passar

- **`carregar_ficha` quebrava com um campo a mais na ficha.** Montava `FichaBanco(**dados)`,
  que levanta `TypeError` com uma chave desconhecida. A própria IA percebeu relendo o código
  antes do commit; agora campos extras são ignorados (`test_carregar_ficha_ignora_campo_extra`).
- **Os testes do gerador não viam o sentido do valor.** Com crédito e débito trocados na
  banco-c, ou `D` e `C` trocados na banco-b, nenhum teste falhava. A própria IA notou a lacuna
  antes do commit e a confirmou com teste de mutação (quebrar o código de propósito e ver se
  algum teste falha); ficou coberta por `test_salario_entra_e_compra_no_mercado_sai`.
- **Quatro regras sem teste**, apontadas pelo prompt de revisão: `app/leitura.py` não importar
  FastAPI nem acessar o banco, nunca registrar o conteúdo das linhas (RNF06), leitura de
  100.000 linhas no prazo e em streaming (RNF04) e descrições do gerador vindas de uma lista
  fixa. Cada uma ganhou um teste, validado por mutação.
- **A branch nasceu rastreando `origin/entrega`.** Um `git push` sem argumentos poderia mirar
  a `entrega`; a IA desfez o vínculo e o push foi feito com `git push -u origin feature/2-leitura`.

## Decisões da IA onde o contrato não fecha

Todas têm teste e ficam abertas à revisão de quem aprovar o PR.

- `ler()` decodifica a linha antes de tudo, depois aplica `COLUNA_AUSENTE` e só então
  `LINHA_TRUNCADA`. Uma linha que nem decodifica continua `ENCODING_INVALIDO` mesmo com coluna
  ausente no cabeçalho.
- `carregar_ficha` exige que o nome esteja em `listar_fichas()`. No Windows o sistema de
  arquivos ignora maiúsculas e `"BANCO-A"` abriria `banco-a.json`; no Docker, não.
- `ler()` remove um `\r` no fim da linha mesmo sem `\n` depois.
- O gerador expõe também `gerar_extrato()`, que devolve o CSV e as linhas defeituosas, para os
  testes contarem as inválidas pelo próprio gerador. `gerar_csv` mantém a assinatura do
  contrato.
- No gerador, a quebra de linha é `\r\n`, a data inexistente é `31/09/2026` no formato da
  ficha e a terceira casa decimal pode ser zero (`12,340`, que o contrato também trata como
  `PRECISAO_INVALIDA`).
- Na CLI, só `--invalidas` é opcional (padrão 0), e erro de uso sai com código 2.

## Pendente: proposta de mudança no contrato

Um `\r` solto no meio de uma célula sem aspas, ou um arquivo que usa só `\r` como quebra de
linha, faz o módulo `csv` levantar erro e derruba a leitura inteira, o que contraria a RN05. O
contrato não define motivo de recusa para esse caso e o prompt proíbe inventar comportamento,
então não foi tratado. Proposta: recusar a linha como `LINHA_TRUNCADA` ("a linha nem pôde ser
recortada").

## O que eu corrigi à mão

Nenhuma linha de código foi editada à mão até a abertura do PR. Minhas intervenções foram de
direção: interromper a primeira execução e reenviar o pedido com o prompt completo, pedir os
commits sem a IA como coautora e autorizar o push e a abertura do PR junto com o prompt de
revisão.
