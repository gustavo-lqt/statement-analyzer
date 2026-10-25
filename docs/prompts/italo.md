# Registro de uso de IA — Italo Henrique

**Parte:** as oito consultas de análise, motor puro (U4, Issue #10, RN07–RN10).
**Branch:** `feature/10-consultas`, com PR #17 para a `entrega`.

## Ferramenta

Claude Code (modelo Claude Opus 5.5), pela extensão do VS Code. Antes de escrever código, o
agente leu `CLAUDE.md`, `docs/SPEC.md`, `docs/tarefas/00-LEIA-PRIMEIRO.md` e
`docs/tarefas/CONTRATO.md`.

## Prompts usados

### 1. Primeira rodada: `normalizar_descricao`, `resumo`, `saldo`, `maior_entrada`, `maior_despesa`, `top_despesas`

Commits `dea9aad`, `bbf6e4a`, `6b39003` e `8654c96`.

O prompt original dessa rodada não ficou salvo. Este resumo foi reconstruído a partir do
histórico do git:

- `dea9aad`: `normalizar_descricao` e `resumo`, com a divisão truncada em direção a zero
  (`_divisao_para_zero`) e 9 testes (normalização e média do exemplo da SPEC).
- `bbf6e4a`: `saldo` por blocos de dia (RN08), com 7 testes (lista embaralhada, mesmo dia
  cruzando o zero, saldo exatamente zero, empate de mínimo, lista vazia).
- `6b39003`: `maior_entrada`, `maior_despesa` e `top_despesas` (RN10), **sem testes**.
- `8654c96`: só acrescenta os imports dessas três funções no teste, apesar da mensagem
  "nova consulta para despesas por categoria".

A rodada parou aí: `por_semana`, `dias_no_negativo` e `repetidos` ficaram de fora, e a
cobertura de `app/consultas.py` ficou em 67%.

### 2. Prompt de implementação (do `04-italo.md`, na íntegra)

Enviado junto com a lista de pendências do item 3, para completar o que faltava.

```text
Você está no repositório statement-analyzer, na branch feature/10-consultas. Leia
CLAUDE.md, docs/SPEC.md (§4 RN07–RN10, §6.5 e a tabela de rastreabilidade da §7),
docs/tarefas/00-LEIA-PRIMEIRO.md e docs/tarefas/CONTRATO.md (decisões D2–D5, Parte A e a
seção "app/consultas.py" da Parte B).

Tarefa: implementar o motor puro de análise (U4, Issue #10): normalizar_descricao,
resumo, saldo, maior_entrada, maior_despesa, top_despesas, por_semana,
dias_no_negativo e repetidos.

Regras desta tarefa:
- Você só pode criar/editar: app/consultas.py e tests/test_consultas.py. Não crie nem
  altere nenhum outro arquivo.
- app/models.py e app/erros.py são congelados. Devolva exatamente os dataclasses de lá
  (Resumo, Periodo, Saldo, Semana, DiasNoNegativo, PeriodoNegativo, GrupoRepetido) e
  use ParametroInvalido. Se precisar de algo que não existe, PARE e me diga o que falta.
- As assinaturas e o comportamento são exatamente os do CONTRATO.md, incluindo
  desempates, ordem da resposta, o que acontece com lista vazia, a semana de segunda a
  domingo recortada ao período e o algoritmo exato de repetidos
  (10 * abs(v*k - S) <= abs(S), média não recalculada). Não invente comportamento.
- Módulo puro: proibido importar fastapi, sqlite3, app.db, app.api, app.leitura ou
  app.regras, e proibido fazer I/O.
- NENHUM float, nem em média nem em porcentagem. Divisão com truncamento em direção a
  zero usando só inteiros (cuidado: em Python, -7 // 2 == -4; o esperado é -3).
- RN08: saldo por blocos de dia; nunca observe saldo intermediário dentro de um dia.
- RN10: o resultado não pode depender da ordem da lista de entrada (a não ser o último
  desempate "ordem da lista" previsto no contrato).
- normalizar_descricao: use unicodedata (NFKD) para tirar acentos.
- Toda função pública tem docstring citando a RN/RF que implementa.

Testes em tests/test_consultas.py (fixtures locais; Lancamento criados no próprio teste,
com descrições inventadas; datas em setembro de 2026):
- normalizar_descricao: acentos, Ç, pontuação, espaços repetidos, caixa.
- resumo: cenário normal conferindo a média com o exemplo da SPEC (-423410 em 30 dias →
  -14113); um único dia; lista vazia; valor zero.
- saldo / RN08: saldo corrente por data com a lista embaralhada; dois lançamentos no
  mesmo dia cruzando o zero (+100 e -150 com saldo 0 → o dia termina em -50, e um saldo
  intermediário não pode aparecer); conta que nunca fica negativa; saldo que chega
  exatamente a zero (não é negativo); empate de mínimo → dia mais antigo; lista vazia.
- maior_entrada / maior_despesa / RN10: único; empate de valor → data mais antiga; o
  mesmo resultado com a lista invertida; sem entradas → None.
- top_despesas: ordem; desempate; n maior que o total; n=0 e n=101 → ParametroInvalido;
  n=1 e n=100 aceitos.
- por_semana / D2: período que começa numa terça (2026-09-01 → primeira semana termina
  em 2026-09-06); semana do meio sem lançamento entra zerada; última semana parcial;
  saldo não acumulado; lista vazia.
- dias_no_negativo / RN07 / RN08: saldo inicial informado; None → assumido True e usa 0;
  dia sem lançamento herda o saldo negativo e conta; dois períodos separados; saldo zero
  não conta; exemplo da SPEC (14 a 17 → 4 dias).
- repetidos / RN09: três iguais formam grupo; duas não formam; valor 11% acima da média
  fica fora; exatamente 10% entra (monte números que dão 10% exato); descrições que só
  diferem em acento/pontuação/caixa caem no mesmo grupo; entradas são ignoradas; ordem
  da resposta; valor_medio truncado em direção a zero.
- Toda função de teste tem docstring citando a regra que verifica.

Ao terminar, rode: pytest tests/test_consultas.py -q --cov=app.consultas --cov-report=term-missing
e mostre a cobertura (meta: 80% ou mais, RNF07). Não rode a suíte inteira: os módulos
dos outros ainda não estão nesta branch. Proponha commits pequenos no padrão do CLAUDE.md
(ex.: "Implement: consulta saldo com blocos por dia (RN08)"). Não faça push.
```

### 3. Lista de pendências da primeira rodada (enviada junto com o prompt 2)

```text
O que falta:
Faltam 3 das 8 funções: por_semana, dias_no_negativo e repetidos. A API chama as três,
então sem elas o import da sua API quebra.
maior_entrada, maior_despesa e top_despesas não têm nenhum teste. Os imports foram
adicionados, mas os testes não.
A cobertura está em 67%, abaixo da meta de 80% (RNF07). Os itens 1 e 2 resolvem isso.
Falta o docs/prompts/italo.md.
A mensagem do último commit está errada. "Implement: nova consulta para despesas por
categoria" não corresponde ao que o commit faz: ele só acrescenta imports no teste. Além
disso, categorização está explicitamente fora do escopo do projeto (SPEC §2), e um commit
com esse nome no histórico pode chamar a atenção do professor. Não precisa reescrever o
histórico, mas vale avisar o Italo para não implementar nada de categoria.
```

### 4. Abertura do PR

Na sequência: "abra o pull request" (com o trecho "Abrir o PR" e "Pronto quando" do
`04-italo.md`), "instale o gh e faça o pull request" e "faça o docs/prompts/italo.md".

## Resultado

- `por_semana`, `dias_no_negativo` e `repetidos` implementados; testes para todas as nove
  funções públicas.
- `pytest tests/test_consultas.py -q --cov=app.consultas`: **55 testes verdes, 100% de
  cobertura** em `app/consultas.py` (antes, 67%).
- `grep -n "float\|round(" app/consultas.py` não encontra nada.

## O que a IA errou ou deixou passar

- **Primeira rodada incompleta.** Faltavam três das oito consultas, e `maior_entrada`,
  `maior_despesa` e `top_despesas` não tinham nenhum teste, só os imports. A cobertura ficou
  em 67%. Foi corrigido na segunda rodada.
- **Mensagem de commit errada no `8654c96`.** "Implement: nova consulta para despesas por
  categoria" descreve algo que o commit não faz: ele só acrescenta imports no teste.
  Categorização está fora do escopo (SPEC §2) e não existe nada disso no código. O histórico
  não foi reescrito, porque a branch já estava no `origin`.
- **A docstring de `_divisao_para_zero` dizia "(não usa float)".** Isso faria o
  `grep -n "float\|round("` do checklist acusar o arquivo sem haver float nenhum. A docstring
  foi reescrita antes do push.
- **O `gh` não estava instalado.** Na primeira tentativa de abrir o PR, a IA fez o push e
  gerou um link do GitHub com título e descrição já preenchidos. Depois instalou o `gh` com
  `winget`, autenticou pelo navegador (`gh auth login --web`) e abriu o PR #17.

## Decisões da IA onde o contrato não fecha

Todas têm teste e ficam abertas à revisão de quem aprovar o PR.

- `dias_no_negativo` com lista vazia devolve `saldo_inicial_centavos` igual ao saldo
  informado (ou 0 se `None`), além de 0 dias e `[]`. O contrato só fala dos dias e dos
  períodos.
- `top_despesas` valida `n` antes de olhar a lista, então `top_despesas([], 0)` também levanta
  `ParametroInvalido`.
- `por_semana` com um único dia devolve uma semana de um dia (`de == ate`).
- Em `repetidos`, a `descricao_normalizada` do grupo é a própria chave de agrupamento
  (`normalizar_descricao` da descrição), não a descrição original do primeiro lançamento.

## O que eu corrigi à mão

Não editei nenhuma linha de código à mão. O meu trabalho foi revisar e decidir:

- **Conferi o resultado da primeira rodada** e vi o que faltava: três das oito consultas,
  os testes de `maior_entrada`, `maior_despesa` e `top_despesas` e a cobertura mínima de 80%
  (estava em 67%).
- **Pedi a segunda rodada**, mandando o prompt completo do `04-italo.md` junto com a lista de
  pendências.
- **Notei a mensagem errada do commit `8654c96`.** "Despesas por categoria" não corresponde ao
  que o commit faz e é justamente algo fora do escopo (SPEC §2). Decidi não reescrever o
  histórico, porque a branch já estava no `origin`, e registrar o erro aqui e na descrição do
  PR. Nada de categoria foi implementado.
- **Conferi o PR #17 e o checklist "Pronto quando"**: testes verdes, cobertura, grep de
  `float`/`round(` e o diff só com os meus arquivos. Autorizei os commits, o push e a abertura
  do PR, e fiz o login do `gh` no navegador.
