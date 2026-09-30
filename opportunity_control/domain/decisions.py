"""Opciones, recomendaciones y decisiones con aprobación humana."""

from dataclasses import dataclass
from datetime import datetime

from .validation import DomainValidationError, require_text


@dataclass(frozen=True)
class DecisionOption:
    """Representa una alternativa de decisión con razón y riesgo."""

    id: str
    opportunity_id: str
    title: str
    rationale: str
    risk: str

    def __post_init__(self) -> None:
        """Valida que la opción pueda ser evaluada de manera explícita."""

        require_text(self.id, "decision_option.id")
        require_text(self.opportunity_id, "decision_option.opportunity_id")
        require_text(self.title, "decision_option.title")
        require_text(self.rationale, "decision_option.rationale")
        require_text(self.risk, "decision_option.risk")


@dataclass(frozen=True)
class Recommendation:
    """Representa una propuesta interna que todavía requiere revisión."""

    opportunity_id: str
    recommended_option_id: str
    rationale: str

    def __post_init__(self) -> None:
        """Valida la opción recomendada y su explicación."""

        require_text(self.opportunity_id, "recommendation.opportunity_id")
        require_text(self.recommended_option_id, "recommendation.recommended_option_id")
        require_text(self.rationale, "recommendation.rationale")


@dataclass(frozen=True)
class Approval:
    """Representa la aprobación explícita realizada por una persona."""

    opportunity_id: str
    option_id: str
    actor: str
    approved_at: datetime

    def __post_init__(self) -> None:
        """Valida la identidad del objeto aprobado y de quien lo aprobó."""

        require_text(self.opportunity_id, "approval.opportunity_id")
        require_text(self.option_id, "approval.option_id")
        require_text(self.actor, "approval.actor")


@dataclass(frozen=True)
class Decision:
    """Representa una opción elegida y su aprobación humana asociada."""

    opportunity_id: str
    selected_option_id: str
    rationale: str
    approval: Approval
    proposal_id: str | None = None

    def __post_init__(self) -> None:
        """Impide asociar una aprobación de otra oportunidad u opción."""

        require_text(self.opportunity_id, "decision.opportunity_id")
        require_text(self.selected_option_id, "decision.selected_option_id")
        require_text(self.rationale, "decision.rationale")
        if self.approval.opportunity_id != self.opportunity_id:
            raise DomainValidationError("la aprobación pertenece a otra oportunidad")
        if self.approval.option_id != self.selected_option_id:
            raise DomainValidationError("la aprobación pertenece a otra opción")
