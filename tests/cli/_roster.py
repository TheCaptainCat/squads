"""Read-backs the roster and notebook CLI tests share: JSON through a command's own output, an
item's stored body, and who a write was attributed to."""

import json
from typing import Any

#: The usage line and error box Click prints for a refused command line, by what is missing.
ERROR_BOX_TOP = "╭─ Error ──────────────────────────────────────────────────────────────────────╮\n"
ERROR_BOX_BOTTOM = (
    "╰──────────────────────────────────────────────────────────────────────────────╯\n"
)


def usage_error(usage: str, hint: str, message: str) -> str:
    """The whole output of a command line Click refuses: the usage, the help hint and the boxed
    *message*, padded as the 80-column box prints it."""
    return f"{usage}\nTry '{hint}' for help.\n{ERROR_BOX_TOP}│ {message:<76} │\n{ERROR_BOX_BOTTOM}"


async def read_json(invoke, args: list[str]) -> Any:
    """The JSON a command that succeeds prints."""
    result = await invoke(args)
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


async def body_of(invoke, number: int) -> str:
    """The stored body of the item numbered *number*, as `sq show --json` prints it."""
    return (await read_json(invoke, ["show", str(number), "--json"]))["body"]


async def actors_of(invoke, item_id: str, op: str) -> list[str]:
    """The actors of the reflog entries of operation *op* on *item_id*, oldest first."""
    entries = await read_json(invoke, ["reflog", "--item", item_id, "--op", op, "--json"])
    return [entry["actor"] for entry in entries]


def forced_terminal(monkeypatch) -> None:
    """Make the shared console behave as a terminal without colour, so rendering that a pipe skips
    (markdown bodies) runs."""
    monkeypatch.setenv("TERM", "dumb")
    monkeypatch.setattr("squads._cli._common.console._force_terminal", True)
