"""The comment verbs, tested on the `task` host: the `comment` group (`-m`, `--file`, `--as`, the
`HASH` argument) and its `show`, `edit` and `remove`. One case each addresses a comment through the
sub-entity, role, skill and operator hosts.

Every other host is held by the verb-set parity guard, so the verbs' parameters are not repeated
per host.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from rich.console import Console

from tests.cli._populated import TASK

pytestmark = pytest.mark.anyio

UNKNOWN_SLUG = "error: unknown slug 'ghost'; valid slugs: manager\n"
NO_AS = "error: --as is required: the actor's slug\n"
NO_TEXT = "error: provide the comment via -m (repeatable) or --file PATH ('-' for stdin)\n"
BOTH = "error: provide the comment via -m or --file, not both\n"
NOT_A_HASH = (
    "error: {token!r} is not a comment hash (4 or more hex characters); "
    "a new comment takes -m or --file\n"
)


def _write_file(name: str = "text.md", text: str = "From a file\n") -> None:
    Path(name).write_text(text, encoding="utf-8")


async def _ran(invoke, args: list[str], **kw: Any) -> tuple[int, str]:
    result = await invoke(args, **kw)
    return result.exit_code, result.output


async def _ok(invoke, args: list[str], **kw: Any) -> str:
    code, output = await _ran(invoke, args, **kw)
    assert code == 0, output
    return output


async def _comments(invoke, host: list[str] | None = None) -> list[dict[str, Any]]:
    """The host's top-level comments, read back through `comments` (the task by default)."""
    return json.loads(await _ok(invoke, [*(host or ["task", str(TASK)]), "comments", "--json"]))


async def _post(invoke, text: str, who: str = "manager", host: list[str] | None = None) -> str:
    """Add a comment to *host* (the task by default) and return its short hash."""
    target = host or ["task", str(TASK)]
    await _ok(invoke, [*target, "comment", "-m", text, "--as", who])
    return (await _comments(invoke, target))[-1]["short_hash"]


async def _add_operator(invoke) -> str:
    await _ok(invoke, ["operator", "add", "Pierre Chat"])
    return "op-pierre"


async def _actors(invoke, target: str, op: str) -> list[str]:
    entries = json.loads(await _ok(invoke, ["reflog", "--item", target, "--op", op, "--json"]))
    return [e["actor"] for e in entries]


# --- the group: adding a comment ------------------------------------------------------------


@pytest.mark.covers("<host> comment", "--message")
async def test_comment_message_adds_each_message_as_a_bullet(populated_project, invoke) -> None:
    out = await _ran(
        invoke, ["task", str(TASK), "comment", "-m", "First", "-m", "Second", "--as", "manager"]
    )
    assert out == (0, "commented on TASK-3 as manager\n")
    [comment] = await _comments(invoke)
    assert (comment["author_slug"], comment["body"]) == ("manager", "- First\n- Second")


@pytest.mark.covers("<host> comment", "--file")
async def test_comment_file_reads_the_text_from_a_file(populated_project, invoke) -> None:
    _write_file()
    await _ok(invoke, ["task", str(TASK), "comment", "--file", "text.md", "--as", "manager"])
    assert [c["body"] for c in await _comments(invoke)] == ["- From a file"]


@pytest.mark.covers("<host> comment", "--file")
async def test_comment_file_reads_the_text_from_stdin_for_a_dash(populated_project, invoke) -> None:
    await _ok(
        invoke, ["task", str(TASK), "comment", "--file", "-", "--as", "manager"], input="Piped in\n"
    )
    assert [c["body"] for c in await _comments(invoke)] == ["- Piped in"]


@pytest.mark.covers("<host> comment", "--file")
async def test_comment_refuses_a_file_that_does_not_exist(populated_project, invoke) -> None:
    out = await _ran(
        invoke, ["task", str(TASK), "comment", "--file", "missing.md", "--as", "manager"]
    )
    assert out == (1, "error: cannot read file 'missing.md': No such file or directory\n")


@pytest.mark.covers("<host> comment", "--message")
async def test_comment_refuses_a_call_with_no_text(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(TASK), "comment", "--as", "manager"]) == (1, NO_TEXT)


