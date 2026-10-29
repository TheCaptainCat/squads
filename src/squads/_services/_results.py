"""Result dataclasses returned by the service layer."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from squads._discussion import Comment
from squads._errors import InvalidIdError
from squads._index._reconcile import ReconcileResult
from squads._migrations._registry import Migration
from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._models._omission import Omission
from squads._models._subentity import SubEntity
from squads._paths import SquadPaths, number_for_id
from squads._services._duplicate_ids import LeftReference, MovedFile
from squads._services._retirement import Severance

#: What a tree surface prints beside a root it invented for a parent cycle (see
#: ``TreeNode.anchor``), shared by every terminal renderer: the root is not a hierarchy anyone
#: wrote, and the full edge set lives elsewhere, since a tree drops the closing edge.
TREE_ANCHOR_MARKER = "[cycle anchor — not a real root; see sq check]"


@dataclass(frozen=True)
class TreeNode:
    """One node in the hierarchy returned by ``ServiceCore.tree_view()``. ``path_only=True`` marks
    an ancestor kept only to anchor a descendant match (dimmed in rendering, not serialised in
    ``--json``). ``anchor=True`` marks a root the bare tree chose for an item on a parent cycle, a
    tiebreak that both the terminal rendering and ``--json`` must disclose; it is never set on an
    explicitly rooted tree. The flags are independent and can both be true.
    """

    item: Item
    path_only: bool  # True = ancestor kept only to anchor a descendant match
    children: list[TreeNode] = field(default_factory=lambda: list[TreeNode]())
    anchor: bool = False  # True = a root invented to reveal a parent cycle


@dataclass(frozen=True)
class GraphNode:
    """One node in the ego-centric ref graph from ``RefsMixin.graph()``. ``edge_kind`` is the
    declared kind key that reached it (``None`` for the root), both dependency spellings normalized
    to one; ``edge_semantic`` is the kind's declared role (``"dependency"``, ``"preload"``,
    ``"supersession"``) or ``None`` for the root, a navigational or an undeclared kind, and
    consumers branch on it. For a dependency, ``direction="out"`` means this node is the blocker and
    ``"in"`` the dependent. ``seen=True`` marks a revisit, not recursed into.
    """

    id: str
    type: str
    status: str  # spec-defined status name
    priority: str | None  # the priority badge code, or None; ``badges`` below is the generic
    #: map, since a type on a different or renamed badge axis leaves ``priority`` null.
    assignee: str | None
    edge_kind: str | None  # None for root; the stored kind's spelling for all other nodes
    # (declared or not — an undeclared kind still traverses, see edge_semantic below)
    edge_semantic: str | None  # the edge kind's declared role, or None (root / navigational)
    direction: str | None  # "out" | "in" | None (None for root)
    seen: bool
    badges: dict[str, str] = field(default_factory=lambda: dict[str, str]())
    """Every spec-declared badge field this node's type carries, keyed by field code (e.g.
    ``{"priority": "high"}``, or ``{"impact": "high", "urgency": "low"}`` for a custom axis) —
    generic over the type's actual vocabulary, unlike the fixed ``priority`` attribute above."""
    children: list[GraphNode] = field(default_factory=lambda: list[GraphNode]())


@dataclass
class CreateResult:
    item: Item
    path: Path
    lane_warning: str | None = None


class SelfRemedied(str):
    """A report line that already carries the one remedy that works, so a caller appends no
    generic tail to it."""


@dataclass
class CheckIssue:
    level: str  # "error" | "warn"
    item: str  # item id or filename ("" if global)
    message: str
    rule: str  # the check that produced it: a validator name or a binding rule


def check_issue_sort_key(issue: CheckIssue) -> tuple[int, int, int, str]:
    """The total order every list of findings is printed in. Squad-global and no-item issues (an
    unresolvable ``item``: a filename, ``""``, ``"workflow"``) form a leading block; item-attached
    issues then sort by sequence number, error before warn, then message. Any remaining tie
    keeps its original relative order."""
    seq: int | None = None
    if issue.item:
        try:
            seq = number_for_id(issue.item)
        except InvalidIdError:
            seq = None
    has_item = 0 if seq is None else 1
    level_rank = 0 if issue.level == "error" else 1
    return (has_item, seq or 0, level_rank, issue.message)


@dataclass
class BlockResult:
    """Where a scaffolded story/subtask/finding block's body lives."""

    local_id: str
    path: Path
    body_tag: str
    start_line: int | None
    end_line: int | None
    title_advisory: str | None = None
    body_command: str = ""


