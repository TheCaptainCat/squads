"""`sq check --json` carries, on every finding, the rule that produced it. One row per finding
source, because each source is its own code path: a planted defect must surface under the
expected rule."""

import json
import re
import shutil
from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from _helpers import create_item
from squads import _sections as sections
from squads._itemfile import read_frontmatter

pytestmark = pytest.mark.anyio


async def _task_file(svc: Any) -> Any:
    item = (await create_item(svc, "task", "t")).item
    return svc.paths.abspath((await svc.get(item.id)).path)


async def _unbalanced_marker(svc: Any, project: Any, mp: Any) -> None:
    path = await _task_file(svc)
    path.write_text(path.read_text(encoding="utf-8") + "\n<!-- sq:body -->\n", encoding="utf-8")


async def _unparseable_frontmatter(svc: Any, project: Any, mp: Any) -> None:
    (await _task_file(svc)).write_text("---\n: [\n---\nbody\n", encoding="utf-8")


async def _unstamped_template_override(svc: Any, project: Any, mp: Any) -> None:
    from squads._overrides._service import scaffold_template

    target = scaffold_template(project.squad_dir, "items/task.md.j2")
    text = target.read_text(encoding="utf-8")
    target.write_text(re.sub(r".*squads:override-base.*\n?", "", text), encoding="utf-8")


async def _orphaned_skill(svc: Any, project: Any, mp: Any) -> None:
    from squads._workflow import bundled_spec

    await svc.seed_bundled_skills()
    kept = sorted(set(bundled_spec().items) - {"guide"})
    overrides = project.squad_dir / ".overrides"
    overrides.mkdir(parents=True, exist_ok=True)
    (overrides / "workflow.toml").write_text(f"[selected]\nitems = {kept!r}\n", encoding="utf-8")


async def _duplicated_id(svc: Any, project: Any, mp: Any) -> None:
    path = await _task_file(svc)
    shutil.copy(path, path.with_name("TASK-000002-copy.md"))


async def _frontmatter_ahead_of_index(svc: Any, project: Any, mp: Any) -> None:
    path = await _task_file(svc)
    text = path.read_text(encoding="utf-8")
    fm = read_frontmatter(text=text)
    fm["status"] = "Ready"
    path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")


async def _dangling_parent(svc: Any, project: Any, mp: Any) -> None:
    path = await _task_file(svc)
    text = path.read_text(encoding="utf-8")
    fm = read_frontmatter(text=text)
    fm["parent"] = "FEAT-999999"
    path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")
    await svc.repair()


async def _missing_backend_file(svc: Any, project: Any, mp: Any) -> None:
    (project.root / "CLAUDE.md").unlink()


async def _item_file_gone(svc: Any, project: Any, mp: Any) -> None:
    (await _task_file(svc)).unlink()


async def _broken_workflow_override(svc: Any, project: Any, mp: Any) -> None:
    _override(project, "workflow", "statuses = 3")


async def _broken_playbook_override(svc: Any, project: Any, mp: Any) -> None:
    _override(project, "playbook", "types = 3")


def _override(project: Any, document: str, body: str) -> None:
    overrides = project.squad_dir / ".overrides"
    overrides.mkdir(parents=True, exist_ok=True)
    (overrides / f"{document}.toml").write_text(body + "\n", encoding="utf-8")


async def _frontmatter_edit(svc: Any, edit: Callable[[dict[str, Any]], None]) -> None:
    path = await _task_file(svc)
    text = path.read_text(encoding="utf-8")
    fm = read_frontmatter(text=text)
    edit(fm)
    path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")


async def _missing_id(svc: Any, project: Any, mp: Any) -> None:
    await _frontmatter_edit(svc, lambda fm: fm.pop("id"))


async def _malformed_id(svc: Any, project: Any, mp: Any) -> None:
    await _frontmatter_edit(svc, lambda fm: fm.update(id="garbage"))


async def _type_invalid_field(svc: Any, project: Any, mp: Any) -> None:
    await _frontmatter_edit(svc, lambda fm: fm.update(refs=3))


async def _missing_timestamps(svc: Any, project: Any, mp: Any) -> None:
    await _frontmatter_edit(svc, lambda fm: fm.pop("created_at"))


async def _unreadable_file(svc: Any, project: Any, mp: Any) -> None:
    (await _task_file(svc)).write_bytes(b"---\n\xff\xfe\n---\n")


async def _shared_number(svc: Any, project: Any, mp: Any) -> None:
    held = (await create_item(svc, "task", "held")).item
    other = await svc.create("bug", "other", author="manager")
    text = other.path.read_text(encoding="utf-8")
    data = read_frontmatter(text=text)
    data["id"] = f"BUG-{held.sequence_id:06d}"
    data["sequence_id"] = held.sequence_id
    other.path.write_text(sections.replace_frontmatter(text, data), encoding="utf-8")


