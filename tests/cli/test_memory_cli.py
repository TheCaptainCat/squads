"""CLI smoke for ``sq memory <role> ...``: role is a positional subject (like ``sq inbox``/
``sq mine``) over the memory storage layer. Covers the add->list->show->forget round-trip,
search matching, and clean errors on an unknown role or slug.
"""

import json

import pytest

pytestmark = pytest.mark.anyio


async def test_add_then_list_then_show_then_forget_round_trips_a_memory(project, invoke):
    added = await invoke(["memory", "manager", "add", "the scale suite takes about 4 minutes"])
    assert added.exit_code == 0
    assert "the-scale-suite-takes-about-4-minutes" in added.output

    listed = await invoke(["memory", "manager", "list"])
    assert listed.exit_code == 0
    assert "the-scale-suite-takes-about-4-minutes" in listed.output
    assert "the scale suite takes about 4 minutes" in listed.output

    shown = await invoke(["memory", "manager", "show", "the-scale-suite-takes-about-4-minutes"])
    assert shown.exit_code == 0
    assert "the scale suite takes about 4 minutes" in shown.output

    forgotten = await invoke(
        ["memory", "manager", "forget", "the-scale-suite-takes-about-4-minutes"]
    )
    assert forgotten.exit_code == 0

    listed_after = await invoke(["memory", "manager", "list"])
    assert listed_after.exit_code == 0
    assert "the-scale-suite-takes-about-4-minutes" not in listed_after.output


async def test_add_with_file_supplies_a_longer_body_than_the_fact(project, invoke, tmp_path):
    body_path = tmp_path / "body.md"
    body_path.write_text("Longer freeform notes about strict mode gotchas.\n", encoding="utf-8")

    added = await invoke(
        ["memory", "manager", "add", "pyright runs in strict mode", "--file", str(body_path)]
    )
    assert added.exit_code == 0

    shown = await invoke(["memory", "manager", "show", "pyright-runs-in-strict-mode"])
    assert shown.exit_code == 0
    assert "Longer freeform notes about strict mode gotchas." in shown.output


async def test_list_json_shape_matches_the_index_entry_schema(project, invoke):
    await invoke(["memory", "manager", "add", "a fact worth remembering"])

    result = await invoke(["memory", "manager", "list", "--json"])
    assert result.exit_code == 0
    rows = json.loads(result.output)
    assert rows == [
        {
            "slug": "a-fact-worth-remembering",
            "filename": "a-fact-worth-remembering.md",
            "description": "a fact worth remembering",
        }
    ]


async def test_search_finds_memories_matching_content_and_json_matches_human_output(
    project, invoke
):
    await invoke(["memory", "manager", "add", "pyright runs in strict mode"])
    await invoke(["memory", "manager", "add", "the scale suite is slow"])

    human = await invoke(["memory", "manager", "search", "strict"])
    assert human.exit_code == 0
    assert "pyright-runs-in-strict-mode" in human.output
    assert "the-scale-suite-is-slow" not in human.output

    as_json = await invoke(["memory", "manager", "search", "strict", "--json"])
    rows = json.loads(as_json.output)
    assert [r["slug"] for r in rows] == ["pyright-runs-in-strict-mode"]

    empty = await invoke(["memory", "manager", "search", "no-such-needle-anywhere"])
    assert empty.exit_code == 0
    assert "no matches" in empty.output


async def test_show_addresses_a_memory_by_slug_independent_of_its_list_position(project, invoke):
    """Line position in the index carries no meaning and is not relied on: forgetting
    the alphabetically-first memory shifts every remaining memory's position in `list`; `show`
    must still resolve the others by their own stable slug, unaffected by that shift."""
    await invoke(["memory", "manager", "add", "aaa first fact"])
    await invoke(["memory", "manager", "add", "bbb second fact"])
    await invoke(["memory", "manager", "add", "ccc third fact"])

    before = await invoke(["memory", "manager", "list", "--json"])
    assert [r["slug"] for r in json.loads(before.output)] == [
        "aaa-first-fact",
        "bbb-second-fact",
        "ccc-third-fact",
    ]

    await invoke(["memory", "manager", "forget", "aaa-first-fact"])

    after = await invoke(["memory", "manager", "list", "--json"])
    assert [r["slug"] for r in json.loads(after.output)] == [
        "bbb-second-fact",
        "ccc-third-fact",
    ]

    shown = await invoke(["memory", "manager", "show", "ccc-third-fact"])
    assert shown.exit_code == 0
    assert "ccc third fact" in shown.output


async def test_an_unknown_role_raises_a_clean_error_not_a_traceback(project, invoke):
    result = await invoke(["memory", "some-unregistered-role", "list"])
    assert result.exit_code == 1
    assert "unknown slug" in result.output
    assert "Traceback" not in result.output


async def test_showing_an_unknown_slug_raises_a_clean_error_not_a_traceback(project, invoke):
    result = await invoke(["memory", "manager", "show", "never-existed"])
    assert result.exit_code == 1
    assert "no memory" in result.output
    assert "Traceback" not in result.output


async def test_forgetting_an_unknown_slug_raises_a_clean_error_not_a_traceback(project, invoke):
    result = await invoke(["memory", "manager", "forget", "never-existed"])
    assert result.exit_code == 1
    assert "no memory" in result.output
    assert "Traceback" not in result.output
