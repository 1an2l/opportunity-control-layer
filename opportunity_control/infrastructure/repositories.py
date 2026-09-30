"""Repositorio SQLite que traduce filas sin introducir reglas de negocio."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime

from opportunity_control.application.errors import (
    DuplicateRecordError,
    PersistenceError,
)
from opportunity_control.domain import (
    Account,
    ActionStatus,
    Approval,
    AuditEvent,
    ConfidenceState,
    DecisionOption,
    EventOutcome,
    Evidence,
    Hypothesis,
    NextAction,
    Opportunity,
    OpportunityStage,
    Unknown,
)

from .workflow_repository import WorkflowRepositoryMixin


class SQLiteOpportunityRepository(WorkflowRepositoryMixin):
    """Guarda y reconstruye objetos del dominio mediante SQLite."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Recibe una conexión ya configurada e inicializada."""

        self._connection = connection
        self._transaction_depth = 0

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Confirma todas las escrituras o las revierte si alguna falla."""

        is_outermost = self._transaction_depth == 0
        savepoint = f"workflow_{self._transaction_depth}"
        if is_outermost:
            self._connection.execute("BEGIN IMMEDIATE")
        else:
            self._connection.execute(f"SAVEPOINT {savepoint}")
        self._transaction_depth += 1
        try:
            yield
            if is_outermost:
                self._connection.commit()
            else:
                self._connection.execute(f"RELEASE SAVEPOINT {savepoint}")
        except Exception:
            if is_outermost:
                self._connection.rollback()
            else:
                self._connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                self._connection.execute(f"RELEASE SAVEPOINT {savepoint}")
            raise
        finally:
            self._transaction_depth -= 1

    def add_account(self, account: Account) -> None:
        """Guarda una cuenta y traduce duplicados a un error estable."""

        self._insert(
            "INSERT INTO accounts (id, name) VALUES (?, ?)",
            (account.id, account.name),
            record_type="account",
            record_id=account.id,
        )

    def get_account(self, account_id: str) -> Account | None:
        """Busca una cuenta por identificador."""

        row = self._connection.execute(
            "SELECT id, name FROM accounts WHERE id = ?",
            (account_id,),
        ).fetchone()
        if row is None:
            return None
        return Account(id=row["id"], name=row["name"])

    def list_accounts(self) -> list[Account]:
        """Devuelve las cuentas ordenadas por identificador."""

        rows = self._connection.execute(
            "SELECT id, name FROM accounts ORDER BY id"
        ).fetchall()
        return [Account(id=row["id"], name=row["name"]) for row in rows]

    def add_opportunity(self, opportunity: Opportunity) -> None:
        """Guarda una oportunidad asociada a una cuenta existente."""

        self._insert(
            """
            INSERT INTO opportunities (id, account_id, title, owner, stage)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                opportunity.id,
                opportunity.account_id,
                opportunity.title,
                opportunity.owner,
                opportunity.stage.value,
            ),
            record_type="opportunity",
            record_id=opportunity.id,
        )

    def get_opportunity(self, opportunity_id: str) -> Opportunity | None:
        """Busca una oportunidad por identificador."""

        row = self._connection.execute(
            """
            SELECT id, account_id, title, owner, stage
            FROM opportunities
            WHERE id = ?
            """,
            (opportunity_id,),
        ).fetchone()
        if row is None:
            return None
        return self._opportunity_from_row(row)

    def list_opportunities(self) -> list[Opportunity]:
        """Devuelve las oportunidades ordenadas por identificador."""

        rows = self._connection.execute(
            """
            SELECT id, account_id, title, owner, stage
            FROM opportunities
            ORDER BY id
            """
        ).fetchall()
        return [self._opportunity_from_row(row) for row in rows]

    def update_opportunity_stage(
        self,
        opportunity_id: str,
        expected_stage: OpportunityStage,
        next_stage: OpportunityStage,
    ) -> bool:
        """Cambia la etapa sólo si nadie modificó antes la oportunidad."""

        cursor = self._connection.execute(
            """
            UPDATE opportunities
            SET stage = ?
            WHERE id = ? AND stage = ?
            """,
            (next_stage.value, opportunity_id, expected_stage.value),
        )
        self._commit_if_standalone()
        return cursor.rowcount == 1

    def add_evidence(self, evidence: Evidence) -> None:
        """Guarda evidencia conservando fuente, procedencia y confianza."""

        self._insert(
            """
            INSERT INTO evidence (
                id, opportunity_id, statement, source, provenance,
                confidence_state, confidence, recorded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evidence.id,
                evidence.opportunity_id,
                evidence.statement,
                evidence.source,
                evidence.provenance,
                evidence.confidence_state.value,
                evidence.confidence,
                evidence.recorded_at.isoformat(),
            ),
            record_type="evidence",
            record_id=evidence.id,
        )

    def list_evidence(self, opportunity_id: str) -> list[Evidence]:
        """Devuelve evidencia ordenada por fecha e identificador."""

        rows = self._connection.execute(
            """
            SELECT id, opportunity_id, statement, source, provenance,
                   confidence_state, confidence, recorded_at
            FROM evidence
            WHERE opportunity_id = ?
            ORDER BY recorded_at, id
            """,
            (opportunity_id,),
        ).fetchall()
        return [
            Evidence(
                id=row["id"],
                opportunity_id=row["opportunity_id"],
                statement=row["statement"],
                source=row["source"],
                provenance=row["provenance"],
                confidence_state=ConfidenceState(row["confidence_state"]),
                confidence=row["confidence"],
                recorded_at=self._parse_datetime(row["recorded_at"]),
            )
            for row in rows
        ]

    def add_hypothesis(self, hypothesis: Hypothesis) -> None:
        """Guarda una hipótesis con confianza inferida explícita."""

        self._insert(
            """
            INSERT INTO hypotheses (
                id, opportunity_id, statement, rationale,
                confidence_state, confidence
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                hypothesis.id,
                hypothesis.opportunity_id,
                hypothesis.statement,
                hypothesis.rationale,
                hypothesis.confidence_state.value,
                hypothesis.confidence,
            ),
            record_type="hypothesis",
            record_id=hypothesis.id,
        )

    def list_hypotheses(self, opportunity_id: str) -> list[Hypothesis]:
        """Devuelve las hipótesis ordenadas por identificador."""

        rows = self._connection.execute(
            """
            SELECT id, opportunity_id, statement, rationale,
                   confidence_state, confidence
            FROM hypotheses
            WHERE opportunity_id = ?
            ORDER BY id
            """,
            (opportunity_id,),
        ).fetchall()
        return [
            Hypothesis(
                id=row["id"],
                opportunity_id=row["opportunity_id"],
                statement=row["statement"],
                rationale=row["rationale"],
                confidence_state=ConfidenceState(row["confidence_state"]),
                confidence=row["confidence"],
            )
            for row in rows
        ]

    def add_unknown(self, unknown: Unknown) -> None:
        """Guarda una pregunta pendiente sin inventar su respuesta."""

        self._insert(
            """
            INSERT INTO unknowns (
                id, opportunity_id, question, confidence_state, confidence
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                unknown.id,
                unknown.opportunity_id,
                unknown.question,
                unknown.confidence_state.value,
                unknown.confidence,
            ),
            record_type="unknown",
            record_id=unknown.id,
        )

    def list_unknowns(self, opportunity_id: str) -> list[Unknown]:
        """Devuelve las preguntas pendientes ordenadas por identificador."""

        rows = self._connection.execute(
            """
            SELECT id, opportunity_id, question, confidence_state, confidence
            FROM unknowns
            WHERE opportunity_id = ?
            ORDER BY id
            """,
            (opportunity_id,),
        ).fetchall()
        return [
            Unknown(
                id=row["id"],
                opportunity_id=row["opportunity_id"],
                question=row["question"],
                confidence_state=ConfidenceState(row["confidence_state"]),
                confidence=row["confidence"],
            )
            for row in rows
        ]

    def add_next_action(self, action: NextAction) -> None:
        """Guarda una acción interna sin capacidad de ejecutarla."""

        self._insert(
            """
            INSERT INTO next_actions (
                id, opportunity_id, description, owner, due_date, status
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                action.id,
                action.opportunity_id,
                action.description,
                action.owner,
                action.due_date.isoformat(),
                action.status.value,
            ),
            record_type="next_action",
            record_id=action.id,
        )

    def list_next_actions(self, opportunity_id: str) -> list[NextAction]:
        """Devuelve acciones internas ordenadas por fecha e identificador."""

        rows = self._connection.execute(
            """
            SELECT id, opportunity_id, description, owner, due_date, status
            FROM next_actions
            WHERE opportunity_id = ?
            ORDER BY due_date, id
            """,
            (opportunity_id,),
        ).fetchall()
        return [
            NextAction(
                id=row["id"],
                opportunity_id=row["opportunity_id"],
                description=row["description"],
                owner=row["owner"],
                due_date=date.fromisoformat(row["due_date"]),
                status=ActionStatus(row["status"]),
            )
            for row in rows
        ]

    def add_decision_option(self, option: DecisionOption) -> None:
        """Guarda una opción vinculada a una oportunidad existente."""

        self._insert(
            """
            INSERT INTO decision_options (
                id, opportunity_id, title, rationale, risk
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                option.id,
                option.opportunity_id,
                option.title,
                option.rationale,
                option.risk,
            ),
            record_type="decision_option",
            record_id=option.id,
        )

    def list_decision_options(self, opportunity_id: str) -> list[DecisionOption]:
        """Devuelve las opciones de una oportunidad ordenadas por ID."""

        rows = self._connection.execute(
            """
            SELECT id, opportunity_id, title, rationale, risk
            FROM decision_options
            WHERE opportunity_id = ?
            ORDER BY id
            """,
            (opportunity_id,),
        ).fetchall()
        return [
            DecisionOption(
                id=row["id"],
                opportunity_id=row["opportunity_id"],
                title=row["title"],
                rationale=row["rationale"],
                risk=row["risk"],
            )
            for row in rows
        ]

    def add_approval(self, approval: Approval) -> None:
        """Guarda una aprobación para una opción de la misma oportunidad."""

        self._insert(
            """
            INSERT INTO approvals (opportunity_id, option_id, actor, approved_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                approval.opportunity_id,
                approval.option_id,
                approval.actor,
                approval.approved_at.isoformat(),
            ),
            record_type="approval",
            record_id=approval.opportunity_id,
        )

    def get_approval(self, opportunity_id: str) -> Approval | None:
        """Busca la aprobación humana de una oportunidad."""

        row = self._connection.execute(
            """
            SELECT opportunity_id, option_id, actor, approved_at
            FROM approvals
            WHERE opportunity_id = ?
            """,
            (opportunity_id,),
        ).fetchone()
        if row is None:
            return None
        return Approval(
            opportunity_id=row["opportunity_id"],
            option_id=row["option_id"],
            actor=row["actor"],
            approved_at=self._parse_datetime(row["approved_at"]),
        )

    def append_audit_event(self, event: AuditEvent) -> None:
        """Agrega un evento al final del historial protegido."""

        self._insert(
            """
            INSERT INTO audit_events (
                id, opportunity_id, event_type, actor, occurred_at, outcome,
                previous_stage, next_stage, detail
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                event.opportunity_id,
                event.event_type,
                event.actor,
                event.occurred_at.isoformat(),
                event.outcome.value,
                event.previous_stage.value if event.previous_stage else None,
                event.next_stage.value if event.next_stage else None,
                event.detail,
            ),
            record_type="audit_event",
            record_id=event.id,
        )

    def list_audit_events(self, opportunity_id: str) -> list[AuditEvent]:
        """Devuelve eventos en el mismo orden en que fueron agregados."""

        rows = self._connection.execute(
            """
            SELECT id, opportunity_id, event_type, actor, occurred_at, outcome,
                   previous_stage, next_stage, detail
            FROM audit_events
            WHERE opportunity_id = ?
            ORDER BY sequence
            """,
            (opportunity_id,),
        ).fetchall()
        return [
            AuditEvent(
                id=row["id"],
                opportunity_id=row["opportunity_id"],
                event_type=row["event_type"],
                actor=row["actor"],
                occurred_at=self._parse_datetime(row["occurred_at"]),
                outcome=EventOutcome(row["outcome"]),
                previous_stage=(
                    OpportunityStage(row["previous_stage"])
                    if row["previous_stage"]
                    else None
                ),
                next_stage=(
                    OpportunityStage(row["next_stage"]) if row["next_stage"] else None
                ),
                detail=row["detail"],
            )
            for row in rows
        ]

    def _insert(
        self,
        statement: str,
        parameters: tuple[object, ...],
        *,
        record_type: str,
        record_id: str,
    ) -> None:
        try:
            self._connection.execute(statement, parameters)
            self._commit_if_standalone()
        except sqlite3.IntegrityError as error:
            if self._transaction_depth == 0:
                self._connection.rollback()
            message = str(error)
            if "UNIQUE constraint failed" in message:
                raise DuplicateRecordError(
                    f"{record_type} duplicado: {record_id}"
                ) from error
            raise PersistenceError(
                f"no se pudo guardar {record_type} {record_id}: {message}"
            ) from error

    def _commit_if_standalone(self) -> None:
        if self._transaction_depth == 0:
            self._connection.commit()

    @staticmethod
    def _opportunity_from_row(row: sqlite3.Row) -> Opportunity:
        return Opportunity(
            id=row["id"],
            account_id=row["account_id"],
            title=row["title"],
            owner=row["owner"],
            stage=OpportunityStage(row["stage"]),
        )

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        return datetime.fromisoformat(value)
