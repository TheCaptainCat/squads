"""The `sq override` CLI surface: scaffold/list/diff/update reach the service and exit/print
correctly, `--json` on each carries a pinned shape, and `sq check --json` surfaces an override
error at exit 3. Service-level behaviour lives in
tests/integration/test_override_scaffold_scan_diff_update_and_check.py.
"""

import json
from pathlib import Path

import pytest

from squads import __version__
from squads._overrides._service import STATE_CURRENT
from squads._overrides._stamp import read_template_stamp, read_toml_stamp, write_template_stamp

pytestmark = pytest.mark.anyio


def _place_template(squad_dir: Path, name: str, content: str, *, stamp: str) -> Path:
    target = squad_dir / ".overrides" / "templates" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(write_template_stamp(content, stamp), encoding="utf-8")
    return target


def _valid_task_override() -> str:
    return (
        "<!-- sq:body -->\nCUSTOM\n<!-- sq:body:end -->\n\n"
        "<!-- sq:summary -->\n<!-- sq:summary:end -->\n\n"
        "<!-- sq:subtasks -->\n<!-- sq:subtasks:end -->\n\n"
        "## Discussion\n\n<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n"
    )


def _broken_task_override() -> str:
    return (
        "## Description\n\nMISSING MARKERS\n\n<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n"
    )


async def test_scaffold_creates_a_stamped_override_and_refuses_clobber_without_force(
    project, invoke
) -> None:
    r = await invoke(["override", "scaffold", "items/task.md.j2"])
    assert r.exit_code == 0, r.output
    dest = project.squad_dir / ".overrides" / "templates" / "items/task.md.j2"
    assert read_template_stamp(dest.read_text(encoding="utf-8")) is not None

    assert (await invoke(["override", "scaffold", "items/task.md.j2"])).exit_code == 1
    force = await invoke(["override", "scaffold", "--force", "items/task.md.j2"])
    assert force.exit_code == 0, force.output


async def test_scaffold_role_creates_a_stamped_toml(project, invoke) -> None:
    r = await invoke(["override", "scaffold", "--role", "architect"])
    assert r.exit_code == 0, r.output
    assert (project.squad_dir / ".overrides" / "roles" / "architect.toml").exists()


async def test_scaffold_new_creates_a_stamped_toml_and_reports_the_path(project, invoke) -> None:
    r = await invoke(["override", "scaffold", "--new", "security-analyst"])
    assert r.exit_code == 0, r.output
    dest = project.squad_dir / ".overrides" / "roles" / "security-analyst.toml"
    assert dest.exists()
    assert "security-analyst.toml" in r.output.replace("\n", "")
    assert "sq role activate security-analyst" in r.output.replace("\n", " ")

    clobber = await invoke(["override", "scaffold", "--new", "security-analyst"])
    assert clobber.exit_code == 1

    forced = await invoke(["override", "scaffold", "--new", "security-analyst", "--force"])
    assert forced.exit_code == 0, forced.output


async def test_scaffold_new_on_a_bundled_slug_errors_and_points_at_role(project, invoke) -> None:
    r = await invoke(["override", "scaffold", "--new", "architect"])
    assert r.exit_code == 1
    assert "--role" in r.output


async def test_scaffold_new_and_role_are_mutually_exclusive(project, invoke) -> None:
    r = await invoke(["override", "scaffold", "--role", "architect", "--new", "security-analyst"])
    assert r.exit_code != 0


@pytest.mark.parametrize("bad_slug", ["../../pwned", "/tmp/x", ""])
async def test_scaffold_new_rejects_a_traversal_or_empty_slug(project, invoke, bad_slug) -> None:
    r = await invoke(["override", "scaffold", "--new", bad_slug])
    assert r.exit_code == 1, r.output
    escaped = project.squad_dir.parent / "pwned"
    assert not escaped.exists()
    assert not (project.squad_dir / ".overrides" / "roles" / ".toml").exists()


@pytest.mark.parametrize("bad_slug", ["../../pwned", "/tmp/x", ""])
async def test_scaffold_role_rejects_a_traversal_or_empty_slug(project, invoke, bad_slug) -> None:
    r = await invoke(["override", "scaffold", "--role", bad_slug])
    assert r.exit_code == 1, r.output
    escaped = project.squad_dir.parent / "pwned"
    assert not escaped.exists()
    assert not (project.squad_dir / ".overrides" / "roles" / ".toml").exists()


async def test_scaffold_new_with_can_spawn_emits_an_active_true_key(project, invoke) -> None:
    r = await invoke(["override", "scaffold", "--new", "orchestrator", "--can-spawn"])
    assert r.exit_code == 0, r.output
    text = (project.squad_dir / ".overrides" / "roles" / "orchestrator.toml").read_text(
        encoding="utf-8"
    )
    assert "can_spawn = true" in text


async def test_scaffold_with_no_name_and_no_role_exits_nonzero(project, invoke) -> None:
    assert (await invoke(["override", "scaffold"])).exit_code != 0


