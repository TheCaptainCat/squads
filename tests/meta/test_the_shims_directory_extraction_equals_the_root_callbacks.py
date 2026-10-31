"""Repo-hygiene gate: the `-C` values the shim reads from a command line, and the first command
word, are those the root command parses, over every spelling it accepts."""

import pytest

from squads._cli import _hoist_global_options
from squads._cli._common import CHANGE_DIR_PARAM
from squads._shim import leading
from tests.meta._command_tree import root

SPELLINGS = [
    ["-C", "a", "list"],
    ["-Ca", "list"],
    ["-C", "a", "-C", "b", "list"],
    ["-Ca", "-Cb", "list"],
    ["-C", "a", "-Cb", "list"],
    ["-C=a", "list"],
    ["-C", "", "list"],
    ["-C", "-x", "list"],
    ["-C", "a b", "task", "1", "show"],
    ["--at", "2024-01-01", "-C", "a", "list"],
    ["-C", "a", "--at", "2024-01-01", "list"],
    ["--at=2024-01-01", "-C", "a", "list"],
    ["-C", "a", "list", "--at", "2024-01-01"],
    ["list", "--at", "2024-01-01", "-C", "x"],
    ["--dir", "x", "-C", "a", "list"],
    ["--dir=x", "-C", "a", "list"],
    ["-C", "a", "--", "list"],
    ["--", "list"],
    ["-C", "a", "list", "-C", "b"],
    ["-C", "a", "task", "1", "comment", "-m", "-C"],
    ["list"],
    ["--help", "list"],
    ["-C", "a", "--version", "list"],
]


@pytest.mark.parametrize("argv", SPELLINGS, ids=" ".join)
def test_the_shim_reads_the_same_directories_and_command_word_as_the_root_command(
    argv: list[str],
) -> None:
    command = root()
    context = command.make_context("sq", _hoist_global_options(list(argv)), resilient_parsing=True)
    remaining = [*context._protected_args, *context.args]

    shim = leading(argv)

    assert shim.dirs == (context.params.get(CHANGE_DIR_PARAM) or [])
    assert shim.words[:1] == remaining[:1]