@dataclass
class SubentityDetail:
    """A sub-entity's full detail for `sq <kind> show`: state + body + discussion."""

    info: SubEntity
    body: str
    discussion: str
    comments: list[Comment] = field(default_factory=list[Comment])
    #: The title of the item named by ``info.deferred_to``; ``None`` when none resolves.
    carrier_title: str | None = None


@dataclass
class InitResult:
    paths: SquadPaths
    roles: list[Item]
    # WARN-only notices from the backend scaffold and managed-write pass (unmanaged content in a
    # CLAUDE.md/AGENTS.md, candidate orphan files). They never gate the run; the CLI only prints
    # them.
    warnings: list[str] = field(default_factory=list[str])


@dataclass
class AdoptResult:
    """Outcome of ``adopt()``. ``repair`` is the :class:`RepairResult` of the import sweep over the
    adopted folder, carried out whole because that sweep rewrites the content of the files it
    imports and no migration will ever report it.
    """

    paths: SquadPaths
    repair: RepairResult
    roles: list[Item]  # roles newly activated
    warnings: list[str] = field(default_factory=list[str])

    @property
    def imported(self) -> int:
        """How many items the folder yielded — the sweep's own index, not a second count."""
        return len(self.repair.db.items)


@dataclass(frozen=True)
class RetypeResult:
    """Outcome of ``Service.retype()``."""

    item: Item
    old_id: str
    old_type: str  # for display
    status_reset: bool
    old_status: str  # spec-defined status name (meaningful only when status_reset is True)
    rewritten: list[str]  # paths of files whose text was updated (relative display names)


@dataclass(frozen=True)
class RenameResult:
    """Outcome of ``Service.rename_type()``."""

    renamed: int  # count of items moved from old_type to new_type
    ids: list[tuple[str, str]]  # (old_id, new_id) pairs, one per renamed item
    rewritten: list[str]  # paths of files whose text was updated (relative display names)


@dataclass(frozen=True)
class RemoveResult:
    """Outcome of ``Service.remove_work_item()``.

    ``removed_id`` is the formatted ID of the deleted item.
    ``severed_refs`` lists the IDs of referrer items whose forward refs were severed (``--force``).
    The ``op=remove`` reflog entry with the gone-item snapshot is appended post-commit.
    """

    removed_id: str
    severed_refs: list[str]  # referrer IDs whose ref to removed_id was deleted


def strip_notice(stripped: Sequence[str]) -> str | None:
    """The one-line announcement of the content diff a corpus sweep produced, ``None`` when it
    rewrote nothing. ``sq repair``, ``sq migrate up``, ``sq adopt`` and ``sq renumber`` all reach
    the sweep, so one constructor keeps their wording identical; a sweep-reaching result exposes it
    as ``strip_notice()`` over its own ``stripped`` list.
    """
    if not stripped:
        return None
    n = len(stripped)
    return (
        f"stripped retired regions from {n} item {'file' if n == 1 else 'files'} — review the diff"
    )


@dataclass
class RepairResult:
    """Outcome of ``Service.repair()``. ``missing_ids`` are indexed ids whose files are gone.
    ``unreadable`` has one message per file that could not be read or parsed; its previous entry is
    carried forward stale, so it is not in ``missing_ids``. ``canonicalized`` and ``stripped`` list
    items whose files were rewritten for a ref encoding or a retired region, content changes
    reported rather than discovered; an item can be in both.
    """

    db: SquadsDB
    missing_ids: list[str] = field(default_factory=list[str])
    unreadable: list[str] = field(default_factory=list[str])
    canonicalized: list[str] = field(default_factory=list[str])
    stripped: list[str] = field(default_factory=list[str])
    renumbered: list[MovedFile] = field(default_factory=list[MovedFile])
    references: list[LeftReference] = field(default_factory=list[LeftReference])

    @property
    def references_left(self) -> bool:
        """Whether a renumber left references to an old id for a hand check."""
        return bool(self.references)

    def strip_notice(self) -> str | None:
        """This sweep's announcement — see :func:`strip_notice`, the shared constructor."""
        return strip_notice(self.stripped)


class SyncSkips(list[str]):
    """``MaintenanceMixin.sync()``'s return value: the deduplicated skip/notice messages, usable as
    a plain ``list[str]``. Body-tag convergence never declines a region, so it adds none.
    """


