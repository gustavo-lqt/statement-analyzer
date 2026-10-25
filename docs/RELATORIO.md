# Relatório de Encerramento — Statement Analyzer v1.0.0

Relatório técnico-ético e de encerramento do projeto. Cobre a publicação, a governança, os
testes, os erros corrigidos, o loop de re-especificação, a análise crítica do uso de agentes
de IA e a retrospectiva da equipe.

| | |
|---|---|
| **Repositório** | https://github.com/gustavo-lqt/statement-analyzer |
| **Release** | https://github.com/gustavo-lqt/statement-analyzer/releases/tag/v1.0.0 |
| **Disciplina** | Bootcamp III — Turma B — CEUB — 2026/2 |

| Integrante | RA | Parte do sistema |
|---|:---|:---|
| Diego de Souza | 22352472 | Leitura do CSV pela ficha e gerador de extratos |
| Felipe Marinho | 22353607 | Motor de normalização (RN01–RN06) |
| Gustavo Lourenço | 22350665 | Base compartilhada, API HTTP, guarda de arquitetura e integração (líder) |
| Italo Henrique Lins Carneiro | 22350066 | As oito consultas de análise (RN07–RN10) |
| João Caio Dutra Gontijo | 22352975 | Persistência SQLite e Docker |

---

## 1. Resumo executivo

O Statement Analyzer é uma API que recebe um extrato bancário em CSV, entende o formato do
banco por uma ficha declarativa, normaliza os lançamentos para um modelo único e responde
oito consultas de análise: resumo, saldo, maior entrada, maior despesa, maiores despesas,
totais por semana, dias no negativo e gastos repetidos.

A release `v1.0.0` entrega o sistema completo:

- **Escopo:** 14 requisitos funcionais e 10 regras de negócio, com recusa individual de
  linhas inválidas, dinheiro sempre em centavos inteiros e nenhum dado bancário real.
- **Testes:** 282 testes automatizados, 100% aprovados, com 99% de cobertura em `app/` e
  `gerador/`.
- **Execução:** dois comandos no Docker, um para a API e outro para a suíte.
- **Especificação:** a `docs/SPEC.md` está na v1.5 e descreve o sistema como foi entregue
  (as-built).

O trabalho seguiu SDD (Spec-Driven Development). A especificação veio primeiro, cada
integrante implementou a sua parte com um agente de IA a partir dela, e todo código entrou
por Pull Request revisado por outra pessoa. A divisão em cinco partes independentes, com um
contrato de interfaces combinado antes, permitiu que as cinco fossem feitas em paralelo, sem
nenhum conflito de merge.

---

## 2. Governança do repositório

### 2.1 Fluxo de branches

```
feature/<issue>-<nome>  ──PR──▶  entrega  ──PR──▶  main  ──tag──▶  v1.0.0
```

- Cada integrante trabalhou numa feature branch própria e só editou os arquivos da sua
  parte. Isso foi definido no planejamento ([`docs/tarefas/`](tarefas/)).
- `main` e `entrega` são protegidas, inclusive para o administrador:
  - Pull Request obrigatório, com uma aprovação;
  - o último push precisa ser aprovado por outra pessoa (`require_last_push_approval`);
  - conversas resolvidas;
  - sem force push e sem exclusão da branch.
- Commits no padrão `Verbo: escopo` (`Implement`, `Fix`, `Test`, `Docs`, `Chore`...),
  definido no [`CLAUDE.md`](../CLAUDE.md).

### 2.2 Pull Requests

Todo PR traz as quatro seções exigidas pelo `CLAUDE.md`, que funcionam como critério de
aceitação: o que faz (com `Closes #n`), como foi feito (colaboração com IA), como validar
e impacto na SPEC. Antes de abrir o PR, o checklist do planejamento exigia:

- só arquivos do próprio dono no diff;
- os testes da parte verdes;
- nenhum `float` em valor monetário;
- as assinaturas idênticas às do contrato;
- o registro de IA preenchido.

