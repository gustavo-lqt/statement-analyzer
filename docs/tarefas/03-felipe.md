# Felipe Marinho — Motor de normalização (RN01–RN06)

| | |
|---|---|
| **Issues** | #12 (U3 normalização, RN01–RN04), #3 (U3 recusas e lote, RN05–RN06) |
| **Branch** | `feature/12-regras`, criada a partir da `entrega` |
| **Começa quando** | O Gustavo avisar que a `entrega` existe (passo 0) |
| **Antes de começar** | Ler [`00-LEIA-PRIMEIRO.md`](00-LEIA-PRIMEIRO.md) e [`CONTRATO.md`](CONTRATO.md) |

## O que é a sua parte

Você escreve o coração do sistema. Ele recebe cada `LinhaCrua` (texto cru, vindo da leitura
do Diego) e decide se a linha vira um `Lancamento` válido (data, valor em centavos, sinal
certo) ou uma `Recusa` com o motivo. Estas são as regras que mais dão erro, então os casos de
borda importam muito: três casas decimais, `31/02`, valor entre parênteses.

Seu módulo é **puro**: não lê arquivo, não acessa banco e não conhece HTTP. Por isso você
não depende de ninguém. Você mesmo monta as `LinhaCrua` nos testes.

## Arquivos seus (só você cria e edita)

- `app/regras.py`
- `tests/test_regras.py`
- `docs/prompts/felipe.md`

**Não toque em mais nada.** Em especial, não altere `app/models.py`, `app/erros.py`,
`app/fichas/*.json` nem `tests/conftest.py`. Se achar que falta algo neles, avise o Gustavo.

## Passo a passo

```bash
git fetch origin
git switch -c feature/12-regras origin/entrega
# salve em docs/tarefas/ os 3 arquivos que você recebeu no privado:
# 00-LEIA-PRIMEIRO.md, CONTRATO.md e o seu arquivo (a pasta é ignorada pelo git)
python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt
```

## Prompt para a IA

```text
Você está no repositório statement-analyzer, na branch feature/12-regras. Leia CLAUDE.md,
docs/SPEC.md (§4 inteira e a tabela de rastreabilidade da §7), docs/tarefas/00-LEIA-PRIMEIRO.md
e docs/tarefas/CONTRATO.md (Parte A e a seção "app/regras.py" da Parte B).

Tarefa: implementar o motor puro de normalização e validação (U3, Issues #12 e #3):
converter_data, converter_valor, normalizar e processar.

Regras desta tarefa:
- Você só pode criar/editar: app/regras.py e tests/test_regras.py. Não crie nem altere
  nenhum outro arquivo.
- app/models.py, app/erros.py, as fichas e tests/conftest.py são congelados. Use
  LinhaCrua, Lancamento, Recusa, ResultadoLeitura, FichaBanco, MotivoRecusa,
  ConvencaoSinal e NenhumaLinhaValida como estão. Se precisar de algo que não existe,
  PARE e me diga o que falta.
- As assinaturas públicas são exatamente as do CONTRATO.md, e o comportamento é o de lá,
  incluindo a ORDEM das verificações em normalizar(). Não invente comportamento.
- Módulo puro: proibido importar fastapi, sqlite3, app.db, app.api ou app.leitura,
  e proibido fazer I/O.
- RN02/RN04: NENHUM float em nenhum ponto, nem intermediário, nem Decimal convertido para
  float. Converta o texto para centavos com manipulação de string e int(). Três ou mais
  casas decimais recusam a linha (PRECISAO_INVALIDA): nunca arredonde.
- RN01: a data só é interpretada no formato da ficha, com dia/mês de 2 dígitos e ano de
  4. Data inexistente (31/02/2026) recusa. Não use datetime.strptime sozinho, porque ele
  aceita "1/9/2026". Valide o formato com regex antes.
- RN05: normalizar() nunca levanta exceção por dado ruim; devolve Recusa.
- Toda função pública tem docstring citando a(s) RN que aplica.

Testes em tests/test_regras.py (fixtures locais; monte as FichaBanco e LinhaCrua no
próprio teste, nos formatos de banco-a, banco-b e banco-c; dados inventados):
- Para CADA regra, um teste do cenário principal e testes dos casos de borda da tabela de
  rastreabilidade da SPEC §7, no mínimo:
  RN01: os 3 formatos; 31/02/2026; 29/02/2028 válido; 29/02/2026 inválido; data vazia;
        formato diferente do declarado; "1/9/2026"; espaços nas pontas.
  RN02: "1.234,56" → 123456; "1234" → 123400; "12,5" → 1250; "(1.234,56)" → -123456;
        "-92,40"; "+10,00"; banco-b com ponto decimal e sem milhar; valor vazio; só
        separador; "R$ 10"; ",50"; "1,".
  RN03: NEGATIVO_SAIDA; COLUNA_DC com D, C, "d " e "X"; valor com sinal em COLUNA_DC;
        COLUNAS_SEPARADAS com só crédito, só débito, ambos vazios, ambos preenchidos.
  RN04: duas casas passam; "12,30" passa; "12,340" → PRECISAO_INVALIDA; "1,999" →
        PRECISAO_INVALIDA (e não 200).
  RN05: LinhaCrua com erro (ENCODING_INVALIDO, LINHA_TRUNCADA) vira Recusa com o mesmo
        motivo, número e conteúdo; processar com 3 linhas ruins no meio de linhas boas lê
        as demais na ordem; a ordem das verificações (data ruim + valor ruim → DATA_INVALIDA).
  RN06: todas ruins → NenhumaLinhaValida; iterável vazio → NenhumaLinhaValida;
        processar repassa uma exceção levantada pelo iterável (ex.: um gerador de teste que
        levanta ArquivoVazio) sem capturá-la.
  Descrição: com espaços nas pontas → strip; vazia → COLUNA_AUSENTE.
- Toda função de teste tem docstring citando a RN que verifica.

Ao terminar, rode: pytest tests/test_regras.py -q --cov=app.regras --cov-report=term-missing
e mostre a cobertura (meta: 80% ou mais, RNF07). Não rode a suíte inteira: os módulos dos
outros ainda não estão nesta branch. Proponha commits pequenos no padrão do CLAUDE.md
(ex.: "Implement: RN04 (precisão excedente) no motor de normalização"). Não faça push.
```

## Prompt de revisão (antes de abrir o PR)

```text
Revise app/regras.py contra docs/SPEC.md §4 e docs/tarefas/CONTRATO.md ("app/regras.py").
Faça uma tabela: regra/item → onde está implementado → quais testes cobrem → casos de
borda que faltam. Procure qualquer float, round(), Decimal->float ou arredondamento.
Confira que normalizar() segue exatamente a ordem de verificação do contrato. Confira
com git diff --name-only origin/entrega que só os meus arquivos mudaram. Corrija só o
que estiver nos meus arquivos.
```

## Abrir o PR

```bash
git push -u origin feature/12-regras
gh pr create --base entrega --title "Implement: motor de normalização RN01–RN06"
```

Na descrição: `Closes #12`, `Closes #3` e as quatro seções do `00-LEIA-PRIMEIRO.md`.

## Pronto quando

- [ ] `pytest tests/test_regras.py -q` está verde, com cobertura ≥ 80% em `app/regras.py`
- [ ] `grep -n "float\|round(" app/regras.py` não encontra nada
- [ ] `git diff --name-only origin/entrega` mostra só os seus arquivos
- [ ] `docs/prompts/felipe.md` está preenchido
