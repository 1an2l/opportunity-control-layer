"""Persistencia del intake, propuestas, decisiones y borradores locales."""

import json
from datetime import date, datetime

from opportunity_control.domain.accounts import Contact
from opportunity_control.domain.decisions import Decision
from opportunity_control.domain.enums import ActionStatus
from opportunity_control.domain.opportunities import Signal
from opportunity_control.domain.proposals import Proposal


class WorkflowRepositoryMixin:
    """Operaciones complementarias que comparten la transacción del repositorio."""

    def add_contact(self, contact: Contact) -> None:
        """Guarda un rol sanitizado sin habilitar canales de contacto."""
        self._insert(
            "INSERT INTO contacts VALUES (?, ?, ?, ?)",
            (contact.id, contact.account_id, contact.role, contact.display_name),
            record_type="contact",
            record_id=contact.id,
        )

    def list_contacts(self, account_id: str) -> list[Contact]:
        """Obtiene los roles de una cuenta."""
        rows = self._connection.execute(
            "SELECT * FROM contacts WHERE account_id = ? ORDER BY id", (account_id,)
        )
        return [Contact(**dict(row)) for row in rows]

    def add_signal(self, signal: Signal) -> None:
        """Guarda el movimiento observado y su procedencia."""
        self._insert(
            "INSERT INTO signals VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                signal.id,
                signal.opportunity_id,
                signal.account_id,
                signal.title,
                signal.observed_at.isoformat(),
                signal.source,
                signal.provenance,
            ),
            record_type="signal",
            record_id=signal.id,
        )

    def list_signals(self, opportunity_id: str) -> list[Signal]:
        """Obtiene señales ordenadas cronológicamente."""
        rows = self._connection.execute(
            "SELECT * FROM signals WHERE opportunity_id = ? ORDER BY observed_at, id",
            (opportunity_id,),
        )
        return [
            Signal(
                **{**dict(row), "observed_at": date.fromisoformat(row["observed_at"])}
            )
            for row in rows
        ]

    def add_proposal(self, proposal: Proposal) -> None:
        """Conserva cada versión de propuesta sin sobrescribir la anterior."""
        self._insert(
            """INSERT INTO proposals (id, opportunity_id, option_id, rationale,
               evidence_ids, hypothesis_ids, unknown_ids, actor, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                proposal.id,
                proposal.opportunity_id,
                proposal.option_id,
                proposal.rationale,
                json.dumps(proposal.evidence_ids),
                json.dumps(proposal.hypothesis_ids),
                json.dumps(proposal.unknown_ids),
                proposal.actor,
                proposal.created_at.isoformat(),
            ),
            record_type="proposal",
            record_id=proposal.id,
        )

    def list_proposals(self, opportunity_id: str) -> list[Proposal]:
        """Reconstruye versiones en su orden de inserción."""
        rows = self._connection.execute(
            "SELECT * FROM proposals WHERE opportunity_id = ? ORDER BY sequence",
            (opportunity_id,),
        )
        return [
            Proposal(
                id=row["id"],
                opportunity_id=row["opportunity_id"],
                option_id=row["option_id"],
                rationale=row["rationale"],
                evidence_ids=tuple(json.loads(row["evidence_ids"])),
                hypothesis_ids=tuple(json.loads(row["hypothesis_ids"])),
                unknown_ids=tuple(json.loads(row["unknown_ids"])),
                actor=row["actor"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def add_decision(self, decision: Decision) -> None:
        """Guarda la decisión en la misma transacción que la aprobación."""
        self._insert(
            "INSERT INTO decisions VALUES (?, ?, ?, ?)",
            (
                decision.opportunity_id,
                decision.selected_option_id,
                decision.rationale,
                decision.proposal_id,
            ),
            record_type="decision",
            record_id=decision.opportunity_id,
        )

    def get_decision(self, opportunity_id: str) -> Decision | None:
        """Lee la decisión final junto con su aprobación persistida."""
        row = self._connection.execute(
            "SELECT * FROM decisions WHERE opportunity_id = ?", (opportunity_id,)
        ).fetchone()
        if row is None:
            return None
        return Decision(**dict(row), approval=self.get_approval(opportunity_id))

    def save_ai_draft(self, opportunity_id: str, draft: dict[str, object]) -> None:
        """Guarda la salida completa para que sobreviva a reinicios."""
        self._insert(
            "INSERT INTO ai_drafts (id, opportunity_id, payload) VALUES (?, ?, ?)",
            (draft["id"], opportunity_id, json.dumps(draft, ensure_ascii=False)),
            record_type="ai_draft",
            record_id=str(draft["id"]),
        )

    def list_ai_drafts(self, opportunity_id: str) -> list[dict[str, object]]:
        """Recupera borradores, nunca decisiones automáticas."""
        rows = self._connection.execute(
            "SELECT payload FROM ai_drafts WHERE opportunity_id = ? ORDER BY sequence",
            (opportunity_id,),
        )
        return [json.loads(row["payload"]) for row in rows]

    def update_action_status(
        self, opportunity_id: str, action_id: str, status: ActionStatus
    ) -> None:
        """Actualiza sólo una tarea del caso previamente validado."""
        self._connection.execute(
            "UPDATE next_actions SET status = ? WHERE opportunity_id = ? AND id = ?",
            (status.value, opportunity_id, action_id),
        )
        self._commit_if_standalone()
