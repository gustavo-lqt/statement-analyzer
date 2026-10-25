# Italo Henrique — As oito consultas de análise (RN07–RN10)

| | |
|---|---|
| **Issue** | #10 (U4 consultas) |
| **Branch** | `feature/10-consultas`, criada a partir da `entrega` |
| **Começa quando** | O Gustavo avisar que a `entrega` existe (passo 0) |
| **Antes de começar** | Ler [`00-LEIA-PRIMEIRO.md`](00-LEIA-PRIMEIRO.md) e [`CONTRATO.md`](CONTRATO.md) |

## O que é a sua parte

Você escreve as respostas que o usuário vê. São oito funções que recebem uma lista de
`Lancamento` e devolvem os agregados:
- resumo, saldo, maior entrada, maior despesa, top despesas;
- por semana, dias no negativo, gastos repetidos.

As cinco primeiras são da Entrega 2. As três últimas adiantam a Entrega 3 (decisão D7 do
contrato).

Seu módulo é **puro**: não lê arquivo, não acessa banco e não conhece HTTP. Por isso você
não depende de ninguém. Você mesmo cria as listas de `Lancamento` nos testes.

O ponto delicado é a exatidão:
- as fronteiras de cada regra: exatamente 10%, exatamente 3 ocorrências, saldo exatamente
  zero;
- os desempates determinísticos;
- nenhum `float`.

## Arquivos seus (só você cria e edita)

- `app/consultas.py`
- `tests/test_consultas.py`
- `docs/prompts/italo.md`

**Não toque em mais nada.** Em especial, não altere `app/models.py`, `app/erros.py` nem
`tests/conftest.py`. Se achar que falta algo neles, avise o Gustavo.

## Passo a passo

```bash
git fetch origin
git switch -c feature/10-consultas origin/entrega
# salve em docs/tarefas/ os 3 arquivos que você recebeu no privado:
# 00-LEIA-PRIMEIRO.md, CONTRATO.md e o seu arquivo (a pasta é ignorada pelo git)
python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt
```

## Prompt para a IA

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

## Prompt de revisão (antes de abrir o PR)

```text
Revise app/consultas.py contra docs/SPEC.md §4/§6.5 e docs/tarefas/CONTRATO.md
("app/consultas.py"). Para cada uma das 9 funções: o comportamento com lista vazia, os
desempates e a fronteira exata estão implementados e testados? Procure qualquer float,
"/" (divisão real), round() ou "//" aplicado a número negativo sem tratar o
truncamento. Rode cada teste de desempate com a lista invertida para provar que o
resultado não depende da ordem. Confira com git diff --name-only origin/entrega que só
os meus arquivos mudaram. Corrija só o que estiver nos meus arquivos.
```

## Abrir o PR

```bash
git push -u origin feature/10-consultas
gh pr create --base entrega --title "Implement: oito consultas de análise (RN07–RN10)"
```

Na descrição: `Closes #10` e as quatro seções do `00-LEIA-PRIMEIRO.md`.

## Pronto quando

- [ ] `pytest tests/test_consultas.py -q` está verde, com cobertura ≥ 80% em `app/consultas.py`
- [ ] `grep -n "float\|round(" app/consultas.py` não encontra nada
- [ ] `git diff --name-only origin/entrega` mostra só os seus arquivos
- [ ] `docs/prompts/italo.md` está preenchido
