"""Populate a Textual `Tree` from `Service.tree_view()`'s `TreeNode` forest.

Role/Operator leaves under Roster additionally carry their memory pool as UI-only children —
a glance-level count + most-recent-entry age on the parent label, each entry as a child leaf.
This is layered on **after** the service-level `TreeNode` forest is built and sorted
(`squads._tui._browse.sort_siblings` only ever sees real `TreeNode`s, never a memory entry),
using a typed `NodeData` discriminator so `BrowseScreen.on_tree_node_highlighted` never
mistakes a memory entry for an item id.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from rich.text import Text
from textual.widgets import Tree
from textual.widgets.tree import TreeNode as UiTreeNode

from squads import _clock as clock
from squads._memory._model import MemoryEntry
from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._services._results import TREE_ANCHOR_MARKER, TreeNode
from squads._workflow import ROSTER_OPERATOR, ROSTER_ROLE, WorkflowSpec

_WORK_GROUP = "Work"
_RECORDS_GROUP = "Records"
_ROSTER_GROUP = "Roster"

#: Fixed top-level root order, each one always present (even empty) — read off the spec's own
#: closed category catalog rather than a hand-rolled roster/work/records list here.
_GROUP_LABELS: dict[str, str] = {
    "work": _WORK_GROUP,
    "records": _RECORDS_GROUP,
    "roster": _ROSTER_GROUP,
}
_GROUP_ORDER: tuple[str, ...] = ("work", "records", "roster")

#: Concrete Rich/Textual style per semantic colour intent — this client's own rendering of a
#: status role's colour axis (mirrors the CLI's colour choices where sensible, but is its own
#: mapping). "neutral" (no colour override) also serves as the fallback for an intent this
#: build doesn't recognise.
_ROLE_STYLES: dict[str, str] = {
    "positive": "green",
    "danger": "red",
    "warning": "yellow",
    "info": "cyan",
    "muted": "bright_black",
    "neutral": "",
}


@dataclass(frozen=True)
class MemoryNodeData:
    """Tree-node payload for one memory entry, nested under its Role/Operator identity.

    Not an item id and not resolvable as one — `role_slug` + `entry_slug` is exactly what
    `Service.memory_show` needs. Kept distinct from the plain `str` item-id payload so
    `BrowseScreen.on_tree_node_highlighted` can tell the two apart before dispatching.
    """

    role_slug: str
    entry_slug: str


#: Every payload a tree node's `data` can carry, besides the ever-allowed `None` (used for
#: purely structural nodes: the three category groups, and a degraded-read notice leaf).
type NodeData = str | MemoryNodeData

#: One role/operator identity's eagerly-fetched memory pool: its entries plus any per-file
#: read failures, keyed by the identity's own roster slug (`Item.extra[X.SLUG]`, not
#: `Item.id`) — `role_slug` here matches what `Service.memory_list`/`memory_show` expect.
type MemoryBySlug = Mapping[str, tuple[list[MemoryEntry], list[str]]]


def roster_identity_slugs(nodes: list[TreeNode]) -> list[str]:
    """Every Role/Operator node's own roster slug anywhere in *nodes*, recursively.

    Skill nodes carry no notebook and are excluded — reuses the same reserved-type check
    (`ROSTER_ROLE`/`ROSTER_OPERATOR`) the rest of the engine keys memory-eligibility off of,
    rather than a fresh literal list. Used to size the eager `memory_list()` fetch in
    `BrowseScreen.refresh_tree` to exactly the identities this tree is about to render.
    """
    out: list[str] = []
    stack = list(nodes)
    while stack:
        node = stack.pop()
        stack.extend(node.children)
        if node.item.type not in (ROSTER_ROLE, ROSTER_OPERATOR):
            continue
        slug = node.item.extra.get(X.SLUG)
        if isinstance(slug, str) and slug:
            out.append(slug)
    return out


#: (seconds-per-unit, unit suffix), coarsest-fitting wins — ordered finest to coarsest so the
#: first threshold the age still exceeds picks the unit.
_AGE_UNITS: tuple[tuple[int, str], ...] = (
    (60, "m"),
    (60 * 60, "h"),
    (60 * 60 * 24, "d"),
    (60 * 60 * 24 * 30, "mo"),
    (60 * 60 * 24 * 365, "y"),
)


def _humanize_age(created_at: str) -> str:
    """A short "how long ago" rendering of an ISO-8601 timestamp, coarsest unit only."""
    try:
        delta = clock.now() - clock.parse_iso(created_at)
    except ValueError:
        return "unknown age"
    seconds = max(0, int(delta.total_seconds()))
    if seconds < _AGE_UNITS[0][0]:
        return "just now"
    unit_seconds, suffix = _AGE_UNITS[0]
    for next_seconds, next_suffix in _AGE_UNITS[1:]:
        if seconds < next_seconds:
            break
        unit_seconds, suffix = next_seconds, next_suffix
    return f"{seconds // unit_seconds}{suffix} ago"


def _sorted_memory_entries(entries: list[MemoryEntry]) -> list[MemoryEntry]:
    """Oldest-touched first, ties broken stably by slug — the within-role comparison order."""
    return sorted(entries, key=lambda m: (m.created_at, m.slug))


def _memory_glance_suffix(entries: list[MemoryEntry]) -> Text:
    """The count(+age) fragment appended to a Role/Operator's own label — a pool with zero
    entries still renders "(0)" so a quiet role reads as a signal, not as nothing to show."""
    if not entries:
        return Text("  memory: 0", style="dim")
    newest = max(m.created_at for m in entries)
    return Text(f"  memory: {len(entries)} · {_humanize_age(newest)}", style="dim")


def _memory_leaf_label(entry: MemoryEntry) -> Text:
    # Spans, not a markup string — a memory's summary is free-form and may contain brackets.
    return Text.assemble(
        (entry.slug, "bold"),
        "  ",
        entry.summary,
        "  ",
        (f"({_humanize_age(entry.created_at)})", "dim"),
    )


def _skipped_leaf_label(count: int) -> Text:
    files = "file" if count == 1 else "files"
    return Text(f"{count} memory {files} could not be read — listing partial", style="yellow")


def _status_style(status: str, spec: WorkflowSpec) -> str:
    intent = spec.role_for(status).color
    return _ROLE_STYLES.get(intent, _ROLE_STYLES["neutral"])


def _label(item: Item, *, path_only: bool, anchor: bool, spec: WorkflowSpec) -> Text:
    # Built from styled spans, not a markup string — immune to bracket sequences in the
    # title/status regardless of which parser (Rich's or Textual's) ends up reading it.
    text = Text.assemble(
        (item.id, "bold"),
        " ",
        item.title,
        " ",
        (f"({item.status})", _status_style(item.status, spec)),
    )
    if path_only or spec.hidden_by_default(item.type, item.status):
        text.stylize("dim")
    # This browser roots at the bare forest, so it receives the invented roots too — appended
    # after the dim so the disclosure stays legible on a path-only or hidden-by-default node.
    if anchor:
        text.append(f"  {TREE_ANCHOR_MARKER}", style="yellow")
    return text


def _attach_memory_children(
    branch: UiTreeNode[NodeData], role_slug: str, entries: list[MemoryEntry], unreadable: list[str]
) -> None:
    for entry in _sorted_memory_entries(entries):
        branch.add_leaf(
            _memory_leaf_label(entry), MemoryNodeData(role_slug=role_slug, entry_slug=entry.slug)
        )
    if unreadable:
        branch.add_leaf(_skipped_leaf_label(len(unreadable)), None)


def _attach(
    parent: UiTreeNode[NodeData], node: TreeNode, spec: WorkflowSpec, memory: MemoryBySlug
) -> None:
    label = _label(node.item, path_only=node.path_only, anchor=node.anchor, spec=spec)
    if node.children:
        branch = parent.add(label, node.item.id, expand=True)
        for child in node.children:
            _attach(branch, child, spec, memory)
        return
    role_slug = node.item.extra.get(X.SLUG)
    if isinstance(role_slug, str):
        pool = memory.get(role_slug)
        if pool is not None:
            entries, unreadable = pool
            label.append_text(_memory_glance_suffix(entries))
            branch = parent.add(label, node.item.id, expand=False)
            _attach_memory_children(branch, role_slug, entries, unreadable)
            return
    parent.add_leaf(label, node.item.id)


def populate_tree(
    tree: Tree[NodeData], nodes: list[TreeNode], spec: WorkflowSpec, memory: MemoryBySlug
) -> None:
    """Build the tree, fully expanded, from the roots returned by `svc.tree_view()`, grouped
    under three synthetic top-level nodes — Work, Records (decisions/guides/etc.), and Roster
    (roles/operators/skills) — in that fixed order, each always present even when empty.

    *memory* is the eager, already-fetched `memory_list()` result for every Role/Operator
    identity in *nodes* (see `roster_identity_slugs`) — this function never calls the service.
    """
    groups = {
        category: tree.root.add(Text(_GROUP_LABELS[category], style="bold"), None, expand=True)
        for category in _GROUP_ORDER
    }
    for node in nodes:
        category = spec.items[node.item.type].category
        _attach(groups[category], node, spec, memory)
    tree.root.expand()