@pytest.mark.covers("<host> comment", "--message", "--file")
async def test_comment_refuses_message_with_file(populated_project, invoke) -> None:
    _write_file()
    out = await _ran(
        invoke, ["task", str(TASK), "comment", "-m", "x", "--file", "text.md", "--as", "manager"]
    )
    assert out == (1, BOTH)
    assert await _comments(invoke) == []


@pytest.mark.covers("<host> comment", "--as")
async def test_comment_as_names_the_author_of_the_comment(populated_project, invoke) -> None:
    slug = await _add_operator(invoke)
    await _ok(invoke, ["task", str(TASK), "comment", "-m", "Mine", "--as", "manager"])
    await _ok(invoke, ["task", str(TASK), "comment", "-m", "Theirs", "--as", slug])
    assert [(c["author_slug"], c["author"]) for c in await _comments(invoke)] == [
        ("manager", "Catherine Manager"),
        (slug, "Pierre Chat"),
    ]
    assert await _actors(invoke, "TASK-3", "comment") == ["manager", slug]


@pytest.mark.covers("<host> comment", "--as")
async def test_comment_refuses_a_call_with_no_author(populated_project, invoke) -> None:
    assert await _ran(invoke, ["task", str(TASK), "comment", "-m", "x"]) == (1, NO_AS)


@pytest.mark.covers("<host> comment", "--as")
async def test_comment_refuses_an_author_no_roster_entry_has(populated_project, invoke) -> None:
    out = await _ran(invoke, ["task", str(TASK), "comment", "-m", "x", "--as", "ghost"])
    assert out == (1, UNKNOWN_SLUG)


@pytest.mark.covers("<host> comment", "--as")
async def test_comment_refuses_the_reserved_system_slug_as_author(
    populated_project, invoke
) -> None:
    out = await _ran(invoke, ["task", str(TASK), "comment", "-m", "x", "--as", "squads"])
    assert out == (1, "error: cannot act as 'squads': that slug is reserved for system entries\n")
    assert await _comments(invoke) == []


@pytest.mark.covers("<host> comment", "--file")
async def test_comment_refuses_an_empty_file(populated_project, invoke) -> None:
    _write_file(text="\n")
    out = await _ran(invoke, ["task", str(TASK), "comment", "--file", "text.md", "--as", "manager"])
    assert out == (1, "error: --file must not be empty\n")


# --- the group: HASH ------------------------------------------------------------------------


@pytest.mark.covers("<host> comment", "HASH")
async def test_comment_addresses_a_comment_by_four_or_more_leading_hex_characters(
    populated_project, invoke
) -> None:
    short = await _post(invoke, "Findable")
    [full] = [c["hash"] for c in await _comments(invoke)]
    by_short = json.loads(
        await _ok(invoke, ["task", str(TASK), "comment", short, "show", "--json"])
    )
    by_four = json.loads(
        await _ok(invoke, ["task", str(TASK), "comment", full[:4], "show", "--json"])
    )
    by_full = json.loads(await _ok(invoke, ["task", str(TASK), "comment", full, "show", "--json"]))
    assert by_short == by_four == by_full
    assert by_short["body"] == "- Findable"


@pytest.mark.covers("<host> comment", "HASH")
async def test_comment_refuses_a_token_that_is_not_a_hash(populated_project, invoke) -> None:
    out = await _ran(invoke, ["task", str(TASK), "comment", "abc", "show"])
    assert out == (2, NOT_A_HASH.format(token="abc"))


@pytest.mark.covers("<host> comment", "HASH")
async def test_comment_refuses_a_hash_with_no_verb(populated_project, invoke) -> None:
    short = await _post(invoke, "Findable")
    assert await _ran(invoke, ["task", str(TASK), "comment", short]) == (
        2,
        f"error: missing verb after {short}: show|edit|remove\n",
    )


@pytest.mark.covers("<host> comment", "HASH")
async def test_comment_refuses_a_hash_no_comment_carries(populated_project, invoke) -> None:
    await _post(invoke, "Findable")
    assert await _ran(invoke, ["task", str(TASK), "comment", "dead", "show"]) == (
        1,
        "error: no comment dead in TASK-3's discussion (edited or removed since it was read?)\n",
    )


@pytest.mark.covers("<host> comment", "--as", "HASH")
async def test_comment_refuses_message_before_the_verb(populated_project, invoke) -> None:
    short = await _post(invoke, "Findable")
    out = await _ran(invoke, ["task", str(TASK), "comment", "--as", "manager", short, "show"])
    assert out == (
        2,
        "error: -m, --file and --as go after the verb: comment HASH edit -m TEXT --as SLUG\n",
    )


