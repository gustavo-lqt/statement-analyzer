# Relatório técnico e ético sobre uso de IA

| Projeto            | Data       |
| ------------------ | ---------- |
| Statement Analyzer | 22/10/2026 |

**Escopo da evidência:** registro do uso de GitHub Copilot como assistência de implementação e
análise dos riscos associados. Não foi conduzido benchmark comparativo entre produtos; a matriz
compara superfícies e pontos de avaliação, não qualidade medida.

## Matriz comparativa

As ferramentas abaixo representam formas distintas de integrar assistência de IA ao trabalho.
Recursos, modelos, retenção, controles administrativos e termos variam por versão, plano,
configuração e região. A equipe deve confirmar as condições vigentes diretamente com cada
fornecedor antes de enviar qualquer conteúdo.

| Ferramenta  | Superfície típica de trabalho                                       | Ponto de avaliação para este projeto                                                  | Evidência neste repositório |
| ----------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | --------------------------- |
| Claude Code | Agente integrado ao fluxo de desenvolvimento e terminal             | Avaliar revisão de alterações, permissões concedidas e tratamento de contexto enviado | Nenhum uso comprovado       |
| Codex CLI   | Agente de desenvolvimento operado por interface de linha de comando | Avaliar escopo de execução, revisão de patches e condições de tratamento de dados     | Nenhum uso comprovado       |
| Cursor      | Editor de código com assistência e recursos de agente               | Avaliar indexação do workspace, controles de privacidade e revisão de alterações      | Nenhum uso comprovado       |
| Antigravity | Ambiente de desenvolvimento com recursos de agente                  | Avaliar permissões, ações automatizadas, retenção e revisão do resultado              | Nenhum uso comprovado       |
| GitHub Copilot | Assistência integrada ao desenvolvimento no VS Code               | Revisar sugestões, mudanças aplicadas, contexto enviado e políticas da organização    | Usado para apoiar a implementação desta entrega |

A decisão deve considerar qualidade observada em tarefas equivalentes, integração ao fluxo,
controles de acesso e termos aplicáveis. Antes de escolher, comparar versões e configurações
concretas; nomes de produto, isoladamente, não permitem concluir que um tratamento atende à
LGPD ou às políticas da equipe.

## Quatro pilares éticos

### 1. Alucinação e confiabilidade

Um modelo pode produzir código plausível que viole as regras do projeto, por exemplo usar
ponto flutuante em dinheiro ou arredondar uma precisão que a RN04 manda recusar. Uma resposta
do modelo não é evidência de correção.

Controles previstos:

- Tratar `docs/SPEC.md` como fonte normativa e interromper a implementação quando faltar
  requisito.
- Cobrir regras e fronteiras com testes determinísticos; executar a suíte completa antes de
  aceitar uma mudança.
- Revisar diffs, erros e resultados de execução por uma pessoa responsável.
- Não apresentar testes inexistentes ou não executados como aprovados. A suíte desta entrega
  teve 65 testes aprovados em Python 3.11.9; a imagem Python 3.12 e o Docker não foram
  validados neste host.

### 2. Privacidade e LGPD

Extratos podem conter dados pessoais e financeiros. O repositório é público e proíbe dados
bancários reais em código, prompts versionados, issues, logs e fixtures (RNF05 e RNF06). O
envio de conteúdo a um fornecedor de IA pode constituir tratamento de dados; a ferramenta
escolhida não elimina as obrigações de finalidade, necessidade, transparência, segurança e
avaliação das bases legais aplicáveis. Este relatório não é parecer jurídico nem certificação
de conformidade.

Controles previstos:

- Usar dados sintéticos, gerados com semente fixa, em exemplos e testes.
- Nesta implementação, os CSVs usados nas validações foram sintéticos; nenhum extrato bancário
  real foi incluído no repositório ou usado como fixture.
- Não enviar extratos reais, credenciais, tokens ou dados identificáveis ao modelo.
- Antes de habilitar uma ferramenta, revisar configurações de retenção, treinamento,
  suboperadores, localização, controles administrativos e contrato de tratamento aplicável.
- Sanitizar logs e saídas para não registrar descrições de lançamentos em texto claro.

### 3. Propriedade intelectual

Saídas de IA podem conter trechos semelhantes a material existente, dependências ou código sob
licença incompatível. A geração por IA não comprova originalidade, titularidade ou permissão de
redistribuição. A avaliação depende do conteúdo, das licenças e dos termos vigentes.

Controles previstos:

- Revisar dependências, licenças e avisos antes de incorporar código externo.
- Não solicitar reprodução de código proprietário ou de obras protegidas não fornecidas com
  autorização.
- Manter atribuição e avisos exigidos por licenças; pedir revisão quando a origem de um trecho
  for incerta.
- Não adicionar dependências sem aprovação e registro arquitetural, conforme `CLAUDE.md`.

### 4. Revisão humana e responsabilização

O autor humano continua responsável pelo conteúdo submetido. A IA pode auxiliar a análise, mas
não aprova requisitos, segurança, privacidade nem publicação.

Controles previstos:

- Revisar cada alteração em Pull Request e manter a proteção de branch definida pela
  governança do repositório.
- Solicitar revisão humana independente dos commits antes de integrar ou publicar a versão
  final em branch protegida; a assistência de IA não equivale a essa aprovação.
- Exigir evidência de testes executáveis, além de inspeção do diff e dos impactos na SPEC.
- Registrar limitações e decisões, sem atribuir ao modelo responsabilidade pela decisão final.
- Bloquear publicação se testes, revisão ou tratamento de dados não puderem ser confirmados.

## Conclusão

GitHub Copilot foi usado como apoio à implementação, mas não houve comparação experimental
com Claude Code, Codex CLI, Cursor ou Antigravity. A revisão humana independente continua
pendente. A equipe deve confirmar os controles e termos vigentes da ferramenta escolhida e
aplicar os quatro pilares acima a todo o ciclo de desenvolvimento.
