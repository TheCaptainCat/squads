"""Populate a Textual `Tree` from `Service.tree_view()`'s `TreeNode` forest."""

from rich.markup import escape as e
from textual.widgets import Tree
from textual.widgets.tree import TreeNode as UiTreeNode

from squads._models._item import Item
from squads._services._results import TreeNode


def _label(item: Item, *, path_only: bool) -> str:
    base = f"[bold]{item.id}[/bold] {e(item.title)} [dim]({item.status})[/dim]"
    return f"[dim]{base}[/dim]" if path_only else base


def _attach(parent: UiTreeNode[str], node: TreeNode) -> None:
    if node.children:
        branch = parent.add(_label(node.item, path_only=node.path_only), node.item.id, expand=True)
        for child in node.children:
            _attach(branch, child)
    else:
        parent.add_leaf(_label(node.item, path_only=node.path_only), node.item.id)


def populate_tree(tree: Tree[str], nodes: list[TreeNode]) -> None:
    """Build the tree, fully expanded, from the roots returned by `svc.tree_view()`."""
    for node in nodes:
        _attach(tree.root, node)
    tree.root.expand()
