"""Casos de uso y contratos que coordinan el dominio."""

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
    DuplicateRecordError,
    ExternalActionBlockedError,
    PersistenceError,
    RecordNotFoundError,
)
from .ports import OpportunityRepository
from .services import OpportunityControlService

__all__ = [
    "ConcurrentChangeError",
    "DuplicateRecordError",
    "ExternalActionBlockedError",
    "FounderBrief",
    "OpportunityControlService",
    "OpportunityRepository",
    "PersistenceError",
    "RecordDecisionOptionCommand",
    "RecordEvidenceCommand",
    "RecordHypothesisCommand",
    "RecordNextActionCommand",
    "RecordNotFoundError",
    "RecordUnknownCommand",
    "TransitionOpportunityCommand",
]
