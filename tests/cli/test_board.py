"""`sq board …`: posting notices to the team board, listing and reading the current ones and
clearing one."""

import json
from typing import Any

import pytest

from tests.cli._output import read_json
from tests.cli._roster import forced_colour, usage_error

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


@pytest.mark.covers("board post", "summary")
@pytest.mark.covers("board post", "--as")
async def test_post_adds_a_notice_signed_by_the_actor(project, invoke) -> None:
    result = await invoke(["board", "post", "Freeze on Friday", "--as", "manager"])
    notice_id = result.output.split()[1]
    assert (result.exit_code, result.output) == (0, f"posted {notice_id} as manager\n")
    assert await _board(invoke) == [
        {
            "n": 1,
            "id": notice_id,
            "summary": "Freeze on Friday",
            "author": "manager",
            "author_name": "Catherine Manager",
            "posted_at": STAMP,
            "until": None,
        }
    ]
    assert (await read_json(invoke, ["board", "show", "1", "--json"]))["body"] == ""


@pytest.mark.covers("board post", "summary")
async def test_post_needs_a_summary_that_is_not_blank(project, invoke) -> None:
    missing = await invoke(["board", "post", "-m", "Detail only", "--as", "manager"])
    assert (missing.exit_code, missing.output) == (
        2,
        usage_error(
            "Usage: sq board post [OPTIONS] {summary}",
            "sq board post --help",
            "Missing argument 'summary'.",
        ),
    )
    blank = await invoke(["board", "post", "   ", "--as", "manager"])
    assert (blank.exit_code, blank.output) == (
        1,
        "error: a board notice needs a non-empty summary\n",
    )
    assert await _board(invoke) == []


@pytest.mark.covers("board post", "summary")
async def test_post_with_a_multi_line_summary_stores_it_and_warns(project, invoke) -> None:
    result = await invoke(["board", "post", "First\nSecond", "--as", "manager"])
    notice_id = result.output.split("posted ")[1].split()[0]
    assert (result.exit_code, result.output) == (
        0,
        f"warning: notice 1 ({notice_id}) has a multi-line summary; post it again with a one-line"
        ' summary: `sq board post "<summary>" --file <body> --as manager`,'
        " then `sq board clear 1`\n"
        f"posted {notice_id} as manager\n",
    )
    assert [n["summary"] for n in await _board(invoke)] == ["First\nSecond"]


@pytest.mark.covers("board post", "summary")
async def test_post_warns_on_every_separator_splitlines_splits_on(project, invoke) -> None:
    result = await invoke(["board", "post", "First\rSecond\u2028Third", "--as", "manager"])
    notice_id = result.output.split("posted ")[1].split()[0]
    assert (result.exit_code, result.output) == (
        0,
        f"warning: notice 1 ({notice_id}) has a multi-line summary; post it again with a one-line"
        ' summary: `sq board post "<summary>" --file <body> --as manager`,'
        " then `sq board clear 1`\n"
        f"posted {notice_id} as manager\n",
    )


@pytest.mark.covers("board post", "--message")
async def test_post_keeps_the_indentation_of_the_body(project, invoke) -> None:
    await _post(invoke, "Freeze", "-m", "    indented code\n\nand prose")
    body = (await read_json(invoke, ["board", "show", "1", "--json"]))["body"]
    assert body == "    indented code\n\nand prose"


@pytest.mark.covers("board post", "--as")
async def test_post_as_is_required(project, invoke) -> None:
    result = await invoke(["board", "post", "Freeze on Friday"])
    assert (result.exit_code, result.output) == (1, AS_REQUIRED)
    assert await _board(invoke) == []


