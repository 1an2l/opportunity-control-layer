"""Conversión explícita de objetos internos a valores compatibles con JSON."""

from dataclasses import fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import cast

from opportunity_control.application import FounderBrief


def to_json_value(value: object) -> object:
    """Convierte dataclasses, fechas y enumeraciones de forma recursiva."""

    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: to_json_value(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): to_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json_value(item) for item in value]
    return value


def founder_brief_to_dict(brief: FounderBrief) -> dict[str, object]:
    """Agrega indicadores comprensibles al resumen ejecutivo."""

    serialized = cast(dict[str, object], to_json_value(brief))
    states = {"VERIFIED": 0, "INFERRED": 0, "UNKNOWN": 0}
    for evidence in brief.evidence:
        states[evidence.confidence_state.value] += 1
    average = (
        sum(item.confidence for item in brief.evidence) / len(brief.evidence)
        if brief.evidence
        else 0.0
    )
    serialized["confidence_summary"] = {
        "average": round(average, 2),
        "evidence_by_state": states,
        "interpretation": (
            "Sin evidencia registrada"
            if not brief.evidence
            else "Promedio informativo; no reemplaza la revisión de fuentes"
        ),
    }
    serialized["governance"] = {
        "human_approval_required": True,
        "external_actions_enabled": False,
        "ai_has_decision_authority": False,
    }
    serialized["recommendation"] = {
        "status": "HUMAN_APPROVED"
        if brief.approval
        else ("PENDING_HUMAN_REVIEW" if brief.proposals else "NOT_PROPOSED"),
        "selected_option_id": brief.approval.option_id if brief.approval else None,
        "message": (
            "La opción fue aprobada explícitamente por una persona."
            if brief.approval
            else "La propuesta requiere revisión humana."
            if brief.proposals
            else "Aún no hay propuesta registrada."
        ),
    }
    serialized["proposal"] = (
        to_json_value(brief.proposals[-1]) if brief.proposals else None
    )
    from opportunity_control.domain.transitions import ALLOWED_TRANSITIONS

    serialized["allowed_transitions"] = sorted(
        stage.value for stage in ALLOWED_TRANSITIONS[brief.opportunity.stage]
    )
    serialized["risks"] = [option.risk for option in brief.options]
    serialized["assumptions"] = [item.statement for item in brief.hypotheses]
    serialized["next_action"] = next(
        (
            to_json_value(item)
            for item in brief.next_actions
            if item.status.value == "PENDING"
        ),
        None,
    )
    return serialized
