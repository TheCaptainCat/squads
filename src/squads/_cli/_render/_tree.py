"""The tree renderer: the item hierarchy, one line per node."""

from rich.console import Console
from rich.text import Text
from rich.tree import Tree

from squads._api._dto._tree import TreeNode, TreeView
from squads._cli._render._style import e, lead_badge, status_text


def _label(node: TreeNode) -> Text:
    """One node's line: id, lead badge, title and status, dimmed when the node is only on the
    path to a match, then the note beside a root invented for a parent cycle."""
    shown = node.display
    prio = lead_badge(shown)
    text = Text.from_markup(f"[bold]{node.id}[/bold] {prio}{e(node.title)} ")
    text.append("(", style="dim")
    text.append_text(status_text(node.status, shown.status.intent))
    text.append(")", style="dim")
    if shown.dimmed:
        text.stylize("dim")
    if shown.anchor:
        text.append(f"  {shown.anchor}", style="yellow")
    return text


def _attach(parent: Tree, node: TreeNode) -> None:
    branch = parent.add(_label(node))
    for child in node.children:
        _attach(branch, child)


def render_tree(view: TreeView, console: Console) -> None:
    """The hierarchy under a ``squad`` root; an empty one says how many closed items it hid."""
    if not view.items:
        if view.hidden:
            console.print(f"[dim]{view.hidden} closed items hidden — use --all[/dim]")
        else:
            console.print("[dim]no items[/dim]")
        return
    tree = Tree("squad")
    for node in view.items:
        _attach(tree, node)
    console.print(tree)
