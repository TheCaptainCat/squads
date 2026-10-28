"""The pairs one argument list reaches on the live tree: what the ``invoke`` fixture compares a
test's ``covers`` markers with."""

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
            ("<type> show", None),
        },
    ),
    "a sub-entity verb with its address": (
        ["task", "3", "subtask", "ST1", "update", "--story", "US1"],
        {
            ("<type>", "N"),
            ("<type> <kind>", "LOCAL-ID"),
            ("<type> <kind> update", "--story"),
            ("<type> <kind> update", None),
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
            ("<host> comment edit", None),
        },
    ),
    "a create option a type adds": (
        ["create", "bug", "T", "--severity", "S1"],
        {("create <type>", "TITLE"), ("create <type>", "--severity"), ("create <type>", None)},
    ),
    "a parameterless leaf": (["sync"], {("sync", None)}),
    "a leaf with its argument missing": (["search"], {("search", None)}),
    "a built create with its title missing": (["create", "task"], {("create <type>", None)}),
    "a hand-written create keeps its own key": (
        ["create", "guide", "G", "--tag", "ops"],
        {("create guide", "TITLE"), ("create guide", "--tag"), ("create guide", None)},
    ),
    "a hidden create alias of the hand-written create": (
        ["create", "g", "G"],
        {("create guide", "TITLE"), ("create guide", None)},
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
            ("role status", None),
        },
    ),
    "a roster comments listing folds onto the host key": (
        ["operator", "op-a", "comments", "--json"],
        {("operator", "<slug|id|n>"), ("<host> comments", "--json"), ("<host> comments", None)},
    ),
    "a short alias is its long flag": (
        ["list", "-t", "task"],
        {("list", "--type"), ("list", None)},
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
