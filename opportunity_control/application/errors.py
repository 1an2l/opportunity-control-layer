"""Errores independientes de la tecnología usada para persistir datos."""


class PersistenceError(RuntimeError):
    """Indica que un registro no pudo guardarse de forma válida."""


class DuplicateRecordError(PersistenceError):
    """Indica que ya existe un registro con el mismo identificador."""


class RecordNotFoundError(PersistenceError):
    """Indica que el objeto solicitado no existe."""


class ConcurrentChangeError(PersistenceError):
    """Indica que el estado cambió mientras se procesaba una operación."""


class ExternalActionBlockedError(RuntimeError):
    """Indica que una acción externa fue detenida intencionalmente."""
