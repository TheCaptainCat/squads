"""`_hoist_global_options`: the pure function that makes `--at`/`--dir` position-independent
by moving them (and their value) to the front of the argument list, wherever they appear —
so `sq <subcommand> ... --at ...` works exactly like `sq --at ... <subcommand> ...`.
"""

import pytest

from squads._cli import _hoist_global_options as hoist


def test_leading_global_options_are_left_untouched():
    assert hoist(["--at", "2024-01-01", "create", "task", "X"]) == [
        "--at",
        "2024-01-01",
        "create",
        "task",
        "X",
    ]


def test_a_trailing_global_option_is_hoisted_to_the_front():
    assert hoist(["create", "task", "X", "--at", "2024-01-01"]) == [
        "--at",
        "2024-01-01",
        "create",
        "task",
        "X",
    ]


def test_the_equals_form_is_hoisted_too():
    assert hoist(["list", "--dir=/s", "--at=2024-01-01"]) == ["--dir=/s", "--at=2024-01-01", "list"]


def test_a_dangling_at_with_no_value_is_left_for_click_to_report():
    assert hoist(["create", "task", "X", "--at"]) == ["create", "task", "X", "--at"]


def test_a_trailing_dir_with_no_value_is_hoisted_in_its_equals_form_so_it_reaches_the_refusal():
    assert hoist(["list", "--dir"]) == ["--dir=", "list"]


def test_c_is_never_hoisted():
    assert hoist(["task", "3", "comment", "-m", "-C", "list", "--at", "2024-01-01"]) == [
        "--at",
        "2024-01-01",
        "task",
        "3",
        "comment",
        "-m",
        "-C",
        "list",
    ]


#: Tokens that spell a global option but are not one: an option's value, or after ``--``.
_NOT_OPTIONS = {
    "a trailing --dir that is the value of -m": ["task", "3", "comment", "-m", "--dir"],
    "a --dir that is the value of -m": ["task", "3", "comment", "-m", "--dir", "x"],
    "a --dir after the separator": ["task", "3", "comment", "--", "--dir"],
    "a --dir with a value after the separator": ["create", "task", "--", "--dir", "x"],
    "an --at after the separator": ["create", "task", "--", "--at", "x"],
    "a --dir that is the value of -C": ["-C", "--dir", "list"],
    "an --at that is the value of -C": ["-C", "--at", "list"],
    "a --dir= that is the value of -m": ["task", "3", "comment", "-m", "--dir=x"],
}


@pytest.mark.parametrize("row", _NOT_OPTIONS)
def test_a_token_that_is_not_an_option_of_its_own_is_left_where_it_is(row: str):
    assert hoist(_NOT_OPTIONS[row]) == _NOT_OPTIONS[row]


def test_a_global_option_before_the_separator_is_still_hoisted():
    assert hoist(["create", "task", "--at", "x", "--", "--dir"]) == [
        "--at",
        "x",
        "create",
        "task",
        "--",
        "--dir",
    ]


def test_nothing_to_hoist_leaves_the_arguments_unchanged():
    assert hoist(["create", "task", "X"]) == ["create", "task", "X"]


def test_completion_flags_are_passed_through_untouched():
    # --show-completion/--install-completion are not global value-options and must not be
    # mistaken for one, or their shell-name argument would be reordered away from them.
    assert hoist(["--show-completion", "bash"]) == ["--show-completion", "bash"]
    assert hoist(["--show-completion", "zsh"]) == ["--show-completion", "zsh"]
    assert hoist(["--install-completion", "zsh"]) == ["--install-completion", "zsh"]


def test_a_real_global_option_mixed_after_a_completion_flag_is_hoisted_around_it():
    result = hoist(["--show-completion", "bash", "--dir", "/tmp"])
    assert result == ["--dir", "/tmp", "--show-completion", "bash"]


def test_the_value_option_table_is_built_once_per_process():
    from squads._cli._common import value_options

    assert value_options() is value_options()
    assert {"-C", "--at", "-m"} <= value_options()
