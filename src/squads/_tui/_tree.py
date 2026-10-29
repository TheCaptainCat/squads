"""Populate a Textual `Tree` from the `tree` operation's nodes.

Role/Operator leaves under Roster also carry their memory pool as UI-only children: a count
and most-recent-entry age on the parent label, each entry as a child leaf. It is layered on
after the forest is fetched and sorted, so `squads._tui._browse.sort_siblings` only sees tree
nodes, and a typed `NodeData` discriminator keeps `BrowseScreen.on_tree_node_highlighted` from
mistaking a memory entry for an item id.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from rich.text import Text
from textual.widgets import Tree
from textual.widgets.tree import TreeNode as UiTreeNode

from squads import _clock as clock
from squads._api._dto._memory import MemoryRow
from squads._api._dto._tree import TreeNode
from squads._api._dto._workflow import TypeCatalog
from squads._tui._session import categories

#: Rich/Textual style per colour intent, this client's own mapping of a status role's colour
#: axis. "neutral" (no override) is also the fallback for an unrecognised intent.
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

    Not an item id and not resolvable as one: `role_slug` + `entry_slug` address the `memory
    show` operation. Kept distinct from the plain `str` item-id payload so
    `BrowseScreen.on_tree_node_highlighted` can tell the two apart before dispatching.
    """

    role_slug: str
    entry_slug: str


#: Every payload a tree node's `data` can carry, besides the ever-allowed `None` (used for
#: purely structural nodes: the category groups, and a degraded-read notice leaf).
type NodeData = str | MemoryNodeData

#: One role/operator identity's eagerly-fetched memory pool: its entries and how many memory
#: files could not be read, keyed by the identity's notebook slug (`TreeNode.notebook`).
type MemoryBySlug = Mapping[str, tuple[list[MemoryRow], int]]


def roster_identity_slugs(nodes: list[TreeNode]) -> list[str]:
    """Every notebook slug anywhere in *nodes*, recursively: the identities whose memory pool
    `BrowseScreen.refresh_tree` fetches."""
    out: list[str] = []
    stack = list(nodes)
    while stack:
        node = stack.pop()
        stack.extend(node.children)
        if node.notebook:
            out.append(node.notebook)
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


def _sorted_memory_entries(entries: list[MemoryRow]) -> list[MemoryRow]:
    """Oldest-touched first, ties broken stably by slug — the within-role comparison order."""
    return sorted(entries, key=lambda m: (m.created_at, m.slug))


def _memory_glance_suffix(entries: list[MemoryRow]) -> Text:
    """The count(+age) fragment appended to a Role/Operator's own label — a pool with zero
    entries still renders "(0)" so a quiet role reads as a signal, not as nothing to show."""
    if not entries:
        return Text("  memory: 0", style="dim")
    newest = max(m.created_at for m in entries)
    return Text(f"  memory: {len(entries)} · {_humanize_age(newest)}", style="dim")


def _memory_leaf_label(entry: MemoryRow) -> Text:
    # Spans, not a markup string — a memory's summary is free-form and may contain brackets.
    return Text.assemble(
        (entry.slug, "bold"),
        "  ",
        entry.description,
        "  ",
        (f"({_humanize_age(entry.created_at)})", "dim"),
    )


def _skipped_leaf_label(count: int) -> Text:
    files = "file" if count == 1 else "files"
    return Text(f"{count} memory {files} could not be read — listing partial", style="yellow")


def _named(node: TreeNode) -> Text:
    """The title, followed by the pronouns the squad shows, dimmed."""
    text = Text(node.title)
    if node.display.pronouns:
        text.append(" ")
        text.append(f"({node.display.pronouns})", style="dim")
    return text


def _label(node: TreeNode) -> Text:
    # Built from styled spans, not a markup string — immune to bracket sequences in the
    # title/status regardless of which parser (Rich's or Textual's) ends up reading it.
    style = _ROLE_STYLES.get(node.display.status.intent, _ROLE_STYLES["neutral"])
    text = Text.assemble(
        (node.id, "bold"),
        " ",
        _named(node),
        " ",
        (f"({node.status})", style),
    )
    if node.display.dimmed or node.closed:
        text.stylize("dim")
    # This browser roots at the bare forest, so it receives the invented roots too — appended
    # after the dim so the disclosure stays legible on a path-only or closed node.
    if node.display.anchor:
        text.append(f"  {node.display.anchor}", style="yellow")
    return text


def _attach_memory_children(
    branch: UiTreeNode[NodeData], role_slug: str, entries: list[MemoryRow], unreadable: int
) -> None:
    for entry in _sorted_memory_entries(entries):
        branch.add_leaf(
            _memory_leaf_label(entry), MemoryNodeData(role_slug=role_slug, entry_slug=entry.slug)
        )
    if unreadable:
        branch.add_leaf(_skipped_leaf_label(unreadable), None)


def _attach(parent: UiTreeNode[NodeData], node: TreeNode, memory: MemoryBySlug) -> None:
    """Attach *node* and its subtree under *parent*, layering a Role/Operator's memory pool on.

    The memory signal is independent of real item children; gating on `not node.children` would
    drop it once an identity has any.

    A branch is created when there is something to disclose: real item children, a memory entry,
    or an unreadable memory file. A pool that fetched clean and empty collapses to a leaf, since
    an expandable `memory: 0` answers nothing. A pool empty because every file was unreadable
    keeps its branch so the "listing partial" child stays reachable.
    """
    label = _label(node)
    entries: list[MemoryRow] = []
    unreadable = 0
    pool = memory.get(node.notebook) if node.notebook else None
    if pool is not None:
        entries, unreadable = pool
        label.append_text(_memory_glance_suffix(entries))

    if node.children or entries or unreadable:
        branch = parent.add(label, node.id, expand=bool(node.children))
        for child in node.children:
            _attach(branch, child, memory)
        if node.notebook is not None and pool is not None:
            _attach_memory_children(branch, node.notebook, entries, unreadable)
        return
    parent.add_leaf(label, node.id)


def populate_tree(
    tree: Tree[NodeData], nodes: list[TreeNode], types: TypeCatalog, memory: MemoryBySlug
) -> None:
    """Build the fully expanded tree from the roots the `tree` operation answered.

    Nodes sit under one synthetic top-level group per category a declared type names, ordered
    by the first type of each category in the type catalog's `order`; a category no type names
    has no group. A group with types but no node in view still shows. *memory* is the
    already-fetched `memory list` result for every notebook slug in *nodes* (see
    `roster_identity_slugs`); this function makes no call.
    """
    category_of = {row.type: row.category for row in types.items}
    groups = {
        category: tree.root.add(Text(category.capitalize(), style="bold"), None, expand=True)
        for category in categories(types)
    }
    for node in nodes:
        _attach(groups[category_of[node.type]], node, memory)
    tree.root.expand()
