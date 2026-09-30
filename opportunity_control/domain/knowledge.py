"""Información separada en evidencia, hipótesis e incógnitas."""

from dataclasses import dataclass
from datetime import datetime

from .enums import ConfidenceState
from .validation import DomainValidationError, require_text


@dataclass(frozen=True)
class Evidence:
    """Representa una afirmación respaldada por fuente y procedencia."""

    id: str
    opportunity_id: str
    statement: str
    source: str
    provenance: str
    confidence_state: ConfidenceState
    confidence: float
    recorded_at: datetime

    def __post_init__(self) -> None:
        """Valida la trazabilidad y confianza numérica de la evidencia."""

        require_text(self.id, "evidence.id")
        require_text(self.opportunity_id, "evidence.opportunity_id")
        require_text(self.statement, "evidence.statement")
        require_text(self.source, "evidence.source")
        require_text(self.provenance, "evidence.provenance")
        if (
            isinstance(self.confidence, bool)
            or not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise DomainValidationError("evidence.confidence debe estar entre 0 y 1")
        if not isinstance(self.confidence_state, ConfidenceState):
            raise DomainValidationError(
                "evidence.confidence_state debe ser un estado válido"
            )
        if self.confidence_state == ConfidenceState.UNKNOWN and self.confidence != 0:
            raise DomainValidationError("evidence UNKNOWN debe tener confianza 0")
        if (
            not isinstance(self.recorded_at, datetime)
            or self.recorded_at.tzinfo is None
        ):
            raise DomainValidationError(
                "evidence.recorded_at requiere fecha y zona horaria"
            )


@dataclass(frozen=True)
class Hypothesis:
    """Representa una explicación posible que todavía debe verificarse."""

    id: str
    opportunity_id: str
    statement: str
    rationale: str
    confidence_state: ConfidenceState = ConfidenceState.INFERRED
    confidence: float = 0.5

    def __post_init__(self) -> None:
        """Valida que la hipótesis incluya afirmación y fundamento."""

        require_text(self.id, "hypothesis.id")
        require_text(self.opportunity_id, "hypothesis.opportunity_id")
        require_text(self.statement, "hypothesis.statement")
        require_text(self.rationale, "hypothesis.rationale")
        if self.confidence_state is not ConfidenceState.INFERRED:
            raise DomainValidationError("hypothesis.confidence_state debe ser INFERRED")
        if (
            isinstance(self.confidence, bool)
            or not isinstance(self.confidence, (int, float))
            or not 0 <= self.confidence <= 1
        ):
            raise DomainValidationError("hypothesis.confidence debe estar entre 0 y 1")


@dataclass(frozen=True)
class Unknown:
    """Representa una pregunta que el sistema aún no puede responder."""

    id: str
    opportunity_id: str
    question: str
    confidence_state: ConfidenceState = ConfidenceState.UNKNOWN
    confidence: float = 0.0

    def __post_init__(self) -> None:
        """Valida que la incógnita esté vinculada y sea explícita."""

        require_text(self.id, "unknown.id")
        require_text(self.opportunity_id, "unknown.opportunity_id")
        require_text(self.question, "unknown.question")
        if self.confidence_state is not ConfidenceState.UNKNOWN:
            raise DomainValidationError("unknown.confidence_state debe ser UNKNOWN")
        if self.confidence != 0:
            raise DomainValidationError("unknown.confidence debe ser 0")
