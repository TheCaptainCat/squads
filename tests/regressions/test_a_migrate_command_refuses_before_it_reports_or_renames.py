"""`sq migrate chlog` does not read a typo as "nothing to do" and `sq migrate repad` does not
rename files to an unusable width."""

import json

import pytest

pytestmark = pytest.mark.anyio


async def test_chlog_does_not_answer_a_typo_with_no_manual_steps(invoke) -> None:
    result = await invoke(["migrate", "chlog", "a..b"])
    assert (result.exit_code, result.output) == (
        1,
        "error: expected a range like v0.1.1..v0.2.0 (vfrom..vto, from below to), got 'a..b'\n",
    )


async def test_repad_does_not_rename_files_to_an_absurd_width(populated, invoke) -> None:
    result = await invoke(["migrate", "repad", "99"])
    assert (result.exit_code, result.output) == (
        1,
        "error: new padding 99 is above the maximum of 32 digits; padding can only increase, "
        "so a width that wide could not be taken back\n",
    )
    shown = await invoke(["task", "3", "show", "--json"])
    assert json.loads(shown.output)["path"] == "tasks/TASK-000003-build-the-query-parser.md"
