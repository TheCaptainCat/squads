"""`sq override diff --json` prints one JSON array on stdout whether or not anything drifted;
the plain output keeps its one-line notice."""

import json

import pytest

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("scaffolded", [False, True])
async def test_json_is_an_empty_array_when_nothing_drifted(project, invoke, scaffolded) -> None:
    if scaffolded:
        await invoke(["override", "scaffold", "items/task.md.j2"])

    result = await invoke(["override", "diff", "--json"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == []


async def test_plain_output_keeps_the_notice(project, invoke) -> None:
    result = await invoke(["override", "diff"])

    assert result.exit_code == 0, result.output
    assert "no drifted overrides found" in result.output
