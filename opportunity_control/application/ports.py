"""Contratos de persistencia que la aplicación espera poder utilizar."""

from contextlib import AbstractContextManager
from typing import Protocol

from opportunity_control.domain import (
    Account,
    Approval,
    AuditEvent,
    DecisionOption,
    Evidence,
    Hypothesis,
    NextAction,
    Opportunity,
    OpportunityStage,
    Unknown,
)

from .workflow_ports import WorkflowRepository


class OpportunityRepository(WorkflowRepository, Protocol):
    """Define las operaciones de almacenamiento necesarias en esta etapa."""

    def transaction(self) -> AbstractContextManager[None]:
        """Agrupa escrituras para confirmarlas o revertirlas juntas."""

    def add_account(self, account: Account) -> None:
        """Guarda una cuenta nueva."""

    def get_account(self, account_id: str) -> Account | None:
        """Busca una cuenta por identificador."""

    def list_accounts(self) -> list[Account]:
        """Devuelve todas las cuentas en orden estable."""

    def add_opportunity(self, opportunity: Opportunity) -> None:
        """Guarda una oportunidad nueva."""

    def get_opportunity(self, opportunity_id: str) -> Opportunity | None:
        """Busca una oportunidad por identificador."""

    def list_opportunities(self) -> list[Opportunity]:
        """Devuelve todas las oportunidades en orden estable."""

    def add_evidence(self, evidence: Evidence) -> None:
        """Guarda evidencia trazable para una oportunidad."""

    def list_evidence(self, opportunity_id: str) -> list[Evidence]:
        """Devuelve la evidencia de una oportunidad en orden temporal."""

    def add_hypothesis(self, hypothesis: Hypothesis) -> None:
        """Guarda una hipótesis sin convertirla en evidencia."""

    def list_hypotheses(self, opportunity_id: str) -> list[Hypothesis]:
        """Devuelve las hipótesis de una oportunidad."""

    def add_unknown(self, unknown: Unknown) -> None:
        """Guarda una incógnita explícita."""

    def list_unknowns(self, opportunity_id: str) -> list[Unknown]:
        """Devuelve las incógnitas de una oportunidad."""

    def add_next_action(self, action: NextAction) -> None:
        """Guarda un siguiente paso exclusivamente interno."""

    def list_next_actions(self, opportunity_id: str) -> list[NextAction]:
        """Devuelve siguientes acciones ordenadas por fecha."""

    def add_decision_option(self, option: DecisionOption) -> None:
        """Guarda una alternativa de decisión."""

    def list_decision_options(self, opportunity_id: str) -> list[DecisionOption]:
        """Devuelve las alternativas registradas para una oportunidad."""

    def add_approval(self, approval: Approval) -> None:
        """Guarda una aprobación humana explícita."""

    def get_approval(self, opportunity_id: str) -> Approval | None:
        """Busca la aprobación de una oportunidad."""

    def update_opportunity_stage(
        self,
        opportunity_id: str,
        expected_stage: OpportunityStage,
        next_stage: OpportunityStage,
    ) -> bool:
        """Actualiza la etapa sólo si conserva el valor esperado."""

    def append_audit_event(self, event: AuditEvent) -> None:
        """Agrega un evento sin modificar el historial existente."""

    def list_audit_events(self, opportunity_id: str) -> list[AuditEvent]:
        """Devuelve el historial de una oportunidad en orden temporal."""
