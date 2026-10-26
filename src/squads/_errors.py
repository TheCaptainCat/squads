"""Exception hierarchy. CLI catches SquadsError and prints a clean message."""

from pathlib import Path


class SquadsError(Exception):
    """Base class for all expected, user-facing errors."""


class NotInitializedError(SquadsError):
    """No .squads.toml found walking up from the directory the command ran in."""

    def __init__(self, searched: Path) -> None:
        self.searched = searched
        super().__init__(self.describe(named=False))

    def describe(self, *, named: bool) -> str:
        """The message, naming the searched directory when the caller chose it with ``-C``."""
        where = str(self.searched) if named else "this"
        return f"no .squads.toml found in {where} or any parent directory — run `sq init`"


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


class ConfigIntegrityError(SquadsError):
    """A roster status transition would leave generated backend config structurally invalid.

    The ``no_live_role``/``preloaded_skill`` clauses live in ``_services/_config_integrity.py``.
    Unlike ``InvalidTransitionError``/``StatusNotInWorkflowError``, which gate the lifecycle's own
    vocabulary and edges and yield to ``--force``, this is a property of the resulting projection
    and never overridable.
    """


class UndecodableFileError(SquadsError):
    """A file's on-disk bytes aren't valid UTF-8 — raised by :func:`squads._aio.read_text`."""


class UnreadableFileError(SquadsError):
    """A file exists but the OS refused the read — permission denied, an I/O error, anything
    ``FileNotFoundError`` is not — raised by :func:`squads._aio.read_text`."""


class PlaybookConfigError(SquadsError):
    """The active playbook (bundled base plus an override) failed to load or validate.

    Raised by ``_spec_documents.resolve_playbook``. It is distinct from a plain ``SquadsError`` so
    a caller that also opens the workflow spec (``open_service``, ``sq check``) can name the
    actually-broken file, not point at ``sq workflow lint``, which never reads
    ``.overrides/playbook.toml``.
    """


class IndexFullError(SquadsError):
    """Every id the index's padding can name is used up."""

    def __init__(self, message: str, *, capacity: int, padding: int) -> None:
        super().__init__(message)
        self.capacity = capacity
        self.padding = padding


class IndexLockTimeoutError(SquadsError):
    """The index lock stayed held by another process for the whole wait."""

    def __init__(self, lock_path: Path) -> None:
        super().__init__(
            f"the index lock {lock_path} is held by another sq process; "
            "nothing was written, retry the command"
        )
        self.lock_path = lock_path
