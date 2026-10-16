"""CLI smoke for the comment writers: the retype system entry and the bulk importer stamp the
slug header, and an importer actor outside the slug grammar is refused with nothing written."""

import json

import pytest

pytestmark = pytest.mark.anyio

TS = "2026-06-07T10:00:00Z"


def _stored_headers(project) -> list[str]:
    lines: list[str] = []
    for path in sorted((project.squad_dir / "tasks").glob("*.md")) + sorted(
        (project.squad_dir / "bugs").glob("*.md")
    ):
        lines += [
            ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.startswith("- [")
        ]
    return lines


async def test_retype_and_import_write_the_slug_header(project, invoke, tmp_path) -> None:
    await invoke(["create", "task", "First", "--author", "manager"])
    await invoke(["create", "task", "Second", "--author", "manager"])
    r = await invoke(["task", "2", "retype", "bug"])
    assert r.exit_code == 0, r.output
    events = tmp_path / "events.jsonl"
    events.write_text(
        json.dumps({"op": "comment", "target": "TASK-3", "message": "hi", "as": "manager"}) + "\n",
        encoding="utf-8",
    )

    r = await invoke(["import", str(events)])

    assert r.exit_code == 0, r.output
    assert _stored_headers(project) == [
        f"- [{TS}] `manager` Catherine Manager:",
        f"- [{TS}] `squads` squads:",
    ]


async def test_import_refuses_an_actor_outside_the_slug_grammar(project, invoke, tmp_path) -> None:
    await invoke(["create", "task", "First", "--author", "manager"])
    events = tmp_path / "events.jsonl"
    events.write_text(
        json.dumps({"op": "comment", "target": "TASK-2", "message": "x", "as": "Bad Actor"}) + "\n",
        encoding="utf-8",
    )

    r = await invoke(["import", str(events)])

    assert r.exit_code == 1
    assert "cannot write a comment as 'Bad Actor'" in r.output
    assert _stored_headers(project) == []