@dataclass(frozen=True)
class MigrationRun:
    """Outcome of ``Service.run_pending_migrations()``. ``applied`` are the migrations run, in
    order; ``changed``, ``skipped`` and ``reports`` are keyed by each migration's ``to_schema``.
    ``repair`` is the rebuild after the runners and ``reconcile`` the one before the first, both
    ``None`` exactly when nothing applied. ``config_dropped`` names ``.squads.toml`` keys a
    regeneration left out because the config model does not carry them.
    """

    applied: list[Migration]
    changed: dict[str, int] = field(default_factory=lambda: dict[str, int]())
    skipped: dict[str, list[str]] = field(default_factory=lambda: dict[str, list[str]]())
    reports: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: dict[str, tuple[str, ...]]()
    )
    repair: RepairResult | None = None
    reconcile: ReconcileResult | None = None
    config_dropped: tuple[str, ...] = ()


@dataclass
class RenumberResult:
    """Outcome of ``Service.renumber()``. ``remap`` maps each shifted item's old display id to its
    new one (empty when nothing shifted); ``db`` is the rebuilt index with the counter at the new
    maximum. ``warning`` is set on the ``--by`` path, where only the operator can guarantee the
    shift clears the other branch's counter. ``stripped`` names items the rebuild also rewrote to
    remove a retired region.
    """

    remap: dict[str, str]
    db: SquadsDB
    warning: str | None = None
    stripped: list[str] = field(default_factory=list[str])

    def strip_notice(self) -> str | None:
        """This sweep's announcement — see :func:`strip_notice`, the shared constructor."""
        return strip_notice(self.stripped)


@dataclass
class WorkloadRow:
    """Per-assignee work counts for `sq workload` (``None`` assignee = unassigned).
    ``open``/``closed``/``total`` count items only;
    ``subentity_open``/``subentity_closed``/``subentity_total`` separately count the assignee's sub-
    entity assignments, never folded into the item counts.
    """

    assignee: str | None
    open: int
    closed: int
    total: int
    subentity_open: int = 0
    subentity_closed: int = 0
    subentity_total: int = 0


@dataclass(frozen=True)
class MineRow:
    """One `sq mine` match: the item plus every sub-entity of it assigned to the same slug.

    ``matched_subentities`` lists *every* sub-entity of ``item`` assigned to the queried
    slug, regardless of status — the visibility predicate decides whether the row is
    returned at all, not what this list contains (a caller can always see the full set of
    reasons a row is theirs).
    """

    item: Item
    matched_subentities: list[SubEntity]


@dataclass(frozen=True)
class InboxLine:
    """One matched line in `sq inbox`: the stripped text plus the sub-entity region it falls in
    (``"<kind>:<local_id>"`` or ``"<kind>:<local_id>:discussion#<n>"``), ``None`` for any item-level
    mention. Narrower than `search`'s region vocabulary, which it collapses to ``None``.
    """

    text: str
    region: str | None
    hash: str | None = None
    """The full hash of the comment the line is in, when it is in one."""


@dataclass(frozen=True)
class InboxHit:
    """One `sq inbox` match: the item plus each matching line and its region attribution."""

    item: Item
    lines: list[InboxLine]


@dataclass(frozen=True)
class SearchHit:
    """One matching line within an item. ``region`` is the machine-stable locator: ``"title"``,
    ``"description"``, ``"body"``, ``"discussion"`` or ``"discussion#<n>"``, or a sub-entity
    (``"<kind>:<local_id>"`` or ``"<kind>:<local_id>:discussion#<n>"``). ``location`` is the human
    spelling and ``snippet`` the text around the match.
    """

    region: str
    location: str
    snippet: str
    hash: str | None = None
    """The full hash of the comment the hit landed in, when it did."""


@dataclass(frozen=True)
class SearchResult:
    """One item matching a :meth:`squads._services._collab.CollabMixin.search` query."""

    item: Item
    hits: list[SearchHit]


#: One :class:`~squads._models._omission.Omission` per item file a corpus-walking read skipped,
#: returned alongside the results: one unreadable file degrades that file, never the answer. A
#: usable-but-short result is paired with exit code ``4``.
type UnreadableItems = list[Omission]


@dataclass(frozen=True)
class ImportIssue:
    """One validate-first pre-pass problem (bulk import): a line number plus a
    human message. The pre-pass collects every one of these across the whole file — it never
    stops at the first."""

    line: int
    message: str


@dataclass
class ImportOpCount:
    """Per-op-name event counts, in first-seen order (``dict`` insertion order is stable) —
    what both ``--dry-run`` and the real apply report alongside the handle plan."""

    counts: dict[str, int] = field(default_factory=lambda: dict[str, int]())

    def bump(self, op: str) -> None:
        self.counts[op] = self.counts.get(op, 0) + 1


