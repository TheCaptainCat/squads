"""``Service.seed_bundled_skills()`` is idempotent: calling it a second time allocates no new
ids or sequence numbers, returning an empty list once every bundled skill is already stamped
with a convention-named file.
"""

import pytest

pytestmark = pytest.mark.anyio


async def test_seeding_a_second_time_allocates_nothing_new(svc):
    first = await svc.seed_bundled_skills()
    assert first  # sanity: something was actually seeded

    skills_before = await svc.list_items(item_type="skill")
    ids_before = {sk.id for sk in skills_before}
    seqs_before = {sk.sequence_id for sk in skills_before}

    second = await svc.seed_bundled_skills()
    assert second == []

    skills_after = await svc.list_items(item_type="skill")
    assert {sk.id for sk in skills_after} == ids_before
    assert {sk.sequence_id for sk in skills_after} == seqs_before
