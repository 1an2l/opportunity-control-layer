"""Traducción HTTP de intake, propuesta, decisión y seguimiento interno."""

from datetime import date, datetime, timezone

from opportunity_control.domain.accounts import Account, Contact
from opportunity_control.domain.enums import ActionStatus
from opportunity_control.domain.opportunities import Opportunity, Signal
from opportunity_control.domain.proposals import Proposal

from .serializers import to_json_value


class WorkflowRoutes:
    """Endpoints complementarios; las reglas viven en los casos de uso."""

    def _create_opportunity(self, body: dict[str, object]) -> dict[str, object]:
        account = Account(
            self._text(body, "account_id"), self._text(body, "account_name")
        )
        opportunity = Opportunity(
            self._text(body, "id"),
            account.id,
            self._text(body, "title"),
            self._text(body, "owner"),
        )
        self._service.create_opportunity(
            account, opportunity, self._text(body, "actor")
        )
        return {"opportunity": to_json_value(opportunity)}

    def _workflow_action(
        self, action: str, opportunity_id: str, body: dict[str, object]
    ) -> dict[str, object] | None:
        handlers = {
            "signals": self._signal,
            "contacts": self._contact,
            "proposals": self._proposal,
            "decisions": self._decision,
            "action-status": self._action_status,
        }
        if action not in handlers:
            return None
        return handlers[action](opportunity_id, body)

    def _signal(
        self, opportunity_id: str, body: dict[str, object]
    ) -> dict[str, object]:
        brief = self._service.get_founder_brief(opportunity_id)
        signal = Signal(
            id=self._text(body, "id"),
            account_id=brief.account.id,
            title=self._text(body, "title"),
            observed_at=date.fromisoformat(self._text(body, "observed_at")),
            opportunity_id=opportunity_id,
            source=self._text(body, "source"),
            provenance=self._text(body, "provenance"),
        )
        self._service.record_signal(signal, self._text(body, "actor"))
        return {"signal": to_json_value(signal)}

    def _contact(
        self, opportunity_id: str, body: dict[str, object]
    ) -> dict[str, object]:
        brief = self._service.get_founder_brief(opportunity_id)
        contact = Contact(
            self._text(body, "id"),
            brief.account.id,
            self._text(body, "role"),
            self._text(body, "display_name", default="Rol sanitizado"),
        )
        self._service.record_contact(opportunity_id, contact, self._text(body, "actor"))
        return {"contact": to_json_value(contact)}

    def _proposal(
        self, opportunity_id: str, body: dict[str, object]
    ) -> dict[str, object]:
        proposal = Proposal(
            id=self._text(body, "id"),
            opportunity_id=opportunity_id,
            option_id=self._text(body, "option_id"),
            rationale=self._text(body, "rationale"),
            evidence_ids=self._references(body, "evidence_ids"),
            hypothesis_ids=self._references(body, "hypothesis_ids"),
            unknown_ids=self._references(body, "unknown_ids"),
            actor=self._text(body, "actor"),
            created_at=datetime.now(timezone.utc),
        )
        self._service.record_proposal(proposal)
        return {"proposal": to_json_value(proposal)}

    def _decision(
        self, opportunity_id: str, body: dict[str, object]
    ) -> dict[str, object]:
        decision = self._service.decide(
            opportunity_id,
            proposal_id=self._text(body, "proposal_id"),
            option_id=self._text(body, "option_id"),
            rationale=self._text(body, "rationale"),
            actor=self._text(body, "actor"),
            confirmed=body.get("confirmed") is True,
        )
        return {"decision": to_json_value(decision)}

    def _action_status(
        self, opportunity_id: str, body: dict[str, object]
    ) -> dict[str, object]:
        self._service.change_action_status(
            opportunity_id,
            self._text(body, "id"),
            ActionStatus(self._text(body, "status")),
            self._text(body, "actor"),
        )
        return {"status": "updated", "external_effects": False}

    @staticmethod
    def _references(body: dict[str, object], field: str) -> tuple[str, ...]:
        value = body.get(field, [])
        if not isinstance(value, list) or any(
            not isinstance(item, str) or not item.strip() for item in value
        ):
            raise ValueError(f"{field} debe ser una lista de identificadores")
        return tuple(value)
