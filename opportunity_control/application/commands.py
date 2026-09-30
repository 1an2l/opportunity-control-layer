"""Solicitudes inmutables que reciben los casos de uso de aplicación."""

from dataclasses import dataclass

from opportunity_control.domain import (
    Approval,
    DecisionOption,
    Evidence,
    Hypothesis,
    NextAction,
    OpportunityStage,
    Unknown,
)
from opportunity_control.domain.decisions import Decision


@dataclass(frozen=True)
class RecordEvidenceCommand:
    """Solicita registrar evidencia y el actor responsable."""

    evidence: Evidence
    actor: str


@dataclass(frozen=True)
class RecordDecisionOptionCommand:
    """Solicita registrar una opción y el actor responsable."""

    option: DecisionOption
    actor: str


@dataclass(frozen=True)
class RecordHypothesisCommand:
    """Solicita registrar una hipótesis separada de la evidencia."""

    hypothesis: Hypothesis
    actor: str


@dataclass(frozen=True)
class RecordUnknownCommand:
    """Solicita registrar una pregunta que permanece sin respuesta."""

    unknown: Unknown
    actor: str


@dataclass(frozen=True)
class RecordNextActionCommand:
    """Solicita registrar un siguiente paso exclusivamente interno."""

    action: NextAction
    actor: str


@dataclass(frozen=True)
class TransitionOpportunityCommand:
    """Solicita cambiar una oportunidad a una etapa específica."""

    opportunity_id: str
    next_stage: OpportunityStage
    actor: str
    approval: Approval | None = None
    decision: Decision | None = None
    rationale: str | None = None
