from __future__ import annotations

import argparse
from pathlib import Path

from app.catalogo import carregar_fichas
from gerador.fixtures import gerar_csv_sintetico


def main() -> None:
    fichas = carregar_fichas()
    parser = argparse.ArgumentParser(description="Gera um CSV financeiro totalmente sintético.")
    parser.add_argument("--bank", choices=sorted(fichas), default="banco-a")
    parser.add_argument("--seed", type=int, default=20261022)
    parser.add_argument("--quantity", type=int, default=30)
    parser.add_argument("--output", type=Path, default=None)
    arguments = parser.parse_args()

    output = arguments.output or Path("dados") / f"{arguments.bank}-synthetic.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    content = gerar_csv_sintetico(
        fichas[arguments.bank], seed=arguments.seed, quantidade=arguments.quantity
    )
    output.write_bytes(content)
    print(f"CSV sintético gerado: {output} ({arguments.quantity} linhas)")


if __name__ == "__main__":
    main()