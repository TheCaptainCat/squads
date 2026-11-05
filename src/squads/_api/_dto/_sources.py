"""The source DTOs: the credential verbs, which carry a secret in and never one out."""

from pydantic import Field

from squads._api._dto._base import DTO
from squads._api._dto._items import ItemAddress


class CredentialFieldsRequest(DTO):
    """Ask which fields the credential of *source* holds."""

    source: str


class CredentialFields(DTO):
    """The fields a credential for *source* is made of, in the order they are asked for."""

    source: str
    base_url: str
    fields: list[str]


class CredentialSetRequest(DTO):
    """Store *values*, one per field of the connector, as the credential of *source*."""

    source: str
    values: dict[str, str] = Field(repr=False)


class CredentialWritten(DTO):
    """A credential stored: which source, under which address, and the file that holds it."""

    source: str
    base_url: str
    fields: list[str]
    path: str


class CredentialRemoveRequest(DTO):
    """Delete the credential of *source*."""

    source: str


class CredentialRemoved(DTO):
    """A credential deleted, or ``removed`` false when there was none."""

    source: str
    base_url: str
    removed: bool


class SourcePullRequest(DTO):
    """Pull the issues of the source *name*, or of every enabled source when it is ``None``;
    *dry_run* stops after the checks and writes nothing."""

    name: str | None = None
    dry_run: bool = False


class SourcePullReport(DTO):
    """What a pull did for one source: the items it created, why it skipped the source if it did,
    and a line for every case worth reporting. Every issue the pull sees lands in exactly one
    counter (``created`` counts the issues it made items for), so the counters sum to the issues
    seen."""

    name: str
    created: list[str]
    #: Issues an item holds that the pull changed in at least one way; an issue two items of the
    #: source hold counts once.
    refreshed: int
    #: Issues an item holds that the pull wrote nothing for.
    unchanged: int
    left_out: str | None
    lines: list[str]
    #: Whether the source was left out because it failed its access probes.
    failed: bool = False
    #: Issues the squad refused every event for, so nothing was written; the next pull retries.
    dropped: int = 0
    #: Issues an item holds that the tracker neither lists nor returns by ID; the record is
    #: rewritten to state ``gone``.
    gone: int = 0
    #: Issues the listing dropped as restricted that no item holds.
    restricted: int = 0
    #: Issues an item of another source of the tracker holds, with no item of this source.
    held_elsewhere: int = 0
    #: Listed issues the filter rejects that no item of any source holds.
    filtered_out: int = 0
    #: Selected issues no item holds whose type map gives no type or two.
    skipped_no_type: int = 0


class SourcePulled(DTO):
    """The outcome of a pull, one report per source it looked at."""

    dry_run: bool
    sources: list[SourcePullReport]


class SourceRefreshRequest(ItemAddress):
    """Fetch the issue behind one item again and write what changed."""


class SourceRefreshed(DTO):
    """An item refreshed from its issue: whether anything changed, and a line for every case
    worth reporting."""

    id: str
    changed: bool
    lines: list[str]


class SourceUnlinkRequest(ItemAddress):
    """Cut an item from its issue."""


class SourceUnlinked(DTO):
    """An item cut from its issue: which source and key it left."""

    id: str
    source: str
    key: str


class SourceRelinkRequest(ItemAddress):
    """Attach an item a source created to the issue *issue* (a key or an immutable ID) of the
    source *source*, and refresh it."""

    source: str
    issue: str


class SourceRelinked(DTO):
    """An item attached to an issue: which source and key, and a line for every case worth
    reporting."""

    id: str
    source: str
    key: str
    lines: list[str]


class SourceListRequest(DTO):
    """List the sources the squad declares."""


class SourceRow(DTO):
    """One declared source: its connector, whether it is enabled, whether a credential is stored
    for it (never the value), how many items it holds and when the newest of them changed on the
    tracker."""

    name: str
    connector: str
    version: str
    enabled: bool
    credential: bool
    items: int
    newest_updated_at: str | None


class SourceListed(DTO):
    """The declared sources, by name."""

    sources: list[SourceRow]


class SourceCheckRequest(DTO):
    """Check the source *name*, or every declared source, disabled ones included, when it is
    ``None``."""

    name: str | None = None


class ProbeLine(DTO):
    """One probe's outcome: its family, a verdict of ``pass``, ``fail`` or ``warn``, what it found
    and, for a failure or a warning, the fix."""

    family: str
    verdict: str
    text: str
    fix: str


class SourceChecklist(DTO):
    """The checklist of one source; ``ok`` is false when any line is a blocking failure."""

    name: str
    connector: str
    version: str
    enabled: bool
    ok: bool
    lines: list[ProbeLine]


class SourceChecked(DTO):
    """The checklists of the sources checked; ``ok`` is false when any has a blocking failure."""

    ok: bool
    sources: list[SourceChecklist]
