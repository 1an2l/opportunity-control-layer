"""Pruebas de contratos HTTP sin iniciar un proceso de red."""

import unittest
from datetime import datetime, timezone
from itertools import count

from opportunity_control.ai import LocalGovernedDraftGenerator
from opportunity_control.api import ApiApplication
from opportunity_control.application import OpportunityControlService
from opportunity_control.infrastructure import (
    SQLiteOpportunityRepository,
    connect_database,
    initialize_database,
)
from opportunity_control.seed import seed_repository


class ApiApplicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = connect_database(":memory:")
        initialize_database(self.connection)
        self.repository = SQLiteOpportunityRepository(self.connection)
        seed_repository(self.repository)
        sequence = count(1)
        now = datetime(2026, 9, 28, 20, 0, tzinfo=timezone.utc)
        service = OpportunityControlService(
            self.repository,
            clock=lambda: now,
            event_id_factory=lambda: f"EVENT-API-{next(sequence):03d}",
        )
        ai_generator = LocalGovernedDraftGenerator(
            clock=lambda: now,
            id_factory=lambda: "AI-DRAFT-API-001",
        )
        self.api = ApiApplication(service, ai_generator)
        self.opportunity_id = "OPPORTUNITY-UVA-AI-PILOT"

    def tearDown(self) -> None:
        self.connection.close()

    def test_health_reports_external_actions_disabled(self) -> None:
        response = self.api.handle("GET", "/api/health")

        self.assertEqual(response.status, 200)
        self.assertEqual(response.payload["external_actions"], "disabled")

    def test_list_returns_three_seed_opportunities(self) -> None:
        response = self.api.handle("GET", "/api/opportunities")

        self.assertEqual(response.status, 200)
        self.assertEqual(len(response.payload), 3)

    def test_founder_brief_keeps_information_categories_separate(self) -> None:
        response = self.api.handle(
            "GET",
            f"/api/opportunities/{self.opportunity_id}/brief",
        )

        self.assertEqual(response.status, 200)
        self.assertIn("evidence", response.payload)
        self.assertIn("hypotheses", response.payload)
        self.assertIn("unknowns", response.payload)
        self.assertIn("recommendation", response.payload)
        self.assertIn("risks", response.payload)
        self.assertIn("next_action", response.payload)
        self.assertFalse(response.payload["governance"]["external_actions_enabled"])

    def test_missing_opportunity_returns_404(self) -> None:
        response = self.api.handle("GET", "/api/opportunities/DOES-NOT-EXIST")

        self.assertEqual(response.status, 404)
        self.assertEqual(response.payload["error"], "not_found")

    def test_incomplete_evidence_returns_400(self) -> None:
        response = self.api.handle(
            "POST",
            f"/api/opportunities/{self.opportunity_id}/evidence",
            {"id": "EVIDENCE-001", "actor": "reviewer"},
        )

        self.assertEqual(response.status, 400)
        self.assertEqual(response.payload["error"], "invalid_request")

    def test_duplicate_evidence_returns_409(self) -> None:
        body = {
            "id": "EVIDENCE-001",
            "statement": "Dato sintético",
            "source": "fixture",
            "provenance": "test_api",
            "confidence_state": "UNKNOWN",
            "confidence": 0,
            "actor": "reviewer",
        }

        first = self.api.handle(
            "POST",
            f"/api/opportunities/{self.opportunity_id}/evidence",
            body,
        )
        second = self.api.handle(
            "POST",
            f"/api/opportunities/{self.opportunity_id}/evidence",
            body,
        )

        self.assertEqual(first.status, 201)
        self.assertEqual(second.status, 409)

    def test_invalid_transition_returns_422_and_is_audited(self) -> None:
        response = self.api.handle(
            "POST",
            f"/api/opportunities/{self.opportunity_id}/transitions",
            {"next_stage": "APPROVED", "actor": "reviewer"},
        )

        self.assertEqual(response.status, 422)
        events = self.api.handle(
            "GET",
            f"/api/opportunities/{self.opportunity_id}/events",
        )
        self.assertEqual(events.payload[-1]["outcome"], "REJECTED")

    def test_external_action_is_always_blocked_and_audited(self) -> None:
        response = self.api.handle(
            "POST",
            f"/api/opportunities/{self.opportunity_id}/external-action",
            {
                "actor": "reviewer",
                "description": "Intentar enviar un correo",
            },
        )

        self.assertEqual(response.status, 403)
        self.assertEqual(response.payload["error"], "external_action_blocked")
        events = self.repository.list_audit_events(self.opportunity_id)
        self.assertEqual(events[-1].event_type, "EXTERNAL_ACTION_BLOCKED")

    def test_ai_output_is_identified_as_non_executable_draft(self) -> None:
        response = self.api.handle(
            "POST",
            f"/api/opportunities/{self.opportunity_id}/ai-draft",
            {"actor": "reviewer"},
        )

        self.assertEqual(response.status, 201)
        draft = response.payload["draft"]
        self.assertEqual(draft["mode"], "local")
        self.assertTrue(draft["requires_human_review"])
        self.assertFalse(draft["can_execute_external_actions"])
        self.assertEqual(
            self.repository.list_audit_events(self.opportunity_id)[-1].event_type,
            "AI_DRAFT_GENERATED",
        )


if __name__ == "__main__":
    unittest.main()
