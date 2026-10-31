"""A memory search prints a matching line once when the body repeats the summary."""

import pytest

pytestmark = pytest.mark.anyio


async def test_a_body_line_equal_to_the_summary_is_not_repeated(project, invoke) -> None:
    added = await invoke(["memory", "manager", "add", "Widget quirk", "--slug", "widget"])
    assert added.exit_code == 0, added.output
    result = await invoke(["memory", "manager", "search", "widget"])
    assert (result.exit_code, result.output) == (0, "widget  Widget quirk\n    Widget quirk\n")