# --- show -----------------------------------------------------------------------------------


@pytest.mark.covers("<host> comment show", "--json")
async def test_show_json_prints_the_comment_as_one_object(populated_project, invoke) -> None:
    short = await _post(invoke, "Findable")
    [listed] = await _comments(invoke)
    shown = json.loads(await _ok(invoke, ["task", str(TASK), "comment", short, "show", "--json"]))
    assert shown == {**listed, "item": "TASK-3", "scope": None, "copies": 1}


@pytest.mark.covers("<host> comment show")
async def test_show_prints_the_item_and_the_comment(populated_project, invoke) -> None:
    short = await _post(invoke, "Findable")
    assert await _ran(invoke, ["task", str(TASK), "comment", short, "show"]) == (
        0,
        f"TASK-3\n--- {short} [2026-06-07T10:00:00Z] Catherine Manager (manager) ---\n"
        "- Findable\n\n",
    )


@pytest.mark.covers("<host> comment show", "--raw")
async def test_show_raw_prints_plain_text_where_a_terminal_gets_a_panel(
    populated_project, invoke, monkeypatch
) -> None:
    short = await _post(invoke, "Findable")
    monkeypatch.setattr(Console, "is_terminal", property(lambda self: True))
    monkeypatch.setenv("TERM", "dumb")  # a terminal without colour, as the console is built per run
    raw = await _ran(invoke, ["task", str(TASK), "comment", short, "show", "--raw"])
    styled = await _ran(invoke, ["task", str(TASK), "comment", short, "show"])
    assert raw == (
        0,
        f"TASK-3\n--- {short} [2026-06-07T10:00:00Z] Catherine Manager (manager) ---\n"
        "- Findable\n\n",
    )
    assert styled == (
        0,
        f"TASK-3\n╭───────── {short}  2026-06-07T10:00:00Z  Catherine Manager (manager) "
        "─────────╮\n"
        f"│{'':78}│\n"
        f"│{'  • Findable':78}│\n"
        f"╰{'─' * 78}╯\n",
    )


# --- edit -----------------------------------------------------------------------------------


@pytest.mark.covers("<host> comment edit", "--message")
async def test_edit_message_replaces_the_text_and_marks_the_edit(populated_project, invoke) -> None:
    short = await _post(invoke, "Before")
    out = await _ran(
        invoke, ["task", str(TASK), "comment", short, "edit", "-m", "After", "--as", "manager"]
    )
    [edited] = await _comments(invoke)
    assert out == (
        0,
        f"edited {short} on TASK-3 (manager, 2026-06-07T10:00:00Z); now {edited['short_hash']}\n",
    )
    assert (edited["body"], edited["edited_ts"]) == ("- After", "2026-06-07T10:00:00Z")
    assert edited["short_hash"] != short


@pytest.mark.covers("<host> comment edit", "--message")
async def test_edit_says_so_when_the_text_is_the_same(populated_project, invoke) -> None:
    short = await _post(invoke, "Same")
    out = await _ran(
        invoke, ["task", str(TASK), "comment", short, "edit", "-m", "Same", "--as", "manager"]
    )
    assert out == (0, f"{short} on TASK-3 is unchanged; nothing written\n")


@pytest.mark.covers("<host> comment edit", "--file")
async def test_edit_file_replaces_the_text_with_the_file(populated_project, invoke) -> None:
    short = await _post(invoke, "Before")
    _write_file()
    await _ok(
        invoke,
        ["task", str(TASK), "comment", short, "edit", "--file", "text.md", "--as", "manager"],
    )
    assert [c["body"] for c in await _comments(invoke)] == ["- From a file"]


@pytest.mark.covers("<host> comment edit", "--file")
async def test_edit_file_reads_the_text_from_stdin_for_a_dash(populated_project, invoke) -> None:
    short = await _post(invoke, "Before")
    await _ok(
        invoke,
        ["task", str(TASK), "comment", short, "edit", "--file", "-", "--as", "manager"],
        input="Piped in\n",
    )
    assert [c["body"] for c in await _comments(invoke)] == ["- Piped in"]