async def _corrupt_index(svc: Any, project: Any, mp: Any) -> None:
    (project.squad_dir / ".squads.json").write_text("{not json", encoding="utf-8")


_TAG = "<!-- sq:view:milestone_rollup -->\n"
_BODY_CLOSE = "<!-- sq:body:end -->\n"


async def _milestone_text(svc: Any, edit: Callable[[str], str]) -> None:
    created = await svc.create("milestone", "Ship it", author="manager")
    created.path.write_text(edit(created.path.read_text(encoding="utf-8")), encoding="utf-8")


async def _undeclared_view_tag(svc: Any, project: Any, mp: Any) -> None:
    path = await _task_file(svc)
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace("<!-- sq:body -->\n", "<!-- sq:body -->\n<!-- sq:view:no_such_view -->\n", 1),
        encoding="utf-8",
    )


async def _view_tag_outside_the_body(svc: Any, project: Any, mp: Any) -> None:
    await _milestone_text(svc, lambda t: t.replace(_BODY_CLOSE, _BODY_CLOSE + _TAG, 1))


async def _seeded_view_tag_missing(svc: Any, project: Any, mp: Any) -> None:
    await _milestone_text(svc, lambda t: t.replace(_TAG, ""))


async def _body_region_deleted(svc: Any, project: Any, mp: Any) -> None:
    index = await svc.store.load()
    role = next(it for it in index.items.values() if it.type == "role")
    path = svc.paths.abspath(role.path)
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace("<!-- sq:body -->\n", "").replace("<!-- sq:body:end -->\n", ""),
        encoding="utf-8",
    )


async def _block_outside_its_container(svc: Any, project: Any, mp: Any) -> None:
    task = (await svc.create("task", "Host", author="manager")).item
    await svc.add_subtask(task.id, "first")
    path = svc.paths.abspath((await svc.get(task.id)).path)
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace("<!-- sq:subtasks -->\n", "").replace("<!-- sq:subtasks:end -->\n", ""),
        encoding="utf-8",
    )


async def _drifted_workflow_override(svc: Any, project: Any, mp: Any) -> None:
    from squads._overrides._service import scaffold_workflow

    path = scaffold_workflow(project.squad_dir)
    text = path.read_text(encoding="utf-8")
    path.write_text(re.sub(r"(squads:override-base:)\S+", r"\g<1>0.13.1", text), encoding="utf-8")


async def _unloadable_role_override(svc: Any, project: Any, mp: Any) -> None:

    overrides = project.squad_dir / ".overrides" / "roles"
    overrides.mkdir(parents=True, exist_ok=True)
    (overrides / "manager.toml").write_text("not_a_role_key = 1\n", encoding="utf-8")


def _strip_stamp(path: Any) -> None:
    text = path.read_text(encoding="utf-8")
    path.write_text(re.sub(r".*squads:override-base.*\n?", "", text), encoding="utf-8")


def _old_stamp(path: Any) -> None:
    text = path.read_text(encoding="utf-8")
    path.write_text(re.sub(r"(squads:override-base:)\S+", r"\g<1>0.1.0", text), encoding="utf-8")


_TEMPLATE = "items/task.md.j2"


def _template_override(project: Any) -> Any:
    from squads._overrides._service import scaffold_template

    return scaffold_template(project.squad_dir, _TEMPLATE)


async def _template_unreadable(svc: Any, project: Any, mp: Any) -> None:
    _template_override(project).write_bytes(b"\xff\xfe")


async def _template_missing_markers(svc: Any, project: Any, mp: Any) -> None:
    _template_override(project).write_text("no regions here\n", encoding="utf-8")


async def _template_stray_view_tag(svc: Any, project: Any, mp: Any) -> None:
    path = _template_override(project)
    path.write_text("<!-- sq:view:milestone_rollup -->\n" + path.read_text(encoding="utf-8"))


async def _template_drifted(svc: Any, project: Any, mp: Any) -> None:
    import squads._overrides._service as service

    _old_stamp(_template_override(project))
    mp.setattr(service, "template_changed_since", lambda name, stamp: True)


def _role_override(project: Any) -> Any:
    from squads._overrides._service import scaffold_role

    return scaffold_role(project.squad_dir, "manager")


async def _role_unreadable(svc: Any, project: Any, mp: Any) -> None:
    _role_override(project).write_bytes(b"\xff\xfe")


async def _role_unstamped(svc: Any, project: Any, mp: Any) -> None:
    _strip_stamp(_role_override(project))


async def _role_drifted(svc: Any, project: Any, mp: Any) -> None:
    import squads._overrides._service as service

    _old_stamp(_role_override(project))
    mp.setattr(service, "artifact_changed_since", lambda key, stamp: True)


async def _catalog_override_invalid(svc: Any, project: Any, mp: Any) -> None:
    overrides = project.squad_dir / ".overrides"
    overrides.mkdir(parents=True, exist_ok=True)
    (overrides / "roles.toml").write_text("not_a_catalog_key = 1\n", encoding="utf-8")


