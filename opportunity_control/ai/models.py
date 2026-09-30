"""Contratos de salida para borradores generados por IA o replay local."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AIDraft:
    """Propuesta informativa que nunca equivale a evidencia o aprobación."""

    id: str
    opportunity_id: str
    mode: str
    provider: str
    model: str
    prompt_version: str
    generated_at: datetime
    summary: str
    proposed_hypotheses: tuple[str, ...]
    recommended_option_id: str | None
    rationale: str
    limitations: tuple[str, ...]
    requires_human_review: bool = True
    can_execute_external_actions: bool = False
