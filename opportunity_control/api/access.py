"""Credenciales efímeras de sandbox; no son autenticación corporativa."""

import secrets
from dataclasses import dataclass
from urllib.parse import unquote


@dataclass(frozen=True)
class Principal:
    """Identidad y rol establecidos por el operador al iniciar el servidor."""

    actor: str
    role: str


class LocalAccess:
    """Lectura local sin token; escritura y aprobación requieren capacidad secreta."""

    def __init__(
        self, editor: str = "editor-local", reviewer: str = "revisor-local"
    ) -> None:
        """Emite claves independientes, nunca las incluye en la API ni archivos."""
        self.editor_token = secrets.token_urlsafe(32)
        self.reviewer_token = secrets.token_urlsafe(32)
        self._principals = {
            self.editor_token: Principal(editor, "editor"),
            self.reviewer_token: Principal(reviewer, "reviewer"),
        }

    def resolve(self, authorization: str) -> Principal | None:
        """Resuelve un token Bearer comparándolo en tiempo constante."""
        token = authorization.removeprefix("Bearer ")
        if not token.isascii():
            return None
        for known, principal in self._principals.items():
            if secrets.compare_digest(token, known):
                return principal
        return None

    @staticmethod
    def can_write(principal: Principal, path: str, body: dict[str, object]) -> bool:
        """Reservar una decisión final al revisor impide elevar privilegios en JSON."""
        path = unquote(path).rstrip("/")
        final_decision = path.endswith("/decisions") or (
            path.endswith("/transitions")
            and body.get("next_stage") in ("APPROVED", "REJECTED")
        )
        return not final_decision or principal.role == "reviewer"