@pytest.mark.covers("<host> comment edit", "--file")
async def test_edit_refuses_a_file_that_does_not_exist(populated_project, invoke) -> None:
    short = await _post(invoke, "Before")
    out = await _ran(
        invoke,
        ["task", str(TASK), "comment", short, "edit", "--file", "missing.md", "--as", "manager"],
    )
    assert out == (1, "error: cannot read file 'missing.md': No such file or directory\n")


@pytest.mark.covers("<host> comment edit", "--message")
async def test_edit_refuses_a_call_with_no_text(populated_project, invoke) -> None:
    short = await _post(invoke, "Before")
    out = await _ran(invoke, ["task", str(TASK), "comment", short, "edit", "--as", "manager"])
    assert out == (1, NO_TEXT)


@pytest.mark.covers("<host> comment edit", "--message", "--file")
async def test_edit_refuses_message_with_file(populated_project, invoke) -> None:
    short = await _post(invoke, "Before")
    _write_file()
    out = await _ran(
        invoke,
        [
            "task",
            str(TASK),
            "comment",
            short,
            "edit",
            "-m",
            "x",
            "--file",
            "text.md",
            "--as",
            "manager",
        ],
    )
    assert out == (1, BOTH)
    assert [c["body"] for c in await _comments(invoke)] == ["- Before"]


@pytest.mark.covers("<host> comment edit", "--as")
async def test_edit_as_refuses_a_comment_written_by_someone_else(populated_project, invoke) -> None:
    slug = await _add_operator(invoke)
    short = await _post(invoke, "Theirs", who=slug)
    out = await _ran(
        invoke, ["task", str(TASK), "comment", short, "edit", "-m", "Mine", "--as", "manager"]
    )
    assert out == (
        1,
        f"error: {short} on TASK-3 was written by {slug}; --as manager cannot change it\n",
    )
    assert [c["body"] for c in await _comments(invoke)] == ["- Theirs"]


@pytest.mark.covers("<host> comment edit", "--as")
async def test_edit_lets_the_author_change_their_own_comment(populated_project, invoke) -> None:
    slug = await _add_operator(invoke)
    short = await _post(invoke, "Mine", who=slug)
    await _ok(invoke, ["task", str(TASK), "comment", short, "edit", "-m", "Edited", "--as", slug])
    assert [c["body"] for c in await _comments(invoke)] == ["- Edited"]


@pytest.mark.covers("<host> comment edit", "--as")
async def test_edit_refuses_a_call_with_no_author(populated_project, invoke) -> None:
    short = await _post(invoke, "Before")
    assert await _ran(invoke, ["task", str(TASK), "comment", short, "edit", "-m", "x"]) == (
        1,
        NO_AS,
    )


@pytest.mark.covers("<host> comment edit", "--as")
async def test_edit_refuses_an_author_no_roster_entry_has(populated_project, invoke) -> None:
    short = await _post(invoke, "Before")
    out = await _ran(
        invoke, ["task", str(TASK), "comment", short, "edit", "-m", "x", "--as", "ghost"]
    )
    assert out == (1, UNKNOWN_SLUG)


@pytest.mark.covers("<host> comment edit", "--json")
async def test_edit_json_prints_the_edited_comment(populated_project, invoke) -> None:
    short = await _post(invoke, "Before")
    output = await _ok(
        invoke,
        ["task", str(TASK), "comment", short, "edit", "-m", "After", "--as", "manager", "--json"],
    )
    expected = {
        "author": "Catherine Manager",
        "author_slug": "manager",
        "ts": "2026-06-07T10:00:00Z",
        "edited_ts": "2026-06-07T10:00:00Z",
        "hash": "e34c02b36223c904e8969444c9aa3b849d554bd3cd214a754b2d20a0d2e1f341",
        "short_hash": "e34c02b",
        "body": "- After",
        "item": "TASK-3",
        "scope": None,
        "changed": True,
        "previous": {
            "author": "Catherine Manager",
            "author_slug": "manager",
            "ts": "2026-06-07T10:00:00Z",
            "edited_ts": None,
            "hash": "9d413994b321bdff71aa11cb8d0f1c9489355e096ee2b05afe3ef2551cde7bb4",
            "short_hash": "9d41399",
            "body": "- Before",
        },
    }
    assert output == json.dumps(expected, indent=2) + "\n"


# --- remove ---------------------------------------------------------------------------------


