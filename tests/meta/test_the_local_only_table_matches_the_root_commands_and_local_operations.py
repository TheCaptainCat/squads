"""Repo-hygiene gate: the commands the shim runs in its own process are root commands, include
the command of every operation marked `local_only`, and add only the two that manage the daemon
and the terminal."""

from squads._api._ops import OPERATIONS
from squads._shim import LOCAL_ONLY, LOCAL_ROOT_OPTIONS
from tests.meta._command_tree import root

#: Commands with no operation that act on this machine: they manage the daemon, or the terminal.
_MACHINE_COMMANDS = {"daemon", "ui"}


def test_every_local_only_command_is_a_registered_root_command() -> None:
    assert set(root().commands) >= LOCAL_ONLY


def test_the_local_only_commands_are_those_of_the_local_operations_and_the_machine_ones() -> None:
    of_operations = {op.name.removeprefix("squad.") for op in OPERATIONS if op.local_only}
    assert of_operations | _MACHINE_COMMANDS == LOCAL_ONLY


def test_the_local_root_options_are_options_of_the_root_command() -> None:
    declared = {opt for param in root().params for opt in (*param.opts, *param.secondary_opts)}
    assert declared >= LOCAL_ROOT_OPTIONS