@dataclass
class ImportPlan:
    """The validate-first pre-pass result: what a bulk import checks before writing anything.

    Writes nothing — ``handle_to_id``/``handle_to_sub`` is the *projected* allocation plan (a
    simulated counter bump, never the real one); ``issues`` is the ordered, line-numbered error
    list. ``ok`` (no issues) is what gates whether apply may proceed; a non-empty ``issues`` is
    exactly what ``--dry-run`` prints instead of applying.
    """

    op_counts: ImportOpCount
    handle_to_id: dict[str, str]
    handle_to_sub: dict[str, tuple[str, str]]
    issues: list[ImportIssue] = field(default_factory=list[ImportIssue])

    @property
    def ok(self) -> bool:
        return not self.issues


@dataclass
class ImportApplyResult:
    """The outcome of a bulk import's apply pass. ``findings`` carries, level intact, every ``sq
    check`` catalog issue landing on an item the import touched, so the CLI can render them and pick
    an exit code. ``warnings`` is the human-readable warn-level stream: the apply pass's own
    advisories followed by the warn-level findings as ``"<item>: <message>"``; error-level findings
    are only in ``findings`` and earn the non-zero exit.
    """

    op_counts: ImportOpCount
    handle_to_id: dict[str, str]
    handle_to_sub: dict[str, tuple[str, str]]
    created_ids: list[str] = field(default_factory=list[str])
    warnings: list[str] = field(default_factory=list[str])
    findings: list[CheckIssue] = field(default_factory=list[CheckIssue])

    @property
    def error_findings(self) -> list[CheckIssue]:
        """The error-level half of ``findings``, in the order the catalog reported them."""
        return [f for f in self.findings if f.level == "error"]


@dataclass
class ImportResult:
    """The top-level result of :meth:`~squads._services._import.ImportMixin.import_events`.

    ``plan`` is always populated (the pre-pass always runs first). ``applied`` is ``None``
    whenever the pre-pass found any issue, or the caller asked for ``dry_run`` — either way,
    nothing was written.
    """

    plan: ImportPlan
    applied: ImportApplyResult | None = None


@dataclass
class ReflogEntry:
    """One parsed reflog line, surfaced by ``sq reflog``. ``delta`` is a free-form ``dict`` whose
    shape depends on ``op``, and ``v`` carries the schema version. ``session_id`` and
    ``parent_session_id`` are ``None`` when the entry records no lineage; they are best-effort and
    untrusted, read from optional env vars, and never an authorisation input.
    """

    v: str
    ts: str
    actor: str
    op: str
    target: str
    delta: dict[str, Any]
    session_id: str | None = None
    parent_session_id: str | None = None


@dataclass(frozen=True)
class RosterRemoval:
    """Outcome of ``Service.remove_item()``: the removed entry and the board-hygiene warnings
    that warn without refusing (open assigned work, a lost default-role designation)."""

    item: Item
    warnings: list[str]


@dataclass(frozen=True)
class RosterStatusResult:
    """Outcome of ``Service.set_roster_status()`` — the roster ``status`` verb's richer
    counterpart to the generic ``Service.set_status()``, carrying what only a roster transition
    can produce: the edges ``--unlink`` severed (empty when the flag was not passed, or a
    reported no-op when it found nothing severable) and any board-hygiene warnings (open
    assigned work on a retiring role/operator) that warn without refusing.
    """

    item: Item
    severed: list[Severance]
    warnings: list[str]


@dataclass(frozen=True)
class RoleUpdateResult:
    """Outcome of ``Service.update_role()``: the role, and the notices the update raised (a
    per-slug file that also sets a field the update wrote)."""

    item: Item
    warnings: list[str]


@dataclass(frozen=True)
class DefaultRoleMoveResult:
    """Outcome of ``Service.set_default_role()``. ``item`` is the role now carrying the designation,
    ``cleared`` the ids of every other role whose ``is_default`` was cleared in the same
    transaction, and ``changed`` is ``False`` only when *item* already was the sole holder (a
    reported no-op).
    """

    item: Item
    cleared: list[str]
    changed: bool


@dataclass(frozen=True)
class FoundComment:
    """The comment a hash prefix addresses: its item, discussion scope (``""`` for the item's
    own, ``<kind>:<local_id>`` for a sub-entity's), the duplicate group in file order and the
    group's displayed hash."""

    item: Item
    scope: str
    group: list[Comment]
    shown: str


@dataclass(frozen=True)
class EditedComment:
    """The outcome of ``comment <hash> edit``: the comment before, the one now stored, and whether
    anything was written.
    """

    item: Item
    scope: str
    old: Comment
    old_shown: str
    new: Comment
    new_shown: str
    changed: bool


@dataclass(frozen=True)
class RemovedComments:
    """The outcome of ``comment <hash> remove``: every member of the group, as they were."""

    item: Item
    scope: str
    removed: list[Comment]
    shown: str
