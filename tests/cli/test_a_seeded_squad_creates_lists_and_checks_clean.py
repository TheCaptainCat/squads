"""A squad initialised with the bundled skills seeded, as ``sq init`` leaves it by default,
takes new work and passes ``sq check``; the default test fixture skips the seeding."""

import json

import pytest

pytestmark = pytest.mark.anyio


async def test_a_seeded_squad_creates_lists_and_checks_clean(seeded_project, invoke):
    skills = await invoke(["list", "--type", "skill", "--json"])
    assert skills.exit_code == 0, skills.output
    assert "squads" in {row["title"] for row in json.loads(skills.output)}, "not seeded"

    created = await invoke(["create", "task", "Seeded work", "--author", "manager"])
    assert created.exit_code == 0, created.output

    listed = await invoke(["list", "--type", "task", "--json"])
    assert listed.exit_code == 0, listed.output
    assert [row["title"] for row in json.loads(listed.output)] == ["Seeded work"]

    checked = await invoke(["check"])
    assert checked.exit_code == 0, checked.output
