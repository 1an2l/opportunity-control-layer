"""Evento inmutable para explicar cambios e intentos del sistema."""

from dataclasses import dataclass
from datetime import datetime

from .enums import EventOutcome, OpportunityStage
from .validation import require_text


@dataclass(frozen=True)
class AuditEvent:
    """Registra quién hizo qué, cuándo y con qué resultado."""

    id: str
    opportunity_id: str
    event_type: str
    actor: str
    occurred_at: datetime
    outcome: EventOutcome
    previous_stage: OpportunityStage | None = None
    next_stage: OpportunityStage | None = None
    detail: str = ""

    def __post_init__(self) -> None:
        """Valida los identificadores mínimos del evento auditable."""

        require_text(self.id, "audit_event.id")
        require_text(self.opportunity_id, "audit_event.opportunity_id")
        require_text(self.event_type, "audit_event.event_type")
        require_text(self.actor, "audit_event.actor")
