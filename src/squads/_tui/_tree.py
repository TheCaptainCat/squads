"""Populate a Textual `Tree` from `Service.tree_view()`'s `TreeNode` forest."""

from rich.text import Text
from textual.widgets import Tree
from textual.widgets.tree import TreeNode as UiTreeNode

from squads._models._item import Item
from squads._services._results import TreeNode
from squads._workflow import WorkflowSpec

_WORK_GROUP = "Work"
_ROSTER_GROUP = "Roster"


def _label(item: Item, *, path_only: bool) -> Text:
    # Built from styled spans, not a markup string — immune to bracket sequences in the
    # title/status regardless of which parser (Rich's or Textual's) ends up reading it.
    text = Text.assemble((item.id, "bold"), " ", item.title, " ", (f"({item.status})", "dim"))
    if path_only:
        text.stylize("dim")
    return text


def _attach(parent: UiTreeNode[str], node: TreeNode) -> None:
    if node.children:
        branch = parent.add(_label(node.item, path_only=node.path_only), node.item.id, expand=True)
        for child in node.children:
            _attach(branch, child)
    else:
        parent.add_leaf(_label(node.item, path_only=node.path_only), node.item.id)


def populate_tree(tree: Tree[str], nodes: list[TreeNode], spec: WorkflowSpec) -> None:
    """Build the tree, fully expanded, from the roots returned by `svc.tree_view()`, grouped
    under two synthetic top-level nodes: Work (work items) and Roster (roles/operators/skills).
    """
    work_root = tree.root.add(Text(_WORK_GROUP, style="bold"), None, expand=True)
    roster_root = tree.root.add(Text(_ROSTER_GROUP, style="bold"), None, expand=True)
    for node in nodes:
        group = roster_root if spec.item_is_roster(node.item.type) else work_root
        _attach(group, node)
    tree.root.expand()
