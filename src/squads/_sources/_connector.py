"""The connector interface and the records a connector returns. A record carries what the tracker
says, in the tracker's own words; mapping it onto squad vocabulary is the compiler's job."""

from abc import ABC, abstractmethod
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from squads._sources._probes import Expected, Family, ProbeResult
    from squads._sources._spec import SourceScope


#: The side of an issue that holds its labels, and the side that holds its issue type.
LABELS = "labels"
TYPE = "type"
#: The sides only the status map reads: the tracker's own state, Jira's status name and its
#: status category.
STATE_SIDE = "state"
STATUS_SIDE = "status"
CATEGORY_SIDE = "category"


class RestrictedIssueError(Exception):
    """An issue the tracker marks restricted (confidential, or under a security level): squads
    treats it as not returned. ``issue_id`` is the ID it would have, or empty when unknown."""

    def __init__(self, issue_id: str = "") -> None:
        super().__init__(issue_id)
        self.issue_id = issue_id


@dataclass(frozen=True)
class Reference:
    """One tracker reference found in a text: its character span and the full key it names."""

    start: int
    end: int
    key: str


@dataclass(frozen=True)
class Issue:
    """One tracker issue as the tracker reports it."""

    id: str
    key: str
    title: str
    description: str
    state: str
    updated_at: str
    author_id: str
    author_handle: str
    labels: tuple[str, ...] = ()
    #: ``(side, value)`` for each side besides the labels that the issue has a value on.
    sides: tuple[tuple[str, str], ...] = ()
    #: Opaque values the connector needs again to fetch this issue's comments and links.
    locator: tuple[tuple[str, str], ...] = ()

    def values(self, side: str) -> tuple[str, ...]:
        """The values the issue has on *side*: its labels, or the one value of another side."""
        if side == LABELS:
            return self.labels
        return tuple(value for name, value in self.sides if name == side and value)


@dataclass(frozen=True)
class Comment:
    """One tracker comment: a human note, never a system note."""

    id: str
    body: str
    author_id: str
    author_handle: str
    author_name: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Link:
    """One link from an issue to another, with the tracker's own name for the link type as read
    from this issue and the name the other issue reads it by (empty when the tracker names none)."""

    link_type: str
    target_id: str
    target_key: str
    inverse: str = ""


@dataclass(frozen=True)
class FetchedIssue:
    """An issue with the comments and links the pull needs for it."""

    issue: Issue
    comments: tuple[Comment, ...] = ()
    links: tuple[Link, ...] = ()


@dataclass(frozen=True)
class SourceFetch:
    """What the fetch phase brings back for one source.

    ``changed`` holds the issues fetched in detail (a selected issue no item holds, or one an item
    holds whose listed ``updated_at`` or state differs from the stored one), ``untouched`` counts
    the held issues that needed nothing, ``listed`` the IDs of every issue of the scope (closed
    included), and ``linked`` the one-off fetch of each held item the listing lacks: ``None`` for
    an issue the tracker no longer returns.
    """

    changed: tuple[FetchedIssue, ...] = ()
    untouched: int = 0
    listed: frozenset[str] = frozenset()
    linked: dict[str, FetchedIssue | None] = field(
        default_factory=lambda: dict[str, FetchedIssue | None]()
    )
    #: One line for each listed issue the tracker stopped returning while it was read.
    skipped: tuple[str, ...] = ()
    #: How many restricted issues the listing dropped that no item holds.
    restricted: int = 0
    #: How many unheld listed issues the filter rejected, and how many accepted ones map to no type.
    filtered_out: int = 0
    skipped_no_type: int = 0
    #: How many unheld listed issues an item of another source of the tracker holds.
    held_elsewhere: int = 0


class Connector(ABC):
    """What the pull, handle resolution and reference translation ask of one tracker."""

    #: The fields of the credential entry this connector reads, in the order they are asked for.
    credential_fields: tuple[str, ...]

    #: How many restricted issues the last :meth:`listing` dropped, and their IDs.
    restricted: int = 0
    restricted_ids: frozenset[str] = frozenset()

    @abstractmethod
    def __init__(self, base_url: str, scope: SourceScope, credential: Mapping[str, str]) -> None:
        """A connector for the tracker at *base_url*, reading the issues of *scope*."""

    @abstractmethod
    def listing(self) -> list[Issue]:
        """Every unrestricted issue of the scope, closed ones included, with its tracker
        ``updated_at``; the restricted ones are counted in :attr:`restricted`."""

    @abstractmethod
    def issue(self, issue_id: str, key: str) -> Issue | None:
        """One issue, found by the connector from its immutable ID and last known *key*, or
        ``None`` when the tracker does not return it to this credential."""

    @abstractmethod
    def in_scope(self, issue: Issue) -> bool:
        """Whether *issue* belongs to the scope, decided without listing it: from its key where
        the key names its container, with one search where it does not."""

    @abstractmethod
    def lookup(self, reference: str) -> Issue | None:
        """The issue a person names by its key or its immutable ID, or ``None`` when the tracker
        does not return one to this credential."""

    @abstractmethod
    def comments(self, issue: Issue) -> list[Comment]:
        """The human comments of *issue*, oldest first."""

    @abstractmethod
    def links(self, issue: Issue) -> list[Link]:
        """The links from *issue* to other issues."""

    @abstractmethod
    def issue_url(self, key: str) -> str:
        """The web address of the issue named by *key*."""

    @abstractmethod
    def user_url(self, handle: str) -> str:
        """The web address of the user named by *handle*."""

    @abstractmethod
    def resolve_handle(self, handle: str) -> str | None:
        """The immutable user ID behind *handle*, or ``None`` when no user has it."""

    @abstractmethod
    def references(self, text: str, host_key: str) -> list[Reference]:
        """Every tracker reference in *text*, qualified against *host_key*. Pure: no network."""

    @abstractmethod
    def probes(self, family: Family, expected: Expected) -> Iterator[ProbeResult]:
        """The checks of one *family* for ``sq source check``, each yielded as it is made so the
        runner can stop at the first blocking access failure."""
