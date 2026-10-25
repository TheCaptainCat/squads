"""`sq list --compact` prints one borderless line per item, cut to the terminal width."""

import pytest

from squads._cli._common import console

pytestmark = pytest.mark.anyio


async def _create(invoke, title: str) -> str:
    result = await invoke(["create", "task", title, "--author", "manager"])
    assert result.exit_code == 0, result.output
    return result.output.split("→")[0].removeprefix("created").strip()


def _lines(output: str) -> list[str]:
    return [ln for ln in output.splitlines() if ln.strip()]


async def test_a_title_that_fits_prints_whole_on_one_line(project, invoke) -> None:
    item_id = await _create(invoke, "Short title")
    result = await invoke(["list", "--type", "task", "--compact"])
    assert result.exit_code == 0, result.output
    assert _lines(result.output) == [f"{item_id}  Draft  Short title"]


async def test_a_longer_title_is_cut_with_an_ellipsis_within_the_width(
    project, invoke, monkeypatch
) -> None:
    await _create(invoke, "A title far longer than the terminal is wide")
    monkeypatch.setattr(console, "width", 40)
    result = await invoke(["list", "--type", "task", "--compact"])
    (line,) = _lines(result.output)
    assert line.endswith("…")
    assert len(line) <= 40


async def test_a_width_narrower_than_the_id_and_status_still_prints_one_line_per_item(
    project, invoke, monkeypatch
) -> None:
    await _create(invoke, "First")
    await _create(invoke, "Second")
    monkeypatch.setattr(console, "width", 8)
    result = await invoke(["list", "--type", "task", "--compact"])
    lines = _lines(result.output)
    assert len(lines) == 2
    assert all(len(ln) <= 8 for ln in lines)


async def test_compact_with_json_is_refused(project, invoke) -> None:
    await _create(invoke, "Anything")
    result = await invoke(["list", "--compact", "--json"])
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output


async def test_the_hidden_items_footer_still_prints(project, invoke) -> None:
    item_id = await _create(invoke, "Dropped")
    cancelled = await invoke(["task", item_id, "status", "Cancelled"])
    assert cancelled.exit_code == 0, cancelled.output
    result = await invoke(["list", "--type", "task", "--compact"])
    assert "1 closed items hidden — use --all" in result.output
