"""Read-backs the roster and notebook CLI tests share: an item's stored body, who a write was
attributed to, and the error box Click prints for a refused command line."""

from tests.cli._output import read_json

#: The usage line and error box Click prints for a refused command line, by what is missing.
ERROR_BOX_TOP = "╭─ Error ──────────────────────────────────────────────────────────────────────╮\n"
ERROR_BOX_BOTTOM = (
    "╰──────────────────────────────────────────────────────────────────────────────╯\n"
)


def usage_error(usage: str, hint: str, message: str) -> str:
    """The whole output of a command line Click refuses: the usage, the help hint and the boxed
    *message*, padded as the 80-column box prints it."""
    return f"{usage}\nTry '{hint}' for help.\n{ERROR_BOX_TOP}│ {message:<76} │\n{ERROR_BOX_BOTTOM}"


async def body_of(invoke, number: int) -> str:
    """The stored body of the item numbered *number*, as `sq show --json` prints it."""
    return (await read_json(invoke, ["show", str(number), "--json"]))["body"]


async def actors_of(invoke, item_id: str, op: str) -> list[str]:
    """The actors of the reflog entries of operation *op* on *item_id*, oldest first."""
    entries = await read_json(invoke, ["reflog", "--item", item_id, "--op", op, "--json"])
    return [entry["actor"] for entry in entries]


def panel_rows(output: str) -> list[str]:
    """The rows a styled show prints inside its panel, one string per row."""
    return [line.strip("│ ") for line in output.splitlines() if line.startswith("│")]


def as_bullets(rows: list[str], *, unlabelled_first: bool) -> str:
    """Panel *rows* as the list `--raw` prints: ``- **label:** value``, with a plain first bullet
    when the first row has no label."""
    bullets = []
    for number, row in enumerate(rows):
        if unlabelled_first and number == 0:
            bullets.append(f"- {row}")
            continue
        label, _, value = row.partition(": ")
        bullets.append(f"- **{label}:** {value}")
    return "\n".join(bullets)


async def raw_forms(invoke, monkeypatch, argv: list[str]) -> tuple[str, str, str]:
    """A roster entry's panel rows as the list `--raw` should print, its `--raw` output and its
    `--raw --no-header` output, the last two with a forced colour and a narrow width."""
    expected = as_bullets(panel_rows(await _printed(invoke, argv)), unlabelled_first=True)
    forced_colour(monkeypatch)
    return (
        expected,
        await _printed(invoke, [*argv, "--raw"]),
        await _printed(invoke, [*argv, "--raw", "--no-header"]),
    )


async def _printed(invoke, argv: list[str]) -> str:
    result = await invoke(argv)
    assert result.exit_code == 0, result.output
    return result.output


def forced_colour(monkeypatch) -> None:
    """Make the invocation's console a coloured terminal 40 columns wide, as `FORCE_COLOR` does."""
    monkeypatch.setenv("FORCE_COLOR", "3")
    monkeypatch.setenv("TTY_COMPATIBLE", "1")
    monkeypatch.setenv("COLUMNS", "40")


def forced_terminal(monkeypatch) -> None:
    """Make the invocation's console behave as a terminal without colour, so rendering that a pipe
    skips (markdown bodies) runs."""
    monkeypatch.setenv("TERM", "dumb")
    monkeypatch.setenv("TTY_COMPATIBLE", "1")
