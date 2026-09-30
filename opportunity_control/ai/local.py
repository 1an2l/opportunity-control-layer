"""Generador local determinista para demos sin credenciales ni red."""

from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid4

from opportunity_control.application.briefs import FounderBrief

from .models import AIDraft


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _draft_id() -> str:
    return f"AI-DRAFT-{uuid4()}"


class LocalGovernedDraftGenerator:
    """Construye propuestas reproducibles sin fingir una llamada a un LLM."""

    def __init__(
        self,
        *,
        clock: Callable[[], datetime] = _utc_now,
        id_factory: Callable[[], str] = _draft_id,
    ) -> None:
        self._clock = clock
        self._id_factory = id_factory

    def generate(self, brief: FounderBrief) -> AIDraft:
        """Genera un borrador etiquetado a partir de datos ya registrados."""

        option_id = brief.options[0].id if brief.options else None
        hypothesis_texts = tuple(item.statement for item in brief.hypotheses)
        if not hypothesis_texts:
            hypothesis_texts = (
                "Falta revisión humana para formular una hipótesis sustentada.",
            )

        return AIDraft(
            id=self._id_factory(),
            opportunity_id=brief.opportunity.id,
            mode="local",
            provider="deterministic-local",
            model="governed-draft-v1",
            prompt_version="founder-brief-v1",
            generated_at=self._clock(),
            summary=(
                f"Borrador local para {brief.account.name}: "
                f"{len(brief.evidence)} evidencias, "
                f"{len(brief.hypotheses)} hipótesis y "
                f"{len(brief.unknowns)} incógnitas registradas."
            ),
            proposed_hypotheses=hypothesis_texts,
            recommended_option_id=option_id,
            rationale=(
                "Si aparece una opción, se muestra la primera por orden estable "
                "únicamente para revisión; no es una decisión automática."
            ),
            limitations=(
                "Modo local sin llamada a un modelo externo.",
                "No verifica fuentes ni convierte hipótesis en hechos.",
                "No cambia etapas, no aprueba y no ejecuta acciones.",
            ),
        )
