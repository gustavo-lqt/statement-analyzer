# Roteiro de apresentação e demonstração

| Duração-alvo | Formato                       | Estado considerado                                           |
| ------------ | ----------------------------- | ------------------------------------------------------------ |
| 4 minutos    | Gravação de tela com narração | API e harness funcionais; dados sintéticos |

Use somente o CSV gerado abaixo; não exiba respostas inventadas nem arquivos com dados
bancários reais. A última validação local passou em Python 3.11.9; a imagem Python 3.12 e o
Compose ainda precisam ser executados em um host com Docker ativo.

## Preparação

- Inicie os serviços e gere um CSV fictício com semente fixa:

	```bash
	docker compose up --build -d api
	python -m gerador --bank banco-a --seed 17 --quantity 12 --output dados/demo.csv
	```

- Abra `http://localhost:8000/docs` e deixe `dados/demo.csv` pronto para upload.
- Desative notificações e não exponha credenciais, arquivos pessoais ou dados bancários.
- Use um cronômetro e mantenha a gravação entre 3 e 5 minutos.
- Rode `docker compose run --rm tests` antes de gravar, no host Docker da demonstração.

## Roteiro cronometrado

### 0:00–0:35 — Problema e proposta

**Tela:** título do projeto no `README.md`.

**Fala:**

> Extratos bancários costumam ser arquivos extensos e variam de banco para banco. O Statement
> Analyzer foi especificado para receber um CSV, normalizar seus lançamentos e responder
> perguntas como total de entradas e saídas, saldo e gastos repetidos. O escopo é analisar um
> extrato, não controlar orçamento nem categorizar despesas.

### 0:35–1:20 — Arquitetura

**Tela:** diagrama Mermaid no README; em seguida, módulos na árvore do projeto.

**Fala:**

> A aplicação separa leitura CSV, normalização, consultas, API e persistência. A camada HTTP
> traduz as requisições, enquanto as regras trabalham sem FastAPI ou SQL e usam centavos
> inteiros. As três fichas são sintéticas e demonstram convenções diferentes de sinal.

### 1:20–2:20 — Upload e análise

**Tela:** envie `dados/demo.csv` em `POST /extratos`; depois abra os endpoints de resumo,
`por-semana`, `repetidos` e `dias-no-negativo` no Swagger.

**Fala:**

> O upload retorna as linhas aceitas e recusadas. As consultas usam o extrato persistido: o
> resumo soma centavos, o agrupamento semanal começa na segunda-feira, e os gastos repetidos
> exigem ao menos três ocorrências dentro da tolerância de 10%. O saldo é avaliado em blocos por
> data, sem inventar ordem entre lançamentos do mesmo dia.

### 2:20–3:05 — Privacidade e uso de IA

**Tela:** `docs/RELATORIO_IA.md` e `ERROS.md`.

**Fala:**

> Dados bancários reais não são usados. A fixture da demonstração é gerada com semente fixa e
> o diretório `dados/` não é versionado. A equipe deve rever saídas de IA, dependências,
> privacidade e propriedade intelectual; os testes e a revisão humana são controles separados.

### 3:05–3:45 — Testes e limites

**Tela:** resultado de `docker compose run --rm tests` e `docs/COVERAGE.md`.

**Fala:**

> A suíte local tem 66 testes aprovados, cobertura de 94,6% em regras e 100% em consultas. O
> benchmark local processou cem mil linhas sintéticas em 1,25 segundo; isso não substitui uma
> medição de memória nem a validação nas condições exatas de hardware da especificação. O
> ambiente Docker e Python 3.12 devem ser confirmados no host de entrega.

## Encerramento

Finalize em até 4 minutos, mostrando respostas reais da API para o arquivo sintético e mantendo
as limitações de ambiente explícitas. Remova o serviço depois da gravação com
`docker compose down`; não use `-v`, para não apagar o volume local.
