"""A write to an item file changes only the region it edits: lines it leaves alone keep their
bytes, line endings included, and what it adds takes the file's dominant ending."""

import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import pytest

from _helpers import create_item
from squads._backends._managed_region import inject
from squads._sections import split_lines

pytestmark = pytest.mark.anyio

_Verb = Callable[[Any, str], Awaitable[object]]


async def _comment(svc: Any, task: str) -> object:
    return await svc.comment(task, ["a note"], as_slug="manager")


async def _body(svc: Any, task: str) -> object:
    return await svc.set_body(task, "a new body", force=True)


async def _status(svc: Any, task: str) -> object:
    return await svc.set_status(task, "Ready")


async def _add_subtask(svc: Any, task: str) -> object:
    return await svc.add_subtask(task, "another")


async def _subtask_body(svc: Any, task: str) -> object:
    return await svc.set_subtask_body(task, "ST1", "prose for the first", force=True)


async def _subtask_status(svc: Any, task: str) -> object:
    return await svc.set_subtask_status(task, "ST1", "InProgress")


async def _subtask_comment(svc: Any, task: str) -> object:
    return await svc.comment(task, ["on the first"], as_slug="manager", subtask="ST1")


async def _remove_subtask(svc: Any, task: str) -> object:
    return await svc.remove_block(task, "subtask", "ST2")


_VERBS: list[tuple[str, _Verb]] = [
    ("comment", _comment),
    ("body", _body),
    ("status", _status),
    ("add-subtask", _add_subtask),
    ("subtask-body", _subtask_body),
    ("subtask-status", _subtask_status),
    ("subtask-comment", _subtask_comment),
    ("remove-subtask", _remove_subtask),
]


def _crlf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\n", "\r\n")


def _mixed(text: str) -> str:
    lines = split_lines(text.replace("\r\n", "\n"), keepends=True)
    return "".join(
        ln[:-1] + "\r\n" if i % 3 == 0 and ln.endswith("\n") else ln for i, ln in enumerate(lines)
    )


_SHAPES: dict[str, Callable[[str], str]] = {"crlf": _crlf, "mixed": _mixed, "lf": lambda t: t}


async def _task_file(svc: Any, shape: str) -> tuple[str, Path]:
    task = (await create_item(svc, "task", "Auth")).item
    await svc.add_subtask(task.id, "first")
    await svc.add_subtask(task.id, "second")
    path = svc.paths.abspath((await svc.get(task.id)).path)
    path.write_bytes(_SHAPES[shape](path.read_bytes().decode()).encode())
    return task.id, path


def _unique_endings(text: str) -> dict[str, str]:
    """Each distinct non-blank line's content mapped to its ending, for lines that occur once."""
    seen: dict[str, list[str]] = {}
    for line in split_lines(text, keepends=True):
        content = line.rstrip("\r\n")
        if content.strip():
            seen.setdefault(content, []).append(line[len(content) :])
    return {c: e[0] for c, e in seen.items() if len(e) == 1}


@pytest.mark.parametrize("shape", list(_SHAPES))
@pytest.mark.parametrize(("name", "verb"), _VERBS, ids=[n for n, _ in _VERBS])
async def test_untouched_lines_keep_their_bytes(svc, shape: str, name: str, verb: _Verb) -> None:
    task, path = await _task_file(svc, shape)
    before = path.read_bytes().decode()

    await verb(svc, task)

    after = path.read_bytes().decode()
    assert after != before
    kept = _unique_endings(before)
    for content, ending in _unique_endings(after).items():
        if content in kept:
            assert ending == kept[content], (name, content)
    if shape != "mixed":
        want = "\r\n" if shape == "crlf" else "\n"
        assert {e for e in re.findall(r"\r\n|\n", after)} == {want}


@pytest.mark.parametrize("shape", ["crlf", "mixed"])
async def test_a_file_in_another_ending_still_checks_and_repairs(svc, shape: str) -> None:
    task, path = await _task_file(svc, shape)
    await _comment(svc, task)

    issues = [i for i in await svc.check() if i.item == path.name]
    await svc.repair()

    assert [i for i in issues if i.level == "error"] == []
    assert (await svc.get(task)).title == "Auth"
    assert [i for i in await svc.check() if i.item == path.name and i.level == "error"] == []


async def test_a_crlf_index_loads_and_a_write_still_lands(svc) -> None:
    task = (await create_item(svc, "task", "Auth")).item
    index = svc.paths.index_path
    index.write_bytes(_crlf(index.read_bytes().decode()).encode())

    await svc.set_status(task.id, "Ready")

    assert (await svc.get(task.id)).status == "Ready"


async def test_a_crlf_managed_region_file_keeps_its_endings(tmp_path: Path) -> None:
    target = tmp_path / "CLAUDE.md"
    target.write_bytes(
        b"# Mine\r\n\r\n<!-- squads:start -->\r\nold\r\n<!-- squads:end -->\r\n\r\ntail\r\n"
    )

    await inject(target, "line one\nline two\n", missing_header="")

    after = target.read_bytes().decode()
    assert "line two" in after and "old" not in after
    assert "\n" not in after.replace("\r\n", "")
