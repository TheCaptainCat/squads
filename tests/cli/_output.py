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


def without_hashes(comments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """*comments* with the content digest each carries (`hash`, and its prefix `short_hash`) set
    aside, once the prefix is shown to belong to it; every other field is left for the caller to
    compare."""
    for comment in comments:
        assert comment["hash"].startswith(comment["short_hash"])
    return [{k: v for k, v in c.items() if k not in ("hash", "short_hash")} for c in comments]


def pull_report(name: str = "platform", **given: Any) -> dict[str, Any]:
    """One source's entry of the `source pull --json` document: an empty pull of *name*, with the
    fields a case is about given."""
    return {
        "name": name,
        "created": [],
        "refreshed": 0,
        "unchanged": 0,
        "left_out": None,
        "lines": [],
        "failed": False,
        "dropped": 0,
        "gone": 0,
        "restricted": 0,
        "held_elsewhere": 0,
        "filtered_out": 0,
        "skipped_no_type": 0,
        **given,
    }


def pull_document(*reports: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
    """The `source pull --json` document of *reports*."""
    return {"dry_run": dry_run, "sources": list(reports)}


#: The row `list --json` shows for the squad's one role, which every squad of the suite starts
#: with; it is the same on the bundled squad and the override squad.
MANAGER_ROW: dict[str, Any] = {
    "sequence_id": 1,
    "type": "role",
    "title": "Catherine Manager",
    "slug": "manager",
    "status": "Active",
    "description": "",
    "parent": None,
    "author": "manager",
    "assignee": None,
    "labels": [],
    "refs": [],
    "subentities": [],
    "path": "agents/roles/ROLE-000001-manager.md",
    "created_at": "2026-06-07T10:00:00Z",
    "updated_at": "2026-06-07T10:00:00Z",
    "created_session": None,
    "modified_session": None,
    "id": "ROLE-1",
    "origin": "system",
    "badges": {},
    "display": {
        "type": "Role",
        "status": {"badge": "\u26aa Active", "intent": "positive"},
        "badges": {},
        "assignee": None,
    },
}


def alice_document(identities: dict[str, str]) -> dict[str, Any]:
    """The `operator op-alice show --json` document of the operator `operator add "Alice Tester"`
    makes first, holding *identities*."""
    return {
        "id": "OP-2",
        "slug": "op-alice",
        "full_name": "Alice Tester",
        "pronouns": None,
        "status": "Active",
        "path": "operators/OP-000002-op-alice.md",
        "display": {
            "name": "Alice Tester",
            "pronouns": None,
            "body": (
                "# Alice Tester\n\n**Operator (human)**  \u00b7  **Slug:** `op-alice`\n\n"
                "A human who works on this project \u2014 authors items and review points, and "
                "can be assigned work (including manual steps).\n\n"
                "Attribute their words with `sq <type> <n> comment --as op-alice -m "
                '"\u2026"`,\n'
                "correct or withdraw their comment with `comment <hash> edit|remove --as "
                "op-alice`,\n"
                "and assign work to them with `--assignee op-alice`."
            ),
            "discussion": [],
        },
        "identities": identities,
    }
