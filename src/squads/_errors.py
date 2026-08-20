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


class ConfigIntegrityError(SquadsError):
    """A roster status transition would leave generated backend config structurally invalid
    (the ``no_live_role``/``preloaded_skill`` clauses in ``_services/_config_integrity.py``).
    Distinct from ``InvalidTransitionError``/``StatusNotInWorkflowError``: those two gate the
    lifecycle's own vocabulary and edges, and ``--force`` overrides them; this one never is —
    it is a config-integrity property of the resulting projection, not a policy choice the
    operator is entitled to overrule."""


class UndecodableFileError(SquadsError):
    """A file's on-disk bytes aren't valid UTF-8 — raised by :func:`squads._aio.read_text`."""


class UnreadableFileError(SquadsError):
    """A file exists but the OS refused the read — permission denied, an I/O error, anything
    ``FileNotFoundError`` is not — raised by :func:`squads._aio.read_text`."""


class PlaybookConfigError(SquadsError):
    """The active playbook (bundled base + any ``.overrides/playbook.toml``) failed to load or
    validate — raised by ``_services._service.resolve_playbook``, distinct from a plain
    ``SquadsError`` so a caller that also opens the workflow spec (``open_service``, ``sq
    check``) can tell a playbook failure apart from a workflow-spec failure and name the
    actually-broken file rather than pointing at ``sq workflow lint``, which never reads
    ``.overrides/playbook.toml`` at all."""