def _write_override(project: Any, name: str, body: str) -> None:
    path = project.squad_dir / ".overrides" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


async def _catalog_override_unstamped(svc: Any, project: Any, mp: Any) -> None:
    _write_override(project, "roles.toml", '[[roles]]\nslug = "architect"\ntitle = "Chief"\n')


async def _workflow_override_unstamped(svc: Any, project: Any, mp: Any) -> None:
    _write_override(project, "workflow.toml", '[items.task]\nfolder = "tickets"\n')


async def _playbook_override_unstamped(svc: Any, project: Any, mp: Any) -> None:
    _write_override(project, "playbook.toml", '[types.task]\nroles = ["$(*self)"]\n')


# (source, plant, rule the planted defect is reported under)
_SOURCES: list[tuple[str, Callable[[Any, Any, Any], Awaitable[None]], str]] = [
    ("raw-text scan: markers", _unbalanced_marker, "markers_balanced"),
    ("file load: unparseable", _unparseable_frontmatter, "frontmatter_parses"),
    ("override checks: unstamped", _unstamped_template_override, "override_stamped"),
    ("override checks: drifted", _drifted_workflow_override, "override_current"),
    ("override checks: does not load", _unloadable_role_override, "override_loads"),
    ("template override: unreadable", _template_unreadable, "override_loads"),
    ("template override: markers", _template_missing_markers, "override_loads"),
    ("template override: stray view tag", _template_stray_view_tag, "view_tag_in_region"),
    ("template override: drifted", _template_drifted, "override_current"),
    ("role override: unreadable", _role_unreadable, "override_loads"),
    ("role override: unstamped", _role_unstamped, "override_stamped"),
    ("role override: drifted", _role_drifted, "override_current"),
    ("catalog override: invalid", _catalog_override_invalid, "override_loads"),
    ("catalog override: unstamped", _catalog_override_unstamped, "override_stamped"),
    ("workflow override: unstamped", _workflow_override_unstamped, "override_stamped"),
    ("playbook override: unstamped", _playbook_override_unstamped, "override_stamped"),
    ("raw-text scan: undeclared view", _undeclared_view_tag, "view_target_resolves"),
    ("raw-text scan: stray view tag", _view_tag_outside_the_body, "view_tag_in_region"),
    ("raw-text scan: seeded view", _seeded_view_tag_missing, "seeded_view_resolves"),
    ("raw-text scan: body region", _body_region_deleted, "body_regions_present"),
    ("raw-text scan: block outside container", _block_outside_its_container, "block_in_container"),
    ("file load: unreadable", _unreadable_file, "file_readable"),
    ("file load: no id", _missing_id, "id_present"),
    ("file load: bad id", _malformed_id, "id_well_formed"),
    ("file load: bad field", _type_invalid_field, "fields_valid"),
    ("file load: no timestamps", _missing_timestamps, "timestamps_present"),
    ("shared number", _shared_number, "numbers_unique"),
    ("corpus scan", _corrupt_index, "corpus_scans"),
    ("orphaned skills", _orphaned_skill, "skill_type_declared"),
    ("duplicate ids", _duplicated_id, "ids_unique"),
    ("cross-source drift", _frontmatter_ahead_of_index, "frontmatter_matches_index"),
    ("cross-source reconcile", _item_file_gone, "index_reconciled"),
    ("per-item catalog", _dangling_parent, "parent_in"),
    ("squad-global catalog", _missing_backend_file, "backend_reconciled"),
    ("config load: workflow", _broken_workflow_override, "workflow_loads"),
    ("config load: playbook", _broken_playbook_override, "playbook_loads"),
]


@pytest.mark.parametrize(("plant", "rule"), [pytest.param(p, r, id=s) for s, p, r in _SOURCES])
async def test_a_planted_defect_is_reported_under_its_rule(
    svc, project, invoke, monkeypatch, plant, rule
):
    await plant(svc, project, monkeypatch)

    r = await invoke(["check", "--json"])

    issues = json.loads(r.stdout)
    assert issues, r.output
    assert all(isinstance(i["rule"], str) and i["rule"] for i in issues)
    assert rule in {i["rule"] for i in issues}, issues


async def test_a_workflow_override_that_will_not_load_names_the_cause(project, invoke):
    _override(project, "workflow", '[items.task]\nvalidators = ["bogus_name"]')

    r = await invoke(["check", "--json"])

    found = [i for i in json.loads(r.stdout) if i["rule"] == "workflow_loads"]
    assert len(found) == 1
    assert "bogus_name" in found[0]["message"]


async def test_missing_timestamps_are_reported_at_a_declared_level(
    svc, project, invoke, monkeypatch
):
    await _missing_timestamps(svc, project, monkeypatch)

    r = await invoke(["check", "--json"])

    found = [i for i in json.loads(r.stdout) if i["rule"] == "timestamps_present"]
    assert [i["level"] for i in found] == ["warn"]
