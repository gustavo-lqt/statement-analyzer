# Relatório de cobertura de testes

| Data da verificação | Estado |
|---|---|
| 22/10/2026 | Não medido; nenhum relatório de execução foi gerado |

## Resultado

| Módulo alvo | Cobertura | Estado |
|---|---:|---|
| `app/regras.py` | N/A | Arquivo não existe |
| `app/consultas.py` | N/A | Arquivo não existe |

O diretório `tests/` contém somente `.gitkeep`. Não há testes Pytest, dependências de teste ou
`docker-compose.yml`; o comando `pytest` também não está disponível no ambiente verificado.
Sem código e testes executáveis, qualquer percentual seria enganoso. Este documento registra o
bloqueio e não substitui um relatório gerado pelo runner.

## Configuração preparada

O arquivo `.coveragerc` define os módulos de origem e o mínimo de 80% previsto pela RNF07.
Nenhuma dependência foi instalada. Quando a aplicação e o harness forem adicionados, a equipe
deve aprovar e incluir `pytest-cov` nas dependências de teste, configurar o serviço `tests` para
executar `pytest --cov --cov-report=term-missing --cov-report=html` e validar a suíte completa
no ambiente de referência:

```bash
docker compose run --rm tests
```

Depois da execução, substituir este registro por evidência real: comando e ambiente, resultado
da suíte, percentual medido de cada módulo, linhas não cobertas e artefato produzido. A meta
RNF07 só é atendida quando `app/regras.py` e `app/consultas.py` atingirem pelo menos 80% na
execução validada.