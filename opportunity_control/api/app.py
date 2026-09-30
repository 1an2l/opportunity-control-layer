"""Enrutador JSON que traduce HTTP a comandos de aplicación."""

import math
from dataclasses import dataclass
from datetime import date, datetime, timezone
from urllib.parse import unquote, urlparse

from opportunity_control.ai import LocalGovernedDraftGenerator
from opportunity_control.application import (
    DuplicateRecordError,
    ExternalActionBlockedError,
    OpportunityControlService,
    PersistenceError,
    RecordDecisionOptionCommand,
    RecordEvidenceCommand,
    RecordHypothesisCommand,
    RecordNextActionCommand,
    RecordNotFoundError,
    RecordUnknownCommand,
    TransitionOpportunityCommand,
)
from opportunity_control.domain import (
    Approval,
    ConfidenceState,
    DecisionOption,
    DomainValidationError,
    Evidence,
    Hypothesis,
    NextAction,
    OpportunityStage,
    Unknown,
)

from .serializers import founder_brief_to_dict, to_json_value
from .workflow_routes import WorkflowRoutes


class RequestValidationError(ValueError):
    """Indica que el JSON no cumple el contrato del endpoint."""


@dataclass(frozen=True)
class ApiResponse:
    """Respuesta independiente del servidor HTTP concreto."""

    status: int
    payload: dict[str, object] | list[object]


