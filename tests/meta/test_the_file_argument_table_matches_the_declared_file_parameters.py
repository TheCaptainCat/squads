"""Repo-hygiene gate: the shim attaches exactly the client files the command line names. Its table
of file options is the options the shared `--file` helper declares, and its table of file
arguments the first argument of the commands that take one."""

from squads._shim import FILE_ARGUMENT_COMMANDS, FILE_OPTIONS
from tests.meta._command_tree import walk


def _declared() -> tuple[set[str], dict[str, int]]:
    """The option names of every parameter named `file`, and for each command that has an argument
    named `file` its position among the command's arguments."""
    options: set[str] = set()
    arguments: dict[str, int] = {}
    for path, command in walk():
        positions = [p for p in command.params if p.param_type_name == "argument"]
        for param in command.params:
            if param.name != "file":
                continue
            if param.param_type_name == "option":
                options.update(param.opts)
            else:
                arguments[" ".join(path)] = positions.index(param)
    return options, arguments


def test_the_file_options_are_the_ones_the_shared_helper_declares() -> None:
    options, _ = _declared()
    assert options == set(FILE_OPTIONS)


def test_the_file_argument_commands_are_the_commands_that_take_a_first_file_argument() -> None:
    _, arguments = _declared()
    assert arguments == dict.fromkeys(FILE_ARGUMENT_COMMANDS, 0)
