"""The reflog renderers: one line per entry, or the entries grouped by the session lineage they
declare."""

import json

from rich.console import Console
from rich.tree import Tree

from squads._api._dto._reflog import Reflog, ReflogEntryRow
from squads._cli._render._style import e


def _line(entry: ReflogEntryRow) -> str:
    delta = json.dumps(entry.delta, separators=(",", ":"), ensure_ascii=False)
    return (
        f"[dim]{e(entry.ts)}[/dim]  [bold]{e(entry.op)}[/bold]"
        f"  [cyan]{e(entry.target)}[/cyan]"
        f"  [dim]actor={e(entry.actor)}[/dim]  {e(delta)}"
    )


def render_reflog(reflog: Reflog, console: Console) -> None:
    """One line per entry, oldest first."""
    if not reflog.items:
        console.print("[dim]no reflog entries[/dim]")
        return
    for entry in reflog.items:
        console.print(_line(entry))


type _Sessions = dict[str, list[ReflogEntryRow]]


def _sessions(
    entries: list[ReflogEntryRow],
) -> tuple[_Sessions, dict[str, str | None], dict[str, list[str]], list[ReflogEntryRow]]:
    """The entries by session, each session's declared parent (its first entry's), each
    session's children within the view, and the entries that declare no session."""
    by_session: _Sessions = {}
    parents: dict[str, str | None] = {}
    no_session: list[ReflogEntryRow] = []
    for entry in entries:
        sid = entry.session_id
        if sid is None:
            no_session.append(entry)
        else:
            by_session.setdefault(sid, []).append(entry)
            parents.setdefault(sid, entry.parent_session_id)
    children: dict[str, list[str]] = {}
    for sid in by_session:
        parent = parents.get(sid)
        if parent and parent in by_session:
            children.setdefault(parent, []).append(sid)
    return by_session, parents, children, no_session


def _attach(
    node: Tree,
    sid: str,
    by_session: _Sessions,
    children: dict[str, list[str]],
    visited: set[str],
) -> None:
    """Attach *sid*'s child sessions under *node*; *visited* keeps a cycle from looping."""
    for child in sorted(children.get(sid, [])):
        if child in visited:
            continue
        visited.add(child)
        child_node = node.add(f"[dim]session:[/dim] {e(child)}")
        for entry in by_session.get(child, []):
            child_node.add(_line(entry))
        _attach(child_node, child, by_session, children, visited)


def _root(tree: Tree, label: str, sid: str, by_session: _Sessions) -> Tree:
    node = tree.add(label)
    for entry in by_session.get(sid, []):
        node.add(_line(entry))
    return node


def render_reflog_tree(reflog: Reflog, console: Console) -> None:
    """The entries as a forest of sessions under the parent each declares. Lineage is declared,
    not verified, so the tree is a hint: a session whose parent is outside the view, or in a
    cycle, is a root, and entries with no session are roots of their own."""
    console.print("[dim]Spawn-lineage tree — BEST-EFFORT / UNTRUSTED / OBSERVABILITY-ONLY[/dim]")
    console.print(
        "[dim]Reflects declared lineage; no tamper-evidence or enforcement guarantee.[/dim]"
    )
    console.print()
    if not reflog.items:
        console.print("[dim]no reflog entries[/dim]")
        return
    by_session, parents, children, no_session = _sessions(reflog.items)
    tree = Tree("[dim]reflog[/dim]")
    visited: set[str] = set()
    for sid in sorted(by_session):
        parent = parents.get(sid)
        if parent is not None and parent in by_session:
            continue
        label = f"[dim]session:[/dim] {e(sid)}"
        if parent:
            label += f"  [dim](parent {e(parent)} not in view — forest root)[/dim]"
        visited.add(sid)
        _attach(_root(tree, label, sid, by_session), sid, by_session, children, visited)
    for sid in sorted(by_session):
        if sid in visited:
            continue
        visited.add(sid)
        parent = parents.get(sid)
        label = (
            f"[dim]session:[/dim] {e(sid)}  [dim](parent {e(parent)} — cycle/forest root)[/dim]"
            if parent
            else f"[dim]session:[/dim] {e(sid)}  [dim](cycle/forest root)[/dim]"
        )
        _attach(_root(tree, label, sid, by_session), sid, by_session, children, visited)
    for entry in no_session:
        node = tree.add(f"[dim]actor=[/dim]{e(entry.actor)}  [dim](no session recorded)[/dim]")
        node.add(_line(entry))
    console.print(tree)
