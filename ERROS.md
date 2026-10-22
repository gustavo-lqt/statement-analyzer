# Registro de falhas e validação

Este arquivo registra defeitos encontrados durante implementação, evidência de correção e
limitações de validação. Todos os exemplos e testes usam dados sintéticos.

## Estado atual

| Verificação | Resultado | Evidência ou limitação |
|---|---|---|
| Suíte Pytest | 66 passaram | Executada no Windows com Python 3.11.9 |
| Cobertura RNF07 | Regras 94,6%; consultas 100%; total 97,2% | Relatório em `docs/COVERAGE.md` |
| Importação de 100.000 linhas | 1,25 s | Medição local sintética; não certifica 2 vCPU/4 GB nem consumo de memória |
| Docker e Python 3.12 | Não validados neste host | Daemon Docker indisponível; imagem configurada para Python 3.12 |

## Falhas corrigidas

| Regra/área | Sintoma | Causa raiz | Correção e regressão |
|---|---|---|---|
| RN02 | `1.234,56` era recusado | A validação de dígitos ocorria antes da remoção do separador de milhar | Validar agrupamento e remover o milhar antes da conversão; coberto em `tests/test_regras.py` |
| RN04 | Precisão acima de duas casas recebia `VALOR_INVALIDO` | Erros monetários eram colapsados em um único motivo | Detectar precisão excedente antes do parse e devolver `PRECISAO_INVALIDA`; coberto em `tests/test_regras.py` |
| RN05 | Byte UTF-8 inválido no meio do arquivo abortava a leitura | O decodificador fazia leitura antecipada do fluxo completo | Decodificar linhas físicas e recusar somente o registro, continuando os seguintes; coberto em `tests/test_leitura.py` |
| RN07 | Saldo inicial omitido era indistinguível de zero informado | Apenas o valor numérico era persistido | Persistir `saldo_inicial_assumido`; coberto em `tests/test_db.py` e `tests/test_api.py` |

Não há falha conhecida na última execução local. A validação Docker/Python 3.12 continua
pendente; aprovação local não substitui essa checagem no ambiente de referência.

Não incluir descrições de lançamentos, extratos ou qualquer dado bancário real neste arquivo,
em logs ou fixtures (RNF05 e RNF06).
