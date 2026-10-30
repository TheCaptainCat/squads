"""Repo-hygiene gate: the shim, which parses nothing, gives no answer deadline to exactly the
commands whose operation the operation table classes `long`."""

from squads._api._api import Timeout
from squads._api._ops import OPERATIONS
from squads._shim import LONG_COMMANDS
from tests.meta._command_tree import root


def test_the_long_commands_name_the_long_operations() -> None:
    long = {op.name for op in OPERATIONS if op.timeout is Timeout.LONG}
    assert {name for _, name in LONG_COMMANDS} == long


def test_every_long_command_path_is_a_registered_command() -> None:
    for path, _ in LONG_COMMANDS:
        command = root()
        for word in path:
            command = command.commands[word]
