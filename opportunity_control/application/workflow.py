"""Casos de uso del recorrido completo y sus límites operativos."""

from dataclasses import replace

from opportunity_control.domain import (
    Approval,
    DomainValidationError,
    EventOutcome,
    OpportunityStage,
)
from opportunity_control.domain.accounts import Account, Contact
from opportunity_control.domain.decisions import Decision
from opportunity_control.domain.enums import ActionStatus
from opportunity_control.domain.opportunities import Opportunity, Signal
from opportunity_control.domain.proposals import Proposal
from opportunity_control.domain.validation import require_text

from .commands import TransitionOpportunityCommand
from .errors import RecordNotFoundError


class WorkflowOperations:
    """Operaciones agrupadas por flujo; no conocen HTTP, SQL ni la interfaz."""

    def create_opportunity(
        self, account: Account, opportunity: Opportunity, actor: str
    ) -> None:
        """Crea cuenta y oportunidad de intake de forma atómica."""
        if (
            opportunity.account_id != account.id
            or opportunity.stage != OpportunityStage.INTAKE
        ):
            raise DomainValidationError(
                "la oportunidad debe iniciar en INTAKE en la cuenta indicada"
            )
        with self._repository.transaction():
            existing = self._repository.get_account(account.id)
            if existing is None:
                self._repository.add_account(account)
            elif existing.name != account.name:
                raise DomainValidationError(
                    "el identificador de cuenta ya tiene otro nombre"
                )
            self._repository.add_opportunity(opportunity)
            self._repository.append_audit_event(
                self._content_event(
                    opportunity.id,
                    actor,
                    "OPPORTUNITY_CREATED",
                    f"Cuenta: {account.id}; owner: {opportunity.owner}",
                )
            )

    def record_signal(self, signal: Signal, actor: str) -> None:
        """Registra una señal sin elevarla automáticamente a evidencia."""
        with self._repository.transaction():
            opportunity = self._get_opportunity(signal.opportunity_id)
            self._require_editable(opportunity.id)
            if opportunity.account_id != signal.account_id:
                raise DomainValidationError("la señal pertenece a otra cuenta")
            if signal.observed_at > self._clock().date():
                raise DomainValidationError(
                    "una señal observada no puede tener fecha futura"
                )
            self._repository.add_signal(signal)
            self._repository.append_audit_event(
                self._content_event(
                    opportunity.id,
                    actor,
                    "SIGNAL_RECORDED",
                    f"Señal: {signal.id}; fuente: {signal.source}",
                )
            )

    def record_contact(self, opportunity_id: str, contact: Contact, actor: str) -> None:
        """Registra sólo una referencia sanitizada, sin datos de conexión."""
        with self._repository.transaction():
            opportunity = self._get_opportunity(opportunity_id)
            if opportunity.account_id != contact.account_id:
                raise DomainValidationError("el contacto pertenece a otra cuenta")
            self._repository.add_contact(contact)
            self._repository.append_audit_event(
                self._content_event(
                    opportunity_id,
                    actor,
                    "CONTACT_RECORDED",
                    f"Rol sanitizado: {contact.id}",
                )
            )

    def record_proposal(self, proposal: Proposal) -> None:
        """Valida referencias y conserva una nueva versión de recomendación."""
        with self._repository.transaction():
            self._require_editable(proposal.opportunity_id)
            brief = self.get_founder_brief(proposal.opportunity_id)
            if proposal.option_id not in {item.id for item in brief.options}:
                raise DomainValidationError(
                    "la opción recomendada no pertenece a esta oportunidad"
                )
            for references, records in (
                (proposal.evidence_ids, brief.evidence),
                (proposal.hypothesis_ids, brief.hypotheses),
                (proposal.unknown_ids, brief.unknowns),
            ):
                if not set(references) <= {item.id for item in records}:
                    raise DomainValidationError(
                        "referencia inexistente o de otra oportunidad"
                    )
            self._repository.add_proposal(proposal)
            self._repository.append_audit_event(
                self._content_event(
                    proposal.opportunity_id,
                    proposal.actor,
                    "PROPOSAL_RECORDED",
                    f"Propuesta: {proposal.id}; opción: {proposal.option_id}; evidencia: {', '.join(proposal.evidence_ids)}",
                )
            )

    def decide(
        self,
        opportunity_id: str,
        *,
        proposal_id: str,
        option_id: str,
        rationale: str,
        actor: str,
        confirmed: bool,
    ) -> Decision:
        """Persiste elección, aprobación, transición y evento en una transacción."""
        require_text(rationale, "decision.rationale")
        if confirmed is not True:
            raise DomainValidationError("se requiere confirmación humana explícita")
        with self._repository.transaction():
            proposals = self._repository.list_proposals(opportunity_id)
            if not proposals or proposals[-1].id != proposal_id:
                raise DomainValidationError(
                    "debe revisar la versión vigente de la propuesta"
                )
            approval = Approval(opportunity_id, option_id, actor, self._clock())
            decision = Decision(
                opportunity_id, option_id, rationale, approval, proposal_id
            )
            self.transition_opportunity(
                TransitionOpportunityCommand(
                    opportunity_id, OpportunityStage.APPROVED, actor, approval, decision
                )
            )
            self._repository.append_audit_event(
                self._content_event(
                    opportunity_id,
                    actor,
                    "DECISION_RECORDED",
                    f"Propuesta revisada: {proposal_id}; elección: {option_id}; motivo: {rationale}",
                )
            )
        return decision

    def change_action_status(
        self, opportunity_id: str, action_id: str, status: ActionStatus, actor: str
    ) -> None:
        """Sólo simula tras una decisión; cancelar o bloquear no ejecuta nada."""
        with self._repository.transaction():
            opportunity = self._get_opportunity(opportunity_id)
            action = next(
                (
                    item
                    for item in self._repository.list_next_actions(opportunity_id)
                    if item.id == action_id
                ),
                None,
            )
            if action is None:
                raise RecordNotFoundError("acción no encontrada en esta oportunidad")
            if action.status != ActionStatus.PENDING or status == ActionStatus.PENDING:
                raise DomainValidationError("sólo una tarea pendiente puede cerrarse")
            if status == ActionStatus.SIMULATED and (
                opportunity.stage != OpportunityStage.APPROVED
                or self._repository.get_decision(opportunity_id) is None
            ):
                raise DomainValidationError(
                    "simular requiere una decisión humana aprobada"
                )
            self._repository.update_action_status(opportunity_id, action_id, status)
            self._repository.append_audit_event(
                self._content_event(
                    opportunity_id,
                    actor,
                    "ACTION_STATUS_CHANGED",
                    f"{action_id}: {action.status.value} → {status.value}; sin efecto externo",
                )
            )

    def save_ai_draft(
        self, opportunity_id: str, actor: str, draft: dict[str, object]
    ) -> None:
        """Guarda salida y auditoría juntas, sin alterar la decisión."""
        with self._repository.transaction():
            self._repository.save_ai_draft(opportunity_id, draft)
            self.record_ai_draft_event(
                opportunity_id, actor=actor, draft_id=str(draft["id"])
            )

    def record_rejection(
        self, opportunity_id: str, actor: str, operation: str, reason: str
    ) -> None:
        """Registra rechazos después del rollback, sin guardar credenciales."""
        self._get_opportunity(opportunity_id)
        event = self._content_event(opportunity_id, actor, operation, reason)
        with self._repository.transaction():
            self._repository.append_audit_event(
                replace(event, outcome=EventOutcome.REJECTED)
            )

    def _require_editable(self, opportunity_id: str) -> None:
        stage = self._get_opportunity(opportunity_id).stage
        if stage in {
            OpportunityStage.PENDING_APPROVAL,
            OpportunityStage.APPROVED,
            OpportunityStage.REJECTED,
        }:
            raise DomainValidationError(
                "el expediente está congelado; pause antes de cambiar evidencia o propuestas"
            )
