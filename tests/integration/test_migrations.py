"""Forward-only per-version migration runners: each folds/lifts an older on-disk shape into
the next one, idempotently, without touching body prose. Also: migration never rewrites files
under `.overrides/` (a cross-cutting guarantee with the override system).
"""

import re

import pytest

from _helpers import create_item
from squads import _sections as sections
from squads._itemfile import read_frontmatter
from squads._migrations import _meta_compat, _v0_1_to_v0_2, _v0_2_to_v0_3
from squads._models import _markers as markers

pytestmark = pytest.mark.anyio


async def _write_legacy_task(svc) -> str:
    """A task created normally, then hand-rewritten to the pre-0.2 (bare refs + ref_kinds)
    shape."""
    task = (await create_item(svc, "task", "t")).item
    path = svc.paths.abspath(task.path)
    text = path.read_text(encoding="utf-8")
    fm, _ = sections.split_frontmatter(text)
    fm["refs"] = ["GUIDE-000002", "BUG-000003"]
    fm["extra"] = {"ref_kinds": {"BUG-000003": "fixes"}}
    path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")
    return task.id


async def test_v0_1_to_v0_2_folds_ref_kinds_inline_and_is_idempotent(svc):
    task_id = await _write_legacy_task(svc)
    path = svc.paths.abspath((await svc.get(task_id)).path)
    body_before = sections.split_frontmatter(path.read_text(encoding="utf-8"))[1]

    changed = _v0_1_to_v0_2.migrate(svc.paths)
    assert changed == 1

    fm = read_frontmatter(path)
    assert fm["refs"] == ["GUIDE-000002", "BUG-000003:fixes"]
    assert "extra" not in fm
    assert sections.split_frontmatter(path.read_text(encoding="utf-8"))[1] == body_before

    assert _v0_1_to_v0_2.migrate(svc.paths) == 0  # idempotent


async def test_v0_1_to_v0_2_is_a_noop_on_an_already_current_squad(svc):
    await create_item(svc, "task", "fresh")  # already written in the new format
    assert _v0_1_to_v0_2.migrate(svc.paths) == 0


async def test_v0_1_to_v0_2_gives_a_legacy_review_a_findings_skeleton(svc):
    rev = (await create_item(svc, "review", "R")).item
    path = svc.paths.abspath(rev.path)
    text = path.read_text(encoding="utf-8")
    for tag in ("findings", "summary"):
        inner = sections.get_section(text, tag)
        if inner is not None:
            text = text.replace(f"<!-- sq:{tag} -->{inner}<!-- sq:{tag}:end -->\n\n", "")
    path.write_text(text, encoding="utf-8")
    assert not sections.has_section(path.read_text(encoding="utf-8"), "findings")

    assert _v0_1_to_v0_2.migrate(svc.paths) >= 1
    final = path.read_text(encoding="utf-8")
    assert sections.has_section(final, "findings") and sections.has_section(final, "summary")
    await svc.add_finding(rev.id, "Null deref", severity="high")
    assert (await svc.list_findings(rev.id))[0].title == "Null deref"


async def _devolve_to_v0_2(svc, item_id: str, kind: str) -> None:
    """Turn a live item file back into 0.2 shape: sub-entity state in a body `:meta` region,
    nothing in frontmatter, no `:head`."""
    p = svc.paths.abspath((await svc.get(item_id)).path)
    fm, body = sections.split_frontmatter(p.read_text(encoding="utf-8"))
    subs = fm.pop("subentities", []) or []
    body = re.sub(
        r"<!-- sq:[^>]+:head -->.*?<!-- sq:[^>]+:head:end -->\n\n", "", body, flags=re.DOTALL
    )
    for s in subs:
        meta = _meta_compat.render_meta(
            {k: s.get(k) for k in ("status", "assignee", "severity", "story")}
        )
        tag = _meta_compat.meta_tag(kind, s["local_id"])
        region = f"{markers.open_marker(tag)}\n{meta}\n{markers.close_marker(tag)}\n\n"
        body_open = markers.open_marker(f"{kind}:{s['local_id']}:body")
        body = body.replace(body_open, region + body_open, 1)
    p.write_text(sections.join_frontmatter(fm, body), encoding="utf-8")


