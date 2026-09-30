"""Entidades que representan cuentas y contactos sanitizados."""

from dataclasses import dataclass

from .validation import require_text


@dataclass(frozen=True)
class Account:
    """Representa una organización analizada por el sistema."""

    id: str
    name: str

    def __post_init__(self) -> None:
        """Valida los datos obligatorios después de construir la cuenta."""

        require_text(self.id, "account.id")
        require_text(self.name, "account.name")


@dataclass(frozen=True)
class Contact:
    """Representa un contacto o rol sanitizado asociado a una cuenta."""

    id: str
    account_id: str
    role: str
    display_name: str | None = None

    def __post_init__(self) -> None:
        """Valida la identidad, cuenta y función obligatorias del contacto."""

        require_text(self.id, "contact.id")
        require_text(self.account_id, "contact.account_id")
        require_text(self.role, "contact.role")
