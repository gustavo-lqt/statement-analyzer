# Registro de uso de IA — Felipe

## Prompt principal

Solicitei a implementação do motor puro de normalização e validação da U3
(Issues #12 e #3), seguindo `docs/SPEC.md` e `docs/tarefas/CONTRATO.md`, com as
funções `converter_data`, `converter_valor`, `normalizar` e `processar`.

Restrições destacadas no prompt:

- alterar somente `app/regras.py` e `tests/test_regras.py`;
- manter dinheiro como inteiro em centavos, sem `float` ou arredondamento;
- validar datas estritamente conforme a ficha;
- preservar a ordem de validação de `normalizar`;
- continuar o processamento após recusas;
- testar RN01–RN06 e obter pelo menos 80% de cobertura.

## Correções e validação

- Ajustei os testes para seguir as assinaturas congeladas do contrato:
  `converter_data(texto, formato) -> date | None` e
  `converter_valor(texto, separador_decimal, separador_milhar) -> int | str`.
- A revisão encontrou aceitação indevida de espaços internos em valores entre
  parênteses; foi adicionado um teste regressivo e a implementação passou a
  aceitar espaços somente nas pontas.
- Validação final:
  `python -m pytest tests/test_regras.py -q --cov=app.regras --cov-report=term-missing`
  com 38 testes aprovados e 94% de cobertura.
