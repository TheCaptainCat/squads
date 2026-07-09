import re

import pytest

from squads import _sections as sections
from squads._itemfile import read_frontmatter
from squads._migrations import _meta_compat, _v0_1_to_v0_2, _v0_2_to_v0_3
from squads._models import _markers as markers

pytestmark = pytest.mark.anyio


async def _write_legacy_task(svc) -> str:
    """A task created normally, then hand-rewritten to the pre-2 (bare refs + ref_kinds) shape."""
    task = (await svc.create("task", "t")).item
    path = svc.paths.abspath(task.path)
    text = path.read_text(encoding="utf-8")
    fm, _ = sections.split_frontmatter(text)
    fm["refs"] = ["GUIDE-000002", "BUG-000003"]
    fm["extra"] = {"ref_kinds": {"BUG-000003": "fixes"}}
    path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")
    return task.id


async def test_migrate_folds_kinds_and_is_idempotent(svc):
    task_id = await _write_legacy_task(svc)
    path = svc.paths.abspath((await svc.get(task_id)).path)
    body_before = sections.split_frontmatter(path.read_text(encoding="utf-8"))[1]

    changed = _v0_1_to_v0_2.migrate(svc.paths)
    assert changed == 1

    fm = read_frontmatter(path)
    assert fm["refs"] == ["GUIDE-000002", "BUG-000003:fixes"]  # kind folded inline
    assert "extra" not in fm  # emptied ref_kinds map dropped entirely
    # body + markers untouched
    assert sections.split_frontmatter(path.read_text(encoding="utf-8"))[1] == body_before

    # idempotent: a second pass changes nothing
    assert _v0_1_to_v0_2.migrate(svc.paths) == 0


async def test_migrate_noop_on_already_v2(svc):
    await svc.create("task", "fresh")  # written in the new format already
    assert _v0_1_to_v0_2.migrate(svc.paths) == 0


async def test_migrate_gives_legacy_review_a_findings_skeleton(svc):
    rev = (await svc.create("review", "R")).item
    path = svc.paths.abspath(rev.path)
    # devolve to pre-2: a review with no findings container / summary region (free-form prose only)
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
    # the new finding commands now work on the migrated review (the manual LLM step)
    await svc.add_finding(rev.id, "Null deref", severity="high")
    assert (await svc.list_findings(rev.id))[0].title == "Null deref"


async def _devolve_to_v0_2(svc, item_id: str, kind: str) -> None:
    """Turn a live (0.3) item file back into 0.2 shape: each sub-entity's state in a body ``:meta``
    region, no frontmatter ``subentities``, no ``:head``."""
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


async def test_v0_2_to_v0_3_lifts_meta_to_frontmatter_and_backfills_head(svc):
    await svc.add_dev("python", name="Grace Hopper")  # python-dev
    feat = (await svc.create("feature", "Login")).item
    await svc.add_story(feat.id, "As a user, I want to reset my password")  # US1
    task = (await svc.create("task", "Auth", parent=feat.id)).item
    await svc.add_subtask(task.id, "Validate", story="US1", assignee="python-dev")
    rev = (await svc.create("review", "r")).item
    await svc.add_finding(rev.id, "Null deref", severity="high")

    for item_id, kind in ((feat.id, "story"), (task.id, "subtask"), (rev.id, "finding")):
        await _devolve_to_v0_2(svc, item_id, kind)
    sub_path = svc.paths.abspath((await svc.get(task.id)).path)
    # sanity: genuinely 0.2 now — state in :meta, nothing in frontmatter
    assert _meta_compat.has_meta(sub_path.read_text(encoding="utf-8"), "subtask")
    assert "subentities" not in sections.split_frontmatter(sub_path.read_text(encoding="utf-8"))[0]

    changed = _v0_2_to_v0_3.migrate(svc.paths)
    assert changed == 3  # the feature (story), the task (subtask), the review (finding)

    # state lifted into frontmatter, typed and complete
    (sub,) = read_frontmatter(sub_path)["subentities"]
    assert sub == {
        "local_id": "ST1",
        "title": "Validate",
        "status": "Todo",
        "assignee": "python-dev",
        "story": "US1",
    }
    # :meta gone from the body; the :head is rendered with resolved names/titles
    final = sub_path.read_text(encoding="utf-8")
    assert not _meta_compat.has_meta(final, "subtask")
    sub_head = sections.get_section(final, "subtask:ST1:head")
    assert sub_head is not None
    assert "**Status:** ⚪ Todo" in sub_head
    assert "**Assignee:** Grace Hopper" in sub_head  # slug resolved to the role's full name
    assert "**Implements:** US1 — As a user, I want to reset my password" in sub_head
    find_path = svc.paths.abspath((await svc.get(rev.id)).path)
    find_head = sections.get_section(find_path.read_text(encoding="utf-8"), "finding:F1:head")
    assert find_head is not None and "**Severity:** 🟠 High" in find_head
    # idempotent: nothing left to lift
    assert _v0_2_to_v0_3.migrate(svc.paths) == 0


async def test_v0_2_to_v0_3_backfills_sequence_id(svc):
    task = (await svc.create("task", "t")).item  # TASK-2 (sequence 2)
    p = svc.paths.abspath(task.path)
    # simulate a file written before sequence_id was persisted: drop the line
    stripped = re.sub(r"\nsequence_id: \d+", "", p.read_text(encoding="utf-8"))
    p.write_text(stripped, encoding="utf-8")
    assert "sequence_id:" not in stripped

    _v0_2_to_v0_3.migrate(svc.paths)

    fm = read_frontmatter(p)
    assert fm["sequence_id"] == 2 and fm["id"] == "TASK-2"

    assert _v0_2_to_v0_3.migrate(svc.paths) == 0  # idempotent
