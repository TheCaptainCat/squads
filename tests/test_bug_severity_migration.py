"""Schema 0.7 -> 0.8 migration: relocate bug item-level severity off extra onto a top-level key."""

import pytest

from squads import _sections as sections
from squads._itemfile import read_frontmatter
from squads._migrations import _v0_7_to_v0_8

pytestmark = pytest.mark.anyio


async def _devolve_to_legacy_severity(svc, bug_id: str, value: str, *, other_extra: bool = False):
    """Hand-rewrite a bug's frontmatter to the pre-0.8 shape: severity nested under ``extra``,
    no top-level ``severity`` key — what a pre-migration file looks like on disk today."""
    item = await svc.get(bug_id)
    path = svc.paths.abspath(item.path)
    text = path.read_text(encoding="utf-8")
    fm, _ = sections.split_frontmatter(text)
    fm.pop("severity", None)
    fm["extra"] = {"other": "kept"} if other_extra else {}
    fm["extra"]["severity"] = value
    path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")


async def test_migrate_relocates_severity_and_drops_extra(svc):
    bug = (await svc.create("bug", "Session leak")).item
    await _devolve_to_legacy_severity(svc, bug.id, "critical")
    path = svc.paths.abspath((await svc.get(bug.id)).path)
    body_before = sections.split_frontmatter(path.read_text(encoding="utf-8"))[1]

    changed = _v0_7_to_v0_8.migrate(svc.paths)
    assert changed == 1

    fm = read_frontmatter(path)
    assert fm["severity"] == "critical"
    assert "extra" not in fm  # emptied extra dropped entirely, not left as {}
    body_after = sections.split_frontmatter(path.read_text(encoding="utf-8"))[1]
    assert body_after == body_before

    assert _v0_7_to_v0_8.migrate(svc.paths) == 0  # idempotent


async def test_migrate_keeps_other_extra_keys(svc):
    bug = (await svc.create("bug", "Flaky test")).item
    await _devolve_to_legacy_severity(svc, bug.id, "high", other_extra=True)

    changed = _v0_7_to_v0_8.migrate(svc.paths)
    assert changed == 1

    fm = read_frontmatter(svc.paths.abspath((await svc.get(bug.id)).path))
    assert fm["severity"] == "high"
    assert fm["extra"] == {"other": "kept"}  # severity popped, sibling key survives


async def test_migrate_noop_on_bug_with_no_legacy_severity(svc):
    await svc.create("bug", "Fresh bug")  # written in the new (or no-severity) shape already
    assert _v0_7_to_v0_8.migrate(svc.paths) == 0


async def test_migrate_does_not_overwrite_an_already_set_top_level_severity(svc):
    bug = (await svc.create("bug", "Race condition")).item
    item = await svc.get(bug.id)
    path = svc.paths.abspath(item.path)
    text = path.read_text(encoding="utf-8")
    fm, _ = sections.split_frontmatter(text)
    fm["severity"] = "low"
    fm["extra"] = {"severity": "critical"}  # stale legacy copy that disagrees with the real value
    path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")

    changed = _v0_7_to_v0_8.migrate(svc.paths)
    assert changed == 1

    fm = read_frontmatter(path)
    assert fm["severity"] == "low"  # top-level value wins, never overwritten from the stale extra
    assert "extra" not in fm


async def test_migrate_leaves_non_bug_types_untouched(svc):
    """Only the bugs folder is walked — findings/priority live elsewhere and stay untouched."""
    rev = (await svc.create("review", "R")).item
    await svc.add_finding(rev.id, "Null deref", severity="high")
    task = (await svc.create("task", "t")).item
    task_path = svc.paths.abspath(task.path)
    task_body_before = task_path.read_text(encoding="utf-8")

    assert _v0_7_to_v0_8.migrate(svc.paths) == 0
    assert task_path.read_text(encoding="utf-8") == task_body_before
    finding_fm = read_frontmatter(svc.paths.abspath((await svc.get(rev.id)).path))
    (finding,) = finding_fm["subentities"]
    assert finding["severity"] == "high"  # sub-entity severity is unaffected — different location
