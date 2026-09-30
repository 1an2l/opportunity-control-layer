"""Pruebas de coordinación atómica y auditabilidad de los casos de uso."""

import unittest
from datetime import datetime, timezone
from itertools import count

from opportunity_control.application import (
    DuplicateRecordError,
    ExternalActionBlockedError,
    OpportunityControlService,
    RecordDecisionOptionCommand,
    RecordEvidenceCommand,
    RecordNotFoundError,
    TransitionOpportunityCommand,
)
from opportunity_control.domain import (
    Account,
    Approval,
    AuditEvent,
    ConfidenceState,
    DecisionOption,
    DomainValidationError,
    EventOutcome,
    Evidence,
    Opportunity,
    OpportunityStage,
)
from opportunity_control.domain.proposals import Proposal
from opportunity_control.infrastructure import (
    SQLiteOpportunityRepository,
    connect_database,
    initialize_database,
)


class OpportunityControlServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = connect_database(":memory:")
        initialize_database(self.connection)
        self.repository = SQLiteOpportunityRepository(self.connection)
        self.repository.add_account(Account(id="ACCOUNT-001", name="Cuenta de prueba"))
        self.repository.add_opportunity(
            Opportunity(
                id="OPPORTUNITY-001",
                account_id="ACCOUNT-001",
                title="Oportunidad de prueba",
                owner="test-owner",
            )
        )
        self.event_sequence = count(1)
        self.now = datetime(2026, 9, 28, 18, 0, tzinfo=timezone.utc)
        self.service = OpportunityControlService(
            self.repository,
            clock=lambda: self.now,
            event_id_factory=lambda: f"EVENT-{next(self.event_sequence):03d}",
        )

    def tearDown(self) -> None:
        self.connection.close()

    def _evidence(self) -> Evidence:
        return Evidence(
            id="EVIDENCE-001",
            opportunity_id="OPPORTUNITY-001",
            statement="Dato sintético de prueba",
            source="synthetic-fixture",
            provenance="tests/test_services.py",
            confidence_state=ConfidenceState.UNKNOWN,
            confidence=0.0,
            recorded_at=self.now,
        )

    def _option(self, number: int) -> DecisionOption:
        return DecisionOption(
            id=f"OPTION-{number:03d}",
            opportunity_id="OPPORTUNITY-001",
            title=f"Opción sintética {number}",
            rationale="Rationale de prueba",
            risk="Riesgo de prueba",
        )

    def test_record_evidence_is_saved_with_audit_event(self) -> None:
        evidence = self._evidence()

        self.service.record_evidence(
            RecordEvidenceCommand(evidence=evidence, actor="reviewer")
        )

        self.assertEqual(self.repository.list_evidence("OPPORTUNITY-001"), [evidence])
        events = self.repository.list_audit_events("OPPORTUNITY-001")
        self.assertEqual(events[0].event_type, "EVIDENCE_RECORDED")
        self.assertEqual(events[0].outcome, EventOutcome.ACCEPTED)

    def test_audit_failure_rolls_back_evidence(self) -> None:
        self.repository.append_audit_event(
            AuditEvent(
                id="EVENT-DUPLICATE",
                opportunity_id="OPPORTUNITY-001",
                event_type="PREEXISTING_EVENT",
                actor="test-suite",
                occurred_at=self.now,
                outcome=EventOutcome.ACCEPTED,
            )
        )
        service = OpportunityControlService(
            self.repository,
            clock=lambda: self.now,
            event_id_factory=lambda: "EVENT-DUPLICATE",
        )

        with self.assertRaises(DuplicateRecordError):
            service.record_evidence(
                RecordEvidenceCommand(
                    evidence=self._evidence(),
                    actor="reviewer",
                )
            )

        self.assertEqual(self.repository.list_evidence("OPPORTUNITY-001"), [])

    def test_valid_transition_updates_stage_and_writes_accepted_event(self) -> None:
        updated = self.service.transition_opportunity(
            TransitionOpportunityCommand(
                opportunity_id="OPPORTUNITY-001",
                next_stage=OpportunityStage.EVIDENCE_REVIEW,
                actor="reviewer",
            )
        )

        self.assertEqual(updated.stage, OpportunityStage.EVIDENCE_REVIEW)
        events = self.repository.list_audit_events("OPPORTUNITY-001")
        self.assertEqual(events[0].previous_stage, OpportunityStage.INTAKE)
        self.assertEqual(events[0].next_stage, OpportunityStage.EVIDENCE_REVIEW)
        self.assertEqual(events[0].outcome, EventOutcome.ACCEPTED)

    def test_audit_failure_rolls_back_stage_transition(self) -> None:
        self.repository.append_audit_event(
            AuditEvent(
                id="EVENT-DUPLICATE",
                opportunity_id="OPPORTUNITY-001",
                event_type="PREEXISTING_EVENT",
                actor="test-suite",
                occurred_at=self.now,
                outcome=EventOutcome.ACCEPTED,
            )
        )
        service = OpportunityControlService(
            self.repository,
            clock=lambda: self.now,
            event_id_factory=lambda: "EVENT-DUPLICATE",
        )

        with self.assertRaises(DuplicateRecordError):
            service.transition_opportunity(
                TransitionOpportunityCommand(
                    opportunity_id="OPPORTUNITY-001",
                    next_stage=OpportunityStage.EVIDENCE_REVIEW,
                    actor="reviewer",
                )
            )

        opportunity = self.repository.get_opportunity("OPPORTUNITY-001")
        self.assertIsNotNone(opportunity)
        self.assertEqual(opportunity.stage, OpportunityStage.INTAKE)

    def test_invalid_transition_keeps_stage_and_writes_rejected_event(self) -> None:
        with self.assertRaises(DomainValidationError):
            self.service.transition_opportunity(
                TransitionOpportunityCommand(
                    opportunity_id="OPPORTUNITY-001",
                    next_stage=OpportunityStage.APPROVED,
                    actor="reviewer",
                )
            )

        opportunity = self.repository.get_opportunity("OPPORTUNITY-001")
        self.assertIsNotNone(opportunity)
        self.assertEqual(opportunity.stage, OpportunityStage.INTAKE)
        events = self.repository.list_audit_events("OPPORTUNITY-001")
        self.assertEqual(events[0].outcome, EventOutcome.REJECTED)

    def test_complete_controlled_flow_requires_persisted_human_approval(self) -> None:
        self.service.transition_opportunity(
            TransitionOpportunityCommand(
                opportunity_id="OPPORTUNITY-001",
                next_stage=OpportunityStage.EVIDENCE_REVIEW,
                actor="reviewer",
            )
        )
        self.service.record_evidence(
            RecordEvidenceCommand(evidence=self._evidence(), actor="reviewer")
        )
        self.service.transition_opportunity(
            TransitionOpportunityCommand(
                opportunity_id="OPPORTUNITY-001",
                next_stage=OpportunityStage.OPTIONS_READY,
                actor="reviewer",
            )
        )
        for number in (1, 2):
            self.service.record_decision_option(
                RecordDecisionOptionCommand(
                    option=self._option(number),
                    actor="reviewer",
                )
            )
        self.service.record_proposal(
            Proposal(
                "PROPOSAL-001",
                "OPPORTUNITY-001",
                "OPTION-001",
                "Evaluar sólo localmente",
                ("EVIDENCE-001",),
                (),
                (),
                "reviewer",
                self.now,
            )
        )
        self.service.transition_opportunity(
            TransitionOpportunityCommand(
                opportunity_id="OPPORTUNITY-001",
                next_stage=OpportunityStage.PENDING_APPROVAL,
                actor="reviewer",
            )
        )

        with self.assertRaisesRegex(DomainValidationError, "aprobación humana"):
            self.service.transition_opportunity(
                TransitionOpportunityCommand(
                    opportunity_id="OPPORTUNITY-001",
                    next_stage=OpportunityStage.APPROVED,
                    actor="reviewer",
                )
            )

        approval = Approval(
            opportunity_id="OPPORTUNITY-001",
            option_id="OPTION-001",
            actor="human-reviewer",
            approved_at=self.now,
        )
        self.service.decide(
            "OPPORTUNITY-001",
            proposal_id="PROPOSAL-001",
            option_id="OPTION-001",
            rationale="Revisión humana realizada",
            actor="human-reviewer",
            confirmed=True,
        )
        approved = self.repository.get_opportunity("OPPORTUNITY-001")
        self.assertEqual(approved.stage, OpportunityStage.APPROVED)
        self.assertEqual(
            self.repository.get_approval("OPPORTUNITY-001"),
            approval,
        )
        with self.assertRaises(ExternalActionBlockedError):
            self.service.block_external_action(
                "OPPORTUNITY-001",
                actor="human-reviewer",
                description="La aprobación interna no permite enviar nada",
            )
        self.assertEqual(
            self.repository.list_audit_events("OPPORTUNITY-001")[-1].event_type,
            "EXTERNAL_ACTION_BLOCKED",
        )

    def test_missing_opportunity_is_rejected(self) -> None:
        with self.assertRaisesRegex(RecordNotFoundError, "no encontrada"):
            self.service.transition_opportunity(
                TransitionOpportunityCommand(
                    opportunity_id="OPPORTUNITY-MISSING",
                    next_stage=OpportunityStage.EVIDENCE_REVIEW,
                    actor="reviewer",
                )
            )


if __name__ == "__main__":
    unittest.main()
