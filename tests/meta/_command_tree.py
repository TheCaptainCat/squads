"""The registered command tree of the CLI, read from the Click commands the Typer application
builds, for the guards that hold a table of the shim to it."""

from collections.abc import Iterator
from typing import Any

import typer.main

from squads._cli import app


def root() -> Any:
    """The root Click group, with every bundled command group and item type reachable."""
    return typer.main.get_command(app)


def walk(command: Any = None, path: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], Any]]:
    """Each command below *command* (the root by default) with its path of command words."""
    command = root() if command is None else command
    for name in list(command.commands):
        child = command.commands[name]
        yield (*path, name), child
        if hasattr(child, "commands"):
            yield from walk(child, (*path, name))
