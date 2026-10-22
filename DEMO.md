# Roteiro de apresentação e demonstração

| Duração-alvo | Formato | Estado considerado |
|---|---|---|
| 4 minutos | Gravação de tela com narração | Documentação e estrutura inicial; aplicação não implementada |

Este roteiro não simula uma API funcional. Não exiba respostas inventadas nem arquivos com
dados bancários reais. Caso a implementação esteja disponível na data da gravação, atualize o
roteiro, rode a suíte completa e substitua a parte de arquitetura por uma demonstração real,
validada e com dados sintéticos.

## Preparação

- Grave em uma janela limpa, com `README.md` e `docs/SPEC.md` prontos para mostrar.
- Desative notificações e não exponha credenciais, arquivos pessoais ou dados bancários.
- Use um cronômetro e mantenha a gravação entre 3 e 5 minutos.
- Não apresente o diagrama ou os contratos como funcionalidades já executáveis.

## Roteiro cronometrado

### 0:00–0:35 — Problema e proposta

**Tela:** título do projeto no `README.md`.

**Fala:**

> Extratos bancários costumam ser arquivos extensos e variam de banco para banco. O Statement
> Analyzer foi especificado para receber um CSV, normalizar seus lançamentos e responder
> perguntas como total de entradas e saídas, saldo e gastos repetidos. O escopo é analisar um
> extrato, não controlar orçamento nem categorizar despesas.

### 0:35–1:20 — Arquitetura

**Tela:** diagrama Mermaid no README; em seguida, seção de arquitetura na SPEC.

**Fala:**

> A arquitetura proposta separa leitura do arquivo, regras de normalização, consultas, API e
> persistência. A camada HTTP deve traduzir as requisições; as regras de negócio ficam isoladas
> e trabalham com valores inteiros em centavos. O diagrama representa o desenho previsto, não
> módulos disponíveis nesta versão do repositório.

### 1:20–2:20 — Regras que protegem os resultados

**Tela:** `docs/SPEC.md` §4 e tabela de requisitos funcionais.

**Fala:**

> A especificação define regras para evitar inferências silenciosas: a data segue o formato da
> ficha do banco, valores com precisão excedente são recusados e uma linha inválida não deve
> interromper o restante do arquivo. Também define como agrupar lançamentos do mesmo dia para
> analisar o saldo. Essas decisões precisam ser verificadas por testes antes de qualquer
> resultado ser tratado como confiável.

### 2:20–3:05 — Privacidade e uso de IA

**Tela:** `docs/RELATORIO_IA.md` e `ERROS.md`.

**Fala:**

> Dados de extrato são sensíveis. O projeto proíbe dados bancários reais em fixtures e logs, e
> prevê exemplos sintéticos. A análise de IA documenta riscos de alucinação, privacidade,
> propriedade intelectual e a necessidade de revisão humana. Não há neste repositório evidência
> de uma ferramenta de IA usada nem de uma avaliação comparativa executada.

### 3:05–3:45 — Estado entregue e próximos passos

**Tela:** árvore de arquivos ou `ERROS.md` e a seção As-Built da SPEC.

**Fala:**

> Transparência sobre o estado atual: esta entrega contém a documentação e a estrutura inicial.
> A API, o banco, as fichas, o ambiente Docker e os testes ainda não estão implementados; por
> isso, não existe uma execução funcional nem um percentual de cobertura para apresentar. Os
> próximos passos são implementar os módulos conforme a SPEC, criar o harness com dados
> sintéticos e só então gravar uma demonstração de ponta a ponta.

## Encerramento

Finalize em até 4 minutos com a limitação explícita. Se a implementação e os testes forem
concluídos antes da gravação, atualize as falas e mostre somente uma execução real cuja saída
tenha sido validada. Não altere a duração escondendo pré-requisitos ou simulando resultados.