"""``Service.set_body``: replaces the ``:body`` region by default, joins onto the existing
content with a blank-line separator when ``append=True``, and is rejected outright for a
role/skill — those bodies are generated from their fields, not hand-written.
"""

import pytest

from squads._errors import SquadsError

pytestmark = pytest.mark.anyio


async def test_set_body_replaces_by_default_and_appends_with_a_blank_line_separator(svc):
    task = (await svc.create("task", "t", description="summary stays in frontmatter")).item

    await svc.set_body(task.id, "## Description\n\nFull body content.")
    assert await svc.read_body(task.id) == "## Description\n\nFull body content."
    # the frontmatter summary is untouched by a body change
    assert (await svc.get(task.id)).description == "summary stays in frontmatter"

    await svc.set_body(task.id, "More detail.", append=True)
    assert (await svc.read_body(task.id)).endswith("Full body content.\n\nMore detail.")


async def test_set_body_on_a_role_or_skill_is_rejected_as_generated_from_its_fields(svc):
    with pytest.raises(SquadsError, match="generated from its fields"):
        await svc.set_body("ROLE-000001", "free-form body")

    seeded = await svc.seed_bundled_skills()
    with pytest.raises(SquadsError, match="generated from its fields"):
        await svc.set_body(seeded[0].id, "free-form body")
