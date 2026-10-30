"""`sq board …`: posting notices to the team board, listing the current ones and clearing one."""

import json
from typing import Any

import pytest

from tests.cli._output import read_json, unknown_option
from tests.cli._roster import usage_error

pytestmark = pytest.mark.anyio

STAMP = "2026-06-07T10:00:00Z"
EARLIER = "2026-06-07T09:00:00Z"
AS_REQUIRED = "error: --as is required: the actor's slug\n"


async def _board(invoke) -> list[dict[str, Any]]:
    return await read_json(invoke, ["board", "list", "--json"])


async def _post(invoke, *args: str, at: str = STAMP) -> str:
    """Post as `manager` at the time *at* and return the id of the notice."""
    result = await invoke(["--at", at, "board", "post", *args, "--as", "manager"])
    assert result.exit_code == 0, result.output
    return result.output.split()[1]


# ------------------------------------------------------------------------------------ post


@pytest.mark.covers("board post", "--message")
@pytest.mark.covers("board post", "--as")
async def test_post_adds_a_notice_signed_by_the_actor(project, invoke) -> None:
    result = await invoke(["board", "post", "-m", "Freeze on Friday", "--as", "manager"])
    notice_id = result.output.split()[1]
    assert (result.exit_code, result.output) == (0, f"posted {notice_id} as manager\n")
    assert await _board(invoke) == [
        {
            "n": 1,
            "id": notice_id,
            "author": "manager",
            "posted_at": STAMP,
            "until": None,
            "body": "Freeze on Friday",
        }
    ]


@pytest.mark.covers("board post", "--as")
async def test_post_as_is_required(project, invoke) -> None:
    result = await invoke(["board", "post", "-m", "Freeze on Friday"])
    assert (result.exit_code, result.output) == (1, AS_REQUIRED)
    assert await _board(invoke) == []


