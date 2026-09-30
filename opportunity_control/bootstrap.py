"""Composición de dependencias para ejecutar el producto local."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from opportunity_control.ai import LocalGovernedDraftGenerator
from opportunity_control.api import ApiApplication
from opportunity_control.application import OpportunityControlService
from opportunity_control.infrastructure import (
    SQLiteOpportunityRepository,
    connect_database,
    initialize_database,
)
from opportunity_control.seed import seed_repository


@dataclass
class RuntimeApplication:
    """Mantiene juntas la API y la conexión que debe cerrarse al terminar."""

    api: ApiApplication
    connection: sqlite3.Connection

    def close(self) -> None:
        """Cierra la base local de forma explícita."""

        self.connection.close()


def build_runtime(database_path: str | Path) -> RuntimeApplication:
    """Inicializa esquema y seed sólo cuando la base está vacía."""

    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = connect_database(path)
    initialize_database(connection)
    repository = SQLiteOpportunityRepository(connection)
    if not repository.list_accounts():
        seed_repository(repository)
    service = OpportunityControlService(repository)
    api = ApiApplication(service, LocalGovernedDraftGenerator())
    return RuntimeApplication(api=api, connection=connection)
