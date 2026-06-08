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
