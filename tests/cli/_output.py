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
