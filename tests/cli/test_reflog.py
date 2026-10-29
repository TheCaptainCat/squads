"""`sq reflog`: the log of the commands that changed the squad, each filter alone, the tail limit,
the tree form and the JSON form."""

import json
from typing import Any

import pytest

from tests.cli._readable import init_readable_with_history, lines

pytestmark = pytest.mark.anyio

NEXT_DAY_LINE = '2026-06-08T09:00:00Z  comment  TASK-4  actor=manager  {"author":"manager"}'
LAST_DAY_ONE_LINE = '2026-06-07T10:00:00Z  comment  TASK-3  actor=system  {"author":"manager"}'


@pytest.fixture
def history(copy_squad):
    return copy_squad("history", init_readable_with_history)


async def _reflog(invoke, *args: str) -> tuple[int, list[str]]:
    result = await invoke(["reflog", *args])
    return result.exit_code, lines(result.output)


async def _entries(invoke, *args: str) -> list[dict[str, Any]]:
    result = await invoke(["reflog", "--json", *args])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


async def test_reflog_prints_every_entry_oldest_first(history, invoke) -> None:
    code, out = await _reflog(invoke)
    assert (code, out[0], out[-2:]) == (
        0,
        '2026-06-07T10:00:00Z  create  ROLE-1  actor=system  {"title":"Catherine',
        [LAST_DAY_ONE_LINE, NEXT_DAY_LINE],
    )


async def test_reflog_of_a_new_squad_prints_its_first_entry(project, invoke) -> None:
    assert await _reflog(invoke) == (
        0,
        [
            '2026-06-07T10:00:00Z  create  ROLE-1  actor=system  {"title":"Catherine',
            'Manager","type":"role","status":"Active"}',
        ],
    )


@pytest.mark.covers("reflog", "--item")
async def test_item_keeps_the_entries_on_one_item(history, invoke) -> None:
    assert await _reflog(invoke, "--item", "TASK-4") == (
        0,
        [
            '2026-06-07T10:00:00Z  create  TASK-4  actor=system  {"title":"Rank',
            'results","type":"task","status":"Draft"}',
            "2026-06-07T10:00:00Z  ref  TASK-4  actor=system",
            '{"add":"TASK-3","kind":"depends-on"}',
            "2026-06-07T10:00:00Z  ref  TASK-4  actor=system",
            '{"add":"REV-7","kind":"related"}',
            NEXT_DAY_LINE,
        ],
    )


async def test_item_prints_nothing_for_an_id_no_entry_names(history, invoke) -> None:
    assert await _reflog(invoke, "--item", "TASK-99") == (0, ["no reflog entries"])


@pytest.mark.covers("reflog", "--actor")
async def test_actor_keeps_the_entries_by_one_slug(history, invoke) -> None:
    assert await _reflog(invoke, "--actor", "manager") == (0, [NEXT_DAY_LINE])


@pytest.mark.covers("reflog", "--op")
async def test_op_keeps_the_entries_of_one_operation(history, invoke) -> None:
    assert await _reflog(invoke, "--op", "comment") == (0, [LAST_DAY_ONE_LINE, NEXT_DAY_LINE])


@pytest.mark.covers("reflog", "--since")
async def test_since_keeps_the_entries_at_or_after_the_time(history, invoke) -> None:
    assert await _reflog(invoke, "--since", "2026-06-08") == (0, [NEXT_DAY_LINE])
    assert await _reflog(invoke, "--since", "2026-06-08T09:00:00Z") == (0, [NEXT_DAY_LINE])
    assert await _reflog(invoke, "--since", "2026-06-08T09:00:01Z") == (0, ["no reflog entries"])


async def test_since_refuses_text_that_is_not_an_iso_8601_time(history, invoke) -> None:
    assert await _reflog(invoke, "--since", "notadate") == (
        1,
        [
            "error: invalid --since timestamp 'notadate' (use ISO 8601, e.g. 2026-01-15 or "
            "2026-01-15T09:30:00Z)"
        ],
    )


@pytest.mark.covers("reflog", "--tail")
async def test_tail_keeps_the_latest_entries(history, invoke) -> None:
    assert await _reflog(invoke, "--tail", "2") == (0, [LAST_DAY_ONE_LINE, NEXT_DAY_LINE])
    everything = await _entries(invoke, "--tail", "0")
    assert (everything[0]["target"], everything[-1]["target"]) == ("ROLE-1", "TASK-4")


async def test_tail_refuses_a_value_that_is_not_an_integer(history, invoke) -> None:
    assert await _reflog(invoke, "--tail", "many") == (
        2,
        [
            "Usage: sq reflog [OPTIONS]",
            "Try 'sq reflog --help' for help.",
            "╭─ Error ──────────────────────────────────────────────────────────────────────╮",
            "│ Invalid value for '--tail' / '-n': 'many' is not a valid integer.            │",
            "╰──────────────────────────────────────────────────────────────────────────────╯",
        ],
    )


@pytest.mark.covers("reflog", "--tree")
async def test_tree_groups_the_entries_by_the_session_that_wrote_them(project, invoke) -> None:
    assert await _reflog(invoke, "--tree") == (
        0,
        [
            "Spawn-lineage tree — BEST-EFFORT / UNTRUSTED / OBSERVABILITY-ONLY",
            "Reflects declared lineage; no tamper-evidence or enforcement guarantee.",
            "",
            "reflog",
            "└── actor=system  (no session recorded)",
            '    └── 2026-06-07T10:00:00Z  create  ROLE-1  actor=system  {"title":"Catherine',
            '        Manager","type":"role","status":"Active"}',
        ],
    )


@pytest.mark.covers("reflog", "--json")
async def test_json_prints_one_object_per_entry(history, invoke) -> None:
    assert json.dumps(await _entries(invoke, "--since", "2026-06-08")) == json.dumps(
        [
            {
                "v": "0.17",
                "ts": "2026-06-08T09:00:00Z",
                "actor": "manager",
                "op": "comment",
                "target": "TASK-4",
                "delta": {"author": "manager"},
                "session_id": None,
                "parent_session_id": None,
            }
        ]
    )
