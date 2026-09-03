"""Result dataclasses returned by the service layer."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from squads._migrations._registry import Migration
from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._models._subentity import SubEntity
from squads._paths import SquadPaths
from squads._services._retirement import Severance

#: What a tree surface prints beside a root it invented to reveal a parent cycle (see
#: ``TreeNode.anchor``). One wording, shared by every terminal renderer, so the disclosure reads
#: the same everywhere. It has to stop a reader concluding this is the top of a hierarchy
#: somebody wrote, and point at where the full edge set lives — a tree drawing of a cycle must
#: drop the edge closing back to the anchor, so the tree under-reports the relation it draws.
TREE_ANCHOR_MARKER = "[cycle anchor — not a real root; see sq check]"


@dataclass(frozen=True)
class TreeNode:
    """One node in the filtered/pruned hierarchy returned by ``ServiceCore.tree_view()``.

    ``path_only=True`` marks an ancestor that is kept solely to anchor a descendant match —
    it did not itself pass the ``ItemFilter``.  This flag drives dimmed rendering at the CLI
    edge; it is **not** serialised in ``--json`` output (path-only ancestors appear as
    ordinary nodes in JSON consumers).

    ``anchor=True`` marks a root the bare tree chose for itself: the item is on a parent cycle,
    so it has a parent and no forest of parentless items would ever have rooted at it.  Every
    member of that cycle is an equally good root, which makes the choice a tiebreak rather than
    a truth — a fabrication, acceptable only because it is disclosed.  Both surfaces must
    therefore say so (a marker in the terminal rendering, a field in ``--json``); a consumer
    that ignores the flag renders an invented root as one somebody wrote.  Never set on an
    explicitly rooted tree, where the root is the caller's own choice.

    The two flags are **independent and can both be true**: under a filter matching something
    below the cycle, the members enter the keep set as ancestors, so the chosen anchor is a
    path-only node as well.  Render them as combining states, not alternatives.

    ``children`` lists the surviving child nodes after filter + depth pruning.
    """

    item: Item
    path_only: bool  # True = ancestor kept only to anchor a descendant match
    children: list[TreeNode] = field(default_factory=lambda: list[TreeNode]())
    anchor: bool = False  # True = a root invented to reveal a parent cycle


@dataclass(frozen=True)
class GraphNode:
    """One node in the ego-centric ref graph returned by ``RefsMixin.graph()``.

    Two fields describe the edge that reached this node, or ``None``/``None`` for the root —
    each answers a different question, and a consumer wanting to know *what kind of thing* an
    edge is (a dependency, worth following for "what's blocking this") branches on
    ``edge_semantic``, never ``edge_kind``:

    - ``edge_kind`` is the **declared kind key** — a project's own spelling, never a fixed
      sentinel. Both raw spellings of a dependency edge normalize to one declared key: the
      kind carrying the ``dependency`` semantic in the DEPENDENT direction, or the
      BLOCKER-direction kind when a project declares only that half
      (:meth:`~squads._workflow._models.WorkflowSpec.canonical_dependency_ref_kind`). Every
      other kind keeps its own literal key.
    - ``edge_semantic`` is the edge kind's **declared semantic role** (``"dependency"``,
      ``"preload"``, ``"supersession"``), or ``None`` for the root, for a navigational kind
      (declared, no role), **or for a kind the merged spec does not declare at all** — an
      undeclared-kind edge still traverses and is still emitted (never silently dropped); only
      ``edge_kind``'s stored spelling distinguishes it from a navigational one, since both
      report ``edge_semantic=None``. This is the field a consumer branches on: testing
      ``edge_kind == "depends-on"`` breaks the moment a project renames its dependency kind,
      the exact declared-but-found-by-literal defect this decision removes from the engine
      itself.

    ``direction`` disambiguates a dependency edge's two ends:

    - ``edge_semantic="dependency"``, ``direction="out"`` → this node is the blocker; the
      expanded item depends on it → display label "depends on"
    - ``edge_semantic="dependency"``, ``direction="in"`` → this node is the dependent; the
      expanded item is required by it → display label "required by"

    For a navigational kind the label is the kind name; ``direction`` records the traversal
    direction for callers that care.

    ``seen=True`` marks a node that was already emitted higher in the tree; the traversal does
    not recurse into it (cycle / breadth-first revisit termination).

    ``children`` is empty when ``seen=True`` or when the depth limit was reached.
    """

    id: str
    type: str
    status: str  # spec-defined status name
    priority: str | None  # the priority badge code, or None — kept for the CLI's bundled-axis
    #: rendering (``_cli/_main.py``); ``badges`` below is the generic replacement for --json
    #: consumers, since a type on a different/renamed badge axis leaves ``priority`` null.
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

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict (for ``--json`` output)."""
        return {
            "id": self.id,
            "type": self.type,
            "status": self.status,
            "priority": self.priority,
            "badges": self.badges,
            "assignee": self.assignee,
            "edge_kind": self.edge_kind,
            "edge_semantic": self.edge_semantic,
            "direction": self.direction,
            "seen": self.seen,
            "children": [c.to_dict() for c in self.children],
        }


