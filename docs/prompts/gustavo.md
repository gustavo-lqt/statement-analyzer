# Registro de uso de IA — Gustavo

Ferramenta: Claude Code (Claude Opus 5.5) com o plugin Superpowers
(skill `test-driven-development`). Nenhuma linha de código foi editada à mão.

Tarefas: base compartilhada (Issue #1), camada HTTP (U5, Issue #9) e guarda de
arquitetura (Issue #7).

## Passo 0 — Base compartilhada

O grupo combinou antes as interfaces entre os módulos, para que as cinco partes pudessem
ser feitas em paralelo. As decisões que mudaram a SPEC estão na §8 (D1–D7).

Prompt principal: criar a base que todos usam, sem implementar nenhuma lógica.

- criar `app/models.py`, `app/erros.py`, as fichas `banco-a`, `banco-b` e `banco-c`,
  `requirements.txt`, `pytest.ini` e `tests/conftest.py`, com o conteúdo combinado pelo
  grupo;
- não criar `leitura.py`, `regras.py`, `consultas.py`, `db.py`, `api.py`, Docker nem testes,
  porque cada um tem outro dono;
- atualizar a SPEC para v1.2: uma linha na §8 para cada decisão D1–D7, as dúvidas da §9
  marcadas como resolvidas e `saldo_inicial_centavos` como `INTEGER` (aceita `NULL`), sem
  mudar mais nada;
- conferir que os módulos importam e que as fichas são JSON válido;
- propor o commit no padrão do CLAUDE.md, sem push.

Resultado: commit `5ec5f1b` ("Chore: base compartilhada da Entrega 2").

Correção: na revisão, a assinatura de `dias_no_negativo` na §7 da SPEC estava sem o
`None`. Ela foi corrigida para
`dias_no_negativo(lancamentos, saldo_inicial: int | None)`, de acordo com a decisão D3.

## Passo 1 — API HTTP e guarda de arquitetura

Prompt principal: "Use a skill superpowers:test-driven-development", seguido das
instruções da tarefa e de "vai fazendo commits a cada coisa importante". As instruções
pediam:

- editar só `app/api.py`, `tests/test_api.py` e `tests/test_arquitetura.py`;
- importar os módulos dos colegas e chamar as assinaturas combinadas, sem versões
  próprias, e parar se faltasse algo nos arquivos congelados;
- API fina: sem regra de negócio, sem SQL e sem cálculo de consulta;
- todas as rotas, com os status e os corpos da SPEC §6, datas `AAAA-MM-DD` e dinheiro
  sempre `int`;
- erros no formato único da §6.6, com handlers para `ErroDominio`, para a validação do
  FastAPI (422 `PARAMETRO_INVALIDO`) e para `Exception` (500 `ERRO_INTERNO`), e
  `ARQUIVO_AUSENTE` quando falta o arquivo;
- conexão por `obter_conexao()`, lendo `STATEMENT_DB`, e nunca registrar a descrição de
  lançamento em log (RNF06);
- `test_api.py` com `TestClient`, um banco `:memory:` novo por teste, CSVs inventados nas
  três fichas e os casos de sucesso e de erro das §6.3 a §6.5;
- `test_arquitetura.py` analisando o código com `ast`: o motor não importa `fastapi`,
  `starlette`, `sqlite3`, `app.db` nem `app.api`, e nenhum arquivo de `app/` além de
  `db.py` tem SQL em string;
- docstring citando a regra em todo teste, commits pequenos e sem push.

**Erro 1:** o texto colado não chegou à IA, que recebeu só o marcador
`[Pasted text #4 +44 lines]`. A IA não começou a adivinhar e pediu o texto. Foi a
decisão certa.

**Erro 2:** como `leitura.py`, `regras.py`, `consultas.py` e `db.py` ainda não existiam na
branch, a IA sugeriu usar dublês dos módulos ou trazer o código de outras branches. As duas
opções quebrariam a divisão por dono. Prompt de correção (sem as referências aos
arquivos de instrução do grupo, que não ficam no repositório):

```text
Sobre os módulos que faltam: escreva app/api.py e tests/test_api.py contra as
assinaturas combinadas, importando os módulos reais (app.leitura, app.regras,
app.consultas, app.db). Não crie dublês nem stubs desses módulos e não traga código de
outras branches: eles são de outras pessoas e entram na branch entrega por PR. O
test_api.py vai falhar com ImportError até lá, e isso é esperado.

Use TDD de verdade (vermelho → verde) no tests/test_arquitetura.py, que já roda. No
test_api.py, escreva os testes primeiro, depois a API, sem tentar rodar. Quando os
módulos chegarem, eu faço merge da entrega e rodamos tudo.
```

Resultado, em 5 commits:

| Commit | O quê |
|---|---|
| `55e9434` Test | Detector de imports da guarda (simples, `from app import db`, relativos) |
| `de4e5e2` Test | Detector de SQL em strings, incluindo f-strings; ignora docstrings |
| `abcdaa0` Implement | Guardas aplicadas ao código de `app/` |
| `3598329` Test | `tests/test_api.py`, escrito antes da API |
| `ef82631` Implement | `app/api.py` |

Na guarda de arquitetura, os detectores passaram pelo ciclo vermelho → verde contra
código inventado. Para conferir que as guardas reprovam código real, a IA criou por um
instante um `regras.py` com `from fastapi import ...` e um `consultas.py` com `SELECT`. As
duas guardas falharam com mensagens claras, e ela apagou os arquivos em seguida.

Decisões tomadas pela IA, que revisei e mantive:

- `ARQUIVO_AUSENTE` usa uma exceção da própria camada HTTP (`ErroProtocolo`), porque
  `app/erros.py` está congelado e não tem essa exceção.
- `GET /extratos/{id}` não devolve as recusas, porque a SPEC §6.4 não pede.
- Rota inexistente e 405 continuam no formato padrão do FastAPI. A SPEC não define um
  código para esses casos.
- O log do erro 500 registra só o tipo da exceção, sem a mensagem (RNF06).

## Integração

Depois que os PRs #15, #16, #17 e #18 entraram na `entrega`, juntei a `entrega` com a
`feature/9-api` numa cópia isolada (git worktree) e rodei a suíte inteira. Prompt de
revisão (sem as referências aos arquivos de instrução do grupo):

```text
Fiz o merge de origin/entrega na minha branch e agora todos os módulos existem. Rode
pytest -q (a suíte inteira). Para cada falha, diga se o problema está em app/api.py
(o meu), em um teste meu, ou em outro módulo. Corrija só o que for meu. Se for de outro
módulo, descreva a divergência para eu repassar ao dono.
Não altere arquivos de outras pessoas.
```

Resultado: o merge não teve conflito e passaram 273 testes, sem nenhum pulado, incluindo os
da API e da guarda. O comportamento da API não precisou mudar.

Correção: os comentários de `app/api.py` e de `tests/test_api.py` citavam o arquivo
de instruções do grupo, que não fica no repositório. Agora eles citam só as seções da
SPEC.

A revisão dos PRs também achou um bug no módulo de outra pessoa:

- **PR #18 (regras):** a IA testou `converter_valor("1²")` e viu que ele levantava
  `ValueError`, porque `"²".isdigit()` é `True` mas `int()` falha. Pela API, isso virava
  erro 500 no upload inteiro, contra a RN05. Repassei ao Felipe, que corrigiu. Conferido
  depois pela API: o mesmo CSV devolve 201, com a linha recusada como `VALOR_INVALIDO`.
