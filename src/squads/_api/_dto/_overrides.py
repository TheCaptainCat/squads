"""The override DTOs: the squad's overrides listed and diffed, one scaffolded, and re-stamped.

An override is addressed by ``kind`` (``template``, ``role``, ``workflow``, ``playbook`` or
``roles``) and ``name``; a request without them means every override the command applies to.
``errors`` holds the message for each override that could not be handled, and ``failed`` says
the command exits 1 for one that is broken."""

from squads._api._dto._base import DTO


class OverrideListRequest(DTO):
    """List every override."""


class OverrideRow(DTO):
    """An override: its name, kind, the version it was based on and its state."""

    name: str
    kind: str
    base_version: str | None
    state: str


class OverrideList(DTO):
    """Every override, with the causes of the broken ones."""

    items: list[OverrideRow]
    errors: list[str]
    failed: bool


class OverrideDiffRequest(DTO):
    """Diff one override, or every drifted one when *kind* is not given."""

    kind: str | None = None
    name: str | None = None


class OverrideDiffRow(DTO):
    """An override's two deltas: against the current bundled default, and what the upgrade
    changed in the default since its base version."""

    name: str
    kind: str
    base_version: str | None
    base_available: bool
    delta_mine: str
    delta_upgrade: str


class OverrideDiff(DTO):
    """The overrides diffed, and a message for each broken one."""

    items: list[OverrideDiffRow]
    errors: list[str]
    failed: bool


class OverrideScaffoldRequest(DTO):
    """Copy the bundled default of the override *kind* *name* into ``.overrides/``; *force*
    overwrites one that exists."""

    kind: str
    name: str
    force: bool = False


class OverrideFile(DTO):
    """An override's kind, name and file."""

    kind: str
    name: str
    path: str


class ScaffoldedOverride(DTO):
    """The override written, and whether it starts from the current definition (a role's
    commented fields) rather than an empty one."""

    entry: OverrideFile
    prefilled: bool


class OverrideUpdateRequest(DTO):
    """Re-stamp one override, or every valid one when *kind* is not given."""

    kind: str | None = None
    name: str | None = None


class StampedOverrides(DTO):
    """The overrides re-stamped, the version they now carry, and a message for each one that
    could not be read."""

    stamped: list[str]
    version: str
    errors: list[str]