@dataclass
class CreateResult:
    item: Item
    path: Path
    lane_warning: str | None = None


@dataclass
class CheckIssue:
    level: str  # "error" | "warn"
    item: str  # item id or filename ("" if global)
    message: str


@dataclass
class BlockResult:
    """Where a scaffolded story/subtask/finding block's body lives."""

    local_id: str
    path: Path
    body_tag: str
    start_line: int | None
    end_line: int | None
    title_advisory: str | None = None


@dataclass
class SubentityDetail:
    """A sub-entity's full detail for `sq <kind> show`: state + body + discussion."""

    info: SubEntity
    body: str
    discussion: str


@dataclass
class InitResult:
    paths: SquadPaths
    roles: list[Item]
    # WARN-only board-debt-shaped notices from the backend scaffold/managed-write pass — a
    # pre-existing CLAUDE.md/AGENTS.md with unmanaged content, or a candidate orphan
    # pointer/skill file this run did not generate. Never gates the run; the CLI only prints
    # these.
    warnings: list[str] = field(default_factory=list[str])


@dataclass
class AdoptResult:
    """Outcome of ``adopt()``.

    ``repair`` is the :class:`RepairResult` of the import sweep adopt runs over the folder it
    is adopting. It is carried out rather than reduced to a count because that sweep is also
    the corpus sweep: adopt rewrites the content of the very files it is importing, and this
    is the population with no other route — an existing folder of squads-native markdown
    reaching sq for the first time never runs a migration.
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
    """The one-line announcement of the content diff a corpus sweep produced — ``None`` when it
    rewrote nothing.

    Built here rather than at any call site because **four** commands reach the sweep and all
    four owe the operator the same sentence: ``sq repair`` runs it directly, ``sq migrate up``
    runs it as the tail of the migration, ``sq adopt`` runs it to import an existing folder,
    and ``sq renumber`` reaches it through the shared index rebuild. The announcement is the
    whole mitigation for verbs whose advertised job is the index rewriting content, so a route
    that reached the sweep and said nothing would leave the diff to be discovered rather than
    stated. One constructor is what keeps them from drifting into different wording, or into
    one of them being forgotten again — the two that were.

    Every result a sweep-reaching command returns therefore exposes it as ``strip_notice()``,
    reading its own ``stripped`` list; a new such command wires its result to this function
    rather than phrasing the sentence again.
    """
    if not stripped:
        return None
    n = len(stripped)
    return (
        f"stripped retired regions from {n} item {'file' if n == 1 else 'files'} — review the diff"
    )


@dataclass
class RepairResult:
    """Outcome of ``Service.repair()``.

    ``missing_ids`` holds item IDs that were present in the index *before* repair but whose
    markdown files could not be found on disk — a deletion event worth surfacing to the operator.

    ``unreadable`` holds one message per file whose content could not be read or parsed during
    the rebuild — a merge conflict, invalid UTF-8, an OS permission error. Distinct from
    ``missing_ids``: an unreadable file's *previous* index entry (when one exists) is carried
    forward unchanged rather than dropped, so its item stays resolvable and never appears in
    ``missing_ids`` — only in this list, naming the file so the operator knows the carried
    entry is stale until the file is fixed.

    ``canonicalized`` holds the ID of every item whose file was rewritten because its on-disk
    ref encoding (a legacy ``extra.ref_kinds`` map, or a spelled ref that folds to a different
    literal) differed from the folded frontmatter now stored — the file, not only the index,
    made canonical. Empty when the corpus needed no correction; a corpus already canonical
    triggers no write at all.

    ``stripped`` holds the ID of every item whose file was rewritten because it still stored a
    retired region — a derived rendering whose writer has retired and whose replacement is
    computed on every read. Repair's advertised job is the index, and this is content: the
    operator who ran it to reconcile an index gets a content diff they did not ask for, so it
    is reported here (and in the reflog delta) to be stated rather than discovered. Empty on a
    corpus that carries none, which writes no file at all. An item can appear in both this
    list and ``canonicalized``: a file needing both corrections gets both, in one write.
    """

    db: SquadsDB
    missing_ids: list[str] = field(default_factory=list[str])
    unreadable: list[str] = field(default_factory=list[str])
    canonicalized: list[str] = field(default_factory=list[str])
    stripped: list[str] = field(default_factory=list[str])

    def strip_notice(self) -> str | None:
        """This sweep's announcement — see :func:`strip_notice`, the shared constructor."""
        return strip_notice(self.stripped)


