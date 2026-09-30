"""Punto de entrada para iniciar API e interfaz locales."""

import argparse
from pathlib import Path

from opportunity_control.api.access import LocalAccess
from opportunity_control.api.server import run_server
from opportunity_control.bootstrap import build_runtime


def main() -> None:
    """Procesa opciones seguras e inicia el servidor en localhost."""

    parser = argparse.ArgumentParser(
        description="BridgeLytic Opportunity Control Layer"
    )
    parser.add_argument(
        "--host",
        choices=("127.0.0.1", "localhost"),
        default="127.0.0.1",
        help="El prototipo sólo puede enlazarse a la máquina local.",
    )
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--editor-name", default="editor-local")
    parser.add_argument("--reviewer-name", default="revisor-local")
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("runtime/opportunity_control.db"),
    )
    arguments = parser.parse_args()
    runtime = build_runtime(arguments.database)
    try:
        run_server(
            runtime.api,
            host=arguments.host,
            port=arguments.port,
            access=LocalAccess(arguments.editor_name, arguments.reviewer_name),
        )
    finally:
        runtime.close()


if __name__ == "__main__":
    main()
