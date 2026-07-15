"""CLI smoke for ``sq board ...``: the team bulletin board is team-scoped — no positional
role subject (unlike ``sq memory <role> ...``). Covers the post->list->clear round-trip,
``--until`` expiry hiding a notice, ``--as`` attribution, ``list --json`` shape, and a clean
error on an out-of-range ``clear``.
"""

import json

import pytest

pytestmark = pytest.mark.anyio


async def test_post_then_list_then_clear_round_trips_a_notice(project, invoke):
    posted = await invoke(["board", "post", "-m", "the CI runners are down for maintenance"])
    assert posted.exit_code == 0
    assert "posted" in posted.output

    listed = await invoke(["board", "list"])
    assert listed.exit_code == 0
    assert "the CI runners are down for maintenance" in listed.output
    assert "1." in listed.output

    cleared = await invoke(["board", "clear", "1"])
    assert cleared.exit_code == 0
    assert "cleared" in cleared.output

    listed_after = await invoke(["board", "list"])
    assert listed_after.exit_code == 0
    assert "the CI runners are down for maintenance" not in listed_after.output
    assert "no current notices" in listed_after.output


async def test_until_expiry_hides_a_notice_from_list(project, invoke):
    await invoke(["board", "post", "-m", "old notice", "--until", "2020-01-01"])
    await invoke(["board", "post", "-m", "current notice"])

    listed = await invoke(["board", "list"])
    assert listed.exit_code == 0
    assert "old notice" not in listed.output
    assert "current notice" in listed.output


async def test_as_attributes_the_post_to_a_role_or_operator(project, invoke):
    posted = await invoke(["board", "post", "-m", "freeze the schema", "--as", "manager"])
    assert posted.exit_code == 0
    assert "manager" in posted.output

    listed = await invoke(["board", "list"])
    assert listed.exit_code == 0
    assert "manager" in listed.output


async def test_list_json_shape_includes_ordinal_author_posted_at_and_until(project, invoke):
    await invoke(["board", "post", "-m", "notice with expiry", "--until", "2099-01-01"])

    result = await invoke(["board", "list", "--json"])
    assert result.exit_code == 0
    rows = json.loads(result.output)
    assert len(rows) == 1
    row = rows[0]
    assert row["n"] == 1
    assert row["body"] == "notice with expiry"
    assert row["author"] == "operator"
    assert row["until"] == "2099-01-01T00:00:00Z"
    assert set(row) == {"n", "id", "author", "posted_at", "until", "body"}


async def test_list_json_on_an_empty_board_is_an_empty_list(project, invoke):
    result = await invoke(["board", "list", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output) == []


async def test_clearing_an_out_of_range_ordinal_raises_a_clean_error_not_a_traceback(
    project, invoke
):
    await invoke(["board", "post", "-m", "the only notice"])

    result = await invoke(["board", "clear", "2"])
    assert result.exit_code == 1
    assert "Traceback" not in result.output


async def test_posting_with_an_unknown_as_slug_raises_a_clean_error(project, invoke):
    result = await invoke(["board", "post", "-m", "text", "--as", "not-a-real-slug"])
    assert result.exit_code == 1
    assert "unknown slug" in result.output
    assert "Traceback" not in result.output


async def test_plain_list_shows_author_posted_at_and_until_alongside_the_ordinal(project, invoke):
    await invoke(
        ["board", "post", "-m", "freeze the schema", "--as", "manager", "--until", "2099-01-01"]
    )

    result = await invoke(["board", "list"])
    assert result.exit_code == 0
    assert "1." in result.output
    assert "manager" in result.output
    assert "until" in result.output
    assert "2099-01-01" in result.output
    assert "2026" in result.output  # posted-at (frozen_time) is shown too
