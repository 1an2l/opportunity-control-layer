"""Valores controlados que evitan estados inventados o ambiguos."""

from enum import Enum


class ConfidenceState(str, Enum):
    """Indica qué tan respaldada está una afirmación."""

    VERIFIED = "VERIFIED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"


class OpportunityStage(str, Enum):
    """Representa una etapa interna permitida para una oportunidad."""

    INTAKE = "INTAKE"
    EVIDENCE_REVIEW = "EVIDENCE_REVIEW"
    OPTIONS_READY = "OPTIONS_READY"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PAUSED = "PAUSED"


class ActionStatus(str, Enum):
    """Representa el estado interno de una acción que no se ejecuta afuera."""

    PENDING = "PENDING"
    SIMULATED = "SIMULATED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"


class EventOutcome(str, Enum):
    """Indica si una operación auditada fue aceptada o rechazada."""

    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