@pytest.mark.covers("<host> comment remove", "--yes")
async def test_remove_yes_deletes_the_comment_without_asking(populated_project, invoke) -> None:
    short = await _post(invoke, "Doomed")
    out = await _ran(
        invoke, ["task", str(TASK), "comment", short, "remove", "--as", "manager", "--yes"]
    )
    assert out == (0, f"removed {short} from TASK-3\n")
    assert await _comments(invoke) == []


@pytest.mark.covers("<host> comment remove", "--as")
async def test_remove_asks_for_confirmation_and_keeps_the_comment_when_declined(
    populated_project, invoke
) -> None:
    short = await _post(invoke, "Kept")
    out = await _ran(
        invoke, ["task", str(TASK), "comment", short, "remove", "--as", "manager"], input="n\n"
    )
    assert out == (
        1,
        "2026-06-07T10:00:00Z manager: - Kept\nRemove this comment? [y/N]: n\nAborted.\n",
    )
    assert [c["body"] for c in await _comments(invoke)] == ["- Kept"]


@pytest.mark.covers("<host> comment remove", "--as")
async def test_remove_deletes_the_comment_when_confirmed(populated_project, invoke) -> None:
    short = await _post(invoke, "Doomed")
    out = await _ran(
        invoke, ["task", str(TASK), "comment", short, "remove", "--as", "manager"], input="y\n"
    )
    assert out == (
        0,
        f"2026-06-07T10:00:00Z manager: - Doomed\nRemove this comment? [y/N]: y\n"
        f"removed {short} from TASK-3\n",
    )
    assert await _comments(invoke) == []


@pytest.mark.covers("<host> comment remove", "--json")
async def test_remove_json_prints_each_removed_comment(populated_project, invoke) -> None:
    short = await _post(invoke, "Doomed")
    [listed] = await _comments(invoke)
    printed = json.loads(
        await _ok(
            invoke,
            ["task", str(TASK), "comment", short, "remove", "--as", "manager", "--yes", "--json"],
        )
    )
    assert printed == [listed]


@pytest.mark.covers("<host> comment remove", "--as")
async def test_remove_as_refuses_a_comment_written_by_someone_else(
    populated_project, invoke
) -> None:
    slug = await _add_operator(invoke)
    short = await _post(invoke, "Theirs", who=slug)
    out = await _ran(
        invoke, ["task", str(TASK), "comment", short, "remove", "--as", "manager", "--yes"]
    )
    assert out == (
        1,
        f"error: {short} on TASK-3 was written by {slug}; --as manager cannot change it\n",
    )
    assert [c["body"] for c in await _comments(invoke)] == ["- Theirs"]


@pytest.mark.covers("<host> comment remove", "--as")
async def test_remove_lets_the_author_delete_their_own_comment(populated_project, invoke) -> None:
    slug = await _add_operator(invoke)
    short = await _post(invoke, "Mine", who=slug)
    await _ok(invoke, ["task", str(TASK), "comment", short, "remove", "--as", slug, "--yes"])
    assert await _comments(invoke) == []


@pytest.mark.covers("<host> comment remove", "--as")
async def test_remove_refuses_a_call_with_no_author(populated_project, invoke) -> None:
    short = await _post(invoke, "Doomed")
    assert await _ran(invoke, ["task", str(TASK), "comment", short, "remove", "--yes"]) == (
        1,
        NO_AS,
    )


@pytest.mark.covers("<host> comment remove", "--as")
async def test_remove_refuses_an_author_no_roster_entry_has(populated_project, invoke) -> None:
    short = await _post(invoke, "Doomed")
    out = await _ran(
        invoke, ["task", str(TASK), "comment", short, "remove", "--as", "ghost", "--yes"]
    )
    assert out == (1, UNKNOWN_SLUG)


# --- the other hosts ------------------------------------------------------------------------


@pytest.mark.covers("<type> <kind>", "LOCAL-ID")
async def test_a_subtask_addresses_its_own_discussion(populated_project, invoke) -> None:
    host = ["task", str(TASK), "subtask", "1"]
    await _ok(invoke, [*host, "comment", "-m", "On the subtask", "--as", "manager"])
    [posted] = json.loads(await _ok(invoke, [*host, "show", "--json"]))["discussion"]
    shown = json.loads(
        await _ok(invoke, [*host, "comment", posted["short_hash"], "show", "--json"])
    )
    assert (shown["item"], shown["body"]) == ("TASK-3", "- On the subtask")
    assert await _comments(invoke) == []


