"""Contrato de persistencia para el recorrido vertical."""

from typing import Protocol

from opportunity_control.domain.accounts import Contact
from opportunity_control.domain.decisions import Decision
from opportunity_control.domain.enums import ActionStatus
from opportunity_control.domain.opportunities import Signal
from opportunity_control.domain.proposals import Proposal


class WorkflowRepository(Protocol):
    """Almacenamiento adicional sin acoplamiento a SQLite."""

    def add_contact(self, contact: Contact) -> None:
        """Guarda un contacto sanitizado."""

    def list_contacts(self, account_id: str) -> list[Contact]:
        """Consulta contactos de una cuenta."""

    def add_signal(self, signal: Signal) -> None:
        """Guarda una señal con procedencia."""

    def list_signals(self, opportunity_id: str) -> list[Signal]:
        """Consulta señales de la oportunidad."""

    def add_proposal(self, proposal: Proposal) -> None:
        """Agrega una versión de recomendación."""

    def list_proposals(self, opportunity_id: str) -> list[Proposal]:
        """Consulta las versiones en orden de creación."""

    def add_decision(self, decision: Decision) -> None:
        """Guarda la decisión aprobada."""

    def get_decision(self, opportunity_id: str) -> Decision | None:
        """Consulta la decisión aprobada, si existe."""

    def save_ai_draft(self, opportunity_id: str, draft: dict[str, object]) -> None:
        """Guarda la salida íntegra del borrador."""

    def list_ai_drafts(self, opportunity_id: str) -> list[dict[str, object]]:
        """Consulta borradores persistidos."""

    def update_action_status(
        self, opportunity_id: str, action_id: str, status: ActionStatus
    ) -> None:
        """Actualiza exclusivamente el estado de una tarea interna."""
