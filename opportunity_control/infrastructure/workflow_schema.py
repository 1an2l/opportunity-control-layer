"""Tablas adicionales del recorrido señal → propuesta → decisión."""

WORKFLOW_SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY, account_id TEXT NOT NULL REFERENCES accounts(id),
    role TEXT NOT NULL, display_name TEXT
);
CREATE TABLE IF NOT EXISTS signals (
    id TEXT PRIMARY KEY, opportunity_id TEXT NOT NULL REFERENCES opportunities(id),
    account_id TEXT NOT NULL REFERENCES accounts(id), title TEXT NOT NULL,
    observed_at TEXT NOT NULL, source TEXT NOT NULL, provenance TEXT NOT NULL,
    UNIQUE(opportunity_id, title, source, observed_at)
);
CREATE TABLE IF NOT EXISTS proposals (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE,
    opportunity_id TEXT NOT NULL REFERENCES opportunities(id), option_id TEXT NOT NULL,
    rationale TEXT NOT NULL, evidence_ids TEXT NOT NULL, hypothesis_ids TEXT NOT NULL,
    unknown_ids TEXT NOT NULL, actor TEXT NOT NULL, created_at TEXT NOT NULL,
    FOREIGN KEY(option_id, opportunity_id) REFERENCES decision_options(id, opportunity_id)
);
CREATE TABLE IF NOT EXISTS decisions (
    opportunity_id TEXT PRIMARY KEY REFERENCES approvals(opportunity_id),
    selected_option_id TEXT NOT NULL, rationale TEXT NOT NULL,
    proposal_id TEXT REFERENCES proposals(id),
    FOREIGN KEY(selected_option_id, opportunity_id) REFERENCES decision_options(id, opportunity_id)
);
CREATE TABLE IF NOT EXISTS ai_drafts (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE,
    opportunity_id TEXT NOT NULL REFERENCES opportunities(id), payload TEXT NOT NULL
);
"""
