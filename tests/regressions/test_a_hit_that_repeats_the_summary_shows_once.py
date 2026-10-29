"""A memory search prints each matching line once, and an import names an unknown op in
squads' own words."""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.anyio


def _events_file(event: dict[str, str]) -> str:
    Path("ev.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")
    return "ev.jsonl"


async def test_a_body_line_equal_to_the_summary_is_not_repeated(project, invoke) -> None:
    added = await invoke(["memory", "manager", "add", "Widget quirk", "--slug", "widget"])
    assert added.exit_code == 0, added.output
    result = await invoke(["memory", "manager", "search", "widget"])
    assert (result.exit_code, result.output) == (0, "widget  Widget quirk\n    Widget quirk\n")


async def test_an_import_line_with_no_op_is_named_in_squads_own_words(project, invoke) -> None:
    result = await invoke(["import", _events_file({"as": "manager"})])
    assert (result.exit_code, result.output.splitlines()) == (
        1,
        [
            "line 1: missing op; valid ops: create, status, body, comment, ref, add-sub, "
            "add-story, add-subtask, add-finding, sub-status, sub-body, assign, update",
            "1 issue(s) found — nothing written.",
        ],
    )


async def test_an_unknown_import_op_is_named_without_a_stray_separator(project, invoke) -> None:
    result = await invoke(["import", _events_file({"op": "nope"})])
    assert (result.exit_code, result.output.splitlines()) == (
        1,
        [
            "line 1: unknown op 'nope'; valid ops: create, status, body, comment, ref, add-sub, "
            "add-story, add-subtask, add-finding, sub-status, sub-body, assign, update",
            "1 issue(s) found — nothing written.",
        ],
    )
