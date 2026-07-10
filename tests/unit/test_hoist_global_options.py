"""`_hoist_global_options`: the pure function that makes `--at`/`--dir` position-independent
by moving them (and their value) to the front of the argument list, wherever they appear —
so `sq <subcommand> ... --at ...` works exactly like `sq --at ... <subcommand> ...`.
"""

from squads._cli import _hoist_global_options as hoist  # pyright: ignore[reportPrivateUsage]


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
