"""A skill's ``description`` is its summary and the only copy: ``sq skill add`` stores no second
one, the host's pointer reads ``description`` then ``title``, and editing the description
reaches the pointer. An operator's name is its ``title`` alone."""

import pytest

from squads._sections import split_frontmatter

pytestmark = pytest.mark.anyio


def _pointer(project, slug: str) -> str:
    return (project.root / ".claude" / "skills" / slug / "SKILL.md").read_text(encoding="utf-8")


async def test_a_skill_stores_one_description_and_its_pointer_follows_an_edit(project, svc):
    skill = await svc.add_skill("Release Runbook", description="Ship a release safely")
    on_disk = split_frontmatter(project.squad_dir.joinpath(skill.path).read_text("utf-8"))[0]
    assert on_disk["description"] == "Ship a release safely"
    assert "extra" not in on_disk
    assert "description" not in skill.attributes
    assert "Ship a release safely" in _pointer(project, "release-runbook")

    await svc.update(skill.id, description="Ship a release, then verify it")
    await svc.sync()

    assert "Ship a release, then verify it" in _pointer(project, "release-runbook")
    assert "Ship a release safely" not in _pointer(project, "release-runbook")


async def test_a_skill_without_a_description_is_selected_by_its_title(project, svc):
    await svc.add_skill("Plain Runbook")

    assert "Plain Runbook" in _pointer(project, "plain-runbook")


async def test_an_operator_stores_its_name_as_the_title_and_nothing_else(project, svc):
    op = await svc.add_operator("Alice Tester")

    on_disk = split_frontmatter(project.squad_dir.joinpath(op.path).read_text("utf-8"))[0]
    assert on_disk["title"] == "Alice Tester"
    assert on_disk["slug"] == "op-alice"
    assert "full_name" not in on_disk
    assert "extra" not in on_disk
    assert op.attributes == {}
