import unittest
from datetime import datetime, timezone

from opportunity_control.domain import (
    Account,
    Approval,
    ConfidenceState,
    DomainValidationError,
    Evidence,
    Hypothesis,
    OpportunityStage,
    Unknown,
    validate_transition,
)


class DomainModelTests(unittest.TestCase):
    def test_required_text_rejects_incomplete_account(self) -> None:
        with self.assertRaisesRegex(DomainValidationError, "account.name"):
            Account(id="ACCOUNT-001", name="   ")

    def test_confidence_states_match_the_acceptance_challenge(self) -> None:
        self.assertEqual(
            {state.value for state in ConfidenceState},
            {"VERIFIED", "INFERRED", "UNKNOWN"},
        )

    def test_evidence_requires_source_and_provenance(self) -> None:
        with self.assertRaisesRegex(DomainValidationError, "evidence.source"):
            Evidence(
                id="E-001",
                opportunity_id="O-001",
                statement="Dato de prueba",
                source="",
                provenance="fixture local",
                confidence_state=ConfidenceState.VERIFIED,
                confidence=0.9,
                recorded_at=datetime.now(timezone.utc),
            )

    def test_hypothesis_cannot_be_presented_as_verified(self) -> None:
        with self.assertRaisesRegex(DomainValidationError, "INFERRED"):
            Hypothesis(
                id="HYPOTHESIS-001",
                opportunity_id="OPPORTUNITY-001",
                statement="Suposición de prueba",
                rationale="Todavía no existe evidencia suficiente",
                confidence_state=ConfidenceState.VERIFIED,
            )

    def test_unknown_cannot_claim_numeric_confidence(self) -> None:
        with self.assertRaisesRegex(DomainValidationError, "debe ser 0"):
            Unknown(
                id="UNKNOWN-001",
                opportunity_id="OPPORTUNITY-001",
                question="¿Qué dato falta?",
                confidence=0.5,
            )

    def test_opportunity_cannot_skip_directly_to_approved(self) -> None:
        with self.assertRaisesRegex(DomainValidationError, "transición inválida"):
            validate_transition(
                OpportunityStage.INTAKE,
                OpportunityStage.APPROVED,
            )

    def test_options_require_evidence(self) -> None:
        with self.assertRaisesRegex(DomainValidationError, "evidencia"):
            validate_transition(
                OpportunityStage.EVIDENCE_REVIEW,
                OpportunityStage.OPTIONS_READY,
                evidence_count=0,
            )

    def test_pending_approval_requires_two_or_three_options(self) -> None:
        with self.assertRaisesRegex(DomainValidationError, "dos y tres opciones"):
            validate_transition(
                OpportunityStage.OPTIONS_READY,
                OpportunityStage.PENDING_APPROVAL,
                option_count=1,
            )

    def test_approved_stage_requires_explicit_human_approval(self) -> None:
        with self.assertRaisesRegex(DomainValidationError, "aprobación humana"):
            validate_transition(
                OpportunityStage.PENDING_APPROVAL,
                OpportunityStage.APPROVED,
            )

        approval = Approval(
            opportunity_id="O-001",
            option_id="OPT-001",
            actor="reviewer@example.test",
            approved_at=datetime.now(timezone.utc),
        )
        validate_transition(
            OpportunityStage.PENDING_APPROVAL,
            OpportunityStage.APPROVED,
            approval=approval,
        )


if __name__ == "__main__":
    unittest.main()
