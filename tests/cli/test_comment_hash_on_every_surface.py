"""The hash of a comment is on every surface that shows or finds one: its JSON entry, the first
token of its human header in each render, and the search and inbox hit that lands in it."""

import json
import re

import pytest

from squads import _discussion as discussion
from squads._cli import _common

pytestmark = pytest.mark.anyio

ITEM = ["task", "2"]
SUB = ["task", "2", "subtask", "1"]
COMMENT_KEYS = ["author", "author_slug", "ts", "edited_ts", "hash", "short_hash", "body"]


@pytest.fixture
async def board(project, invoke):
    for argv in (
        ["create", "task", "T", "--author", "manager"],
        ["task", "2", "add-subtask", "Child"],
        [*ITEM, "comment", "--as", "manager", "-m", "needle on the item @manager"],
        [*ITEM, "comment", "--as", "manager", "-m", "second on the item"],
        [*SUB, "comment", "--as", "manager", "-m", "needle on the subtask @manager"],
    ):
        r = await invoke(argv)
        assert r.exit_code == 0, r.output


def _json(r):
    assert r.exit_code == 0, r.output
    return json.loads(r.output)


# (argv, how to reach the entries)
ENTRY_SURFACES = [
    pytest.param(["task", "2", "comments", "--json"], lambda p: p, id="comments"),
    pytest.param(["task", "2", "show", "--json"], lambda p: p["discussion"], id="show-item"),
    pytest.param(
        ["task", "2", "show", "--json"],
        lambda p: p["subentities"][0]["discussion"],
        id="show-subentity-in-item",
    ),
    pytest.param(
        ["task", "2", "subtask", "1", "show", "--json"],
        lambda p: p["discussion"],
        id="show-subentity",
    ),
]


@pytest.mark.parametrize(("argv", "entries"), ENTRY_SURFACES)
async def test_every_json_entry_has_exactly_the_comment_keys(board, invoke, argv, entries) -> None:
    found = entries(_json(await invoke(argv)))

    assert found
    assert all(list(e) == COMMENT_KEYS for e in found)
    assert all(e["short_hash"] == e["hash"][:7] for e in found)


async def test_a_search_hit_in_a_comment_carries_the_hash_that_addresses_it(board, invoke) -> None:
    hits = {
        h["region"]: h["hash"]
        for r in _json(await invoke(["search", "needle", "--json"]))
        for h in r["hits"]
    }

    assert set(hits) >= {"discussion#1", "subtask:ST1:discussion#1"}
    item = _json(await invoke([*ITEM, "comment", hits["discussion#1"][:7], "show", "--json"]))
    sub = _json(
        await invoke([*SUB, "comment", hits["subtask:ST1:discussion#1"][:7], "show", "--json"])
    )
    assert item["body"].startswith("- needle on the item")
    assert sub["body"].startswith("- needle on the subtask")


async def test_a_hit_outside_any_comment_has_no_hash(board, invoke) -> None:
    await invoke([*ITEM, "body", "-m", "a body with needle in it"])

    hits = [h for r in _json(await invoke(["search", "needle", "--json"])) for h in r["hits"]]

    assert {h["region"]: h["hash"] is None for h in hits}["body"]
    assert all(list(h) == ["region", "location", "snippet", "hash"] for h in hits)


async def test_an_inbox_line_in_a_comment_carries_the_hash_that_addresses_it(board, invoke) -> None:
    (entry,) = _json(await invoke(["inbox", "manager", "--json"]))

    assert list(entry) == ["id", "title", "lines", "regions", "hashes"]
    assert len(entry["hashes"]) == len(entry["lines"]) == 2
    by_region = dict(zip(entry["regions"], entry["hashes"], strict=True))
    top, sub = by_region[None], by_region["subtask:ST1:discussion#1"]
    assert _json(await invoke([*ITEM, "comment", top[:7], "show", "--json"]))["hash"] == top
    assert _json(await invoke([*SUB, "comment", sub[:7], "show", "--json"]))["hash"] == sub


