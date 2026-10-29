"""What a CLI test compares a command's output with: the JSON it prints, read back or written out
as the text ``--json`` prints."""

import json
from typing import Any


async def read_json(invoke, args: list[str]) -> Any:
    """The JSON a command that succeeds prints."""
    result = await invoke(args)
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


async def printed(invoke, args: list[str]) -> str:
    """What a command that succeeds prints, compared as text so the key order is held too."""
    result = await invoke(args)
    assert result.exit_code == 0, result.output
    return result.output


def json_text(document: object) -> str:
    """*document* as ``--json`` prints it."""
    return json.dumps(document, indent=2) + "\n"


def entry_text(row: object) -> str:
    """A write that reports nothing beside its entry: the entry under ``entry``, as text."""
    return json_text({"entry": row})


def unknown_option(usage: str, command: str, flag: str, hint: str = "") -> str:
    """What Click prints for an option *command* does not take: its usage lines (*usage*, the
    command as typed after ``sq``, then *command* for the help hint) and the boxed refusal."""
    message = f"No such option: {flag}{hint}"
    return (
        f"Usage: sq {usage}\nTry 'sq {command} --help' for help.\n"
        f"╭─ Error {'─' * 70}╮\n│ {message:<76} │\n╰{'─' * 78}╯\n"
    )