async def test_list_reports_no_overrides_then_the_scaffolded_one_with_a_pinned_json_shape(
    project, invoke
) -> None:
    empty = await invoke(["override", "list"])
    assert empty.exit_code == 0, empty.output
    assert "no overrides" in empty.output.lower()

    await invoke(["override", "scaffold", "items/task.md.j2"])
    r = await invoke(["override", "list", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert len(data) == 1
    assert set(data[0]) == {"name", "kind", "base_version", "state"}
    assert data[0] == {
        "name": "items/task.md.j2",
        "kind": "template",
        "base_version": __version__,
        "state": STATE_CURRENT,
    }


async def test_diff_prints_both_delta_sections_and_a_pinned_json_shape(project, invoke) -> None:
    await invoke(["override", "scaffold", "items/task.md.j2"])
    r = await invoke(["override", "diff", "items/task.md.j2"])
    assert r.exit_code == 0, r.output
    assert "Δ-mine" in r.output
    assert "Δ-upgrade" in r.output

    no_drift = await invoke(["override", "diff"])
    assert "no drifted" in no_drift.output.lower()

    json_result = await invoke(["override", "diff", "items/task.md.j2", "--json"])
    entry = json.loads(json_result.output)[0]
    assert {"name", "delta_mine", "delta_upgrade", "base_available"} <= set(entry)


async def test_update_re_stamps_a_single_override_and_bulk_re_stamps_all(project, invoke) -> None:
    squad_dir = project.squad_dir
    _place_template(squad_dir, "items/task.md.j2", _valid_task_override(), stamp="0.1.0")
    r = await invoke(["override", "update", "items/task.md.j2"])
    assert r.exit_code == 0, r.output
    path = squad_dir / ".overrides" / "templates" / "items/task.md.j2"
    assert read_template_stamp(path.read_text(encoding="utf-8")) == __version__

    _place_template(squad_dir, "items/bug.md.j2", _valid_task_override(), stamp="0.1.0")
    bulk = await invoke(["override", "update"])
    assert bulk.exit_code == 0, bulk.output
    bug_path = squad_dir / ".overrides" / "templates" / "items/bug.md.j2"
    assert read_template_stamp(bug_path.read_text(encoding="utf-8")) == __version__


async def test_update_role_re_stamps_the_toml_and_preserves_its_content(project, invoke) -> None:
    squad_dir = project.squad_dir
    target = squad_dir / ".overrides" / "roles" / "architect.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# squads:override-base:0.1.0\nfull_name = 'Ada'\n", encoding="utf-8")

    r = await invoke(["override", "update", "--role", "architect"])
    assert r.exit_code == 0, r.output
    text = target.read_text(encoding="utf-8")
    assert read_toml_stamp(text) == __version__
    assert "Ada" in text


async def test_check_json_reports_an_override_error_and_exits_3(project, invoke) -> None:
    _place_template(
        project.squad_dir, "items/task.md.j2", _broken_task_override(), stamp=__version__
    )
    result = await invoke(["check", "--json"])
    assert result.exit_code == 3
    data = json.loads(result.output)
    assert [d for d in data if d["level"] == "error" and ".overrides" in d["item"]]


async def test_list_plain_output_renders_a_table_with_the_state_column(project, invoke) -> None:
    """The non-``--json`` render path — every prior list test in this file used ``--json``
    once at least one override existed, so the plain Table (and its per-state color) never ran
    with actual rows."""
    await invoke(["override", "scaffold", "items/task.md.j2"])
    r = await invoke(["override", "list"])
    assert r.exit_code == 0, r.output
    assert "items/task.md.j2" in r.output
    assert "current" in r.output.lower()


async def test_scaffold_diff_and_update_all_reach_the_workflow_kind(project, invoke) -> None:
    """The workflow-kind branch of every override subcommand, driven through the real CLI —
    both the ``workflow`` positional name and the ``--workflow`` flag form."""
    scaffolded = await invoke(["override", "scaffold", "workflow"])
    assert scaffolded.exit_code == 0, scaffolded.output
    dest = project.squad_dir / ".overrides" / "workflow.toml"
    assert dest.exists()

    listed = await invoke(["override", "list"])
    assert "workflow" in listed.output

    diffed = await invoke(["override", "diff", "--workflow"])
    assert diffed.exit_code == 0, diffed.output
    assert "Δ-mine" in diffed.output and "Δ-upgrade" in diffed.output

    from squads._overrides._stamp import stamp_toml_file

    stamp_toml_file(dest, "0.1.0")
    updated = await invoke(["override", "update", "workflow"])
    assert updated.exit_code == 0, updated.output

    from squads import __version__
    from squads._overrides._stamp import read_toml_stamp

    assert read_toml_stamp(dest.read_text(encoding="utf-8")) == __version__


async def test_diff_plain_output_renders_for_the_role_and_workflow_kinds_too(
    project, invoke
) -> None:
    """The template kind's plain diff render is already proven above; role and workflow each
    take their own label branch in ``_print_diff_result``."""
    await invoke(["override", "scaffold", "--role", "architect"])
    role_diff = await invoke(["override", "diff", "--role", "architect"])
    assert role_diff.exit_code == 0, role_diff.output
    assert "--role architect" in role_diff.output

    await invoke(["override", "scaffold", "workflow"])
    workflow_diff = await invoke(["override", "diff", "workflow"])
    assert workflow_diff.exit_code == 0, workflow_diff.output
    assert "kind: workflow" in workflow_diff.output
