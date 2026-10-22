# ADR-007 — Dependências de execução e teste

**Status:** implementada para esta entrega; revisão da equipe pendente  
**Data:** 22/10/2026

## Contexto

A especificação define FastAPI, pytest e Docker, mas o repositório ainda não tinha manifesto de
dependências. O upload `multipart/form-data` exige um parser compatível; a aplicação precisa de
um servidor ASGI; e a validação de contrato HTTP e RNF07 exige cliente de teste e medição de
cobertura.

## Decisão implementada

As dependências diretas estão declaradas em `requirements.txt`:

- `fastapi` para os contratos HTTP definidos na SPEC;
- `uvicorn` para servir a aplicação ASGI;
- `python-multipart` para receber uploads multipart;
- `pytest` e `httpx` para testes unitários e integração da API;
- `pytest-cov` para medir a RNF07 e emitir relatório.

O SQLite permanece na biblioteca padrão do Python. Versões estão limitadas por intervalos
compatíveis; o ambiente de entrega ainda deve validar e travar a resolução. Nenhum extrato real
é necessário para instalar, testar ou demonstrar a aplicação.

## Consequências

A instalação passa a ser reproduzível e o harness pode executar testes e relatório de
cobertura. Há dependências externas adicionais, que exigem revisão de versões, licenças e
atualizações de segurança antes da integração na branch protegida.

## Validação pendente

O manifesto e a aplicação foram exercitados localmente em Python 3.11.9. A equipe ainda deve
revisar versões, licenças e atualizações antes da integração final. O build com Python 3.12 não
foi executado porque o daemon Docker estava indisponível no host desta implementação.