| PR | Parte | Autor | Revisão e aprovação | Merge |
|:---:|:---|:---|:---|:---|
| [#15](https://github.com/gustavo-lqt/statement-analyzer/pull/15) | Persistência SQLite e Docker | João Caio | Gustavo | 23/10 |
| [#16](https://github.com/gustavo-lqt/statement-analyzer/pull/16) | Leitura do CSV e gerador | Diego | Gustavo | 23/10 |
| [#17](https://github.com/gustavo-lqt/statement-analyzer/pull/17) | As oito consultas | Italo | Gustavo | 23/10 |
| [#18](https://github.com/gustavo-lqt/statement-analyzer/pull/18) | Motor de normalização | Felipe | Gustavo | 25/10 |
| [#19](https://github.com/gustavo-lqt/statement-analyzer/pull/19) | API, guarda de arquitetura, README e SPEC v1.3 | Gustavo | Italo | 25/10 |
| [#21](https://github.com/gustavo-lqt/statement-analyzer/pull/21) | `entrega` → `main` | Gustavo | Italo e Diego | 25/10 |

Os PRs com revisão mais rica são o **#16** (a revisão pegou um teste que falhava só com
medição de cobertura) e o **#18** (a revisão pegou o bug do `1²`, e o autor corrigiu no
próprio PR).

Os PRs #13 e #14 são de antes do planejamento: um teste de fluxo com a antiga branch
`develop` e a reversão dele. Ficaram no histórico porque o GitHub não permite apagar PRs.

### 2.3 Issues e histórico

- **Issues:** as 12 (#1 a #12) foram abertas na Entrega 1, uma por unidade da SPEC §7, e
  fechadas pelo merge do #21.
- **Linha do tempo:**
  - **11/09:** estrutura inicial do repositório (Entrega 1);
  - **22/10:** base compartilhada e SPEC v1.2;
  - **23/10:** PRs #15, #16 e #17 integrados;
  - **25/10:** #18, #19 e #21 integrados, SPEC as-built e release `v1.0.0`.
- **Commits na `main`:** Gustavo 27, Diego 10, Italo 9, Felipe 4, João Caio 3.

---

## 3. Testes e cobertura

```bash
docker compose run --rm tests
```

**Resultado: 282 testes, 100% aprovados.** O log da execução no Docker (Python 3.12) está em
[`logs_testes.txt`](../logs_testes.txt).

| Arquivo | Testes | Tipo | O que cobre |
|:---|---:|:---|:---|
| `test_regras.py` | 45 | unidade | Normalização e validação, RN01–RN06 |
| `test_consultas.py` | 55 | unidade | As oito consultas, RN07–RN10 |
| `test_leitura.py` | 63 | unidade | Leitura pela ficha, inclusive 100 mil linhas em streaming (RNF04) |
| `test_gerador.py` | 46 | unidade | Gerador sintético determinístico (RNF05) |
| `test_db.py` | 9 | integração | Persistência, cascata e rollback |
| `test_api.py` | 51 | integração | Contratos HTTP e todos os erros da SPEC §6 |
| `test_arquitetura.py` | 13 | arquitetura | O motor não importa HTTP nem banco, e SQL só em `app/db.py` |

| Módulo | Cobertura |
|:---|---:|
| `app/regras.py` | 95% |
| `app/consultas.py` | 100% |
| `app/leitura.py` | 99% |
| `app/db.py` | 94% |
| `app/api.py` | 99% |
| `gerador/gerar.py` | 100% |
| **Total** | **99%** |

A RNF07 exige 80% em `app/regras.py` e `app/consultas.py`.

- **Linhas não cobertas:** são validações alcançáveis, não código morto. Exemplos: valor com
  parêntese só de um lado, valor com dois separadores decimais e o fechamento da conexão
  quando o schema falha.
- **Testes por regra:** cada regra tem pelo menos um teste do cenário principal e um de caso
  de borda, como "exatamente 10%" na RN09 e "o saldo chega a zero" na RN08. A tabela de
  rastreabilidade fica na SPEC §7.

---

## 4. Erros lógicos encontrados e como foram corrigidos

| # | Erro | Como foi encontrado | Correção | Onde |
|:---:|:---|:---|:---|:---|
| 1 | `converter_valor("1²")` levantava `ValueError`: o `str.isdigit()` aceita `²`, mas o `int()` falha. Pela API, o upload inteiro dava 500, contra a RN05. O mesmo erro aceitava dígitos de outros alfabetos (`"١٢,٣٠"` virava 1230) | Teste exploratório na revisão do PR, enviando caracteres incomuns. Os testes gerados pela IA não pegavam o caso | Aceitar só dígitos ASCII (`isascii() and isdigit()`, `[0-9]` na regex), com 7 testes de regressão vistos falhando antes | #18, SPEC v1.3 |
| 2 | Um `\r` solto fora de aspas fazia o módulo `csv` levantar erro e derrubava a leitura inteira, contra a RN05 | A IA do Diego detectou o caso, mas, como o contrato não definia o comportamento, registrou uma proposta em vez de inventar | Linha recusada como `LINHA_TRUNCADA`; no cabeçalho, as linhas saem `COLUNA_AUSENTE`. Teste primeiro, depois a correção | #16 → #19, SPEC v1.3 |
| 3 | Rota inexistente e método não aceito saíam como `{"detail": ...}`, fora do formato único da RNF01 | Revisão final da SPEC as-built contra o comportamento real da API | Handler que converte 404 e 405 em `ROTA_INEXISTENTE` e `METODO_NAO_PERMITIDO` | SPEC v1.5 |
| 4 | Valor entre parênteses com espaços internos (`"( 1,00 )"`) era aceito | Revisão do código gerado | Aceitar espaços só nas pontas, com teste de regressão | #18 |
| 5 | `carregar_ficha` quebrava com um campo a mais no JSON da ficha (`TypeError`) | A própria IA, relendo o código antes do commit | Campos extras ignorados, com teste | #16 |
| 6 | Os testes do gerador não detectavam crédito e débito trocados | A própria IA, com teste de mutação (quebrar o código de propósito e ver se algum teste falha) | Teste que confere o sentido de cada valor | #16 |
| 7 | O teste "leitura não importa `sqlite3`" falhava só com `--cov`, porque o pytest-cov injeta o `coverage` no subprocesso | Revisão do PR, rodando a suíte como o Docker roda | O teste passou a ler os imports com `ast`, sem subprocesso | #16 |
| 8 | Primeira rodada das consultas incompleta: faltavam 3 das 8 funções, 3 funções sem nenhum teste e cobertura de 67% | Conferência do resultado contra o checklist da tarefa | Segunda rodada com o prompt completo; 55 testes e 100% de cobertura | #17 |
| 9 | Em Python, `//` arredonda para baixo (`-3001 // 3 == -1001`), mas a média de gasto precisa truncar em direção a zero (`-1000`) | Armadilha prevista no prompt da tarefa | `_divisao_para_zero`, só com inteiros | #17 |
| 10 | Commit com mensagem errada ("despesas por categoria"), que descrevia algo fora do escopo e que o commit não fazia | Revisão do histórico | Registrado no PR e no `docs/prompts/italo.md`; nada de categoria foi implementado | #17 |
| 11 | A assinatura de `dias_no_negativo` na SPEC §7 não aceitava `None`, contra a decisão D3 | Revisão da SPEC v1.2 | Assinatura corrigida para `saldo_inicial: int \| None` | base |
| 12 | O PR da persistência foi aberto contra a `main` em vez da `entrega` | Revisão do PR | Destino corrigido para `entrega` | #15 |

**O que funcionou para achar erros:**
- testes exploratórios com entradas incomuns, como caracteres Unicode e quebras de linha
  corrompidas, que acharam os erros 1 e 2;
- testes de mutação, que acharam o erro 6;
- rodar a suíte do mesmo jeito que o Docker roda, que achou o erro 7;
- conferir o resultado contra o checklist da tarefa, que achou o erro 8.

Os testes escritos pela própria IA tendem a cobrir o que ela já previu e falham justamente
no que ela não imaginou.

---

## 5. Loop de re-especificação

Toda mudança de comportamento passou pela SPEC antes do código e ficou registrada na §8, com o
motivo e a referência.

| Versão | O que mudou | Gatilho |
|:---:|:---|:---|
| v1.0 → v1.1 | `recorrentes` virou `repetidos` (RN09); `por-mes` virou `por-semana`; RN08 passou a tratar lançamentos do mesmo dia como bloco | Revisão do grupo: um extrato cobre um mês, e o cálculo de `dias-no-negativo` era ambíguo |
| v1.1 → v1.2 | Decisões D1–D7: fichas sintéticas, semana de segunda a domingo, saldo inicial `NULL`, tolerância de 10% mantida, `null` quando não há resultado, paginação e as oito consultas já na entrega | Detalhar o contrato para o trabalho em paralelo |
| v1.2 → v1.3 | Só dígitos `0`–`9` na RN01 e na RN02; regra do `\r` solto | Bugs 1 e 2 da seção 4, revelados na revisão |
| v1.3 → v1.4 | Todo o escopo na Entrega 3 | O sistema ficou completo de uma vez |
| v1.4 → v1.5 | 404 e 405 no formato único; SPEC as-built | Bug 3 da seção 4 e o fechamento da release |

---

## 6. Arquitetura e decisões

A arquitetura e os seis ADRs estão no [README](../README.md#arquitetura). Em resumo:

| ADR | Decisão | Trade-off assumido |
|:---:|:---|:---|
| 001 | Regras de negócio isoladas da camada HTTP | Exige disciplina, garantida por `test_arquitetura.py` |
| 002 | Fichas de banco declarativas em JSON | Formatos fora do vocabulário da ficha exigem estender o esquema |
| 003 | Dinheiro em centavos inteiros | A formatação fica a cargo do cliente da API |
| 004 | SQLite | Migração necessária se o sistema virar multiusuário |
| 005 | Recusar a linha em vez de adivinhar | Exige a ficha correta antes da primeira leitura |
| 006 | Docker como ambiente de referência | Manter duas definições de ambiente em sincronia |

---

## 7. Análise comparativa de ferramentas de IA

### 7.1 Ferramentas usadas

| Integrante | Ferramenta | Modo de uso |
|:---|:---|:---|
| Gustavo | Claude Code (Claude Opus 5.5) + plugin Superpowers | CLI no terminal |
| Diego | Claude Code (Claude Opus 5.5) + plugin Superpowers | Extensão do VS Code |
| Italo | Claude Code (Claude Opus 5.5) | Extensão do VS Code |
| Felipe | GitHub Copilot | Chat no VS Code |
| João Caio | Antigravity | IDE com agente |

Ninguém do grupo usou o Codex CLI nem o Cursor.

### 7.2 Matriz comparativa

A avaliação se baseia no uso real neste projeto, com evidências nos
[`docs/prompts/`](prompts/), nos PRs e no histórico do git.

| Critério | Claude Code | GitHub Copilot | Antigravity |
|:---|:---|:---|:---|
| **Como funciona** | Agente no terminal ou no IDE; lê o repositório, roda comandos e edita arquivos | Assistente dentro do VS Code, com chat e modo agente que edita os arquivos do workspace | IDE do Google, derivado do VS Code, em que agentes planejam, editam e rodam comandos |
| **Arquivo de contexto** | `CLAUDE.md`, lido automaticamente | `.github/copilot-instructions.md`, que não foi criado; o prompt mandava ler o `CLAUDE.md` | regras do workspace, que não foram criadas; o prompt mandava ler o `CLAUDE.md` |
| **Quem usou** | Gustavo, Diego e Italo | Felipe | João Caio |
| **Pontos fortes observados** | Segue a SPEC e o `CLAUDE.md` à risca; com o Superpowers, aplica TDD de verdade e verificação com evidência; acha os próprios erros relendo o código e com teste de mutação; automatiza git e `gh` | Respeitou as restrições do prompt (só os dois arquivos da parte, nenhum `float`, a ordem de validação); entregou 38 testes e 94% de cobertura na primeira versão; não exige trocar de editor | Disciplina de escopo: ao ver que a pasta não era um repositório git, clonou a `entrega` e levou só os cinco arquivos permitidos; SQL correto de primeira (parâmetros `?`, transação atômica, rollback testado) |
| **Limitações observadas** | Primeira rodada às vezes incompleta (#17); testes próprios não pegam o que ela não previu (o teste que só falhava com `--cov`); sugeriu atalhos que quebrariam a divisão do trabalho (dublês e trazer código de outras branches); mensagem de commit errada; texto colado não chegou | Os primeiros testes não seguiam as assinaturas congeladas do contrato; aceitou espaços internos em valores entre parênteses; o `isdigit()` deixou passar o `1²`, e os testes dele não pegaram. Os três erros foram achados na revisão, não pela ferramenta | Procurou os documentos no caminho errado; não resolveu o ambiente (`pytest` fora do `PATH`, Docker Engine parado) e deixou a validação no Docker pendente; abriu o PR contra a `main` |
| **Impacto na especificação** | Ao achar um caso que a SPEC não cobria (`\r` solto), registrou uma proposta em vez de inventar comportamento, como o `CLAUDE.md` manda | Indireto: o bug do `1²` gerou a SPEC v1.3, que passou a aceitar só os dígitos `0`–`9` na RN01 e na RN02 | Nenhum: implementou o contrato sem precisar de mudança, o esperado para a persistência |
| **Impacto no código** | Código tipado, com docstrings citando as regras e 99% de cobertura; os erros que passaram foram de casos de borda inesperados, não de estrutura | `app/regras.py` com 45 testes e 95% de cobertura depois das correções; as duas mudanças de comportamento vieram da revisão | `app/db.py` com 9 testes e 94% de cobertura; nada precisou mudar na integração, e o Docker funcionou quando o motor foi ligado |

### 7.3 Ferramentas que o grupo não usou

| Critério | Codex CLI | Cursor |
|:---|:---|:---|
| **Como funciona** | Agente da OpenAI no terminal, com modelo de uso parecido com o do Claude Code | IDE derivado do VS Code, com IA no editor e modo agente |
| **Arquivo de contexto** | `AGENTS.md` | regras do projeto (`.cursor/rules`) |

Sem uso real, não há avaliação: a tabela só descreve as ferramentas.

### 7.4 Conclusão da comparação

- **O Claude Code com o Superpowers deu o processo mais completo.** Testes vistos falhando
  antes do código, teste de mutação e revisão própria antes do commit. Os erros que sobraram
  foram casos de borda que ninguém tinha previsto. Ele também foi o que mais agiu fora do
  código (git, `gh`, regras do repositório), e por isso precisou do modo de permissão para
  frear as ações de risco.
- **O Copilot e o Antigravity entregaram código correto dentro do contrato, mas com menos
  verificação própria.** Os erros deles foram achados pela revisão humana ou pelo ambiente,
  e não pela própria ferramenta.
- **O que mais pesou foi o contrato, não a ferramenta.** Cinco partes, escritas com três
  ferramentas diferentes, se encaixaram sem nenhum conflito porque todas seguiram o mesmo
  `CONTRATO.md` e a mesma SPEC. Quanto mais completo o prompt (arquivos permitidos,
  restrições, casos de borda), melhor foi a primeira versão, com qualquer uma das três.

---

## 8. Ética, limites e segurança no uso de IA

### 8.1 Alucinação e código inseguro ou destrutivo

**O que aconteceu no projeto:**
- **Código que passava nos testes e estava errado.** O `isdigit()` aceitava `²` (erro 1 da
  seção 4). A IA escreveu o código e os testes, e os dois tinham o mesmo ponto cego. Um
  teste escrito pelo mesmo agente que escreveu o código não é uma verificação independente.
- **Entrega incompleta apresentada como feita.** Na primeira rodada das consultas, três
  funções não tinham nenhum teste, só os imports (erro 8). Na mesma linha, um commit
  descrevia uma funcionalidade que não existia (erro 10).
- **Atalhos que quebrariam o processo.** A IA sugeriu criar dublês dos módulos dos colegas
  e trazer código de outras branches. Os dois atalhos fariam o código parecer pronto, mas
  violariam a divisão por dono.
- **Ações destrutivas.** No começo do projeto, o agente criou arquivos de código em `app/`
  quando o pedido era só criar a pasta de instruções; o líder rejeitou, e tudo foi
  desfeito. Mais tarde, o modo de permissão automático do Claude Code bloqueou duas ações
  por risco: o agente aprovar um PR em nome do líder e um force push que reescrevia o
  histórico. As duas só aconteceram com a autorização explícita do líder.

**Mitigações que funcionaram:**
- TDD, com o teste visto falhando antes da correção;
- testes de mutação;
- testes de arquitetura que reprovam importação proibida e SQL fora do lugar;
- revisão humana em todo PR;
- branches protegidas;
- o agente rodando num modo de permissão que bloqueia as ações de risco (aprovar PR,
  reescrever histórico, mexer nas regras do repositório) até que uma pessoa autorize.

### 8.2 Vazamento de dados, privacidade e confidencialidade

O domínio é financeiro e o repositório é público, então nenhum dado real pode entrar no
contexto do modelo nem no repositório.

- **Nenhum dado real.** Todo extrato usado em teste, demonstração ou prompt é gerado pelo
  `gerador/`, com semente fixa e descrições de uma lista fictícia (RNF05). O `CLAUDE.md`
  proíbe o agente de criar ou commitar dados reais e de gravar em arquivo um trecho de
  extrato real que receba no prompt.
- **O que vai para o modelo.** O agente lê o código, a SPEC e a saída dos comandos, e tudo
  isso vai para os servidores do provedor do modelo. Por isso nada sensível fica no
  repositório: `dados/` e `*.db` estão no `.gitignore` e no `.dockerignore`.
- **Logs.** Nenhum log registra a descrição de um lançamento (RNF06). O erro 500 registra só
  o tipo da exceção, porque a mensagem poderia conter dados do extrato.
- **Risco que fica.** A API devolve o conteúdo bruto das linhas recusadas, para o usuário
  conferir o que foi rejeitado (RN05), e esse conteúdo inclui a descrição. Num uso real com
  vários usuários, isso exigiria autenticação, que está fora do escopo da v1.0.0.

### 8.3 Propriedade intelectual e direitos autorais

- **Autoria.** A maior parte do código foi escrita pelo agente, a partir de especificações,
  prompts, revisões e decisões humanas. Os integrantes registraram que não editaram código à
  mão: o trabalho humano foi especificar, dividir, revisar, decidir e corrigir o rumo.
- **Transparência.** No fim do projeto, o líder pediu para tirar o agente como coautor
  (`Co-Authored-By`) dos commits e das descrições de PR, para que os integrantes aparecessem
  como autores no GitHub. Em contrapartida, o uso de IA é declarado em detalhe: cada
  integrante tem um registro em `docs/prompts/`, todo PR tem a seção "Como foi feito
  (colaboração com IA)", e o README descreve o fluxo. A posição do grupo é que a autoria
  responsável vem de quem especifica, revisa e responde pelo código, e que o uso da
  ferramenta precisa ficar declarado.
- **Direitos sobre o código gerado.** Os termos dos provedores costumam atribuir ao usuário
  os direitos sobre a saída do modelo. Mesmo assim, em várias jurisdições ainda é incerto se
  código gerado por IA sem contribuição humana significativa é protegido por direito autoral.
  Há também o risco de o modelo reproduzir trechos de código de terceiros com licença
  incompatível. Para reduzir esse risco, o código foi escrito contra a especificação do
  próprio projeto, com dependências mínimas e conhecidas (`requirements.txt`).
- **Licença:** o repositório é público, mas fica sem arquivo de licença, por decisão do
  grupo. Sem licença, o padrão legal é "todos os direitos reservados": qualquer pessoa pode
  ler o código, mas não pode reutilizá-lo sem autorização dos autores. Para um trabalho
  acadêmico, é o mais adequado. Uma licença permissiva, como a MIT, só faria sentido se o
  projeto continuasse como código aberto.

### 8.4 Homologação e revisão humana no fluxo SDD

No SDD, a especificação é a fonte da verdade e o agente implementa a partir dela. Mas o
agente não decide se o resultado está certo: a homologação é humana.

**Como o projeto garantiu isso:**
- **Nada entra sem PR revisado.** `main` e `entrega` só aceitam Pull Request aprovado por
  outra pessoa, inclusive para o administrador.
- **A regra funcionou na prática.** No PR #21, o Italo não conseguiu homologar sozinho,
  porque tinha feito o último push. Foi preciso uma terceira pessoa, o Diego.
- **A revisão pegou o que os testes da IA não pegaram.** Foi o caso dos erros 1, 7 e 8.

**Limitação que registramos com honestidade:** nos PRs #15 a #18, a revisão do líder foi
feita com a ajuda do próprio agente. O líder pediu que o agente conferisse cada PR contra o
contrato e rodasse os testes e a integração, e autorizou o agente a aprovar e fazer o merge
quando estivesse tudo certo. As aprovações foram registradas na conta do líder. A revisão
assistida achou bugs reais (o `1²` e o teste que falhava com `--cov`). Ainda assim, nesses
PRs a homologação humana ficou mais fina do que o ideal: a decisão humana foi delegar, e não
inspecionar cada linha.

**Lição:** o agente é um bom revisor auxiliar, mas a aprovação final deveria ser de uma
pessoa que leu o diff. Numa próxima entrega, o grupo manteria a revisão assistida, mas com a
aprovação dada pelo integrante depois de ler o relatório do agente e o diff.

---

## 9. Relato de experiência e retrospectiva

### 9.1 O que o histórico mostra

- **Paralelismo sem conflito.** O contrato de interfaces combinado antes (modelos, exceções,
  fichas e assinaturas) permitiu que as cinco partes fossem escritas ao mesmo tempo, cada uma
  contra o contrato e sem esperar pelas outras. Na integração, nenhum merge teve conflito.
  Os testes de integração da API, escritos antes de os outros módulos existirem, passaram
  quando tudo foi juntado.
- **Ritmo.** Entre a base compartilhada (22/10) e a release (25/10), o sistema saiu do zero
  para 282 testes aprovados.
- **SDD funcionou como freio.** Quando apareceu um caso não especificado (`\r` solto), o
  agente parou e propôs uma mudança na SPEC em vez de inventar.
- **Governança custou atrito, mas segurou.** A proteção de branches bloqueou mais de uma vez
  quem tentou aprovar o próprio trabalho, que é justamente o objetivo.

### 9.2 Aprendizados e dificuldades de cada integrante

| Integrante | Aprendizado | Dificuldade superada |
|:---|:---|:---|
| Diego | Teste que passa não prova que o código está certo: o teste de mutação mostrou que os testes do gerador não viam crédito e débito trocados. E, diante de um caso que o contrato não cobria (`\r` solto), o certo foi parar e propor, não inventar | O teste de imports que só falhava com `--cov`, que é como o Docker roda a suíte. Foi resolvido lendo os imports com `ast`, sem abrir processo |
| Felipe | A revisão com entradas incomuns acha o que os testes não acham: o `1²` passava pelos 38 testes da primeira versão | Alinhar os testes às assinaturas congeladas do contrato e corrigir o bug do `1²` no próprio PR, com os testes de regressão vistos falhando antes |
| Gustavo | Combinar o contrato de interfaces antes de dividir o trabalho foi o que permitiu cinco partes em paralelo sem nenhum conflito de merge | Coordenar cinco PRs com a proteção de branches valendo até para o administrador, e integrar tudo no fim, inclusive a correção do `\r` no módulo de outro integrante |
| Italo | Conferir o resultado da IA contra o checklist antes de abrir o PR: a primeira rodada parecia pronta, mas tinha três funções faltando e 67% de cobertura | Fazer a média truncar em direção a zero só com inteiros e abrir o PR sem o `gh` instalado, que foi instalado e autenticado no meio do caminho |
| João Caio | O ambiente faz parte da entrega: o Docker precisa ser validado com o motor rodando, e não só pela sintaxe do Compose | Trabalhar numa pasta sem git e com o Docker Engine parado: clonou a `entrega`, levou só os arquivos permitidos e corrigiu o destino do PR para a `entrega` |

### 9.3 Eficácia da IA e ganho de produtividade

- **Ritmo.** Da base compartilhada (22/10) à release (25/10) foram quatro dias, com 282
  testes e 99% de cobertura. Os registros em `docs/prompts/` mostram que nenhuma linha de
  código foi editada à mão: o trabalho humano foi especificar, escrever os prompts, revisar
  e decidir.
- **Onde a IA mais ajudou:**
  - código de regra de negócio com testes, quando o prompt trazia o contrato e os casos de
    borda (a divisão em direção a zero, os 10% exatos da RN09, o dia que cruza o zero);
  - automação de git, `gh` e Docker;
  - documentação: registros, descrições de PR, README e a SPEC as-built.
- **Onde mais atrapalhou:**
  - casos que ninguém previu, como o `1²` e o `\r` solto, em que os testes da própria IA
    tinham o mesmo ponto cego do código;
  - primeiras versões incompletas apresentadas como prontas (#17);
  - o ambiente: `pytest` fora do `PATH`, Docker parado, `gh` não instalado;
  - ações além do pedido, como criar arquivos em `app/` quando o pedido era só a pasta de
    instruções.
- **Conclusão.** O ganho veio na escrita do código. O tempo humano não sumiu, mudou de
  lugar: saiu da digitação e foi para a especificação e a revisão. Sem a revisão, erros como
  o 1, o 7 e o 8 da seção 4 teriam chegado à `main`.

### 9.4 Lições sobre governança em equipe

- Combinar as interfaces antes de dividir o trabalho evita a "branch de correções" no fim.
- Um dono por arquivo elimina conflito de merge, mas exige que mudanças no arquivo de outra
  pessoa passem por ela. Isso aconteceu com a correção do `\r` no módulo do Diego, que ele
  revisou no PR.
- A proteção de branches tem que valer também para o administrador. Sem isso, o líder seria
  o ponto fraco do processo.
- Registrar os prompts e os erros da IA durante o trabalho, e não no fim, deixa o relatório
  honesto. Um dos integrantes não salvou o prompt da primeira rodada e teve de reconstruí-lo
  pelo histórico do git.
- O prompt também é especificação. As partes que começaram com o prompt completo (arquivos
  permitidos, restrições e casos de borda) saíram certas na primeira rodada. A que começou
  sem ele, a das consultas, precisou de uma segunda rodada.
- Cada integrante usar uma ferramenta de IA diferente não atrapalhou, porque o contrato era o
  mesmo para todos.
- Validar no mesmo ambiente da entrega, o Docker, desde o começo. Dois problemas só
  apareceram ali: o teste que falhava com `--cov` e a validação do Docker que ficou pendente.