@dataclass(frozen=True)
class MigrationRun:
    """Outcome of ``Service.run_pending_migrations()`` — what ``sq migrate up`` reports.

    ``applied`` holds the :class:`~squads._migrations._registry.Migration` records that ran, in
    order, and is empty when the squad was already at the current stamp.

    ``repair`` is the :class:`RepairResult` of the rebuild that follows the runners, and is
    ``None`` exactly when ``applied`` is empty (no runner applies, so nothing rebuilds). It is
    carried out of the service rather than discarded because the rebuild is also the corpus
    sweep: on this route the operator gets a content diff from a command whose own output
    otherwise says only "index rebuilt", and the migration is the only route a squad behind the
    current schema takes.
    """

    applied: list[Migration]
    repair: RepairResult | None = None


@dataclass
class RenumberResult:
    """Outcome of ``Service.renumber()`` — the pre-merge block-shift verb.

    ``remap`` maps each shifted item's old (unpadded) display id to its new one; empty when
    no local item had ``sequence_id >= from_seq`` (nothing to shift). ``db`` is the rebuilt
    index reflecting the shift, including the counter bumped to the new post-shift maximum.
    ``warning`` is set on the ``--by`` (no ``--onto``) path: sq cannot certify the shift
    clears the *other* branch's counter without it — that guarantee is the operator's.

    ``stripped`` names every item whose file the shift's index rebuild also rewrote to remove a
    retired region — the same corpus sweep ``repair`` reports, reached here through the shared
    rebuild. Empty on the no-op path, where nothing shifts and no rebuild runs.
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
    """Per-assignee work counts for `sq workload` (None assignee = unassigned).

    ``open``/``closed``/``total`` count **items** only, exactly as published before
    sub-entity assignments were counted at all. ``subentity_open``/``subentity_closed``/
    ``subentity_total`` are separate, additive counts of that assignee's sub-entity
    (story/subtask/finding) assignments — never folded into the item counts, so an actor
    owning both a parent item and one of its sub-entities is counted once in each set.
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
    """One matched line in `sq inbox`: the raw stripped text plus the sub-entity region it
    falls in, when any — ``None`` for an item-level mention (in the item's own body/
    discussion, or anywhere else outside a sub-entity's block), so the two are
    distinguishable. When set, ``region`` is spelled the same way `search` spells a sub-entity
    locator (``"<kind>:<local_id>"`` or ``"<kind>:<local_id>:discussion#<n>"``) — but this is
    narrower than `search`'s full vocabulary: every item-level region name `search` publishes
    (``body``, ``discussion``, ``discussion#<n>``, ``other``) collapses to ``None`` here,
    because sub-entity-vs-item is the only distinction `inbox` makes.
    """

    text: str
    region: str | None