async def test_v0_2_to_v0_3_lifts_meta_to_frontmatter_and_backfills_the_head(svc):
    await svc.add_dev("python", name="Grace Hopper")
    feat = (await create_item(svc, "feature", "Login")).item
    await svc.add_story(feat.id, "As a user, I want to reset my password")
    task = (await create_item(svc, "task", "Auth", parent=feat.id)).item
    await svc.add_subtask(task.id, "Validate", story="US1", assignee="python-dev")
    rev = (await create_item(svc, "review", "r")).item
    await svc.add_finding(rev.id, "Null deref", severity="high")

    for item_id, kind in ((feat.id, "story"), (task.id, "subtask"), (rev.id, "finding")):
        await _devolve_to_v0_2(svc, item_id, kind)
    sub_path = svc.paths.abspath((await svc.get(task.id)).path)
    assert _meta_compat.has_meta(sub_path.read_text(encoding="utf-8"), "subtask")

    changed = _v0_2_to_v0_3.migrate(svc.paths)
    assert changed == 3

    (sub,) = read_frontmatter(sub_path)["subentities"]
    assert sub == {
        "local_id": "ST1",
        "title": "Validate",
        "status": "Todo",
        "assignee": "python-dev",
        "story": "US1",
    }
    final = sub_path.read_text(encoding="utf-8")
    assert not _meta_compat.has_meta(final, "subtask")
    sub_head = sections.get_section(final, "subtask:ST1:head")
    assert sub_head is not None
    assert "**Status:** ⚪ Todo" in sub_head
    assert "**Assignee:** Grace Hopper" in sub_head  # slug resolved to the role's full name
    # No override in play — the carried-forward status is reachable, nothing to flag.
    assert "migration:" not in (sections.get_section(final, "discussion") or "")

    assert _v0_2_to_v0_3.migrate(svc.paths) == 0  # idempotent


async def test_v0_2_to_v0_3_carries_forward_a_status_the_active_override_cant_reach(svc, invoke):
    """A 0.2 squad whose active override replaces the subtask lifecycle: the legacy status is
    carried forward unchanged (never rewritten, never invented) — the runner itself reports
    nothing (it's frozen, and `sq check` already validates a sub-entity's status against this
    same active/override-aware spec, with a non-zero exit)."""
    task = (await create_item(svc, "task", "Auth")).item
    await svc.add_subtask(task.id, "Validate")
    await svc.update_subtask(task.id, "ST1", status="InProgress")
    await svc.update_subtask(task.id, "ST1", status="Done")
    await _devolve_to_v0_2(svc, task.id, "subtask")

    override_dir = svc.paths.squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        """
[statuses.Pending]
role = "pending"

[statuses.Doing]
role = "active"

[statuses.Complete]
role = "done"

[subentity_kinds.subtask]
lifecycle = "custom_subtask"
completion = "Complete"

[lifecycles.custom_subtask]
initial = "Pending"

[lifecycles.custom_subtask.transitions]
Pending = ["Doing"]
Doing = ["Complete"]
Complete = []
""",
        encoding="utf-8",
    )

    changed = _v0_2_to_v0_3.migrate(svc.paths)
    assert changed == 1

    sub_path = svc.paths.abspath((await svc.get(task.id)).path)
    (sub,) = read_frontmatter(sub_path)["subentities"]
    assert sub["status"] == "Done"  # carried forward unchanged, never rewritten/invented
    final_text = sub_path.read_text(encoding="utf-8")
    assert "migration:" not in (sections.get_section(final_text, "discussion") or "")

    r = await invoke(["check"])
    assert r.exit_code != 0
    assert "invalid status" in r.output and "Done" in r.output and task.id in r.output

    assert _v0_2_to_v0_3.migrate(svc.paths) == 0  # idempotent


async def test_v0_2_to_v0_3_backfills_a_missing_sequence_id(svc):
    task = (await create_item(svc, "task", "t")).item
    p = svc.paths.abspath(task.path)
    stripped = re.sub(r"\nsequence_id: \d+", "", p.read_text(encoding="utf-8"))
    p.write_text(stripped, encoding="utf-8")

    _v0_2_to_v0_3.migrate(svc.paths)

    fm = read_frontmatter(p)
    assert fm["sequence_id"] == task.sequence_id and fm["id"] == task.id
    assert _v0_2_to_v0_3.migrate(svc.paths) == 0


# --------------------------------------------------------------------------- migration x overrides


async def test_migrate_up_never_touches_files_under_overrides(project, invoke):
    from squads import __version__
    from squads._overrides._stamp import write_template_stamp

    squad_dir = project.squad_dir
    override_dir = squad_dir / ".overrides" / "templates" / "items"
    override_dir.mkdir(parents=True, exist_ok=True)
    dest = override_dir / "task.md.j2"
    content = (
        "<!-- sq:body -->\nMIGRATE_MUST_NOT_TOUCH_THIS\n<!-- sq:body:end -->\n\n"
        "<!-- sq:summary -->\n<!-- sq:summary:end -->\n\n"
        "<!-- sq:subtasks -->\n<!-- sq:subtasks:end -->\n\n"
        "## Discussion\n\n<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n"
    )
    dest.write_text(write_template_stamp(content, __version__), encoding="utf-8")
    stat_before = dest.stat()

    result = await invoke(["migrate", "up"])  # a no-op today (schema is current)
    assert result.exit_code == 0, result.output

    stat_after = dest.stat()
    assert stat_after.st_mtime == stat_before.st_mtime
    assert "MIGRATE_MUST_NOT_TOUCH_THIS" in dest.read_text(encoding="utf-8")
