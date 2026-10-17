"""A comment's author reaches readers as a display name and a permanent slug: ``author`` and
``author_slug`` in every ``--json`` discussion entry, and ``Name (slug)`` in every human render
(the slug once when the name is the slug)."""

import json
import re

import pytest

from squads import _discussion as discussion
from squads._cli import _common
from squads._tui._reader import _discussion_view

pytestmark = pytest.mark.anyio

ROLE = ("Catherine Manager", "manager")
OPERATOR = ("Pierre Chat", "op-pierre")
SENTINEL = ("Operator", "operator")
SYSTEM = ("squads", "squads")
BRACKETED = ("Ann [x] Lee", "op-ann")

TOP_LEVEL = [ROLE, OPERATOR, SENTINEL, SYSTEM]


@pytest.fixture
async def board(project, svc, invoke, frozen_time):
    """The second item, a task, with top-level comments by a role, an operator, the sentinel and a
    system entry, and a subtask whose one comment is by an operator whose name carries ``[x]``."""
    task = await invoke(["create", "task", "Target", "--author", "manager"])
    assert task.exit_code == 0, task.output
    await svc.add_operator("Pierre Chat")
    await svc.add_operator("Ann [x] Lee")
    for who in ("manager", "op-pierre", "operator"):
        r = await invoke(["task", "2", "comment", "--as", who, "-m", f"by {who}"])
        assert r.exit_code == 0, r.output
    await invoke(["task", "2", "add-subtask", "Child"])
    r = await invoke(["task", "2", "subtask", "ST1", "comment", "--as", BRACKETED[1], "-m", "kid"])
    assert r.exit_code == 0, r.output
    r = await invoke(["migrate", "rename-status", "task", "Draft", "Ready"])
    assert r.exit_code == 0, r.output


def _top(payload):
    return payload["discussion"]


def _sub(payload):
    return payload["subentities"][0]["discussion"]


# (id, argv, how to reach the discussion entries, the (name, slug) pairs expected there)
JSON_SURFACES = [
    pytest.param(["task", "2", "comments", "--json"], lambda p: p, TOP_LEVEL, id="comments-verb"),
    pytest.param(["task", "2", "show", "--json"], _top, TOP_LEVEL, id="show-item-discussion"),
    pytest.param(["task", "2", "show", "--json"], _sub, [BRACKETED], id="show-subentity-in-item"),
    pytest.param(
        ["task", "2", "subtask", "ST1", "show", "--json"],
        lambda p: p["discussion"],
        [BRACKETED],
        id="show-subentity-standalone",
    ),
]


@pytest.mark.parametrize(("argv", "entries", "expected"), JSON_SURFACES)
async def test_every_discussion_entry_carries_the_name_and_the_slug(
    board, invoke, argv, entries, expected
) -> None:
    r = await invoke(argv)
    assert r.exit_code == 0, r.output

    found = entries(json.loads(r.output))

    keys = ["author", "author_slug", "ts", "edited_ts", "hash", "short_hash", "body"]
    assert all(list(e) == keys for e in found)
    assert [(e["author"], e["author_slug"]) for e in found] == expected


@pytest.mark.parametrize("argv", [["task", "2", "show", "--json"]])
@pytest.mark.parametrize("flags", [["--raw"], ["--comments"], ["--full"], ["--full", "--comments"]])
async def test_show_json_is_identical_whatever_render_flags_ride_along(
    board, invoke, argv, flags
) -> None:
    plain = await invoke(argv)
    flagged = await invoke([*argv, *flags])

    assert flagged.output == plain.output


@pytest.mark.parametrize("argv", [["search", "by", "--json"], ["inbox", "manager", "--json"]])
async def test_search_and_inbox_json_carry_no_author_slug(board, invoke, argv) -> None:
    r = await invoke(argv)

    assert r.exit_code == 0, r.output
    assert "author_slug" not in r.output


# --------------------------------------------------------------------------- human renders

SHOWN = {
    ROLE: "Catherine Manager (manager)",
    OPERATOR: "Pierre Chat (op-pierre)",
    SENTINEL: "Operator (operator)",
    SYSTEM: "squads",
    BRACKETED: "Ann [x] Lee (op-ann)",
}

# (render, argv, styled, authors it must show)
RENDERS = [
    pytest.param("comments", False, TOP_LEVEL, id="comments-plain"),
    pytest.param("comments", True, TOP_LEVEL, id="comments-styled"),
    pytest.param("show-comments", False, TOP_LEVEL, id="show-comments-plain"),
    pytest.param("show-comments", True, TOP_LEVEL, id="show-comments-styled"),
    pytest.param("show-full-comments", False, [*TOP_LEVEL, BRACKETED], id="show-full-plain"),
    pytest.param("show-full-comments", True, [*TOP_LEVEL, BRACKETED], id="show-full-styled"),
    pytest.param("show-raw-comments", False, TOP_LEVEL, id="show-raw"),
]
ARGV = {
    "comments": ["task", "2", "comments"],
    "show-comments": ["task", "2", "show", "--comments"],
    "show-full-comments": ["task", "2", "show", "--full", "--comments"],
    "show-raw-comments": ["task", "2", "show", "--raw", "--comments"],
}


@pytest.mark.parametrize(("render", "styled", "authors"), RENDERS)
async def test_each_human_render_shows_the_name_then_the_slug(
    board, invoke, monkeypatch, render, styled, authors
) -> None:
    if styled:
        monkeypatch.setattr(_common, "_is_styled", lambda: True)

    r = await invoke(ARGV[render])

    assert r.exit_code == 0, r.output
    for pair in authors:
        assert SHOWN[pair] in r.output, (pair, r.output)
    assert "squads (squads)" not in r.output
    assert not re.search(r"Operator(?! \(operator\))", r.output)


def test_the_reader_tab_shows_the_name_then_the_slug() -> None:
    comments = [
        discussion.Comment("2026-06-07T10:00:00Z", name, slug, "- hi")
        for name, slug in (ROLE, SYSTEM, BRACKETED)
    ]

    view = _discussion_view(comments)

    assert "_Catherine Manager (manager)_" in view
    assert "_squads_" in view and "squads (squads)" not in view
    assert "_Ann [x] Lee (op-ann)_" in view
