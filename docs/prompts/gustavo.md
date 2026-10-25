# Registro de uso de IA — Gustavo

Ferramenta: Claude Code (Claude Opus 5.5) com o plugin Superpowers
(skill `test-driven-development`). Nenhuma linha de código foi editada à mão.

Tarefas: passo 0 (base compartilhada, Issue #1), camada HTTP (U5, Issue #9) e guarda de
arquitetura (Issue #7).

## Passo 0 — Base compartilhada

Prompt usado, na íntegra:

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

Resultado: commit `5ec5f1b` ("Chore: base compartilhada da Entrega 2").

Correção: na revisão, a assinatura de `dias_no_negativo` na §7 da SPEC estava sem o
`None`. Ela foi corrigida para
`dias_no_negativo(lancamentos, saldo_inicial: int | None)`, de acordo com a decisão D3.

## Passo 1 — API HTTP e guarda de arquitetura

Primeira mensagem: "Use a skill superpowers:test-driven-development", seguida do prompt da
seção "Passo 1" de [`docs/tarefas/01-gustavo.md`](../tarefas/01-gustavo.md), e "vai fazendo commits a cada coisa
importante".

**Erro 1:** o texto colado não chegou à IA, que recebeu só o marcador
`[Pasted text #4 +44 lines]`. A IA não começou a adivinhar e pediu o texto. Foi a
decisão certa.

**Erro 2:** como `leitura.py`, `regras.py`, `consultas.py` e `db.py` ainda não existiam na
branch, a IA sugeriu usar dublês dos módulos ou trazer o código de outras branches. As duas
opções quebrariam a divisão por dono. Mandei este prompt de correção:

```text
O texto colado era o prompt da seção "Passo 1" de docs/tarefas/01-gustavo.md. Leia
direto do arquivo, junto com docs/tarefas/00-LEIA-PRIMEIRO.md e docs/tarefas/CONTRATO.md,
e siga aquele prompt.

Sobre os módulos que faltam: escreva app/api.py e tests/test_api.py contra as
assinaturas do CONTRATO.md, importando os módulos reais (app.leitura, app.regras,
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
| `45e5002` Test | Detector de imports da guarda (simples, `from app import db`, relativos) |
| `b8b83d4` Test | Detector de SQL em strings, incluindo f-strings; ignora docstrings |
| `26f26aa` Implement | Guardas aplicadas ao código de `app/` |
| `e09b481` Test | `tests/test_api.py`, escrito antes da API |
| `17602fb` Implement | `app/api.py` |

Na guarda de arquitetura, os detectores passaram pelo ciclo vermelho → verde contra
código inventado. Para conferir que as guardas reprovam código real, a IA criou por um
instante um `regras.py` com `from fastapi import ...` e um `consultas.py` com `SELECT`. As
duas guardas falharam com mensagens claras, e ela apagou os arquivos em seguida.

Decisões tomadas pela IA, que revisei e mantive:

- `ARQUIVO_AUSENTE` usa uma exceção da própria camada HTTP (`ErroProtocolo`), porque
  `app/erros.py` está congelado e não tem essa exceção.
- `GET /extratos/{id}` não devolve as recusas, porque o CONTRATO não pede.
- Rota inexistente e 405 continuam no formato padrão do FastAPI. A SPEC não define um
  código para esses casos.
- O log do erro 500 registra só o tipo da exceção, sem a mensagem (RNF06).

Faltou neste passo: o prompt só liberava `app/api.py` e os dois testes, então a IA não
criou este arquivo. Ele foi escrito depois, na integração.

## Integração

Depois que os PRs #15, #16, #17 e #18 entraram na `entrega`, juntei a `entrega` com a
`feature/9-api` numa cópia isolada (git worktree) e rodei a suíte inteira. Esse é o
"prompt de revisão" de [`docs/tarefas/01-gustavo.md`](../tarefas/01-gustavo.md):

```text
Fiz o merge de origin/entrega na minha branch e agora todos os módulos existem. Rode
pytest -q (a suíte inteira). Para cada falha, diga se o problema está em app/api.py
(o meu), em um teste meu, ou em outro módulo. Corrija só o que for meu. Se for de outro
módulo, descreva a divergência em relação ao CONTRATO.md para eu repassar ao dono.
Não altere arquivos de outras pessoas.
```

Resultado: o merge não teve conflito e passaram 273 testes, sem nenhum pulado, incluindo os
da API e da guarda. Nada no `app/api.py` precisou mudar.

A revisão dos PRs também achou um bug no módulo de outra pessoa:

- **PR #18 (regras):** a IA testou `converter_valor("1²")` e viu que ele levantava
  `ValueError`, porque `"²".isdigit()` é `True` mas `int()` falha. Pela API, isso virava
  erro 500 no upload inteiro, contra a RN05. Repassei ao Felipe, que corrigiu. Conferido
  depois pela API: o mesmo CSV devolve 201, com a linha recusada como `VALOR_INVALIDO`.

## Fechamento da entrega

Pedido: deixar tudo pronto no PR #19, para não precisar de nenhum commit depois da
aprovação. Isso incluía preencher as referências de PR da SPEC §8 e resolver a proposta do
Diego sobre o `\r` solto, que estava em aberto desde o PR #16.

**`\r` solto no CSV.** A IA reproduziu o problema antes de mexer. Um `\r` fora de aspas,
no meio ou no fim de uma célula, fazia o módulo `csv` levantar `csv.Error`, e isso derrubava
a leitura do arquivo inteiro (500 pela API, contra a RN05). Entre aspas, o `\r` já era
aceito. Decidi seguir a sugestão do Diego:

- a linha com `\r` solto sai `LINHA_TRUNCADA`;
- se o `\r` estiver no cabeçalho, as linhas de dados saem `COLUNA_AUSENTE`, porque o
  cabeçalho não tem as colunas da ficha;
- um arquivo que usa só `\r` como quebra é uma linha só e levanta `ArquivoVazio`, porque
  só `\n` e `\r\n` quebram linha.

A correção ficou em `_celulas` de `app/leitura.py`, que é do Diego. Ela entrou neste PR
porque decidi fechar a entrega sem um PR a mais, e o Diego revisa a mudança no próprio
#19. Os testes vieram primeiro e falharam com `csv.Error` antes da correção. Foram 5 em
`tests/test_leitura.py` e 2 em `tests/test_api.py`, que conferem pela API os dois casos que
davam 500 (o `\r` solto e o `1²` do PR #18).

**SPEC v1.3.**

- A §4 ganhou a regra do `\r`. A RN01 e a RN02 agora dizem que só os dígitos `0`–`9` são
  aceitos, o que registra na SPEC a correção do PR #18.
- A §8 ganhou as duas linhas da v1.3.
- Os 10 `#«n»` da §8 foram preenchidos. Como a SPEC nunca mudou por PR (o v1.1 veio no
  commit inicial e o v1.2 no commit da base), a coluna traz o commit e os PRs que
  implementaram cada decisão.

**Erro da IA:** o script que editou a SPEC leu o arquivo com o modo de texto do Python, que
converteu os `\r` e `\n` escritos como texto em quebras de linha reais. A IA viu o problema
na conferência do diff e corrigiu o arquivo lendo e gravando em modo binário.

Resultado: 280 testes passando, sem nenhum pulado, com 99% de cobertura em `app/` e
`gerador/`.
