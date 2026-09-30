"""Adaptadores locales para almacenamiento y otras tecnologías concretas."""

from .database import connect_database, initialize_database
from .repositories import SQLiteOpportunityRepository

__all__ = [
    "SQLiteOpportunityRepository",
    "connect_database",
    "initialize_database",
]
