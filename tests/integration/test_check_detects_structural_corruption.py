"""``sq check`` catches structural corruption that bypasses the normal service API: an index
entry pointing at a parent that no longer exists, a body whose marker pair was broken by a
direct file edit, and a stray ``SKILL-``-prefixed file with no frontmatter ``id`` at all
(distinct from a pre-migration slug-named skill body file, which is skipped silently on
purpose — that's not corruption, it's a not-yet-migrated file).
"""

import pytest

pytestmark = pytest.mark.anyio


async def test_check_detects_a_dangling_parent(svc):
    task = (await svc.create("task", "t")).item
    async with svc.store.transaction() as db:
        db.items[task.sequence_id].parent = "FEAT-999999"
    issues = await svc.check()
    assert any("dangling parent" in i.message and i.item == task.id for i in issues)


async def test_check_detects_a_broken_marker(svc):
    task = (await svc.create("task", "t")).item
    path = svc.paths.abspath(task.path)
    text = path.read_text(encoding="utf-8").replace("<!-- sq:body:end -->", "")
    path.write_text(text, encoding="utf-8")
    issues = await svc.check()
    assert any("sq:body" in i.message for i in issues)


async def test_check_reports_an_id_prefixed_skill_file_missing_its_frontmatter_id(svc):
    skills_folder = svc.paths.squad_dir / "agents/skills"
    skills_folder.mkdir(parents=True, exist_ok=True)
    (skills_folder / "SKILL-badfile.md").write_text(
        "---\ntitle: broken\n---\n# broken\n", encoding="utf-8"
    )
    issues = await svc.check()
    errors = [i for i in issues if i.level == "error" and "SKILL-badfile.md" in i.item]
    assert errors, f"expected an error for SKILL-badfile.md, got issues: {issues}"
