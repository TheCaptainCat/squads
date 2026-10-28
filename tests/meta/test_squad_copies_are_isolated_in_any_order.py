"""The per-module squad template hands every test its own copy, whatever ran before it."""

from pathlib import Path

import pytest

from tests._helpers import create_item


async def test_a_created_item_takes_the_templates_next_id(svc) -> None:
    """The first item of a fresh copy takes the id the template's counter is at."""
    first = await create_item(svc, "task", "first")
    assert first.item.id == "TASK-2"


async def test_another_created_item_takes_the_same_id(svc) -> None:
    """A twin of the test above: neither sees the other's item."""
    first = await create_item(svc, "task", "first")
    assert first.item.id == "TASK-2"
    assert [i.id for i in await svc.list_items(item_type="task")] == [first.item.id]


@pytest.mark.parametrize("name", ["alpha", "beta", "gamma"])
def test_a_file_written_into_a_copy_is_invisible_to_the_other_rows(project, name: str) -> None:
    """Each row finds none of the files its siblings wrote into their copies."""
    siblings = {"alpha", "beta", "gamma"} - {name}
    assert not any((project.squad_dir / f"{s}.txt").exists() for s in siblings)
    (project.squad_dir / f"{name}.txt").write_text(name, encoding="utf-8")


def test_the_copy_is_the_current_directory(project) -> None:
    assert Path.cwd().resolve() == project.root.resolve()


def test_a_seeded_copy_carries_the_bundled_skills(seeded_project) -> None:
    assert any(p.name.startswith("SKILL-") for p in seeded_project.squad_dir.rglob("*.md"))
