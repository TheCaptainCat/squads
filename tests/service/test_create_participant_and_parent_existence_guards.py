"""Two ``Service.create()`` fail-closed guards that sit ahead of the parent-*type*/ref-kind
rule tables: the parent id must actually exist (not merely be of an allowed type), and the
author must be a genuine participant (role or operator) — a skill's slug is a real, registered
item slug but is deliberately NOT a participant, so it is rejected the same as an unregistered
one.
"""

import pytest

from squads._errors import ItemNotFoundError, SquadsError

pytestmark = pytest.mark.anyio


async def test_create_with_a_nonexistent_parent_id_raises_item_not_found(svc):
    with pytest.raises(ItemNotFoundError, match="does not exist"):
        await svc.create("task", "t", parent="FEAT-999999")


async def test_a_skill_slug_is_not_a_valid_author_only_role_and_operator_slugs_are(svc):
    seeded = await svc.seed_bundled_skills()
    skill_slug = seeded[0].extra.get("slug", seeded[0].slug)
    with pytest.raises(SquadsError, match="not a registered agent or operator"):
        await svc.create("task", "t", author=skill_slug)
