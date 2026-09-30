import sqlite3
import unittest
from datetime import datetime, timezone

from opportunity_control.application import DuplicateRecordError, PersistenceError
from opportunity_control.domain import (
    Account,
    AuditEvent,
    ConfidenceState,
    EventOutcome,
    Evidence,
    Opportunity,
)
from opportunity_control.infrastructure import (
    SQLiteOpportunityRepository,
    connect_database,
    initialize_database,
)
from opportunity_control.seed import seed_repository


class SQLiteOpportunityRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = connect_database(":memory:")
        initialize_database(self.connection)
        self.repository = SQLiteOpportunityRepository(self.connection)

    def tearDown(self) -> None:
        self.connection.close()

    def _add_opportunity(self) -> Opportunity:
        account = Account(id="ACCOUNT-001", name="Cuenta de prueba")
        opportunity = Opportunity(
            id="OPPORTUNITY-001",
            account_id=account.id,
            title="Oportunidad de prueba",
            owner="test-owner",
        )
        self.repository.add_account(account)
        self.repository.add_opportunity(opportunity)
        return opportunity

    def test_account_and_opportunity_round_trip(self) -> None:
        opportunity = self._add_opportunity()

        self.assertEqual(
            self.repository.get_account("ACCOUNT-001"),
            Account(id="ACCOUNT-001", name="Cuenta de prueba"),
        )
        self.assertEqual(
            self.repository.get_opportunity(opportunity.id),
            opportunity,
        )

    def test_duplicate_identifier_is_rejected(self) -> None:
        account = Account(id="ACCOUNT-001", name="Cuenta de prueba")
        self.repository.add_account(account)

        with self.assertRaisesRegex(DuplicateRecordError, "duplicado"):
            self.repository.add_account(account)

    def test_opportunity_requires_an_existing_account(self) -> None:
        opportunity = Opportunity(
            id="OPPORTUNITY-ORPHAN",
            account_id="ACCOUNT-MISSING",
            title="No debe guardarse",
            owner="test-owner",
        )

        with self.assertRaisesRegex(PersistenceError, "FOREIGN KEY"):
            self.repository.add_opportunity(opportunity)

    def test_evidence_preserves_source_provenance_and_confidence(self) -> None:
        opportunity = self._add_opportunity()
        evidence = Evidence(
            id="EVIDENCE-001",
            opportunity_id=opportunity.id,
            statement="Dato sintético de prueba",
            source="synthetic-fixture",
            provenance="tests/test_repository.py",
            confidence_state=ConfidenceState.UNKNOWN,
            confidence=0.0,
            recorded_at=datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc),
        )

        self.repository.add_evidence(evidence)

        self.assertEqual(
            self.repository.list_evidence(opportunity.id),
            [evidence],
        )

    def test_audit_history_preserves_insertion_order(self) -> None:
        opportunity = self._add_opportunity()
        for index in (1, 2):
            self.repository.append_audit_event(
                AuditEvent(
                    id=f"AUDIT-{index:03d}",
                    opportunity_id=opportunity.id,
                    event_type="TEST_EVENT",
                    actor="test-suite",
                    occurred_at=datetime(2026, 9, 28, 12, index, tzinfo=timezone.utc),
                    outcome=EventOutcome.ACCEPTED,
                )
            )

        events = self.repository.list_audit_events(opportunity.id)

        self.assertEqual([event.id for event in events], ["AUDIT-001", "AUDIT-002"])

    def test_audit_history_cannot_be_updated(self) -> None:
        opportunity = self._add_opportunity()
        self.repository.append_audit_event(
            AuditEvent(
                id="AUDIT-001",
                opportunity_id=opportunity.id,
                event_type="TEST_EVENT",
                actor="test-suite",
                occurred_at=datetime.now(timezone.utc),
                outcome=EventOutcome.ACCEPTED,
            )
        )

        with (
            self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"),
            self.connection,
        ):
            self.connection.execute(
                "UPDATE audit_events SET detail = 'alterado' WHERE id = ?",
                ("AUDIT-001",),
            )

    def test_audit_history_cannot_be_deleted(self) -> None:
        opportunity = self._add_opportunity()
        self.repository.append_audit_event(
            AuditEvent(
                id="AUDIT-001",
                opportunity_id=opportunity.id,
                event_type="TEST_EVENT",
                actor="test-suite",
                occurred_at=datetime.now(timezone.utc),
                outcome=EventOutcome.ACCEPTED,
            )
        )

        with (
            self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"),
            self.connection,
        ):
            self.connection.execute(
                "DELETE FROM audit_events WHERE id = ?",
                ("AUDIT-001",),
            )

    def test_seed_creates_three_synthetic_cases(self) -> None:
        seed_repository(self.repository)

        self.assertEqual(len(self.repository.list_accounts()), 3)
        self.assertEqual(len(self.repository.list_opportunities()), 3)
        self.assertEqual(
            {opportunity.id for opportunity in self.repository.list_opportunities()},
            {
                "OPPORTUNITY-UVA-AI-PILOT",
                "OPPORTUNITY-X-HUMANOID-NA",
                "OPPORTUNITY-BOOSTER-PILOTS",
            },
        )


if __name__ == "__main__":
    unittest.main()
