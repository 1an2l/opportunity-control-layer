"""Conexión y esquema SQLite de la capa de control de oportunidades."""

import sqlite3
from pathlib import Path

from .workflow_schema import WORKFLOW_SCHEMA

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY CHECK (length(trim(id)) > 0),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0)
);

CREATE TABLE IF NOT EXISTS opportunities (
    id TEXT PRIMARY KEY CHECK (length(trim(id)) > 0),
    account_id TEXT NOT NULL,
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    owner TEXT NOT NULL CHECK (length(trim(owner)) > 0),
    stage TEXT NOT NULL CHECK (
        stage IN (
            'INTAKE',
            'EVIDENCE_REVIEW',
            'OPTIONS_READY',
            'PENDING_APPROVAL',
            'APPROVED',
            'REJECTED',
            'PAUSED'
        )
    ),
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY CHECK (length(trim(id)) > 0),
    opportunity_id TEXT NOT NULL,
    statement TEXT NOT NULL CHECK (length(trim(statement)) > 0),
    source TEXT NOT NULL CHECK (length(trim(source)) > 0),
    provenance TEXT NOT NULL CHECK (length(trim(provenance)) > 0),
    confidence_state TEXT NOT NULL CHECK (
        confidence_state IN ('VERIFIED', 'INFERRED', 'UNKNOWN')
    ),
    confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    recorded_at TEXT NOT NULL,
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id)
);

CREATE TABLE IF NOT EXISTS hypotheses (
    id TEXT PRIMARY KEY CHECK (length(trim(id)) > 0),
    opportunity_id TEXT NOT NULL,
    statement TEXT NOT NULL CHECK (length(trim(statement)) > 0),
    rationale TEXT NOT NULL CHECK (length(trim(rationale)) > 0),
    confidence_state TEXT NOT NULL CHECK (confidence_state = 'INFERRED'),
    confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id)
);

CREATE TABLE IF NOT EXISTS unknowns (
    id TEXT PRIMARY KEY CHECK (length(trim(id)) > 0),
    opportunity_id TEXT NOT NULL,
    question TEXT NOT NULL CHECK (length(trim(question)) > 0),
    confidence_state TEXT NOT NULL CHECK (confidence_state = 'UNKNOWN'),
    confidence REAL NOT NULL CHECK (confidence = 0),
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id)
);

CREATE TABLE IF NOT EXISTS next_actions (
    id TEXT PRIMARY KEY CHECK (length(trim(id)) > 0),
    opportunity_id TEXT NOT NULL,
    description TEXT NOT NULL CHECK (length(trim(description)) > 0),
    owner TEXT NOT NULL CHECK (length(trim(owner)) > 0),
    due_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('PENDING', 'SIMULATED', 'BLOCKED', 'CANCELLED')
    ),
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id)
);

CREATE TABLE IF NOT EXISTS decision_options (
    id TEXT PRIMARY KEY CHECK (length(trim(id)) > 0),
    opportunity_id TEXT NOT NULL,
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    rationale TEXT NOT NULL CHECK (length(trim(rationale)) > 0),
    risk TEXT NOT NULL CHECK (length(trim(risk)) > 0),
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id),
    UNIQUE (id, opportunity_id)
);

CREATE TABLE IF NOT EXISTS approvals (
    opportunity_id TEXT PRIMARY KEY,
    option_id TEXT NOT NULL,
    actor TEXT NOT NULL CHECK (length(trim(actor)) > 0),
    approved_at TEXT NOT NULL,
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id),
    FOREIGN KEY (option_id, opportunity_id)
        REFERENCES decision_options(id, opportunity_id)
);

CREATE TABLE IF NOT EXISTS audit_events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT NOT NULL UNIQUE CHECK (length(trim(id)) > 0),
    opportunity_id TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (length(trim(event_type)) > 0),
    actor TEXT NOT NULL CHECK (length(trim(actor)) > 0),
    occurred_at TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('ACCEPTED', 'REJECTED')),
    previous_stage TEXT,
    next_stage TEXT,
    detail TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id),
    CHECK (
        previous_stage IS NULL OR previous_stage IN (
            'INTAKE', 'EVIDENCE_REVIEW', 'OPTIONS_READY',
            'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'PAUSED'
        )
    ),
    CHECK (
        next_stage IS NULL OR next_stage IN (
            'INTAKE', 'EVIDENCE_REVIEW', 'OPTIONS_READY',
            'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'PAUSED'
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_opportunities_account
    ON opportunities(account_id);
CREATE INDEX IF NOT EXISTS idx_evidence_opportunity
    ON evidence(opportunity_id, recorded_at, id);
CREATE INDEX IF NOT EXISTS idx_hypotheses_opportunity
    ON hypotheses(opportunity_id, id);
CREATE INDEX IF NOT EXISTS idx_unknowns_opportunity
    ON unknowns(opportunity_id, id);
CREATE INDEX IF NOT EXISTS idx_next_actions_opportunity
    ON next_actions(opportunity_id, due_date, id);
CREATE INDEX IF NOT EXISTS idx_decision_options_opportunity
    ON decision_options(opportunity_id, id);
CREATE INDEX IF NOT EXISTS idx_audit_events_opportunity
    ON audit_events(opportunity_id, sequence);

-- El historial es evidencia operativa: ni la aplicación ni SQL pueden reescribirlo.
CREATE TRIGGER IF NOT EXISTS audit_events_prevent_update
BEFORE UPDATE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'audit_events es append-only');
END;

CREATE TRIGGER IF NOT EXISTS audit_events_prevent_delete
BEFORE DELETE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'audit_events es append-only');
END;
"""


def connect_database(database_path: str | Path) -> sqlite3.Connection:
    """Abre SQLite con claves foráneas y filas accesibles por nombre."""

    # HTTPServer procesa una solicitud a la vez; permitir otro hilo facilita
    # pruebas locales sin introducir acceso concurrente a la conexión.
    connection = sqlite3.connect(str(database_path), check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(connection: sqlite3.Connection) -> None:
    """Crea tablas, índices y protecciones sin borrar datos existentes."""

    with connection:
        connection.executescript(SCHEMA_SQL + WORKFLOW_SCHEMA)
