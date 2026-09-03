"""``sq import`` reports the level of every integrity finding it raises on a touched item, and
an error-level one earns exit 3 with the write kept.

The importer runs the integrity catalog over the items it touched *after* its transaction has
committed. That reporter returns levelled findings, and the level is the only thing separating
"tidy this up when you get to it" from a violation every gated door would have refused — so it
has to survive to both output surfaces. It also has to reach the exit code, because this door is
driven by scripts far more often than it is read by a person: a prefix a human can see and a
wrapper cannot is not a contract.

Exit 3 is the code the integrity check already uses for the same findings from the same catalog,
so the two doors say one thing. It is emphatically **not** exit 1, which on this door means the
pre-pass refused the file and nothing was written: the events behind a 3 are on disk.

The error-level finding driven here reaches the reporter with no ``force`` anywhere — any event
touching the item will do — so the coverage is not pinned to one waiver-shaped route. Which
catalog members can reach this point at all is a property of the effective spec, not a fixed
list: a type naming an error-level rule in an override reaches it too.
"""

import json
from pathlib import Path

import pytest

from squads import __version__
from squads._rendering._engine import invalidate_squad_dir

pytestmark = pytest.mark.anyio

#: Renaming a sub-entity kind's container plural against an existing corpus is a supported
#: customisation that the corpus does not follow automatically: the files keep the old container
#: marker, so `add-<kind>` can no longer find one. The catalog reports that at error level.
#: Stamped like any hand-written override, so the only finding the corpus carries above
#: warn level is the one these tests are about.
_RENAMED_PLURAL = (
    f'# squads:override-base:{__version__}\n[subentity_kinds.subtask]\nplural = "worksteps"\n'
)


def _rename_the_subtask_container(squad_dir: Path) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(_RENAMED_PLURAL, encoding="utf-8")
    invalidate_squad_dir(squad_dir)


async def _task_with_a_stub_subtask(invoke) -> tuple[str, str]:
    """A task carrying one subtask whose body is still the placeholder stub — a warn-level
    finding on its own, and the corpus the plural rename turns into an error-level one too.
    Returns the task's id and its bare number (what the CLI addresses it by)."""
    created = await invoke(["create", "task", "Alpha task", "--author", "manager"])
    assert created.exit_code == 0, created.output
    listed = await invoke(["list", "--type", "task", "--json"])
    task_id = json.loads(listed.output)[0]["id"]
    number = task_id.split("-")[1]
    added = await invoke(["task", number, "add-subtask", "A subtask"])
    assert added.exit_code == 0, added.output
    return task_id, number


def _comment_event(target: str, message: str) -> str:
    return json.dumps({"op": "comment", "target": target, "message": message, "as": "manager"})


async def test_an_error_level_finding_on_a_touched_item_exits_3_and_keeps_the_write(
    project, invoke, tmp_path
):
    task_id, number = await _task_with_a_stub_subtask(invoke)
    _rename_the_subtask_container(project.squad_dir)
    events = tmp_path / "events.jsonl"
    events.write_text(_comment_event(task_id, "Imported comment.") + "\n", encoding="utf-8")

    result = await invoke(["import", str(events)])

    assert result.exit_code == 3, result.output
    # The two levels are told apart by their prefix, the way the integrity check tells them
    # apart -- not flattened into one `warning:` stream.
    assert "error: " in result.output
    assert "worksteps" in result.output
    assert "warning: " in result.output
    assert "body is unwritten" in result.output
    assert "imported 1 event(s)" in result.output

    # Exit 3 means applied-and-flagged: the write stands.
    shown = await invoke(["task", number, "show", "--comments"])
    assert "Imported comment." in shown.output


async def test_the_json_payload_carries_the_level_and_still_says_it_applied(
    project, invoke, tmp_path
):
    task_id, _number = await _task_with_a_stub_subtask(invoke)
    _rename_the_subtask_container(project.squad_dir)
    events = tmp_path / "events.jsonl"
    events.write_text(_comment_event(task_id, "Imported comment.") + "\n", encoding="utf-8")

    result = await invoke(["import", "--json", str(events)])

    assert result.exit_code == 3, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is False
    # `applied` is the field that says the write happened, and it must go on saying so at
    # exit 3 -- a caller that reads a non-zero exit as "nothing happened" would replay the file.
    assert payload["applied"] is True
    levels = {i["level"] for i in payload["issues"]}
    assert levels == {"error", "warn"}
    error_issue = next(i for i in payload["issues"] if i["level"] == "error")
    assert error_issue["item"] == task_id
    assert "worksteps" in error_issue["message"]
    # `warnings` keeps the warn-level lines in the wording it has always used.
    warn_issue = next(i for i in payload["issues"] if i["level"] == "warn")
    assert payload["warnings"] == [f"{task_id}: {warn_issue['message']}"]


async def test_a_warn_level_only_import_still_exits_0(project, invoke, tmp_path):
    task_id, _number = await _task_with_a_stub_subtask(invoke)
    events = tmp_path / "events.jsonl"
    events.write_text(_comment_event(task_id, "Imported comment.") + "\n", encoding="utf-8")

    result = await invoke(["import", "--json", str(events)])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["applied"] is True
    assert [i["level"] for i in payload["issues"]] == ["warn"]
    assert payload["warnings"]


async def test_a_dry_run_over_the_same_events_gains_no_non_zero_path(project, invoke, tmp_path):
    task_id, number = await _task_with_a_stub_subtask(invoke)
    _rename_the_subtask_container(project.squad_dir)
    events = tmp_path / "events.jsonl"
    events.write_text(_comment_event(task_id, "Never written.") + "\n", encoding="utf-8")

    result = await invoke(["import", "--dry-run", "--json", str(events)])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["applied"] is False
    assert payload["dry_run"] is True

    shown = await invoke(["task", number, "show", "--comments"])
    assert "Never written." not in shown.output


async def test_a_pre_pass_refusal_still_exits_1_with_nothing_written(project, invoke, tmp_path):
    """The refusal contract does not move: 1 is still "nothing was written", which is exactly
    what keeps it distinguishable from the applied-and-flagged 3."""
    events = tmp_path / "bad.jsonl"
    events.write_text(
        '{"op":"status","target":"NOPE","status":"weird","as":"manager"}\n', encoding="utf-8"
    )

    result = await invoke(["import", "--json", str(events)])

    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["applied"] is False
    assert payload["issues"][0]["line"] == 1
