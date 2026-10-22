from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.api import create_app
from app.catalogo import carregar_fichas
from app.models import FichaBanco, Lancamento, LinhaCrua


@pytest.fixture
def fichas() -> dict[str, FichaBanco]:
    return carregar_fichas()


@pytest.fixture
def ficha(fichas: dict[str, FichaBanco]) -> FichaBanco:
    return fichas["banco-a"]


@pytest.fixture
def linha_factory() -> Callable[..., LinhaCrua]:
    def build(
        values: dict[str, str] | None = None,
        *,
        number: int = 2,
        raw: str = "synthetic row",
        reason: str | None = None,
    ) -> LinhaCrua:
        fields = values or {
            "data": "15/09/2026",
            "descricao": "Cafe sintetico",
            "valor": "12,34",
        }
        return LinhaCrua(number, raw, fields, reason)

    return build


@pytest.fixture
def lancamento_factory() -> Callable[..., Lancamento]:
    def build(
        transaction_date: str = "2026-09-15",
        amount: int = -1000,
        description: str = "SYNTHETIC ITEM",
        normalized: str | None = None,
    ) -> Lancamento:
        return Lancamento(
            transaction_date,
            amount,
            description,
            normalized if normalized is not None else description,
        )

    return build


@pytest.fixture
def client() -> TestClient:
    application = create_app(":memory:")
    with TestClient(application) as test_client:
        yield test_client
    application.state.database.close()