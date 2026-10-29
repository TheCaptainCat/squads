"""The ref graph renderers: a tree of the linked items, or the graph as Graphviz or Mermaid
text."""

from rich.console import Console
from rich.tree import Tree

from squads._api._dto._graph import GraphNode
from squads._cli._render._style import e, lead_badge


def _node_line(node: GraphNode) -> str:
    """A node's id, lead badge and status."""
    prio = lead_badge(node.display)
    return f"[bold]{node.id}[/bold] {prio}{e(node.status)}"


def _attach(parent: Tree, node: GraphNode) -> None:
    for child in node.children:
        edge = child.display.edge
        edge_part = f" [dim]({e(edge)})[/dim]" if edge is not None else ""
        seen_mark = " [dim](seen)[/dim]" if child.seen else ""
        branch = parent.add(f"{edge_part} {_node_line(child)}{seen_mark}")
        if not child.seen:
            _attach(branch, child)


def render_graph(root: GraphNode, console: Console) -> None:
    """The root and each item its refs reach, an already shown item marked and not expanded."""
    tree = Tree(_node_line(root))
    _attach(tree, root)
    console.print(tree)


def _collect_edges(root: GraphNode) -> tuple[set[str], set[tuple[str, str, str]]]:
    """Every node id and every ``(from, to, text)`` edge once: a revisited node is shown again,
    its edge is not."""
    nodes: set[str] = set()
    edges: set[tuple[str, str, str]] = set()
    stack: list[tuple[GraphNode, str | None]] = [(root, None)]
    while stack:
        node, parent_id = stack.pop()
        nodes.add(node.id)
        if parent_id is not None and node.display.edge is not None:
            edges.add((parent_id, node.id, node.display.edge))
        stack.extend((child, node.id) for child in node.children)
    return nodes, edges


def graph_to_dot(root: GraphNode) -> str:
    """The graph as a Graphviz ``digraph``."""
    nodes, edges = _collect_edges(root)

    def quoted(s: str) -> str:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

    lines = [
        "digraph {",
        *[f"    {quoted(nid)};" for nid in sorted(nodes)],
        *[
            f"    {quoted(from_id)} -> {quoted(to_id)} [label={quoted(label)}];"
            for from_id, to_id, label in sorted(edges)
        ],
        "}",
    ]
    return "\n".join(lines)


def _mermaid_node_id(nid: str) -> str:
    """An item id as a Mermaid node identifier: each non-alphanumeric UTF-16 code unit becomes
    ``_`` and four lowercase hex digits, an injective, fixed-width escape that matches the VS
    Code client's."""
    units = nid.encode("utf-16-be")
    pairs = (int.from_bytes(units[i : i + 2], "big") for i in range(0, len(units), 2))
    return "".join(chr(u) if chr(u).isascii() and chr(u).isalnum() else f"_{u:04x}" for u in pairs)


def _mermaid_label(text: str) -> str:
    """*text* as a quoted Mermaid label, ``"`` written as the HTML entity Mermaid renders."""
    return '"' + text.replace('"', "&quot;") + '"'


def graph_to_mermaid(root: GraphNode) -> str:
    """The graph as a Mermaid ``flowchart LR``: each node an edge touches, labelled with its real
    id, then the edges."""
    _, edges = _collect_edges(root)
    linked = sorted({end for from_id, to_id, _label in edges for end in (from_id, to_id)})
    lines = ["flowchart LR"]
    lines.extend(f"    {_mermaid_node_id(nid)}[{_mermaid_label(nid)}]" for nid in linked)
    lines.extend(
        f"    {_mermaid_node_id(from_id)} -->|{label}| {_mermaid_node_id(to_id)}"
        for from_id, to_id, label in sorted(edges)
    )
    return "\n".join(lines)


def render_graph_text(root: GraphNode, console: Console, *, fmt: str) -> None:
    """The graph as ``dot``, ``mermaid`` or ``mermaid-md`` (Mermaid in a markdown fence)."""
    if fmt == "dot":
        text = graph_to_dot(root)
    elif fmt == "mermaid":
        text = graph_to_mermaid(root)
    else:
        text = f"```mermaid\n{graph_to_mermaid(root)}\n```"
    console.print(text, markup=False, highlight=False)
