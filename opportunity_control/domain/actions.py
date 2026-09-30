"""Siguientes acciones internas sin capacidad de ejecución externa."""

from dataclasses import dataclass
from datetime import date

from .enums import ActionStatus
from .validation import require_text


@dataclass(frozen=True)
class NextAction:
    """Representa un próximo paso interno con responsable y fecha."""

    id: str
    opportunity_id: str
    description: str
    owner: str
    due_date: date
    status: ActionStatus = ActionStatus.PENDING

    def __post_init__(self) -> None:
        """Valida los datos necesarios para administrar la acción."""

        require_text(self.id, "next_action.id")
        require_text(self.opportunity_id, "next_action.opportunity_id")
        require_text(self.description, "next_action.description")
        require_text(self.owner, "next_action.owner")
