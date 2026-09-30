"""Entidades que describen señales y oportunidades comerciales internas."""

from dataclasses import dataclass
from datetime import date

from .enums import OpportunityStage
from .validation import require_text


@dataclass(frozen=True)
class Signal:
    """Representa un movimiento observado que merece evaluación."""

    id: str
    account_id: str
    title: str
    observed_at: date
    opportunity_id: str
    source: str
    provenance: str

    def __post_init__(self) -> None:
        """Valida los textos obligatorios de la señal."""

        require_text(self.id, "signal.id")
        require_text(self.account_id, "signal.account_id")
        require_text(self.title, "signal.title")
        require_text(self.opportunity_id, "signal.opportunity_id")
        require_text(self.source, "signal.source")
        require_text(self.provenance, "signal.provenance")


@dataclass(frozen=True)
class Opportunity:
    """Representa un caso de negocio gobernado mediante etapas."""

    id: str
    account_id: str
    title: str
    owner: str
    stage: OpportunityStage = OpportunityStage.INTAKE

    def __post_init__(self) -> None:
        """Valida los datos mínimos para controlar la oportunidad."""

        require_text(self.id, "opportunity.id")
        require_text(self.account_id, "opportunity.account_id")
        require_text(self.title, "opportunity.title")
        require_text(self.owner, "opportunity.owner")
