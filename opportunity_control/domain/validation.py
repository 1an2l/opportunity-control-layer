"""Errores y validaciones básicas compartidas por el dominio."""


class DomainValidationError(ValueError):
    """Indica que un objeto o transición viola una regla del dominio."""


def require_text(value: str, field_name: str) -> None:
    """Exige que un campo contenga texto distinto de espacios en blanco."""

    if not isinstance(value, str) or not value.strip():
        raise DomainValidationError(f"{field_name} es obligatorio")
