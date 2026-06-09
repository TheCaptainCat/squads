from squads import _sections as sections
from squads._itemfile import read_frontmatter
from squads._migrations import _v1_to_v2
from squads._models._enums import ItemType, Severity


def _write_legacy_task(svc) -> str:
    """A task created normally, then hand-rewritten to the pre-2 (bare refs + ref_kinds) shape."""
    task = svc.create(ItemType.TASK, "t").item
    path = svc.paths.abspath(task.path)
    text = path.read_text(encoding="utf-8")
    fm, _ = sections.split_frontmatter(text)
    fm["refs"] = ["GUIDE-000002", "BUG-000003"]
    fm["extra"] = {"ref_kinds": {"BUG-000003": "fixes"}}
    path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")
    return task.id


def test_migrate_folds_kinds_and_is_idempotent(svc):
    task_id = _write_legacy_task(svc)
    path = svc.paths.abspath(svc.get(task_id).path)
    body_before = sections.split_frontmatter(path.read_text(encoding="utf-8"))[1]

    changed = _v1_to_v2.migrate(svc.paths)
    assert changed == 1

    fm = read_frontmatter(path)
    assert fm["refs"] == ["GUIDE-000002", "BUG-000003:fixes"]  # kind folded inline
    assert "extra" not in fm  # emptied ref_kinds map dropped entirely
    # body + markers untouched
    assert sections.split_frontmatter(path.read_text(encoding="utf-8"))[1] == body_before

    # idempotent: a second pass changes nothing
    assert _v1_to_v2.migrate(svc.paths) == 0


def test_migrate_noop_on_already_v2(svc):
    svc.create(ItemType.TASK, "fresh")  # written in the new format already
    assert _v1_to_v2.migrate(svc.paths) == 0


def test_migrate_gives_legacy_review_a_findings_skeleton(svc):
    rev = svc.create(ItemType.REVIEW, "R").item
    path = svc.paths.abspath(rev.path)
    # devolve to pre-2: a review with no findings container / summary region (free-form prose only)
    text = path.read_text(encoding="utf-8")
    for tag in ("findings", "summary"):
        inner = sections.get_section(text, tag)
        if inner is not None:
            text = text.replace(f"<!-- sq:{tag} -->{inner}<!-- sq:{tag}:end -->\n\n", "")
    path.write_text(text, encoding="utf-8")
    assert not sections.has_section(path.read_text(encoding="utf-8"), "findings")

    assert _v1_to_v2.migrate(svc.paths) >= 1
    final = path.read_text(encoding="utf-8")
    assert sections.has_section(final, "findings") and sections.has_section(final, "summary")
    # the new finding commands now work on the migrated review (the manual LLM step)
    svc.add_finding(rev.id, "Null deref", severity=Severity.HIGH)
    assert svc.list_findings(rev.id)[0].title == "Null deref"
