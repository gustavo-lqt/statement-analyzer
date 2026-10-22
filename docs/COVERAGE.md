# Relatório de cobertura de testes

| Data da verificação | Ambiente |
| ------------------- | -------- |
| 22/10/2026          | Windows, Python 3.11.9, Pytest 8.4.2, pytest-cov 6.3.0 |

## Resultado

| Módulo alvo        | Statements | Não cobertas | Cobertura |
| ------------------ | ----------: | -----------: | --------: |
| `app/regras.py`    |         130 |            7 |     94,6% |
| `app/consultas.py` |         116 |            0 |    100,0% |
| **Total**          |     **246** |        **7** | **97,2%** |

Resultado da suíte: **66 testes passaram**. A meta RNF07 de pelo menos 80% foi atendida nos dois
módulos-alvo. Os sete statements não cobertos estão em ramos excepcionais de validação; o
relatório linha a linha está em `htmlcov/index.html` no workspace local.

## Reprodução

O relatório foi produzido com:

```bash
python -m pytest --cov=app.regras --cov=app.consultas --cov-report=term-missing --cov-report=html
```

O comando de referência do container é `docker compose run --rm tests`. A imagem está definida
para Python 3.12, mas não pôde ser construída neste host porque o daemon Docker estava
indisponível; portanto, os números acima correspondem ao Python 3.11.9 local, não a uma
execução Docker. A pasta `htmlcov/` é ignorada pelo Git; este resumo versionado preserva os
resultados numéricos e o ambiente da medição.
