"""Modelo de lectura para el resumen ejecutivo de una oportunidad."""

from dataclasses import dataclass
from datetime import datetime

from opportunity_control.domain import (
    Account,
    Approval,
    AuditEvent,
    DecisionOption,
    Evidence,
    Hypothesis,
    NextAction,
    Opportunity,
    Unknown,
)
from opportunity_control.domain.accounts import Contact
from opportunity_control.domain.decisions import Decision
from opportunity_control.domain.opportunities import Signal
from opportunity_control.domain.proposals import Proposal


@dataclass(frozen=True)
class FounderBrief:
    """Agrupa hechos, dudas, opciones y control humano para un fundador."""

    account: Account
    opportunity: Opportunity
    evidence: tuple[Evidence, ...]
    hypotheses: tuple[Hypothesis, ...]
    unknowns: tuple[Unknown, ...]
    options: tuple[DecisionOption, ...]
    next_actions: tuple[NextAction, ...]
    approval: Approval | None
    last_movement: AuditEvent | None
    generated_at: datetime
    signals: tuple[Signal, ...] = ()
    contacts: tuple[Contact, ...] = ()
    proposals: tuple[Proposal, ...] = ()
    decision: Decision | None = None
    ai_drafts: tuple[dict[str, object], ...] = ()