@dataclass(frozen=True)
class InboxHit:
    """One `sq inbox` match: the item plus each matching line and its region attribution."""

    item: Item
    lines: list[InboxLine]


@dataclass(frozen=True)
class SearchHit:
    """One matching line within an item, located precisely enough to jump straight to it.

    ``region`` is the compact, machine-stable locator: ``"title"``, ``"description"``,
    ``"body"``, ``"discussion"`` (or ``"discussion#<n>"`` naming the *n*-th comment when the
    match falls inside one), or a named sub-entity (``"<kind>:<local_id>"`` for its
    heading/body, or ``"<kind>:<local_id>:discussion#<n>"`` for its *n*-th comment).
    ``location`` is the same thing spelled out for humans; ``snippet`` is in-context text
    around the match — not the bare stripped line.
    """

    region: str
    location: str
    snippet: str


@dataclass(frozen=True)
class SearchResult:
    """One item matching a :meth:`squads._services._collab.CollabMixin.search` query."""

    item: Item
    hits: list[SearchHit]


#: One human-readable message per item file a corpus-walking read had to skip — the same
#: skipped-file channel ``check``/``repair``/``board list``/``memory list`` already report on,
#: returned alongside the results rather than replacing them.
#:
#: The posture it encodes: **one unreadable file degrades that file, never the answer**. A
#: reader that lets the error propagate discards every result it had already accumulated from
#: files it *could* read, which is both less useful and less honest than naming the one file
#: and returning the rest — and it makes the failure look arbitrary next to ``list``/``tree``/
#: ``blocked``/``show``/``graph``, which walk the same corpus and are unaffected. Callers pair
#: this with a non-zero exit so a script still learns the answer was partial.
type UnreadableItems = list[str]


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
    exactly what ``--dry-run`` (a later task) prints instead of applying.
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
    """The real-apply outcome of a bulk import's single-transaction apply pass.

    ``findings`` carries, **with its level intact**, every issue the same catalog ``sq check``
    reports (unwritten sub-entity bodies, over-long titles, a stale sub-entity container, …)
    that lands on an item this import touched. Apply does not bypass the catalog, so these ride
    back for the CLI to render and to pick an exit code from. The level has to survive this far:
    it is the only thing that separates "tidy this up when you get to it" from a violation any
    gated door would have refused, and once it is dropped no output mode can recover it.

    ``warnings`` is the human-readable **warn-level** stream: the apply pass's own advisories
    (an over-long sub-entity title, an out-of-lane author) as they were raised, followed by the
    warn-level half of ``findings`` rendered as ``"<item>: <message>"``. Error-level findings are
    deliberately absent from it — they are reported through ``findings``, at their own level, and
    they are what earns the command a non-zero exit.
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
    """One parsed reflog line, surfaced by ``sq reflog``.

    The ``delta`` field is a free-form ``dict`` whose shape depends on ``op``; see
    the reflog schema documentation for the full field reference.  The ``v`` field
    carries the schema version so readers can handle future additions gracefully.

    ``session_id`` and ``parent_session_id`` are ``None`` for entries written before
    schema 0.4.  They record **best-effort, untrusted** lineage only — squads is a
    passive tool that reads optional env vars and records them; it does not mint,
    spawn, or verify.  Never use these fields as an authorisation input.

    Stability note: the *command shape* and the fields listed here are documented;
    the exact ``delta`` sub-fields are additive and evolve independently.
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
class DefaultRoleMoveResult:
    """Outcome of ``Service.set_default_role()`` — the ``is_default`` designation move: a move,
    not a set.

    ``item`` is the role now carrying the designation. ``cleared`` lists the ids of every
    *other* role whose ``is_default`` was found set and cleared in the same transaction — not
    just one, so re-running the move against a squad where two roles already carry the
    designation converges it to a single holder in one call. ``changed`` is ``False`` only
    when *item* already was the designation's sole holder and nothing else needed clearing —
    a reported no-op, not an error.
    """

    item: Item
    cleared: list[str]
    changed: bool
