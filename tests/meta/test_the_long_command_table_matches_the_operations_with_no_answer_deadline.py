"""Repo-hygiene gate: the shim, which parses nothing, gives no answer deadline to exactly the
commands whose callback calls an operation the operation table classes `long`, each paired with
that operation, and reads those commands past a global option."""

import inspect
import re

from squads._api import _ops as ops
from squads._api._api import Operation, Timeout
from squads._shim import LONG_COMMANDS, leading, long_command
from tests.meta._command_tree import walk


def _long_operations() -> set[str]:
    """The names of the operations the operation table classes `long`."""
    return {op.name for op in ops.OPERATIONS if op.timeout is Timeout.LONG}


def _bound() -> dict[tuple[str, ...], set[str]]:
    """For each command whose callback names a `long` operation, the operations it names."""
    long = _long_operations()
    bound: dict[tuple[str, ...], set[str]] = {}
    for path, command in walk():
        if command.callback is None:
            continue
        source = inspect.getsource(inspect.unwrap(command.callback))
        named = {getattr(ops, c, None) for c in re.findall(r"\bops\.([A-Z][A-Z_]*)\b", source)}
        names = {op.name for op in named if isinstance(op, Operation)} & long  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
        if names:
            bound[path] = names
    return bound


def test_every_long_command_is_paired_with_the_operation_its_callback_calls() -> None:
    assert {path: {name} for path, name in LONG_COMMANDS} == _bound()


def test_every_long_operation_is_named_by_the_table() -> None:
    assert {name for _, name in LONG_COMMANDS} == _long_operations()


def test_a_global_option_between_the_command_words_does_not_hide_a_long_command() -> None:
    for argv in (["migrate", "--at", "2024-01-01", "up"], ["--at=2024-01-01", "repair"]):
        assert long_command(argv, leading(argv)) is not None
