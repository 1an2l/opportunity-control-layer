"""Pruebas del servidor HTTP real sobre un puerto local efímero."""

import json
import unittest
from datetime import datetime, timezone
from http.client import HTTPConnection
from http.server import HTTPServer
from threading import Thread

from opportunity_control.ai import LocalGovernedDraftGenerator
from opportunity_control.api import ApiApplication
from opportunity_control.api.access import LocalAccess
from opportunity_control.api.server import make_handler
from opportunity_control.application import OpportunityControlService
from opportunity_control.infrastructure import (
    SQLiteOpportunityRepository,
    connect_database,
    initialize_database,
)
from opportunity_control.seed import seed_repository


class HttpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        connection = connect_database(":memory:")
        initialize_database(connection)
        repository = SQLiteOpportunityRepository(connection)
        seed_repository(repository)
        now = datetime(2026, 9, 28, 20, 0, tzinfo=timezone.utc)
        application = ApiApplication(
            OpportunityControlService(repository, clock=lambda: now),
            LocalGovernedDraftGenerator(clock=lambda: now),
        )
        self.connection = connection
        self.access = LocalAccess("editor-test", "reviewer-test")
        self.server = HTTPServer(
            ("127.0.0.1", 0), make_handler(application, self.access)
        )
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = HTTPConnection("127.0.0.1", self.server.server_port)

    def tearDown(self) -> None:
        self.client.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.connection.close()

    def test_server_serves_spanish_interface(self) -> None:
        self.client.request("GET", "/")
        response = self.client.getresponse()
        content = response.read().decode("utf-8")

        self.assertEqual(response.status, 200)
        self.assertIn("Opportunity Control Layer", content)
        self.assertIn("Acciones externas bloqueadas", content)

    def test_health_endpoint_returns_json(self) -> None:
        self.client.request("GET", "/api/health")
        response = self.client.getresponse()
        payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.status, 200)
        self.assertEqual(payload["external_actions"], "disabled")

    def test_server_exposes_seed_opportunities(self) -> None:
        self.client.request("GET", "/api/opportunities")
        response = self.client.getresponse()
        payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.status, 200)
        self.assertEqual(len(payload), 3)

    def test_invalid_json_returns_400(self) -> None:
        self.client.request(
            "POST",
            "/api/opportunities/example/evidence",
            body="{invalid",
            headers={"Content-Type": "application/json"},
        )
        response = self.client.getresponse()
        payload = json.loads(response.read().decode("utf-8"))

        self.assertEqual(response.status, 400)
        self.assertEqual(payload["error"], "invalid_json")

    def post(self, path: str, body: dict, token: str = "", **extra_headers: str):
        """Envía una petición real sin sustituir la capa de permisos."""
        headers = {"Content-Type": "application/json", **extra_headers}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self.client.request("POST", path, json.dumps(body), headers)
        response = self.client.getresponse()
        return response.status, json.loads(response.read())

    def test_anonymous_write_is_denied(self) -> None:
        status, _ = self.post(
            "/api/opportunities/OPPORTUNITY-UVA-AI-PILOT/unknowns",
            {"id": "NO-AUTH", "question": "¿Pendiente?"},
        )
        self.assertEqual(status, 401)

    def test_editor_cannot_approve_even_using_encoded_route(self) -> None:
        for path in ("decisions", "deci%73ions"):
            status, _ = self.post(
                f"/api/opportunities/OPPORTUNITY-UVA-AI-PILOT/{path}",
                {"actor": "reviewer-test", "confirmed": True},
                self.access.editor_token,
            )
            self.assertEqual(status, 403)

    def test_identity_is_taken_from_credential_not_body(self) -> None:
        path = "/api/opportunities/OPPORTUNITY-UVA-AI-PILOT"
        status, _ = self.post(
            f"{path}/unknowns",
            {
                "id": "QUESTION-AUTH",
                "question": "¿Qué falta?",
                "actor": "forged-reviewer",
            },
            self.access.editor_token,
        )
        self.assertEqual(status, 201)
        self.client.request("GET", f"{path}/events")
        events = json.loads(self.client.getresponse().read())
        self.assertEqual(events[-1]["actor"], "editor-test")

    def test_foreign_origin_is_denied_even_with_a_valid_token(self) -> None:
        status, _ = self.post(
            "/api/opportunities/OPPORTUNITY-UVA-AI-PILOT/unknowns",
            {},
            self.access.reviewer_token,
            Origin="https://untrusted.example",
        )
        self.assertEqual(status, 403)

    def test_private_and_database_files_are_not_served(self) -> None:
        for path in (
            "/AGENTS.md",
            "/runtime/opportunity_control.db",
            "/docs/GUIA_DEMO.md",
            "/../README.md",
        ):
            self.client.request("GET", path)
            response = self.client.getresponse()
            response.read()
            self.assertEqual(response.status, 404)

    def test_unknown_api_route_never_returns_html(self) -> None:
        self.client.request("GET", "/api/missing")
        response = self.client.getresponse()
        self.assertEqual(response.status, 404)
        self.assertIn("application/json", response.getheader("Content-Type"))
        response.read()


if __name__ == "__main__":
    unittest.main()
