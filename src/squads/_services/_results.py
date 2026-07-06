"""Result dataclasses returned by the service layer."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._models._subentity import SubEntity
from squads._paths import SquadPaths


@dataclass(frozen=True)
class TreeNode:
    """One node in the filtered/pruned hierarchy returned by ``ServiceCore.tree_view()``.

    ``path_only=True`` marks an ancestor that is kept solely to anchor a descendant match —
    it did not itself pass the ``ItemFilter``.  This flag drives dimmed rendering at the CLI
    edge; it is **not** serialised in ``--json`` output (path-only ancestors appear as
    ordinary nodes in JSON consumers).

    ``children`` lists the surviving child nodes after filter + depth pruning.
    """

    item: Item
    path_only: bool  # True = ancestor kept only to anchor a descendant match
    children: list[TreeNode] = field(default_factory=lambda: list[TreeNode]())


@dataclass(frozen=True)
class GraphNode:
    """One node in the ego-centric ref graph returned by ``RefsMixin.graph()``.

    ``edge_kind`` is the **normalized** kind of the edge that reached this node, or ``None``
    for the root.  Dependency edges are always stored as ``"depends-on"`` regardless of
    whether the on-disk edge was authored as ``depends-on`` or ``blocks``; ``direction``
    disambiguates the two ends:

    - ``edge_kind="depends-on"``, ``direction="out"`` → this node is the blocker; the
      expanded item depends on it → display label "depends on"
    - ``edge_kind="depends-on"``, ``direction="in"`` → this node is the dependent; the
      expanded item is required by it → display label "required by"

    For symmetric kinds (``related``, ``implements``, ``fixes``, ``addresses``, ``supersedes``,
    ``duplicates``) the label is the kind name; ``direction`` records the traversal direction
    for callers that care.

    ``seen=True`` marks a node that was already emitted higher in the tree; the traversal does
    not recurse into it (cycle / breadth-first revisit termination).

    ``children`` is empty when ``seen=True`` or when the depth limit was reached.
    """

    id: str
    type: str  # ItemType.value string
    status: str  # Status.value string
    priority: str | None  # Priority.value string, or None
    assignee: str | None
    edge_kind: str | None  # None for root; normalized kind for all other nodes
    direction: str | None  # "out" | "in" | None (None for root)
    seen: bool
    children: list[GraphNode] = field(default_factory=lambda: list[GraphNode]())

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict (for ``--json`` output)."""
        return {
            "id": self.id,
            "type": self.type,
            "status": self.status,
            "priority": self.priority,
            "assignee": self.assignee,
            "edge_kind": self.edge_kind,
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


@dataclass
class AdoptResult:
    paths: SquadPaths
    imported: int  # items found on disk and indexed
    roles: list[Item]  # roles newly activated


@dataclass(frozen=True)
class RetypeResult:
    """Outcome of ``Service.retype()``."""

    item: Item
    old_id: str
    old_type: str  # ItemType.value string, for display
    status_reset: bool
    old_status: str  # Status.value string (meaningful only when status_reset is True)
    rewritten: list[str]  # paths of files whose text was updated (relative display names)


@dataclass(frozen=True)
class RemoveResult:
    """Outcome of ``Service.remove_work_item()``.

    ``removed_id`` is the formatted ID of the deleted item.
    ``severed_refs`` lists the IDs of referrer items whose forward refs were severed (``--force``).
    The ``op=remove`` reflog entry with the gone-item snapshot is appended post-commit
    (FEAT-000024 / TASK-000112).
    """

    removed_id: str
    severed_refs: list[str]  # referrer IDs whose ref to removed_id was deleted


@dataclass
class RepairResult:
    """Outcome of ``Service.repair()``.

    ``missing_ids`` holds item IDs that were present in the index *before* repair but whose
    markdown files could not be found on disk — a deletion event worth surfacing to the operator.
    """

    db: SquadsDB
    missing_ids: list[str] = field(default_factory=list[str])


@dataclass
class RenumberResult:
    """Outcome of ``Service.renumber()`` — the pre-merge block-shift verb.

    ``remap`` maps each shifted item's old (unpadded) display id to its new one; empty when
    no local item had ``sequence_id >= from_seq`` (nothing to shift). ``db`` is the rebuilt
    index reflecting the shift, including the counter bumped to the new post-shift maximum.
    ``warning`` is set on the ``--by`` (no ``--onto``) path: sq cannot certify the shift
    clears the *other* branch's counter without it — that guarantee is the operator's.
    """

    remap: dict[str, str]
    db: SquadsDB
    warning: str | None = None


@dataclass
class WorkloadRow:
    """Per-assignee work counts for `sq workload` (None assignee = unassigned)."""

    assignee: str | None
    open: int
    closed: int
    total: int


@dataclass
class ReflogEntry:
    """One parsed reflog line, surfaced by ``sq reflog`` (FEAT-000024 / TASK-000113).

    The ``delta`` field is a free-form ``dict`` whose shape depends on ``op``; see
    the reflog schema documentation for the full field reference.  The ``v`` field
    carries the schema version so readers can handle future additions gracefully.

    ``session_id`` and ``parent_session_id`` are ``None`` for entries written before
    schema 0.4 (ADR-000158).  They record **best-effort, untrusted** lineage only —
    squads is a passive tool that reads optional env vars and records them; it does
    not mint, spawn, or verify.  Never use these fields as an authorisation input.

    Stability note: the *command shape* and the fields listed here are documented;
    the exact ``delta`` sub-fields are additive and evolve per FEAT-000013's freeze.
    """

    v: str
    ts: str
    actor: str
    op: str
    target: str
    delta: dict[str, Any]
    session_id: str | None = None
    parent_session_id: str | None = None
