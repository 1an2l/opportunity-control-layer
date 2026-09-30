"""Propuesta trazable: una recomendación no equivale a una decisión."""

from dataclasses import dataclass
from datetime import datetime

from .validation import DomainValidationError, require_text


@dataclass(frozen=True)
class Proposal:
    """Conserva alternativa, evidencia y supuestos revisados por una persona."""

    id: str
    opportunity_id: str
    option_id: str
    rationale: str
    evidence_ids: tuple[str, ...]
    hypothesis_ids: tuple[str, ...]
    unknown_ids: tuple[str, ...]
    actor: str
    created_at: datetime

    def __post_init__(self) -> None:
        """Exige una justificación y referencias explícitas, nunca implícitas."""
        for field in ("id", "opportunity_id", "option_id", "rationale", "actor"):
            require_text(getattr(self, field), f"proposal.{field}")
        if not self.evidence_ids:
            raise DomainValidationError("la propuesta requiere evidencia referenciada")
        for values in (self.evidence_ids, self.hypothesis_ids, self.unknown_ids):
            if len(values) != len(set(values)):
                raise DomainValidationError("las referencias no deben repetirse")
            for value in values:
                require_text(value, "proposal.reference")