@pytest.mark.covers("board post", "--as")
async def test_post_as_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    result = await invoke(["board", "post", "-m", "Freeze on Friday", "--as", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: manager\n",
    )
    assert await _board(invoke) == []


@pytest.mark.covers("board post", "--message")
async def test_post_message_repeated_becomes_one_paragraph_each(project, invoke) -> None:
    await _post(invoke, "-m", "Freeze on Friday", "-m", "Merge before noon")
    assert [n["body"] for n in await _board(invoke)] == ["Freeze on Friday\n\nMerge before noon"]


@pytest.mark.covers("board post", "--file")
async def test_post_file_reads_the_notice_from_the_file(project, invoke, tmp_path) -> None:
    source = tmp_path / "notice.md"
    source.write_text("From a file.\n\nTwo paragraphs.\n", encoding="utf-8")
    await _post(invoke, "--file", str(source))
    assert [n["body"] for n in await _board(invoke)] == ["From a file.\n\nTwo paragraphs."]


@pytest.mark.covers("board post", "--message", "--file")
async def test_post_message_excludes_file(project, invoke, tmp_path) -> None:
    source = tmp_path / "notice.md"
    source.write_text("From a file.\n", encoding="utf-8")
    result = await invoke(
        ["board", "post", "-m", "Inline", "--file", str(source), "--as", "manager"]
    )
    assert (result.exit_code, result.output) == (
        1,
        "error: provide the body via -m or --file, not both\n",
    )
    assert await _board(invoke) == []


@pytest.mark.covers("board post", "--message")
async def test_post_needs_a_message_or_a_file(project, invoke) -> None:
    result = await invoke(["board", "post", "--as", "manager"])
    assert (result.exit_code, result.output) == (
        1,
        "error: provide the body via -m (repeatable) or --file PATH ('-' for stdin)\n",
    )


@pytest.mark.covers("board post", "--until")
async def test_post_until_hides_the_notice_after_that_date(project, invoke) -> None:
    await _post(invoke, "-m", "Open", "--until", "2999-01-01")
    await _post(invoke, "-m", "Expired", "--until", "2000-01-01")
    assert [(n["body"], n["until"]) for n in await _board(invoke)] == [
        ("Open", "2999-01-01T00:00:00Z")
    ]


@pytest.mark.covers("board post", "--until")
async def test_post_until_refuses_a_value_that_is_not_iso_8601(project, invoke) -> None:
    result = await invoke(
        ["board", "post", "-m", "Open", "--until", "yesterday", "--as", "manager"]
    )
    assert (result.exit_code, result.output) == (
        1,
        "error: invalid --until value 'yesterday': Invalid isoformat string: 'yesterday'\n",
    )
    assert await _board(invoke) == []


# ------------------------------------------------------------------------------------ list


@pytest.mark.covers("board list", "--json")
async def test_list_json_numbers_the_current_notices_in_the_order_they_were_posted(
    project, invoke
) -> None:
    assert await _board(invoke) == []
    first = await _post(invoke, "-m", "First", at=EARLIER)
    second = await _post(invoke, "-m", "Second", "--until", "2999-01-01")
    assert json.dumps(await _board(invoke)) == json.dumps(
        [
            {
                "n": 1,
                "id": first,
                "author": "manager",
                "posted_at": EARLIER,
                "until": None,
                "body": "First",
            },
            {
                "n": 2,
                "id": second,
                "author": "manager",
                "posted_at": STAMP,
                "until": "2999-01-01T00:00:00Z",
                "body": "Second",
            },
        ]
    )


@pytest.mark.covers("board list")
async def test_list_prints_one_numbered_line_per_notice(project, invoke) -> None:
    empty = await invoke(["board", "list"])
    assert (empty.exit_code, empty.output) == (0, "no current notices\n")
    await _post(invoke, "-m", "First", at=EARLIER)
    await _post(invoke, "-m", "Second", "--until", "2999-01-01")
    result = await invoke(["board", "list"])
    assert (result.exit_code, result.output) == (
        0,
        f"1. First  (manager @ {EARLIER})\n"
        f"2. Second  (manager @ {STAMP})  until 2999-01-01T00:00:00Z\n",
    )


# ----------------------------------------------------------------------------------- clear


@pytest.mark.covers("board clear", "n")
async def test_clear_takes_down_the_notice_with_that_number(project, invoke) -> None:
    first = await _post(invoke, "-m", "First", at=EARLIER)
    second = await _post(invoke, "-m", "Second")
    result = await invoke(["board", "clear", "1"])
    assert (result.exit_code, result.output) == (0, f"cleared {first}\n")
    assert [(n["n"], n["id"]) for n in await _board(invoke)] == [(1, second)]


@pytest.mark.covers("board clear", "n")
async def test_clear_refuses_a_number_the_listing_does_not_have(project, invoke) -> None:
    await _post(invoke, "-m", "First")
    for number in ("0", "2"):
        result = await invoke(["board", "clear", number])
        assert (result.exit_code, result.output) == (
            1,
            f"error: no notice at position {number} (the board currently lists 1 notice(s))\n",
        )
    assert len(await _board(invoke)) == 1


@pytest.mark.covers("board clear", "n")
async def test_clear_refuses_a_number_that_is_not_an_integer(project, invoke) -> None:
    result = await invoke(["board", "clear", "first"])
    assert (result.exit_code, result.output) == (
        2,
        usage_error(
            "Usage: sq board clear [OPTIONS] {n}",
            "sq board clear --help",
            "Invalid value for 'n': 'first' is not a valid int.",
        ),
    )


@pytest.mark.covers("board clear", "n")
async def test_clear_needs_a_number(project, invoke) -> None:
    result = await invoke(["board", "clear"])
    assert (result.exit_code, result.output) == (
        2,
        usage_error(
            "Usage: sq board clear [OPTIONS] {n}",
            "sq board clear --help",
            "Missing argument 'n'.",
        ),
    )


# ------------------------------------------------------------------------------------ json


@pytest.mark.covers("board post", "--json")
async def test_post_json_prints_the_notice_written(project, invoke) -> None:
    post = ["board", "post", "-m", "Freeze", "--until", "2999-01-01", "--as", "manager"]
    result = await invoke(["--at", STAMP, *post, "--json"])
    assert result.exit_code == 0, result.output
    (listed,) = await _board(invoke)
    assert (
        result.output
        == json.dumps(
            {
                "entry": {
                    "id": listed["id"],
                    "author": "manager",
                    "posted_at": STAMP,
                    "until": "2999-01-01T00:00:00Z",
                    "body": "Freeze",
                }
            },
            indent=2,
        )
        + "\n"
    )


@pytest.mark.covers("board clear", "--json")
async def test_clear_json_prints_the_notice_taken_down(project, invoke) -> None:
    notice_id = await _post(invoke, "-m", "Freeze")
    result = await invoke(["board", "clear", "1", "--json"])
    assert result.exit_code == 0, result.output
    assert (
        result.output
        == json.dumps(
            {
                "entry": {
                    "id": notice_id,
                    "author": "manager",
                    "posted_at": STAMP,
                    "until": None,
                    "body": "Freeze",
                }
            },
            indent=2,
        )
        + "\n"
    )
    assert await _board(invoke) == []


@pytest.mark.covers("board post", "--message")
async def test_post_names_the_options_close_to_an_unknown_one_as_plain_text(
    project, invoke
) -> None:
    await _post(invoke, "-m", "Freeze on Friday")
    result = await invoke(["board", "post", "-m", "Second", "--slug", "manager"])
    assert (result.exit_code, result.output) == (
        2,
        unknown_option("board post [OPTIONS]", "board post", "--slug", " (Possible options: --as)"),
    )
    assert [notice["body"] for notice in await _board(invoke)] == ["Freeze on Friday"]