class ApiApplication(WorkflowRoutes):
    """Expone casos de uso sin duplicar reglas de negocio."""

    def __init__(
        self,
        service: OpportunityControlService,
        ai_generator: LocalGovernedDraftGenerator,
    ) -> None:
        """Recibe casos de uso y generador local, sin crear infraestructura."""
        self._service = service
        self._ai_generator = ai_generator

    def handle(
        self,
        method: str,
        raw_path: str,
        body: dict[str, object] | None = None,
    ) -> ApiResponse:
        """Procesa una solicitud y traduce errores a códigos HTTP estables."""

        try:
            return self._dispatch(method.upper(), raw_path, body or {})
        except RequestValidationError as error:
            self._audit_rejection(method, raw_path, body, str(error))
            return self._error(400, "invalid_request", str(error))
        except RecordNotFoundError as error:
            return self._error(404, "not_found", str(error))
        except DuplicateRecordError as error:
            self._audit_rejection(method, raw_path, body, str(error))
            return self._error(409, "duplicate_record", str(error))
        except ExternalActionBlockedError as error:
            return self._error(403, "external_action_blocked", str(error))
        except DomainValidationError as error:
            self._audit_rejection(method, raw_path, body, str(error))
            return self._error(422, "domain_validation_error", str(error))
        except PersistenceError as error:
            return self._error(400, "persistence_error", str(error))
        except (TypeError, ValueError) as error:
            self._audit_rejection(method, raw_path, body, str(error))
            return self._error(400, "invalid_request", str(error))
        except Exception:  # noqa: BLE001 -- Frontera HTTP: no filtrar errores internos al cliente.
            self._audit_rejection(
                method,
                raw_path,
                body,
                "operación fallida; no se aplicaron cambios parciales",
            )
            return self._error(
                500,
                "internal_error",
                "Ocurrió un error interno sin exponer detalles sensibles.",
            )

    def _dispatch(
        self,
        method: str,
        raw_path: str,
        body: dict[str, object],
    ) -> ApiResponse:
        segments = [
            unquote(segment)
            for segment in urlparse(raw_path).path.strip("/").split("/")
            if segment
        ]
        if method == "GET" and segments == ["api", "health"]:
            return ApiResponse(200, {"status": "ok", "external_actions": "disabled"})
        if segments == ["api", "opportunities"] and method == "GET":
            return ApiResponse(
                200,
                [to_json_value(item) for item in self._service.list_opportunities()],
            )
        if segments == ["api", "opportunities"] and method == "POST":
            return ApiResponse(201, self._create_opportunity(body))
        if len(segments) < 3 or segments[:2] != ["api", "opportunities"]:
            return self._error(404, "route_not_found", "Ruta no encontrada")

        opportunity_id = segments[2]
        if len(segments) == 3 and method == "GET":
            brief = self._service.get_founder_brief(opportunity_id)
            return ApiResponse(200, founder_brief_to_dict(brief))
        if len(segments) != 4:
            return self._error(404, "route_not_found", "Ruta no encontrada")

        action = segments[3]
        if method == "GET" and action == "brief":
            return ApiResponse(
                200,
                founder_brief_to_dict(self._service.get_founder_brief(opportunity_id)),
            )
        if method == "GET" and action == "events":
            return ApiResponse(
                200,
                [
                    to_json_value(event)
                    for event in self._service.list_audit_events(opportunity_id)
                ],
            )
        if method != "POST":
            return self._error(405, "method_not_allowed", "Método no permitido")
        workflow_result = self._workflow_action(action, opportunity_id, body)
        if workflow_result is not None:
            return ApiResponse(201, workflow_result)
        if action == "evidence":
            return self._record_evidence(opportunity_id, body)
        if action == "hypotheses":
            return self._record_hypothesis(opportunity_id, body)
        if action == "unknowns":
            return self._record_unknown(opportunity_id, body)
        if action == "options":
            return self._record_option(opportunity_id, body)
        if action == "next-actions":
            return self._record_next_action(opportunity_id, body)
        if action == "transitions":
            return self._transition(opportunity_id, body)
        if action == "ai-draft":
            return self._generate_ai_draft(opportunity_id, body)
        if action == "external-action":
            return self._block_external_action(opportunity_id, body)
        return self._error(404, "route_not_found", "Ruta no encontrada")

    def _record_evidence(
        self,
        opportunity_id: str,
        body: dict[str, object],
    ) -> ApiResponse:
        evidence = Evidence(
            id=self._text(body, "id"),
            opportunity_id=opportunity_id,
            statement=self._text(body, "statement"),
            source=self._text(body, "source"),
            provenance=self._text(body, "provenance"),
            confidence_state=ConfidenceState(self._text(body, "confidence_state")),
            confidence=self._number(body, "confidence"),
            recorded_at=self._datetime(body.get("recorded_at")),
        )
        self._service.record_evidence(
            RecordEvidenceCommand(evidence=evidence, actor=self._text(body, "actor"))
        )
        return ApiResponse(201, {"evidence": to_json_value(evidence)})

    def _record_hypothesis(
        self,
        opportunity_id: str,
        body: dict[str, object],
    ) -> ApiResponse:
        hypothesis = Hypothesis(
            id=self._text(body, "id"),
            opportunity_id=opportunity_id,
            statement=self._text(body, "statement"),
            rationale=self._text(body, "rationale"),
            confidence=self._number(body, "confidence", default=0.5),
        )
        self._service.record_hypothesis(
            RecordHypothesisCommand(
                hypothesis=hypothesis,
                actor=self._text(body, "actor"),
            )
        )
        return ApiResponse(201, {"hypothesis": to_json_value(hypothesis)})

    def _record_unknown(
        self,
        opportunity_id: str,
        body: dict[str, object],
    ) -> ApiResponse:
        unknown = Unknown(
            id=self._text(body, "id"),
            opportunity_id=opportunity_id,
            question=self._text(body, "question"),
        )
        self._service.record_unknown(
            RecordUnknownCommand(unknown=unknown, actor=self._text(body, "actor"))
        )
        return ApiResponse(201, {"unknown": to_json_value(unknown)})

    def _record_option(
        self,
        opportunity_id: str,
        body: dict[str, object],
    ) -> ApiResponse:
        option = DecisionOption(
            id=self._text(body, "id"),
            opportunity_id=opportunity_id,
            title=self._text(body, "title"),
            rationale=self._text(body, "rationale"),
            risk=self._text(body, "risk"),
        )
        self._service.record_decision_option(
            RecordDecisionOptionCommand(
                option=option,
                actor=self._text(body, "actor"),
            )
        )
        return ApiResponse(201, {"option": to_json_value(option)})

    def _record_next_action(
        self,
        opportunity_id: str,
        body: dict[str, object],
    ) -> ApiResponse:
        action = NextAction(
            id=self._text(body, "id"),
            opportunity_id=opportunity_id,
            description=self._text(body, "description"),
            owner=self._text(body, "owner"),
            due_date=date.fromisoformat(self._text(body, "due_date")),
        )
        self._service.record_next_action(
            RecordNextActionCommand(
                action=action,
                actor=self._text(body, "actor"),
            )
        )
        return ApiResponse(201, {"next_action": to_json_value(action)})

    def _transition(
        self,
        opportunity_id: str,
        body: dict[str, object],
    ) -> ApiResponse:
        next_stage = OpportunityStage(self._text(body, "next_stage"))
        if next_stage == OpportunityStage.APPROVED:
            raise DomainValidationError(
                "use decisions con propuesta, motivo y confirmación explícita"
            )
        approval = self._approval(opportunity_id, body.get("approval"))
        opportunity = self._service.transition_opportunity(
            TransitionOpportunityCommand(
                opportunity_id=opportunity_id,
                next_stage=next_stage,
                actor=self._text(body, "actor"),
                approval=approval,
                rationale=self._text(body, "rationale")
                if body.get("rationale")
                else None,
            )
        )
        return ApiResponse(200, {"opportunity": to_json_value(opportunity)})

    def _generate_ai_draft(
        self,
        opportunity_id: str,
        body: dict[str, object],
    ) -> ApiResponse:
        actor = self._text(body, "actor")
        draft = self._ai_generator.generate(
            self._service.get_founder_brief(opportunity_id)
        )
        self._service.save_ai_draft(opportunity_id, actor, to_json_value(draft))
        return ApiResponse(201, {"draft": to_json_value(draft)})

    def _block_external_action(
        self,
        opportunity_id: str,
        body: dict[str, object],
    ) -> ApiResponse:
        self._service.block_external_action(
            opportunity_id,
            actor=self._text(body, "actor"),
            description=self._text(
                body,
                "description",
                default="Intento de acción externa bloqueado",
            ),
        )
        raise AssertionError("la acción externa siempre debe lanzar un bloqueo")

    @staticmethod
    def _approval(opportunity_id: str, value: object) -> Approval | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise RequestValidationError("approval debe ser un objeto JSON")
        return Approval(
            opportunity_id=opportunity_id,
            option_id=ApiApplication._text(value, "option_id"),
            actor=ApiApplication._text(value, "actor"),
            approved_at=ApiApplication._datetime(value.get("approved_at")),
        )

    def _audit_rejection(
        self, method: str, path: str, body: dict | None, reason: str
    ) -> None:
        """Audita rechazos ligados a un caso existente, después de revertir cambios."""
        segments = urlparse(path).path.strip("/").split("/")
        if (
            method.upper() != "POST"
            or len(segments) != 4
            or segments[:2] != ["api", "opportunities"]
        ):
            return
        try:
            actor = str((body or {}).get("actor") or "unidentified-local-request")
            self._service.record_rejection(
                unquote(segments[2]),
                actor,
                "REQUEST_REJECTED",
                f"{segments[3]}: {reason}",
            )
        except RecordNotFoundError:
            return

    @staticmethod
    def _text(
        body: dict[str, object],
        field: str,
        *,
        default: str | None = None,
    ) -> str:
        value = body.get(field, default)
        if not isinstance(value, str) or not value.strip():
            raise RequestValidationError(f"{field} debe contener texto")
        return value.strip()

    @staticmethod
    def _number(
        body: dict[str, object],
        field: str,
        *,
        default: float | None = None,
    ) -> float:
        value = body.get(field, default)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise RequestValidationError(f"{field} debe ser numérico")
        return float(value)

    @staticmethod
    def _datetime(value: object) -> datetime:
        if value is None:
            return datetime.now(timezone.utc)
        if not isinstance(value, str):
            raise RequestValidationError("la fecha debe usar formato ISO 8601")
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @staticmethod
    def _error(status: int, code: str, message: str) -> ApiResponse:
        return ApiResponse(status, {"error": code, "message": message})
