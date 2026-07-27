"""Exception hierarchy. CLI catches SquadsError and prints a clean message."""


class SquadsError(Exception):
    """Base class for all expected, user-facing errors."""


class NotInitializedError(SquadsError):
    """No .squads.toml found walking up from cwd (and no --dir given)."""


class AlreadyInitializedError(SquadsError):
    pass


class ItemNotFoundError(SquadsError):
    pass


class InvalidIdError(SquadsError):
    pass


class InvalidTransitionError(SquadsError):
    pass


class RoleNotFoundError(SquadsError):
    pass


class StatusNotInWorkflowError(SquadsError):
    pass


class UndecodableFileError(SquadsError):
    """A file's on-disk bytes aren't valid UTF-8 — raised by :func:`squads._aio.read_text`."""
