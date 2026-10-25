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
- A revisão do PR encontrou que `\d` e `str.isdigit()` aceitavam dígitos Unicode;
  a correção passou a aceitar somente dígitos ASCII e adicionou regressões para
  RN01, RN02 e RN05.

## Prompt da correção

Você está no repositório statement-analyzer, na branch feature/12-regras. Leia CLAUDE.md,
docs/SPEC.md (§4, RN01, RN02 e RN05) e docs/tarefas/CONTRATO.md (seção "app/regras.py").

A revisão do PR #18 encontrou um bug. Corrija-o sem mudar nenhum outro comportamento.

Bug: converter_valor usa str.isdigit() e converter_data usa \d na regex. Os dois aceitam
qualquer dígito Unicode, não só 0-9. Consequências:
1. converter_valor("1²", ",", ".") levanta ValueError, porque "²".isdigit() é True mas
   int("1²") falha. Com isso normalizar() levanta exceção em vez de devolver Recusa, e
   processar() aborta o arquivo inteiro: viola a RN05.
2. converter_valor("١٢,٣٠", ",", ".") devolve 1230, e
   converter_data("٠١/٠٩/٢٠٢٦", "dd/mm/aaaa") devolve date(2026, 9, 1). Dígitos não ASCII
   têm que ser recusados (RN01/RN02: recusar, não adivinhar).

Correção esperada:
- Em converter_valor, aceite só dígitos ASCII (por exemplo, troque x.isdigit() por
  x.isascii() and x.isdigit(), nas duas verificações, da parte inteira e da decimal).
- Em converter_data, troque \d por [0-9] nos três padrões.
- Nenhum float, nenhuma outra mudança de comportamento, mesmas assinaturas.

Regras:
- Só pode editar app/regras.py e tests/test_regras.py.
- Primeiro escreva os testes de regressão e veja que falham; depois corrija:
  - converter_valor("1²", ",", ".") == "VALOR_INVALIDO"
  - converter_valor("²", ",", ".") == "VALOR_INVALIDO"
  - converter_valor("١٢,٣٠", ",", ".") == "VALOR_INVALIDO"
  - converter_valor("12,٣٠", ",", ".") == "VALOR_INVALIDO"
  - converter_data("٠١/٠٩/٢٠٢٦", "dd/mm/aaaa") is None
  - normalizar() de uma LinhaCrua do banco-a com valor "1²" devolve Recusa com
    VALOR_INVALIDO (não levanta exceção)
  - processar() com uma linha boa e uma linha com valor "1²" devolve 1 aceito e 1 recusa
  Cada teste com docstring citando a RN (RN01, RN02 ou RN05).
- Rode: python -m pytest tests/test_regras.py -q --cov=app.regras --cov-report=term-missing
  Todos os testes antigos têm que continuar passando.
- Commit no padrão do CLAUDE.md: "Fix: aceita só dígitos ASCII em valor e data (RN01, RN02, RN05)".
- Acrescente em docs/prompts/felipe.md, na seção de correções, uma linha sobre esse bug
  (encontrado na revisão do PR) e cole este prompt na íntegra numa seção "Prompt da
  correção". Commit: "Docs: registra correção de dígitos Unicode".
- Não faça push: me mostre o resultado dos testes e o git diff primeiro.

Depois de conferir o resultado:

git push
