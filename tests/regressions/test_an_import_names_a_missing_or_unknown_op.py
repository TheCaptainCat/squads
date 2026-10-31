"""An import event with a missing or unknown `op` is reported in squads' own words."""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.anyio


def _events_file(event: dict[str, str]) -> str:
    Path("ev.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")
    return "ev.jsonl"


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