async def test_a_separator_inside_an_earlier_comment_does_not_move_the_hit_to_another_hash(
    board, invoke, project
) -> None:
    path = next(project.squad_dir.glob("tasks/TASK-*.md"))
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace("  - needle on the item @manager", f"  - needle{chr(0x2028)}on the item"),
        encoding="utf-8",
    )
    path.write_text(
        path.read_text(encoding="utf-8").replace("second on the item", "later needle"),
        encoding="utf-8",
    )
    comments = _json(await invoke([*ITEM, "comments", "--json"]))

    hits = {
        h["region"]: h["hash"]
        for r in _json(await invoke(["search", "later needle", "--json"]))
        for h in r["hits"]
    }

    assert hits == {"discussion#2": comments[1]["hash"]}


# ------------------------------------------------------------------ human renders

HASH_FIRST = re.compile(r"^(--- |### |)[0-9a-f]{7}[ \]]")


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param([*ITEM, "comments"], id="comments"),
        pytest.param([*ITEM, "show", "--comments"], id="show-comments"),
        pytest.param([*ITEM, "show", "--full", "--comments"], id="show-full-comments"),
        pytest.param([*ITEM, "show", "--raw", "--comments"], id="show-raw-comments"),
        pytest.param([*SUB, "show"], id="subentity-show"),
    ],
)
async def test_each_plain_render_puts_the_short_hash_first_in_every_comment_header(
    board, invoke, argv
) -> None:
    r = await invoke(argv)
    assert r.exit_code == 0, r.output
    entries = (
        _json(await invoke([*ITEM, "comments", "--json"]))
        + _json(await invoke([*SUB, "show", "--json"]))["discussion"]
    )

    headers = [ln for ln in r.output.splitlines() if ln.startswith(("--- ", "### "))]
    shorts = {e["short_hash"] for e in entries}
    assert headers
    assert all(HASH_FIRST.match(h) for h in headers if "[" in h or "###" in h)
    assert all(any(f" {s} " in h or h.startswith(f"--- {s}") for s in shorts) for h in headers)


@pytest.mark.parametrize(
    "argv",
    [[*ITEM, "comments"], [*ITEM, "show", "--comments"], [*SUB, "show"]],
    ids=["comments", "show-comments", "subentity-show"],
)
async def test_each_styled_render_titles_the_pane_with_the_short_hash(
    board, invoke, monkeypatch, argv
) -> None:
    monkeypatch.setattr(_common, "_is_styled", lambda: True)
    shorts = [e["short_hash"] for e in _json(await invoke([*ITEM, "comments", "--json"]))]
    shorts += [e["short_hash"] for e in _json(await invoke([*SUB, "show", "--json"]))["discussion"]]

    r = await invoke(argv)

    assert r.exit_code == 0, r.output
    assert any(s in r.output for s in shorts)


async def test_a_short_hash_is_unique_within_its_discussion_not_across_the_item(
    board, invoke, monkeypatch
) -> None:
    real = discussion.comment_hash

    def collide(seq, scope, slug, ts, text):
        return "abcdefg" + real(seq, scope, slug, ts, text)[7:]

    monkeypatch.setattr(discussion, "comment_hash", collide)

    top = _json(await invoke([*ITEM, "comments", "--json"]))
    sub = _json(await invoke([*SUB, "show", "--json"]))["discussion"]

    assert [len(e["short_hash"]) for e in top] == [8, 8]
    assert [len(e["short_hash"]) for e in sub] == [7]


def test_the_reader_tab_puts_the_short_hash_first_in_every_comment() -> None:
    from squads._tui._reader import _discussion_view

    region = (
        discussion.format_comment("2026-06-07T10:00:00Z", "manager", "Catherine Manager", ["a"])
        + "\n"
        + discussion.format_comment(
            "2026-06-07T10:00:01Z",
            "manager",
            "Catherine Manager",
            ["b"],
            edited_ts="2026-06-08T09:00:00Z",
        )
        + "\n"
    )
    comments = discussion.split_discussion(region, sequence_id=3)

    view = _discussion_view(comments)

    first, second = (b.splitlines()[0] for b in view.split("\n\n---\n\n"))
    shorts = discussion.short_hashes(comments)
    assert first.startswith(f"`{shorts[0]}` **2026-06-07T10:00:00Z**")
    assert second.startswith(f"`{shorts[1]}` **2026-06-07T10:00:01Z**")
    assert second.endswith("(edited 2026-06-08T09:00:00Z)")
