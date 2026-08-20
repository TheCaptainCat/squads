"""``--help`` renders unstyled, so a flag name survives in the output as one literal token.

typer builds its own Rich console for help rendering and forces it into terminal mode whenever
the environment looks like a CI runner (``GITHUB_ACTIONS``) or asks for color
(``FORCE_COLOR``/``PY_COLORS``).  Forced-terminal help output is not merely "plain text plus
escapes around it": typer's option highlighter styles ``-`` and ``--flag`` with two overlapping
patterns, so Rich splits the token and emits ``ESC[36m-ESC[0mESC[36m-unlink`` — the substring
``--unlink`` is then nowhere in the output and every ``"--flag" in result.output`` assertion in
the suite fails.  The root conftest pins that console back to non-terminal; these tests hold the
pin in place and prove it is load-bearing.
"""

import typer.rich_utils

from squads._cli import app


def test_help_output_is_plain_text_with_flag_tokens_intact(runner) -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0, result.output
    assert "\x1b[" not in result.output
    assert "--help" in result.output


def test_a_forced_terminal_really_would_split_flag_tokens_proving_the_pin_is_load_bearing(
    runner, monkeypatch
) -> None:
    """Falsify the pin: with typer's console forced back into terminal mode, the very assertion
    the suite relies on breaks — which is what the conftest pin exists to prevent."""
    monkeypatch.setattr(typer.rich_utils, "FORCE_TERMINAL", True)
    output = runner.invoke(app, ["--help"]).output
    assert "\x1b[" in output
    assert "--help" not in output
