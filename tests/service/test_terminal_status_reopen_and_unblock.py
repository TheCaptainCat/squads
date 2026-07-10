"""Being terminal (Accepted/Published) doesn't mean the lifecycle graph dead-ends: a guide can
cycle Draft->Published->Draft->Published, an accepted decision can still be superseded, and
reaching either terminal status unblocks a dependent exactly like reaching Done would.
"""

import pytest

pytestmark = pytest.mark.anyio


async def test_guide_full_cycle_published_draft_published(svc):
    guide = (await svc.create("guide", "Cycle guide")).item
    await svc.set_status(guide.id, "Published")
    await svc.set_status(guide.id, "Draft")
    await svc.set_status(guide.id, "Published")
    assert (await svc.get(guide.id)).status == "Published"


async def test_accepted_decision_can_be_superseded(svc):
    old_adr = (await svc.create("decision", "Old pattern")).item
    await svc.set_status(old_adr.id, "Accepted")
    await svc.set_status(old_adr.id, "Superseded")
    assert (await svc.get(old_adr.id)).status == "Superseded"


async def test_accepted_decision_unblocks_a_dependent(svc):
    adr = (await svc.create("decision", "API contract")).item
    task = (await svc.create("task", "Implement API")).item
    await svc.add_ref(task.id, adr.id, kind="depends-on")

    assert task.id in {it.id for it, _ in await svc.blocked()}  # Proposed ADR is open → blocks
    await svc.set_status(adr.id, "Accepted")  # terminal now → unblocks
    assert await svc.blocked() == []


async def test_published_guide_unblocks_a_dependent(svc):
    guide = (await svc.create("guide", "Deployment guide")).item
    task = (await svc.create("task", "Deploy service")).item
    await svc.add_ref(task.id, guide.id, kind="depends-on")

    assert task.id in {it.id for it, _ in await svc.blocked()}
    await svc.set_status(guide.id, "Published")
    assert await svc.blocked() == []


@pytest.mark.parametrize(
    ("item_type", "title", "terminal_status", "search_term"),
    [
        ("decision", "ADR: Use PostgreSQL", "Accepted", "PostgreSQL"),
        ("guide", "Squads overview guide", "Published", "overview"),
    ],
)
async def test_terminal_item_hidden_from_open_only_view_but_still_findable(
    svc, item_type, title, terminal_status, search_term
):
    """Terminal items stay in the full list and in search — only the open-only view drops them."""
    from squads import _workflow as workflow

    item = (await svc.create(item_type, title)).item
    await svc.set_status(item.id, terminal_status)

    all_items = await svc.list_items()
    assert item.id in [i.id for i in all_items]
    open_items = [i for i in all_items if workflow.is_open(i.status)]
    assert item.id not in [i.id for i in open_items]

    search_hits = [i.id for i, _ in await svc.search(search_term)]
    assert item.id in search_hits
