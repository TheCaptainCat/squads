"""Walk the live command tree and render its help screens, for the tests that hold ``--help`` to
the help rule.

The tree is the one ``typer.main.get_command`` builds for the squad in the current directory; a
help screen is rendered through the command's own ``get_help`` with the context chain a real
invocation would build, so nothing needs a registered item to exist.
"""

import contextlib
import io
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import typer.main
from typer._click.core import Context

from squads._cli import app

#: A project override declaring one custom type whose name starts with a vowel, hosting a
#: sub-entity kind with an irregular plural, plus a ref kind of its own.
CUSTOM_VOCABULARY_OVERRIDE = """\
[items.investigation]
prefix = "INV"
folder = "investigations"
lifecycle = "work"
subentity_kind = "analysis"

[subentity_kinds.analysis]
lifecycle = "subentity"
completion = "Done"
plural = "analyses"
local_prefix = "AN"

[ref_kinds.mitigates]
label = "Mitigates"
hint = "A mitigates the problem tracked by B"
"""

CUSTOM_TYPE = "investigation"
CUSTOM_KIND = "analysis"


def write_workflow_override(squad_dir: Path, toml: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(toml, encoding="utf-8")


@dataclass(frozen=True)
class Node:
    """One command of the tree: its path under ``sq``, the command, and its context."""

    path: tuple[str, ...]
    command: Any
    ctx: Context

    @property
    def label(self) -> str:
        return " ".join(("sq", *self.path))


def command_nodes() -> list[Node]:
    """Every listed command of the tree for the squad in the current directory."""
    root = typer.main.get_command(app)
    nodes: list[Node] = []

    def walk(command: Any, ctx: Context, path: tuple[str, ...]) -> None:
        nodes.append(Node(path, command, ctx))
        if not hasattr(command, "list_commands"):
            return
        for name in sorted(command.list_commands(ctx)):
            child = command.get_command(ctx, name)
            if child is None or (child.hidden and name != "_addr"):
                continue
            walk(child, Context(child, info_name=name, parent=ctx), (*path, name))

    walk(root, Context(root, info_name="sq"), ())
    return nodes


def render_help(node: Node) -> str:
    """The help screen of *node* as printed at the pinned terminal width."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        node.command.get_help(node.ctx)
    return out.getvalue()


def documented_params(node: Node) -> Iterator[Any]:
    """The options and arguments of *node* that a reader sees (not hidden)."""
    for param in node.command.params:
        if not getattr(param, "hidden", False):
            yield param


def help_source(node: Node) -> str:
    """The command's help text as authored, up to a form feed (maintainer notes follow it)."""
    return (node.command.help or "").split("\f", 1)[0]


def find_node(nodes: list[Node], *path: str) -> Node:
    for node in nodes:
        if node.path == path:
            return node
    raise LookupError(" ".join(path))