@pytest.mark.covers("board post", "--as")
async def test_post_as_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    result = await invoke(["board", "post", "Freeze on Friday", "--as", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: manager\n",
    )
    assert await _board(invoke) == []


@pytest.mark.covers("board post", "--message")
async def test_post_message_repeated_becomes_one_paragraph_each(project, invoke) -> None:
    await _post(invoke, "Freeze", "-m", "Freeze on Friday", "-m", "Merge before noon")
    body = (await read_json(invoke, ["board", "show", "1", "--json"]))["body"]
    assert body == "Freeze on Friday\n\nMerge before noon"


@pytest.mark.covers("board post", "--file")
async def test_post_file_reads_the_body_from_the_file(project, invoke, tmp_path) -> None:
    source = tmp_path / "notice.md"
    source.write_text("From a file.\n\nTwo paragraphs.\n", encoding="utf-8")
    await _post(invoke, "Freeze", "--file", str(source))
    body = (await read_json(invoke, ["board", "show", "1", "--json"]))["body"]
    assert body == "From a file.\n\nTwo paragraphs."


@pytest.mark.covers("board post", "--message", "--file")
async def test_post_message_excludes_file(project, invoke, tmp_path) -> None:
    source = tmp_path / "notice.md"
    source.write_text("From a file.\n", encoding="utf-8")
    result = await invoke(
        ["board", "post", "Freeze", "-m", "Inline", "--file", str(source), "--as", "manager"]
    )
    assert (result.exit_code, result.output) == (
        1,
        "error: provide the body via -m or --file, not both\n",
    )
    assert await _board(invoke) == []


@pytest.mark.covers("board post", "--until")
async def test_post_until_hides_the_notice_after_that_date(project, invoke) -> None:
    await _post(invoke, "Open", "--until", "2999-01-01")
    await _post(invoke, "Expired", "--until", "2000-01-01")
    assert [(n["summary"], n["until"]) for n in await _board(invoke)] == [
        ("Open", "2999-01-01T00:00:00Z")
    ]


@pytest.mark.covers("board post", "--until")
async def test_post_until_refuses_a_value_that_is_not_iso_8601(project, invoke) -> None:
    result = await invoke(["board", "post", "Open", "--until", "yesterday", "--as", "manager"])
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
    first = await _post(invoke, "First", "-m", "Detail", at=EARLIER)
    second = await _post(invoke, "Second", "--until", "2999-01-01")
    assert json.dumps(await _board(invoke)) == json.dumps(
        [
            {
                "n": 1,
                "id": first,
                "summary": "First",
                "author": "manager",
                "author_name": "Catherine Manager",
                "posted_at": EARLIER,
                "until": None,
            },
            {
                "n": 2,
                "id": second,
                "summary": "Second",
                "author": "manager",
                "author_name": "Catherine Manager",
                "posted_at": STAMP,
                "until": "2999-01-01T00:00:00Z",
            },
        ]
    )


@pytest.mark.covers("board list", "--full")
async def test_list_full_json_adds_the_body_to_each_row_and_names_the_author(
    project, invoke
) -> None:
    first = await _post(invoke, "First", "-m", "Detail one", at=EARLIER)
    second = await _post(invoke, "Second")
    ghost = project.squad_dir / "board" / "ghost00001.md"
    ghost.write_text(
        "---\nsummary: Third\nauthor: ghost\nposted_at: '2026-06-07T11:00:00Z'\n---\nBody three\n",
        encoding="utf-8",
    )
    rows = await read_json(invoke, ["board", "list", "--full", "--json"])
    assert json.dumps(rows) == json.dumps(
        [
            {
                "n": 1,
                "id": first,
                "summary": "First",
                "author": "manager",
                "author_name": "Catherine Manager",
                "posted_at": EARLIER,
                "until": None,
                "body": "Detail one",
            },
            {
                "n": 2,
                "id": second,
                "summary": "Second",
                "author": "manager",
                "author_name": "Catherine Manager",
                "posted_at": STAMP,
                "until": None,
                "body": "",
            },
            {
                "n": 3,
                "id": "ghost00001",
                "summary": "Third",
                "author": "ghost",
                "author_name": "ghost",
                "posted_at": "2026-06-07T11:00:00Z",
                "until": None,
                "body": "Body three",
            },
        ]
    )


@pytest.mark.covers("board list", "--full")
async def test_list_full_prints_each_body_under_its_summary(project, invoke) -> None:
    await _post(invoke, "First", "-m", "Detail one", "-m", "Detail two", at=EARLIER)
    await _post(invoke, "Second")
    result = await invoke(["board", "list", "--full"])
    assert (result.exit_code, result.output) == (
        0,
        "1. First  (manager)\n\n   Detail one\n\n   Detail two\n2. Second  (manager)\n",
    )


@pytest.mark.covers("board list", "--full")
async def test_list_full_raw_indents_each_body_in_its_item_and_drops_the_closing_line(
    project, invoke
) -> None:
    await _post(invoke, "First", "-m", "Detail one", "-m", "Detail two", at=EARLIER)
    await _post(invoke, "Second", "--until", "2999-01-01")
    result = await invoke(["board", "list", "--full", "--raw"])
    assert (result.exit_code, result.output) == (
        0,
        "1. First \u2014 manager\n\n   Detail one\n\n   Detail two\n"
        "2. Second \u2014 manager, until 2999-01-01T00:00:00Z\n",
    )


@pytest.mark.covers("board list")
async def test_list_prints_one_numbered_line_per_notice(project, invoke) -> None:
    empty = await invoke(["board", "list"])
    assert (empty.exit_code, empty.output) == (0, "no current notices\n")
    await _post(invoke, "First", "-m", "Detail", at=EARLIER)
    await _post(invoke, "Second", "--until", "2999-01-01")
    result = await invoke(["board", "list"])
    assert (result.exit_code, result.output) == (
        0,
        "1. First  (manager)\n2. Second  (manager)  until 2999-01-01T00:00:00Z\n",
    )


@pytest.mark.covers("board list", "--raw")
async def test_list_raw_numbers_each_notice_with_its_summary_author_and_expiry(
    project, invoke, monkeypatch
) -> None:
    await _post(invoke, "First", "-m", "Detail stays out of the list", at=EARLIER)
    await _post(invoke, "Second", "--until", "2999-01-01")
    forced_colour(monkeypatch)
    result = await invoke(["board", "list", "--raw"])
    assert (result.exit_code, result.output) == (
        0,
        "1. First — manager\n"
        "2. Second — manager, until 2999-01-01T00:00:00Z\n"
        "\n"
        "Read a notice in full with `sq board show <n>`.\n",
    )


@pytest.mark.covers("board list", "--raw")
async def test_list_raw_indents_the_further_lines_of_a_multi_line_summary(project, invoke) -> None:
    await _post(invoke, "First line\nSecond line")
    result = await invoke(["board", "list", "--raw"])
    assert (result.exit_code, result.output) == (
        0,
        "1. First line\n   Second line — manager\n"
        "\nRead a notice in full with `sq board show <n>`.\n",
    )


async def _eleven(invoke, **posts: str) -> None:
    """Post eleven notices, `Notice 1` to `Notice 11`, a minute apart; *posts* maps a number to the
    words that replace its summary."""
    for i in range(1, 12):
        summary = posts.get(f"n{i}", f"Notice {i}")
        await _post(invoke, summary, at=f"2026-06-07T09:{i:02d}:00Z")


@pytest.mark.covers("board list", "--raw")
async def test_list_raw_indents_a_multi_line_summary_by_the_width_of_a_two_digit_marker(
    project, invoke
) -> None:
    await _eleven(invoke, n10="Ten\nlines")
    result = await invoke(["board", "list", "--raw"])
    assert (result.exit_code, result.output) == (
        0,
        "".join(f"{i}. Notice {i} \u2014 manager\n" for i in range(1, 10))
        + "10. Ten\n    lines \u2014 manager\n"
        "11. Notice 11 \u2014 manager\n"
        "\nRead a notice in full with `sq board show <n>`.\n",
    )


@pytest.mark.covers("board list", "--full", "--raw")
async def test_list_full_raw_indents_a_body_by_the_width_of_a_two_digit_marker(
    project, invoke
) -> None:
    for i in range(1, 12):
        body = ("-m", f"Body {i}") if i >= 9 else ()
        await _post(invoke, f"Notice {i}", *body, at=f"2026-06-07T09:{i:02d}:00Z")
    result = await invoke(["board", "list", "--full", "--raw"])
    assert (result.exit_code, result.output) == (
        0,
        "".join(f"{i}. Notice {i} \u2014 manager\n" for i in range(1, 9))
        + "9. Notice 9 \u2014 manager\n\n   Body 9\n"
        "10. Notice 10 \u2014 manager\n\n    Body 10\n"
        "11. Notice 11 \u2014 manager\n\n    Body 11\n",
    )


@pytest.mark.covers("board list", "--raw")
async def test_list_raw_numbers_match_the_ones_clear_takes(project, invoke) -> None:
    await _post(invoke, "First", at=EARLIER)
    await _post(invoke, "Second", at="2026-06-07T10:00:01Z")
    await _post(invoke, "Third", at="2026-06-07T10:00:02Z")
    await invoke(["board", "clear", "2"])
    result = await invoke(["board", "list", "--raw"])
    assert (result.exit_code, result.output) == (
        0,
        "1. First — manager\n2. Third — manager\n"
        "\nRead a notice in full with `sq board show <n>`.\n",
    )


@pytest.mark.covers("board list", "--raw")
async def test_list_raw_prints_nothing_when_a_notice_file_cannot_be_read(project, invoke) -> None:
    await _post(invoke, "First")
    broken = project.squad_dir / "board" / "BOARD-broken.md"
    broken.write_bytes(b"\xff\xfe not text")
    result = await invoke(["board", "list", "--raw"])
    assert (result.exit_code, result.stdout, result.stderr) == (
        4,
        "",
        f"error: {broken} is not valid UTF-8: byte 0xff at offset 0 \u2014 invalid start byte\n",
    )


@pytest.mark.covers("board list", "--raw")
async def test_list_raw_without_a_notice_prints_one_line(project, invoke) -> None:
    result = await invoke(["board", "list", "--raw"])
    assert (result.exit_code, result.output) == (0, "no current notices\n")


# ------------------------------------------------------------------------------------ show


@pytest.mark.covers("board show", "n")
async def test_show_prints_the_header_and_the_body(project, invoke) -> None:
    await _post(invoke, "Freeze", "-m", "Merge before noon", "--until", "2999-01-01")
    result = await invoke(["board", "show", "1"])
    assert (result.exit_code, result.output) == (
        0,
        "Freeze\n"
        "author: manager\n"
        f"posted: {STAMP}\n"
        "until: 2999-01-01T00:00:00Z\n"
        "\n"
        "Merge before noon\n",
    )


@pytest.mark.covers("board show", "--json")
async def test_show_json_prints_the_whole_notice_with_an_empty_body(project, invoke) -> None:
    notice_id = await _post(invoke, "Freeze")
    result = await invoke(["board", "show", "1", "--json"])
    assert result.exit_code == 0, result.output
    assert result.output == (
        json.dumps(
            {
                "n": 1,
                "id": notice_id,
                "summary": "Freeze",
                "author": "manager",
                "author_name": "Catherine Manager",
                "posted_at": STAMP,
                "until": None,
                "body": "",
            },
            indent=2,
        )
        + "\n"
    )


@pytest.mark.covers("board show", "n")
async def test_show_refuses_a_number_the_listing_does_not_have(project, invoke) -> None:
    await _post(invoke, "First")
    result = await invoke(["board", "show", "2"])
    assert (result.exit_code, result.output) == (
        1,
        "error: no notice at position 2 (the board currently lists 1 notice(s))\n",
    )


@pytest.mark.covers("board show", "n")
async def test_show_refuses_a_number_that_is_not_an_integer(project, invoke) -> None:
    result = await invoke(["board", "show", "abc"])
    assert (result.exit_code, result.output) == (
        2,
        usage_error(
            "Usage: sq board show [OPTIONS] {n}",
            "sq board show --help",
            "Invalid value for 'n': 'abc' is not a valid int.",
        ),
    )


# ----------------------------------------------------------------------------------- clear


@pytest.mark.covers("board clear", "n")
async def test_clear_takes_down_the_notice_with_that_number(project, invoke) -> None:
    first = await _post(invoke, "First", at=EARLIER)
    second = await _post(invoke, "Second")
    result = await invoke(["board", "clear", "1"])
    assert (result.exit_code, result.output) == (0, f"cleared {first}\n")
    assert [(n["n"], n["id"]) for n in await _board(invoke)] == [(1, second)]


@pytest.mark.covers("board clear", "n")
async def test_clear_refuses_a_number_the_listing_does_not_have(project, invoke) -> None:
    await _post(invoke, "First")
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
    post = ["board", "post", "Freeze", "--until", "2999-01-01", "--as", "manager"]
    result = await invoke(["--at", STAMP, *post, "--json"])
    assert result.exit_code == 0, result.output
    (listed,) = await _board(invoke)
    assert (
        result.output
        == json.dumps(
            {
                "entry": {
                    "id": listed["id"],
                    "summary": "Freeze",
                    "author": "manager",
                    "author_name": "Catherine Manager",
                    "posted_at": STAMP,
                    "until": "2999-01-01T00:00:00Z",
                    "body": "",
                }
            },
            indent=2,
        )
        + "\n"
    )


@pytest.mark.covers("board clear", "--json")
async def test_clear_json_prints_the_notice_taken_down(project, invoke) -> None:
    notice_id = await _post(invoke, "Freeze")
    result = await invoke(["board", "clear", "1", "--json"])
    assert result.exit_code == 0, result.output
    assert (
        result.output
        == json.dumps(
            {
                "entry": {
                    "id": notice_id,
                    "summary": "Freeze",
                    "author": "manager",
                    "author_name": "Catherine Manager",
                    "posted_at": STAMP,
                    "until": None,
                    "body": "",
                }
            },
            indent=2,
        )
        + "\n"
    )
    assert await _board(invoke) == []
