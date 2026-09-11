# Contexto do Projeto — Statement Analyzer

## O que é este projeto

API que recebe um arquivo de extrato bancário em CSV, lê aplicando a ficha do banco
correspondente, normaliza os lançamentos para um modelo canônico e responde consultas de
análise sobre eles (saldo, maiores movimentações, totais por semana, dias no negativo, gastos
repetidos).

**A FONTE DA VERDADE é `docs/SPEC.md`.** Nunca implemente comportamento que não esteja
especificado lá. Se a tarefa exigir algo fora da SPEC, **PARE** e proponha primeiro uma
alteração na SPEC, explicando o que falta e por quê.

Não é um sistema de controle financeiro: não existe categorização, orçamento, meta ou
comparação com despesas planejadas. Ver `docs/SPEC.md` §2 para o não-escopo completo.

## Fluxo de trabalho (SDD)

1. Leia `docs/SPEC.md` antes de qualquer implementação.
2. Implemente na branch `feature/<n>-<nome>` indicada — **NUNCA** em `main` ou `develop`.
3. Toda função que implementa regra de negócio referencia a RN na docstring
   (ex.: `"""Aplica RN02: valor em centavos inteiros."""`).
4. Após implementar, rode o harness: `docker compose run --rm tests`.
   Só considere a tarefa concluída com a suíte **inteira verde**.
5. **Não altere testes para fazê-los passar.** Se um teste parecer errado, aponte o conflito
   entre o teste e a SPEC e espere decisão humana.
6. Não instale dependência nova sem aprovação em PR — dependência nova exige um ADR.

## Arquitetura (respeitar SEMPRE)

Princípio: **dependências apontam para dentro.** A camada HTTP conhece o motor; o motor não
conhece HTTP.

```
app/api.py  →  app/consultas.py  →  app/regras.py  →  app/models.py
                                    app/leitura.py
app/db.py   (persistência, isolada)
```

- `app/models.py` — entidades puras: `Extrato`, `Lancamento`, `Recusa`, `FichaBanco`.
- `app/leitura.py` — abre o arquivo e aplica a ficha. **PROIBIDO** importar FastAPI.
- `app/regras.py` — motor puro de normalização e validação (RN01–RN06).
  **PROIBIDO** importar FastAPI, fazer I/O de disco ou de rede, ou acessar o banco.
- `app/consultas.py` — motor puro de análise (RN07–RN10). Recebe uma lista de lançamentos
  em memória e devolve agregados. Mesmas proibições de `regras.py`.
- `app/api.py` — camada fina. Sem regra de negócio. Traduz HTTP para chamadas do motor e
  converte exceções do motor para o formato único de erro da SPEC §6.6.
- `app/db.py` — todo o acesso a SQLite vive aqui. Nenhum SQL fora deste módulo.
- `app/fichas/*.json` — um arquivo por banco. **Adicionar um banco é adicionar uma ficha, não
  alterar código de leitura.**

## Regras de negócio críticas

Estas são as que mais geram erro. Ver `docs/SPEC.md` §4 para o texto completo.

- **RN02 — dinheiro é inteiro em centavos.** Nunca use `float` para valor monetário, em
  nenhum ponto, nem em cálculo intermediário.
- **RN01 e RN04 — recusar, não adivinhar.** Data que não casa com o formato declarado na
  ficha recusa a linha. Valor com três ou mais casas decimais recusa a linha — **não
  arredonde**.
- **RN05 — linha ruim não derruba o arquivo.** `normalizar()` devolve `Recusa` em vez de
  levantar exceção; a leitura continua.
- **RN08 — lançamentos da mesma data formam um bloco.** O saldo do dia é o saldo após todos
  eles; não invente ordem interna do dia.
- **RN10 — empates têm desempate determinístico** (data mais antiga). Nunca devolva um
  resultado que dependa da ordem de iteração.

## Dados sensíveis

O repositório é **público** e o domínio é financeiro.

- **NUNCA** crie, sugira ou commite arquivo com dados bancários reais.
- Toda fixture de teste é gerada por `gerador/` com semente fixa, para ser determinística.
- Não escreva descrição de lançamento em log (RNF06).
- Se receber um trecho de extrato real no prompt, não o persista em arquivo do repositório.

## Convenções

- Python 3.12, type hints em todas as funções públicas.
- Identificadores de código em **inglês**; documentação, mensagens de domínio e nomes de
  regra em **português** (ADR-001).
- Nomes alinhados ao vocabulário da SPEC: `Extrato`, `Lancamento`, `Recusa`, `FichaBanco`,
  `valor_centavos`, `descricao_normalizada`.
- Mensagens de commit: **verbo em inglês no imperativo** + escopo. O restante da mensagem
  fica em português.
  Ex.: `Implement: RN04 (precisão excedente) no motor de normalização`

  Verbos usados no projeto:

  | Verbo | Quando usar |
  |---|---|
  | `Implement` | Funcionalidade ou regra nova |
  | `Fix` | Correção de comportamento errado |
  | `Refactor` | Muda a estrutura sem mudar o comportamento |
  | `Test` | Acrescenta ou ajusta testes |
  | `Docs` | SPEC, README, ADRs, comentários |
  | `Chore` | Configuração, dependências, ambiente |
  | `Remove` | Exclusão de código, arquivo ou dependência |
  | `Update` | Ajuste incremental em algo que já existe |
- Branches: `feature/<numero-da-issue>-<nome-curto>`. Ex.: `feature/12-motor-normalizacao`.
- Descrição de PR sempre com as quatro seções: o que faz (+ `Closes #n`), como foi feito
  (colaboração com IA), como validar, impacto na SPEC.

## Testes

- `tests/test_regras.py` — unidade, motor de normalização.
- `tests/test_consultas.py` — unidade, motor de análise.
- `tests/test_api.py` — integração, contratos HTTP.
- `tests/conftest.py` — fixtures compartilhadas.

Toda função de teste tem docstring citando a regra ou o contrato que verifica. Cada regra de
negócio precisa de pelo menos um teste de cenário principal **e** um de caso de borda — as
fronteiras exatas (exatamente duas casas decimais, exatamente 10% na RN09, exatamente três
ocorrências, o dia em que o saldo chega a zero) são onde código gerado mais erra.
