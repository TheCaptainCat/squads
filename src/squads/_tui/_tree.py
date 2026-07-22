"""Populate a Textual `Tree` from `Service.tree_view()`'s `TreeNode` forest."""

from rich.text import Text
from textual.widgets import Tree
from textual.widgets.tree import TreeNode as UiTreeNode

from squads._models._item import Item
from squads._services._results import TreeNode
from squads._workflow import WorkflowSpec

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


def _status_style(status: str, spec: WorkflowSpec) -> str:
    intent = spec.role_for(status).color
    return _ROLE_STYLES.get(intent, _ROLE_STYLES["neutral"])


def _label(item: Item, *, path_only: bool, spec: WorkflowSpec) -> Text:
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
    return text


def _attach(parent: UiTreeNode[str], node: TreeNode, spec: WorkflowSpec) -> None:
    label = _label(node.item, path_only=node.path_only, spec=spec)
    if node.children:
        branch = parent.add(label, node.item.id, expand=True)
        for child in node.children:
            _attach(branch, child, spec)
    else:
        parent.add_leaf(label, node.item.id)


def populate_tree(tree: Tree[str], nodes: list[TreeNode], spec: WorkflowSpec) -> None:
    """Build the tree, fully expanded, from the roots returned by `svc.tree_view()`, grouped
    under three synthetic top-level nodes — Work, Records (decisions/guides/etc.), and Roster
    (roles/operators/skills) — in that fixed order, each always present even when empty.
    """
    groups = {
        category: tree.root.add(Text(_GROUP_LABELS[category], style="bold"), None, expand=True)
        for category in _GROUP_ORDER
    }
    for node in nodes:
        category = spec.items[node.item.type].category
        _attach(groups[category], node, spec)
    tree.root.expand()
