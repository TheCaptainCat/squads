"""``--help`` text wraps identically regardless of the invoking terminal's inherited COLUMNS
— the width analogue of the FORCE_COLOR neutralization, carried by the root conftest's
autouse ``_neutralize_forced_color`` fixture (which pins COLUMNS=80 by default).

Widths are measured on ANSI-stripped text: some consoles (observed in CI) colorize ``--help``
output even with the color-forcing env vars neutralized, and the invisible SGR escape bytes
would otherwise inflate ``len(line)`` past the pinned visual width.
"""

from _helpers import strip_ansi


def test_default_help_output_wraps_within_the_pinned_eighty_columns(runner) -> None:
    from squads._cli import app

    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0, result.output
    output = strip_ansi(result.output)
    longest_line = max((len(line) for line in output.splitlines()), default=0)
    assert longest_line <= 80, f"help output exceeded the pinned 80-column width: {longest_line}"


def test_columns_genuinely_drives_the_wrap_width_proving_the_pin_is_load_bearing(
    runner, monkeypatch
) -> None:
    """Rich re-detects terminal width from COLUMNS per render, not once at import — so an
    un-pinned ambient COLUMNS really would make help-text assertions terminal-dependent."""
    from squads._cli import app

    monkeypatch.setenv("COLUMNS", "40")
    narrow = strip_ansi(runner.invoke(app, ["--help"]).output)
    monkeypatch.setenv("COLUMNS", "200")
    wide = strip_ansi(runner.invoke(app, ["--help"]).output)
    assert narrow != wide
    assert max(len(line) for line in narrow.splitlines()) <= 40
