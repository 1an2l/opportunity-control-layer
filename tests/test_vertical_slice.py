"""Aceptación del recorrido completo y fallos que deben conservar el estado."""

import unittest
from unittest.mock import patch

from opportunity_control.ai import LocalGovernedDraftGenerator
from opportunity_control.api import ApiApplication
from opportunity_control.application import OpportunityControlService
from opportunity_control.domain import Account
from opportunity_control.infrastructure import (
    SQLiteOpportunityRepository,
    connect_database,
    initialize_database,
)
from opportunity_control.seed import seed_repository


class VerticalSliceTests(unittest.TestCase):
    """Evalúa el contrato con SQLite real en memoria, sin servicios externos."""

    def setUp(self) -> None:
        self.connection = connect_database(":memory:")
        initialize_database(self.connection)
        self.repository = SQLiteOpportunityRepository(self.connection)
        seed_repository(self.repository)
        self.service = OpportunityControlService(self.repository)
        self.api = ApiApplication(self.service, LocalGovernedDraftGenerator())
        self.opportunity_id = "OPPORTUNITY-UVA-AI-PILOT"

    def tearDown(self) -> None:
        self.connection.close()

    def post(self, endpoint: str, **body: object):
        """Simula la llamada interna de un adaptador que ya identificó al actor."""
        return self.api.handle(
            "POST",
            f"/api/opportunities/{self.opportunity_id}/{endpoint}",
            {"actor": "revisor-test", **body},
        )

    def brief(self):
        return self.api.handle(
            "GET", f"/api/opportunities/{self.opportunity_id}/brief"
        ).payload

    def prepare(self) -> dict:
        """Recorre revisión, opciones y propuesta sin conceder aprobación."""
        for stage in ("EVIDENCE_REVIEW", "OPTIONS_READY"):
            self.assertEqual(self.post("transitions", next_stage=stage).status, 200)
        brief = self.brief()
        result = self.post(
            "proposals",
            id="PROPOSAL-TEST",
            option_id=brief["options"][0]["id"],
            rationale="Evaluación interna, no autorización comercial",
            evidence_ids=[brief["evidence"][0]["id"]],
            hypothesis_ids=[brief["hypotheses"][0]["id"]],
            unknown_ids=[brief["unknowns"][0]["id"]],
        )
        self.assertEqual(result.status, 201, result.payload)
        self.assertEqual(
            self.post("transitions", next_stage="PENDING_APPROVAL").status, 200
        )
        return brief

    def approve(self) -> None:
        brief = self.prepare()
        result = self.post(
            "decisions",
            proposal_id="PROPOSAL-TEST",
            option_id=brief["options"][1]["id"],
            rationale="El humano elige esperar evidencia adicional",
            confirmed=True,
        )
        self.assertEqual(result.status, 201, result.payload)

    def test_complete_slice_all_three_cases(self) -> None:
        for opportunity in self.repository.list_opportunities():
            with self.subTest(case=opportunity.id):
                self.opportunity_id = opportunity.id
                self.approve_with_unique_proposal()
                brief = self.brief()
                self.assertEqual(brief["opportunity"]["stage"], "APPROVED")
                self.assertEqual(brief["decision"]["approval"]["actor"], "revisor-test")
                self.assertTrue(brief["signals"])
                self.assertTrue(brief["contacts"])
                self.assertEqual(self.post("external-action").status, 403)
                action_id = brief["next_actions"][0]["id"]
                self.assertEqual(
                    self.post("action-status", id=action_id, status="SIMULATED").status,
                    201,
                )
                self.assertIsNone(self.brief()["next_action"])

    def approve_with_unique_proposal(self) -> None:
        """Cada expediente usa una versión de propuesta inequívoca."""
        for stage in ("EVIDENCE_REVIEW", "OPTIONS_READY"):
            self.assertEqual(self.post("transitions", next_stage=stage).status, 200)
        brief = self.brief()
        proposal_id = f"PROPOSAL-{self.opportunity_id}"
        self.assertEqual(
            self.post(
                "proposals",
                id=proposal_id,
                option_id=brief["options"][0]["id"],
                rationale="Fixture revisado",
                evidence_ids=[brief["evidence"][0]["id"]],
            ).status,
            201,
        )
        self.assertEqual(
            self.post("transitions", next_stage="PENDING_APPROVAL").status, 200
        )
        self.assertEqual(
            self.post(
                "decisions",
                proposal_id=proposal_id,
                option_id=brief["options"][0]["id"],
                rationale="Confirmación humana de evaluación",
                confirmed=True,
            ).status,
            201,
        )

    def test_approval_requires_literal_true_and_reason(self) -> None:
        brief = self.prepare()
        for confirmed in (False, "true", 1, None):
            result = self.post(
                "decisions",
                proposal_id="PROPOSAL-TEST",
                option_id=brief["options"][0]["id"],
                rationale="Revisado",
                confirmed=confirmed,
            )
            self.assertEqual(result.status, 422)
            self.assertIsNone(self.repository.get_approval(self.opportunity_id))
        self.assertEqual(
            self.post(
                "decisions",
                proposal_id="PROPOSAL-TEST",
                option_id=brief["options"][0]["id"],
                confirmed=True,
            ).status,
            400,
        )

    def test_direct_approved_transition_cannot_bypass_decision(self) -> None:
        brief = self.prepare()
        result = self.post(
            "transitions",
            next_stage="APPROVED",
            approval={"actor": "revisor-test", "option_id": brief["options"][0]["id"]},
        )
        self.assertEqual(result.status, 422)
        self.assertEqual(self.brief()["opportunity"]["stage"], "PENDING_APPROVAL")

    def test_rejection_requires_and_persists_a_reason(self) -> None:
        self.prepare()
        self.assertEqual(self.post("transitions", next_stage="REJECTED").status, 422)
        result = self.post(
            "transitions",
            next_stage="REJECTED",
            rationale="No existe respaldo suficiente",
        )
        self.assertEqual(result.status, 200)
        self.assertEqual(
            self.repository.list_audit_events(self.opportunity_id)[-1].detail,
            "No existe respaldo suficiente",
        )
        self.assertIsNone(self.repository.get_approval(self.opportunity_id))

    def test_proposal_requires_references_from_same_case(self) -> None:
        brief = self.brief()
        for evidence_ids in ([], ["EVIDENCE-SEED-002"], ["missing"]):
            self.assertEqual(
                self.post(
                    "proposals",
                    id="P",
                    option_id=brief["options"][0]["id"],
                    rationale="Motivo",
                    evidence_ids=evidence_ids,
                ).status,
                422,
            )

    def test_pending_requires_a_proposal_not_only_options(self) -> None:
        for stage in ("EVIDENCE_REVIEW", "OPTIONS_READY"):
            self.post("transitions", next_stage=stage)
        self.assertEqual(
            self.post("transitions", next_stage="PENDING_APPROVAL").status, 422
        )

    def test_duplicate_evidence_detected_even_with_another_id(self) -> None:
        body = dict(self.brief()["evidence"][0])
        body["id"] = "DIFFERENT-ID"
        self.assertEqual(self.post("evidence", **body).status, 409)

    def test_duplicate_signal_rejected(self) -> None:
        body = dict(self.brief()["signals"][0])
        body["id"] = "DIFFERENT-SIGNAL-ID"
        self.assertEqual(self.post("signals", **body).status, 409)

    def test_frozen_case_cannot_change_evidence(self) -> None:
        self.prepare()
        self.assertEqual(
            self.post("unknowns", id="NEW", question="Nueva duda").status, 422
        )
        self.assertEqual(self.post("transitions", next_stage="PAUSED").status, 200)
        self.assertEqual(
            self.post("unknowns", id="NEW", question="Nueva duda").status, 201
        )
        self.assertEqual(
            self.post("transitions", next_stage="EVIDENCE_REVIEW").status, 200
        )

    def test_unapproved_action_cannot_be_simulated(self) -> None:
        action_id = self.brief()["next_actions"][0]["id"]
        self.assertEqual(
            self.post("action-status", id=action_id, status="SIMULATED").status, 422
        )
        self.assertEqual(self.brief()["next_actions"][0]["status"], "PENDING")

    def test_final_audit_failure_rolls_back_decision_approval_and_stage(self) -> None:
        brief = self.prepare()
        original = self.repository.append_audit_event

        def fail_on_final(event):
            if event.event_type == "DECISION_RECORDED":
                raise RuntimeError("injected failure")
            original(event)

        with patch.object(
            self.repository, "append_audit_event", side_effect=fail_on_final
        ):
            result = self.post(
                "decisions",
                proposal_id="PROPOSAL-TEST",
                option_id=brief["options"][0]["id"],
                rationale="Motivo",
                confirmed=True,
            )
        self.assertEqual(result.status, 500)
        self.assertIsNone(self.repository.get_approval(self.opportunity_id))
        self.assertIsNone(self.repository.get_decision(self.opportunity_id))
        self.assertEqual(self.brief()["opportunity"]["stage"], "PENDING_APPROVAL")
        # La siguiente solicitud debe poder completarse tras el rollback.
        self.assertEqual(
            self.post(
                "decisions",
                proposal_id="PROPOSAL-TEST",
                option_id=brief["options"][0]["id"],
                rationale="Reintento revisado",
                confirmed=True,
            ).status,
            201,
        )

    def test_nested_failure_can_be_caught_without_partial_commit(self) -> None:
        with self.repository.transaction():
            self.repository.add_account(Account("OUTER", "Exterior"))
            try:
                with self.repository.transaction():
                    self.repository.add_account(Account("INNER", "Interior"))
                    raise RuntimeError("falla interna")
            except RuntimeError:
                pass
        self.assertIsNotNone(self.repository.get_account("OUTER"))
        self.assertIsNone(self.repository.get_account("INNER"))

    def test_ai_draft_is_persisted_and_never_approves(self) -> None:
        self.assertEqual(self.post("ai-draft").status, 201)
        brief = self.brief()
        self.assertEqual(len(brief["ai_drafts"]), 1)
        self.assertIsNone(brief["decision"])
        self.assertIsNone(brief["proposal"])
        self.assertEqual(brief["opportunity"]["stage"], "INTAKE")

    def test_nonfinite_confidence_rejected(self) -> None:
        body = dict(self.brief()["evidence"][0])
        body["id"], body["statement"] = "NONFINITE", "Otra afirmación"
        for value in (float("nan"), float("inf"), True):
            body["confidence"] = value
            self.assertEqual(self.post("evidence", **body).status, 400)

    def test_new_opportunity_intake_works_without_seed_data(self) -> None:
        result = self.api.handle(
            "POST",
            "/api/opportunities",
            {
                "account_id": "ACCOUNT-NEW",
                "account_name": "Cuenta de prueba",
                "id": "OPP-NEW",
                "title": "Problema local",
                "owner": "analista",
                "actor": "editor-test",
            },
        )
        self.assertEqual(result.status, 201)
        self.opportunity_id = "OPP-NEW"
        self.assertEqual(
            self.post(
                "signals",
                id="SIGNAL-NEW",
                title="Documento recibido en sandbox",
                observed_at="2026-09-28",
                source="fixture",
                provenance="carga manual de prueba",
            ).status,
            201,
        )
        self.assertEqual(
            self.post("transitions", next_stage="EVIDENCE_REVIEW").status, 200
        )
        self.assertEqual(
            self.post("transitions", next_stage="OPTIONS_READY").status, 422
        )


if __name__ == "__main__":
    unittest.main()
