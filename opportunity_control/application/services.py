"""Casos de uso que coordinan reglas, persistencia y auditoría."""

from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid4

from opportunity_control.domain import (
    AuditEvent,
    DomainValidationError,
    EventOutcome,
    Opportunity,
    OpportunityStage,
    validate_transition,
)
from opportunity_control.domain.validation import require_text

from .briefs import FounderBrief
from .commands import (
    RecordDecisionOptionCommand,
    RecordEvidenceCommand,
    RecordHypothesisCommand,
    RecordNextActionCommand,
    RecordUnknownCommand,
    TransitionOpportunityCommand,
)
from .errors import (
    ConcurrentChangeError,
    ExternalActionBlockedError,
    RecordNotFoundError,
)
from .ports import OpportunityRepository
from .workflow import WorkflowOperations


def _utc_now() -> datetime:
    """Devuelve el reloj UTC predeterminado de producción local."""

    return datetime.now(timezone.utc)


def _new_event_id() -> str:
    """Genera un identificador único para un evento de auditoría."""

    return f"EVENT-{uuid4()}"


class OpportunityControlService(WorkflowOperations):
    """Ejecuta operaciones controladas y deja una explicación auditable."""

    def __init__(
        self,
        repository: OpportunityRepository,
        *,
        clock: Callable[[], datetime] = _utc_now,
        event_id_factory: Callable[[], str] = _new_event_id,
    ) -> None:
        """Recibe dependencias sustituibles para facilitar las pruebas."""

        self._repository = repository
        self._clock = clock
        self._event_id_factory = event_id_factory

    def list_opportunities(self) -> list[Opportunity]:
        """Devuelve todas las oportunidades disponibles."""

        return self._repository.list_opportunities()

    def list_audit_events(self, opportunity_id: str) -> list[AuditEvent]:
        """Devuelve el historial después de confirmar que el caso existe."""

        opportunity = self._get_opportunity(opportunity_id)
        return self._repository.list_audit_events(opportunity.id)

    def record_evidence(self, command: RecordEvidenceCommand) -> None:
        """Guarda evidencia y auditoría como una sola operación."""

        opportunity = self._get_opportunity(command.evidence.opportunity_id)
        self._require_editable(opportunity.id)
        for existing in self._repository.list_evidence(opportunity.id):
            if (
                existing.statement.strip().casefold(),
                existing.source.strip().casefold(),
            ) == (
                command.evidence.statement.strip().casefold(),
                command.evidence.source.strip().casefold(),
            ):
                from .errors import DuplicateRecordError

                raise DuplicateRecordError(
                    "la misma afirmación y fuente ya están registradas"
                )
        event = AuditEvent(
            id=self._event_id_factory(),
            opportunity_id=opportunity.id,
            event_type="EVIDENCE_RECORDED",
            actor=command.actor,
            occurred_at=self._clock(),
            outcome=EventOutcome.ACCEPTED,
            detail=f"Evidencia registrada: {command.evidence.id}",
        )

        with self._repository.transaction():
            self._repository.add_evidence(command.evidence)
            self._repository.append_audit_event(event)

    def record_decision_option(
        self,
        command: RecordDecisionOptionCommand,
    ) -> None:
        """Guarda una opción y su evento dentro de la misma transacción."""

        opportunity = self._get_opportunity(command.option.opportunity_id)
        self._require_editable(opportunity.id)
        if len(self._repository.list_decision_options(opportunity.id)) >= 3:
            raise DomainValidationError(
                "el expediente admite un máximo de tres opciones"
            )
        event = AuditEvent(
            id=self._event_id_factory(),
            opportunity_id=opportunity.id,
            event_type="DECISION_OPTION_RECORDED",
            actor=command.actor,
            occurred_at=self._clock(),
            outcome=EventOutcome.ACCEPTED,
            detail=f"Opción registrada: {command.option.id}",
        )

        with self._repository.transaction():
            self._repository.add_decision_option(command.option)
            self._repository.append_audit_event(event)

    def record_hypothesis(self, command: RecordHypothesisCommand) -> None:
        """Guarda una hipótesis y la mantiene separada de la evidencia."""

        opportunity = self._get_opportunity(command.hypothesis.opportunity_id)
        self._require_editable(opportunity.id)
        event = self._content_event(
            opportunity.id,
            command.actor,
            "HYPOTHESIS_RECORDED",
            f"Hipótesis registrada: {command.hypothesis.id}",
        )
        with self._repository.transaction():
            self._repository.add_hypothesis(command.hypothesis)
            self._repository.append_audit_event(event)

    def record_unknown(self, command: RecordUnknownCommand) -> None:
        """Guarda una incógnita sin fabricar una respuesta."""

        opportunity = self._get_opportunity(command.unknown.opportunity_id)
        self._require_editable(opportunity.id)
        event = self._content_event(
            opportunity.id,
            command.actor,
            "UNKNOWN_RECORDED",
            f"Incógnita registrada: {command.unknown.id}",
        )
        with self._repository.transaction():
            self._repository.add_unknown(command.unknown)
            self._repository.append_audit_event(event)

    def record_next_action(self, command: RecordNextActionCommand) -> None:
        """Guarda una acción interna y su rastro de auditoría."""

        opportunity = self._get_opportunity(command.action.opportunity_id)
        event = self._content_event(
            opportunity.id,
            command.actor,
            "NEXT_ACTION_RECORDED",
            f"Acción interna registrada: {command.action.id}",
        )
        with self._repository.transaction():
            self._repository.add_next_action(command.action)
            self._repository.append_audit_event(event)

    def get_founder_brief(self, opportunity_id: str) -> FounderBrief:
        """Construye una vista ejecutiva sin alterar ningún dato."""

        opportunity = self._get_opportunity(opportunity_id)
        account = self._repository.get_account(opportunity.account_id)
        if account is None:
            raise RecordNotFoundError(f"cuenta no encontrada: {opportunity.account_id}")
        events = self._repository.list_audit_events(opportunity.id)
        return FounderBrief(
            account=account,
            opportunity=opportunity,
            evidence=tuple(self._repository.list_evidence(opportunity.id)),
            hypotheses=tuple(self._repository.list_hypotheses(opportunity.id)),
            unknowns=tuple(self._repository.list_unknowns(opportunity.id)),
            options=tuple(self._repository.list_decision_options(opportunity.id)),
            next_actions=tuple(self._repository.list_next_actions(opportunity.id)),
            approval=self._repository.get_approval(opportunity.id),
            last_movement=events[-1] if events else None,
            generated_at=self._clock(),
            signals=tuple(self._repository.list_signals(opportunity.id)),
            contacts=tuple(self._repository.list_contacts(account.id)),
            proposals=tuple(self._repository.list_proposals(opportunity.id)),
            decision=self._repository.get_decision(opportunity.id),
            ai_drafts=tuple(self._repository.list_ai_drafts(opportunity.id)),
        )

    def block_external_action(
        self,
        opportunity_id: str,
        *,
        actor: str,
        description: str,
    ) -> None:
        """Audita y bloquea siempre una acción con efectos externos."""

        opportunity = self._get_opportunity(opportunity_id)
        event = AuditEvent(
            id=self._event_id_factory(),
            opportunity_id=opportunity.id,
            event_type="EXTERNAL_ACTION_BLOCKED",
            actor=actor,
            occurred_at=self._clock(),
            outcome=EventOutcome.REJECTED,
            detail=description,
        )
        with self._repository.transaction():
            self._repository.append_audit_event(event)
        raise ExternalActionBlockedError("las acciones externas están deshabilitadas")

    def record_ai_draft_event(
        self,
        opportunity_id: str,
        *,
        actor: str,
        draft_id: str,
    ) -> None:
        """Registra que se generó un borrador sin aprobarlo ni ejecutarlo."""

        opportunity = self._get_opportunity(opportunity_id)
        event = self._content_event(
            opportunity.id,
            actor,
            "AI_DRAFT_GENERATED",
            f"Borrador para revisión humana: {draft_id}",
        )
        with self._repository.transaction():
            self._repository.append_audit_event(event)

    def transition_opportunity(
        self,
        command: TransitionOpportunityCommand,
    ) -> Opportunity:
        """Valida, cambia y audita una etapa sin dejar cambios parciales."""

        try:
            with self._repository.transaction():
                opportunity = self._get_opportunity(command.opportunity_id)
                evidence_count = len(self._repository.list_evidence(opportunity.id))
                options = self._repository.list_decision_options(opportunity.id)
                self._validate_approval(command, {option.id for option in options})
                validate_transition(
                    opportunity.stage,
                    command.next_stage,
                    evidence_count=evidence_count,
                    option_count=len(options),
                    approval=command.approval,
                )
                if (
                    command.next_stage == OpportunityStage.PENDING_APPROVAL
                    and not self._repository.list_proposals(opportunity.id)
                ):
                    raise DomainValidationError(
                        "registre una propuesta trazable antes de solicitar aprobación"
                    )
                if command.next_stage == OpportunityStage.REJECTED:
                    require_text(command.rationale, "motivo del rechazo")
                if command.approval is not None:
                    decision = command.decision
                    if decision is None or decision.approval != command.approval:
                        raise DomainValidationError(
                            "la aprobación humana requiere decisión con motivo y propuesta"
                        )
                    proposals = self._repository.list_proposals(opportunity.id)
                    if not proposals or proposals[-1].id != decision.proposal_id:
                        raise DomainValidationError(
                            "la decisión debe revisar la propuesta vigente"
                        )
                    self._repository.add_approval(command.approval)
                    self._repository.add_decision(decision)
                updated = self._repository.update_opportunity_stage(
                    opportunity.id, opportunity.stage, command.next_stage
                )
                if not updated:
                    raise ConcurrentChangeError(
                        "la oportunidad cambió durante la transición"
                    )
                self._repository.append_audit_event(
                    self._transition_event(
                        command,
                        opportunity,
                        outcome=EventOutcome.ACCEPTED,
                        detail=command.rationale or "Transición aceptada",
                    )
                )
        except DomainValidationError as error:
            self._record_rejected_transition(command, opportunity, str(error))
            raise

        return self._get_opportunity(opportunity.id)

    def _validate_approval(
        self,
        command: TransitionOpportunityCommand,
        option_ids: set[str],
    ) -> None:
        approval = command.approval
        if approval is None:
            return
        if command.next_stage is not OpportunityStage.APPROVED:
            raise DomainValidationError(
                "la aprobación sólo puede usarse para llegar a APPROVED"
            )
        if approval.opportunity_id != command.opportunity_id:
            raise DomainValidationError("la aprobación pertenece a otra oportunidad")
        if approval.actor != command.actor:
            raise DomainValidationError(
                "el aprobador debe coincidir con el actor autenticado"
            )
        if approval.option_id not in option_ids:
            raise DomainValidationError(
                "la aprobación pertenece a una opción no registrada"
            )

    def _record_rejected_transition(
        self,
        command: TransitionOpportunityCommand,
        opportunity: Opportunity,
        reason: str,
    ) -> None:
        event = self._transition_event(
            command,
            opportunity,
            outcome=EventOutcome.REJECTED,
            detail=reason,
        )
        with self._repository.transaction():
            self._repository.append_audit_event(event)

    def _transition_event(
        self,
        command: TransitionOpportunityCommand,
        opportunity: Opportunity,
        *,
        outcome: EventOutcome,
        detail: str,
    ) -> AuditEvent:
        return AuditEvent(
            id=self._event_id_factory(),
            opportunity_id=opportunity.id,
            event_type="OPPORTUNITY_STAGE_TRANSITION",
            actor=command.actor,
            occurred_at=self._clock(),
            outcome=outcome,
            previous_stage=opportunity.stage,
            next_stage=command.next_stage,
            detail=detail,
        )

    def _content_event(
        self,
        opportunity_id: str,
        actor: str,
        event_type: str,
        detail: str,
    ) -> AuditEvent:
        return AuditEvent(
            id=self._event_id_factory(),
            opportunity_id=opportunity_id,
            event_type=event_type,
            actor=actor,
            occurred_at=self._clock(),
            outcome=EventOutcome.ACCEPTED,
            detail=detail,
        )

    def _get_opportunity(self, opportunity_id: str) -> Opportunity:
        opportunity = self._repository.get_opportunity(opportunity_id)
        if opportunity is None:
            raise RecordNotFoundError(f"oportunidad no encontrada: {opportunity_id}")
        return opportunity
