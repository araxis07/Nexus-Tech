"""Persistence-layer exceptions."""


class PersistenceError(Exception):
    """Base class for recoverable save/load failures."""


class SaveNotFoundError(PersistenceError):
    """Raised when a requested save slot or database is missing."""


class CorruptSaveError(PersistenceError):
    """Raised when persisted state is incomplete or malformed."""
