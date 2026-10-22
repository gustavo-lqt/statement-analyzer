# ADR-007 — Dependências de execução e teste

**Status:** proposta para revisão da equipe  
**Data:** 22/10/2026

## Contexto

A especificação define FastAPI, pytest e Docker, mas o repositório ainda não tinha manifesto de
dependências. O upload `multipart/form-data` exige um parser compatível; a aplicação precisa de
um servidor ASGI; e a validação de contrato HTTP e RNF07 exige cliente de teste e medição de
cobertura.

## Decisão proposta

Declarar no manifesto as dependências diretas necessárias:

- `fastapi` para os contratos HTTP definidos na SPEC;
- `uvicorn` para servir a aplicação ASGI;
- `python-multipart` para receber uploads multipart;
- `pytest` e `httpx` para testes unitários e integração da API;
- `pytest-cov` para medir a RNF07 e emitir relatório.

O SQLite permanece na biblioteca padrão do Python. Versões serão limitadas por intervalos
compatíveis no manifesto e devem ser travadas pelo ambiente de entrega após revisão. Nenhum
extrato real é necessário para instalar, testar ou demonstrar a aplicação.

## Consequências

A instalação passa a ser reproduzível e o harness pode executar testes e relatório de
cobertura. Há dependências externas adicionais, que exigem revisão de versões, licenças e
atualizações de segurança antes da integração na branch protegida.

## Validação pendente

Esta ADR documenta a necessidade técnica, mas a equipe deve revisar e aprovar as dependências
antes de integrar o manifesto em uma entrega oficial.