# Registro de falhas e validação

Este registro separa falhas observadas de verificações que não puderam ser executadas.
Não há harness no estado atual do repositório; portanto, não atribuímos erros hipotéticos a
uma execução inexistente.

## Estado da validação

| Data | Verificação | Resultado | Causa | Correção ou prevenção |
|---|---|---|---|---|
| 2026-10-22 | Inspeção do conteúdo versionado | Bloqueada | `app/` e `tests/` contêm apenas `.gitkeep`; não há `docker-compose.yml` nem projeto Python executável. | Adicionar a implementação e o harness previstos em `docs/SPEC.md` antes de rodar testes. |
| 2026-10-22 | Pytest e cobertura | Não executados | O comando `pytest` não está disponível neste ambiente e não há testes no repositório. Instalar uma dependência isoladamente não criaria testes nem código a medir. | Após a entrega do harness, configurar as dependências aprovadas, executar a suíte completa e guardar o relatório real, incluindo a cobertura de `app/regras.py` e `app/consultas.py`. |

Nenhuma falha lógica de teste foi observada nesta revisão: nenhum teste pôde ser iniciado.
Este estado não equivale a uma suíte aprovada.

## Registro de falhas do harness

Quando o harness existir, registrar cada falha com evidência reproduzível:

| Data | Teste/regra | Sintoma e evidência | Causa raiz | Correção | Prevenção/regressão |
|---|---|---|---|---|---|
| — | Ainda não há execuções | — | Harness ausente | — | Preencher esta linha somente após executar os testes. |

Não incluir descrições de lançamentos ou qualquer dado bancário real neste arquivo. Fixtures
e exemplos devem ser sintéticos, conforme RNF05 e RNF06.