@pytest.mark.covers("<type> <kind>", "LOCAL-ID")
async def test_a_comment_on_a_subtask_the_item_lacks_names_the_subtask(
    populated_project, invoke
) -> None:
    out = await _ran(
        invoke, ["task", str(TASK), "subtask", "9", "comment", "-m", "x", "--as", "manager"]
    )
    assert out == (1, "error: no subtask ST9 in TASK-3\n")


@pytest.mark.covers("role", "<slug|id|n>")
async def test_a_role_addresses_its_own_discussion(populated_project, invoke) -> None:
    host = ["role", "manager"]
    short = await _post(invoke, "On the role", host=host)
    shown = json.loads(await _ok(invoke, [*host, "comment", short, "show", "--json"]))
    assert (shown["item"], shown["body"]) == ("ROLE-1", "- On the role")
    await _ok(invoke, [*host, "comment", short, "remove", "--as", "manager", "--yes"])
    assert await _comments(invoke, host) == []


@pytest.mark.covers("skill", "<slug|id|n>")
async def test_a_skill_addresses_its_own_discussion(populated_project, invoke) -> None:
    await _ok(invoke, ["skill", "add", "Query tips"])
    host = ["skill", "query-tips"]
    short = await _post(invoke, "On the skill", host=host)
    shown = json.loads(await _ok(invoke, [*host, "comment", short, "show", "--json"]))
    assert shown["body"] == "- On the skill"
    assert shown["item"] == "SKILL-5"
    await _ok(invoke, [*host, "comment", short, "edit", "-m", "Reworded", "--as", "manager"])
    assert [c["body"] for c in await _comments(invoke, host)] == ["- Reworded"]


@pytest.mark.covers("operator", "<slug|id|n>")
async def test_an_operator_addresses_its_own_discussion(populated_project, invoke) -> None:
    slug = await _add_operator(invoke)
    host = ["operator", slug]
    short = await _post(invoke, "On the operator", who=slug, host=host)
    shown = json.loads(await _ok(invoke, [*host, "comment", short, "show", "--json"]))
    assert (shown["item"], shown["body"]) == ("OP-5", "- On the operator")
    await _ok(invoke, [*host, "comment", short, "remove", "--as", slug, "--yes"])
    assert await _comments(invoke, host) == []


# --- the added comment, with --json --------------------------------------------------------


@pytest.mark.covers("<host> comment", "--json")
async def test_comment_json_prints_the_added_comment(populated_project, invoke) -> None:
    await _post(invoke, "Earlier")
    printed = await _ok(
        invoke, ["task", str(TASK), "comment", "-m", "Hello", "--as", "manager", "--json"]
    )
    [_, listed] = await _comments(invoke)
    # Compared as text, so the key order is held as well as the content.
    expected = {
        "author": "Catherine Manager",
        "author_slug": "manager",
        "ts": "2026-06-07T10:00:00Z",
        "edited_ts": None,
        "hash": listed["hash"],
        "short_hash": listed["short_hash"],
        "body": "- Hello",
        "item": "TASK-3",
        "scope": None,
        "copies": 1,
    }
    assert printed == json.dumps({"entry": expected}, indent=2) + "\n"


@pytest.mark.covers("<host> comment", "--json")
async def test_comment_refuses_json_before_a_verb(populated_project, invoke) -> None:
    short = await _post(invoke, "Findable")
    out = await _ran(invoke, ["task", str(TASK), "comment", "--json", short, "show"])
    assert out == (2, "error: --json goes after the verb: comment HASH show --json\n")


@pytest.mark.covers("<host> comment remove", "--json")
async def test_remove_json_previews_and_asks_on_stderr_and_prints_only_the_document_on_stdout(
    populated_project, invoke
) -> None:
    short = await _post(invoke, "Doomed")
    [listed] = await _comments(invoke)
    result = await invoke(
        ["task", str(TASK), "comment", short, "remove", "--as", "manager", "--json"],
        input="y\n",
    )
    assert result.exit_code == 0, result.output
    assert result.stdout == json.dumps([listed], indent=2) + "\n"
    assert result.stderr == ("2026-06-07T10:00:00Z manager: - Doomed\nRemove this comment? [y/N]: ")
