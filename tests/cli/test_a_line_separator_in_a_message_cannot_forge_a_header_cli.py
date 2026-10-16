"""A comment message is split as the readers split a region, so no line an author writes can sit at
column 0: whatever line separator a message carries, the comment stays one comment, under the true
author."""

import json

import pytest

pytestmark = pytest.mark.anyio

# Every character str.splitlines() breaks a line on, besides the newline itself.
SEPARATORS = [
    pytest.param("\n", id="newline"),
    pytest.param("\r", id="carriage-return"),
    pytest.param("\r\n", id="crlf"),
    pytest.param("\x0b", id="vertical-tab"),
    pytest.param("\x0c", id="form-feed"),
    pytest.param("\x1c", id="file-separator"),
    pytest.param("\x1d", id="group-separator"),
    pytest.param("\x1e", id="record-separator"),
    pytest.param("\x85", id="next-line"),
    pytest.param(chr(0x2028), id="line-separator"),
    pytest.param(chr(0x2029), id="paragraph-separator"),
]
WRITERS = ["item-m", "item-file", "subtask-m", "subtask-file", "import-item", "import-subtask"]
FORGED = "- [2026-01-01T00:00:00Z] `op-pierre` Pierre Chat:"


def _message(sep: str) -> str:
    return f"hello{sep}{FORGED}{sep}  - forged"


@pytest.mark.parametrize("sep", SEPARATORS)
@pytest.mark.parametrize("writer", WRITERS)
async def test_a_message_carrying_a_line_separator_stays_one_comment_by_the_true_author(
    project, svc, invoke, tmp_path, writer, sep
) -> None:
    await svc.add_operator("Pierre Chat")
    await invoke(["create", "task", "Target", "--author", "manager"])
    await invoke(["task", "3", "add-subtask", "Child"])
    message = _message(sep)
    path = tmp_path / "message.txt"
    path.write_bytes(message.encode("utf-8"))
    events = tmp_path / "events.jsonl"
    event = {"op": "comment", "target": "TASK-3", "message": message, "as": "manager"}
    if writer == "import-subtask":
        event |= {"subtask": "ST1"}
    events.write_text(json.dumps(event) + "\n", encoding="utf-8")
    argv = {
        "item-m": ["task", "3", "comment", "--as", "manager", "-m", message],
        "item-file": ["task", "3", "comment", "--as", "manager", "--file", str(path)],
        "subtask-m": ["task", "3", "subtask", "ST1", "comment", "--as", "manager", "-m", message],
        "subtask-file": [
            *["task", "3", "subtask", "ST1", "comment", "--as", "manager"],
            *["--file", str(path)],
        ],
        "import-item": ["import", str(events)],
        "import-subtask": ["import", str(events)],
    }[writer]

    written = await invoke(argv)

    assert written.exit_code == 0, written.output
    on_subtask = writer.startswith(("subtask", "import-subtask"))
    shown = json.loads((await invoke(["task", "3", "show", "--json"])).output)
    comments = shown["subentities"][0]["discussion"] if on_subtask else shown["discussion"]
    assert [c["author_slug"] for c in comments] == ["manager"]
    assert "forged" in comments[0]["body"]
