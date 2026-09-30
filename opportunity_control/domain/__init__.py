"""Interfaz pública del modelo de dominio.

Este módulo reúne las piezas que el resto de la aplicación puede importar.
La implementación permanece separada por responsabilidad en módulos pequeños.
"""

from .accounts import Account, Contact
from .actions import NextAction
from .audit import AuditEvent
from .decisions import Approval, Decision, DecisionOption, Recommendation
from .enums import ActionStatus, ConfidenceState, EventOutcome, OpportunityStage
from .knowledge import Evidence, Hypothesis, Unknown
from .opportunities import Opportunity, Signal
from .proposals import Proposal
from .transitions import ALLOWED_TRANSITIONS, validate_transition
from .validation import DomainValidationError

__all__ = [
    "ALLOWED_TRANSITIONS",
    "Account",
    "ActionStatus",
    "Approval",
    "AuditEvent",
    "ConfidenceState",
    "Contact",
    "Decision",
    "DecisionOption",
    "DomainValidationError",
    "EventOutcome",
    "Evidence",
    "Hypothesis",
    "NextAction",
    "Opportunity",
    "OpportunityStage",
    "Proposal",
    "Recommendation",
    "Signal",
    "Unknown",
    "validate_transition",
]
