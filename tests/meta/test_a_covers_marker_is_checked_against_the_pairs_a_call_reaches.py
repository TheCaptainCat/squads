"""The pairs one argument list reaches on the live tree: what the ``invoke`` fixture compares a
test's ``covers`` markers with. A leaf called with none of its own parameters reaches its bare
pair ``(key, None)``, and only then; a required parameter it leaves out is reached as the one
Click's missing-parameter error names."""

import pytest

from squads._workflow import bundled_spec
from tests._cli_surface import Pair, reached_pairs

type Case = tuple[list[str], set[Pair]]

CASES: dict[str, Case] = {
    "a root option and an aliased type group": (
        ["-C", "x", "t", "5", "show", "--json"],
        {
            ("", "-C"),
            ("<type>", "N"),
            ("<type> show", "--json"),
        },
    ),
    "a sub-entity verb with its address": (
        ["task", "3", "subtask", "ST1", "update", "--story", "US1"],
        {
            ("<type>", "N"),
            ("<type> <kind>", "LOCAL-ID"),
            ("<type> <kind> update", "--story"),
        },
    ),
    "an item comment group given a message": (
        ["task", "3", "comment", "-m", "x", "--as", "me"],
        {("<type>", "N"), ("<host> comment", "--message"), ("<host> comment", "--as")},
    ),
    "a roster comment addressed by a hash": (
        ["role", "pierre", "comment", "abcd", "edit", "-m", "x"],
        {
            ("role", "<slug|id|n>"),
            ("<host> comment", "HASH"),
            ("<host> comment edit", "--message"),
        },
    ),
    "a create option a type adds, the author left out": (
        ["create", "bug", "T", "--severity", "S1"],
        {
            ("create <type>", "TITLE"),
            ("create <type>", "--severity"),
            ("create <type>", "--author"),
        },
    ),
    "a parameterless leaf": (["sync"], {("sync", None)}),
    "a leaf that has parameters, called with none": (
        ["task", "3", "show"],
        {("<type>", "N"), ("<type> show", None)},
    ),
    "a leaf with its argument missing": (["search"], {("search", None), ("search", "TEXT")}),
    "a built create with its title missing": (
        ["create", "task"],
        {("create <type>", None), ("create <type>", "TITLE")},
    ),
    "a create option an attribute adds": (
        ["create", "guide", "G", "--tags", "ops"],
        {("create <type>", "TITLE"), ("create <type>", "--tags"), ("create <type>", "--author")},
    ),
    "a hidden create alias of a built create": (
        ["create", "g", "G"],
        {("create <type>", "TITLE"), ("create <type>", "--author")},
    ),
    "a group with its address missing": (["task"], set()),
    "a roster comment with the hash missing is read as a slug": (
        ["role", "comment"],
        {("role", "<slug|id|n>")},
    ),
    "options after an eager help": (
        ["task", "3", "update", "--help", "--title", "x"],
        {("<type>", "N")},
    ),
    "options before an eager help": (
        ["task", "3", "update", "--title", "x", "--help"],
        {("<type>", "N")},
    ),
    "a shared roster verb folds onto the reference host": (
        ["skill", "s", "status", "Archived", "--unlink"],
        {
            ("skill", "<slug|id|n>"),
            ("role status", "STATUS"),
            ("role status", "--unlink"),
        },
    ),
    "a roster comments listing folds onto the host key": (
        ["operator", "op-a", "comments", "--json"],
        {("operator", "<slug|id|n>"), ("<host> comments", "--json")},
    ),
    "a short alias is its long flag": (
        ["list", "-t", "task"],
        {("list", "--type")},
    ),
}


@pytest.mark.parametrize("name", list(CASES))
def test_the_pairs_an_argument_list_names_are_the_ones_it_reaches(name: str) -> None:
    args, expected = CASES[name]
    assert reached_pairs(args, bundled_spec()) == expected


def test_a_parameter_that_is_not_given_is_not_reached() -> None:
    assert ("<type> show", "--raw") not in reached_pairs(
        ["task", "3", "show", "--json"], bundled_spec()
    )


def test_a_level_that_does_not_parse_keeps_the_pairs_of_the_levels_before_it() -> None:
    reached = reached_pairs(["task", "3", "show", "--no-such-option"], bundled_spec())
    assert reached == {("<type>", "N")}


def test_an_unknown_command_reaches_nothing_beyond_the_root() -> None:
    assert reached_pairs(["nonesuch"], bundled_spec()) == set()


def test_a_failed_call_reaches_the_options_its_output_names_by_any_flag() -> None:
    refusal = "error: provide the body via -m (repeatable); --as-slug and x-file are not flags\n"
    reached = reached_pairs(["board", "post", "--until", "2999-01-01"], bundled_spec(), refusal)
    assert reached == {("board post", "--until"), ("board post", "--message")}
