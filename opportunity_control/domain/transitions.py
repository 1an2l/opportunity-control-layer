"""Mapa y reglas deterministas para cambiar etapas de oportunidad."""

from .decisions import Approval
from .enums import OpportunityStage
from .validation import DomainValidationError

ALLOWED_TRANSITIONS: dict[OpportunityStage, frozenset[OpportunityStage]] = {
    OpportunityStage.INTAKE: frozenset({OpportunityStage.EVIDENCE_REVIEW}),
    OpportunityStage.EVIDENCE_REVIEW: frozenset(
        {OpportunityStage.OPTIONS_READY, OpportunityStage.PAUSED}
    ),
    OpportunityStage.OPTIONS_READY: frozenset(
        {OpportunityStage.PENDING_APPROVAL, OpportunityStage.PAUSED}
    ),
    OpportunityStage.PENDING_APPROVAL: frozenset(
        {
            OpportunityStage.APPROVED,
            OpportunityStage.REJECTED,
            OpportunityStage.PAUSED,
        }
    ),
    OpportunityStage.PAUSED: frozenset({OpportunityStage.EVIDENCE_REVIEW}),
    OpportunityStage.APPROVED: frozenset(),
    OpportunityStage.REJECTED: frozenset(),
}


def validate_transition(
    current_stage: OpportunityStage,
    next_stage: OpportunityStage,
    *,
    evidence_count: int = 0,
    option_count: int = 0,
    approval: Approval | None = None,
) -> None:
    """Valida una transición sin modificar estado ni ejecutar acciones."""

    if next_stage not in ALLOWED_TRANSITIONS[current_stage]:
        raise DomainValidationError(
            f"transición inválida: {current_stage.value} -> {next_stage.value}"
        )

    if next_stage is OpportunityStage.OPTIONS_READY and evidence_count < 1:
        raise DomainValidationError(
            "se requiere al menos una evidencia antes de preparar opciones"
        )

    if next_stage is OpportunityStage.PENDING_APPROVAL and not 2 <= option_count <= 3:
        raise DomainValidationError(
            "se requieren entre dos y tres opciones antes de pedir aprobación"
        )

    # La aprobación debe provenir de una persona; el dominio nunca la infiere.
    if next_stage is OpportunityStage.APPROVED and approval is None:
        raise DomainValidationError(
            "una decisión no puede aprobarse sin aprobación humana explícita"
        )
