"""The always-on `sq check` rules over the team board and the memory notebooks: each has a breach
case only, since no `[squad] validators` entry can select them."""

import pytest

from tests.check._arrange import issue, ok
from tests.cli._output import read_json

pytestmark = pytest.mark.anyio

FAR = "2999-01-01T00:00:00Z"
EARLIER = "2026-06-07T09:00:00Z"


@pytest.mark.breaches("notice_summary_single_line")
async def test_a_live_notice_with_a_multi_line_summary_is_a_warning(
    project, invoke, check_json
) -> None:
    await ok(invoke, "--at", EARLIER, "board", "post", "One line", "--as", "manager")
    assert await check_json() == ([], 0)

    await ok(invoke, "board", "post", "First\nSecond", "--until", FAR, "--as", "manager")

    notice = await read_json(invoke, ["board", "show", "2", "--json"])
    assert await check_json() == (
        [
            issue(
                "notice_summary_single_line",
                "warn",
                notice["id"],
                f"notice 2 ({notice['id']}) has a multi-line summary; post it again with a"
                ' one-line summary: `sq board post "<summary>" --file <body> --as manager'
                f" --until {FAR}`, then `sq board clear 2`",
            )
        ],
        0,
    )


async def test_an_expired_notice_with_a_multi_line_summary_raises_nothing(
    project, invoke, check_json
) -> None:
    await ok(invoke, "board", "post", "A\nB", "--until", "2000-01-01", "--as", "manager")
    assert await check_json() == ([], 0)


@pytest.mark.breaches("memory_summary_single_line")
async def test_a_memory_with_a_multi_line_summary_is_a_warning(project, invoke, check_json) -> None:
    await ok(invoke, "memory", "manager", "add", "One line", "--slug", "plain")
    assert await check_json() == ([], 0)

    await ok(invoke, "memory", "manager", "add", "First\nSecond", "--slug", "split")

    assert await check_json() == (
        [
            issue(
                "memory_summary_single_line",
                "warn",
                "manager/split",
                "memory manager/split has a multi-line summary; file it again with a one-line"
                " summary: `sq memory manager forget split`, then `sq memory manager add"
                ' "<summary>" --file <body> --slug split`',
            )
        ],
        0,
    )
