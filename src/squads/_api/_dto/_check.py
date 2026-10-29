"""The check DTOs: the squad's lint report, in its stable order, and the managed files a sync
regenerates."""

from squads._api._dto._base import DTO


class CheckRequest(DTO):
    """Lint the squad."""


class CheckIssueRow(DTO):
    """One finding: its level, the item or file it is about, its message and the rule that
    produced it."""

    level: str
    item: str
    message: str
    rule: str


class CheckReport(DTO):
    """Every finding, and how many are errors, which make the command exit 3."""

    items: list[CheckIssueRow]
    errors: int


class SyncRequest(DTO):
    """Regenerate the managed files to this squads version."""


class SyncReport(DTO):
    """What the regeneration left alone, one notice each."""

    skipped: list[str]
