"""`sq repair`'s counter/renumber-collision guarantees, and its idempotency across the setups
that actually exercise it (fresh squad, skill-seeded, repadded) — consolidated into one
parametrized case per CONVENTIONS.md's dedup discipline rather than one near-identical test
per feature.
"""

import pytest

pytestmark = pytest.mark.anyio


async def test_repair_keeps_the_counter_after_the_top_items_file_is_deleted(svc):
    await svc.create("feature", "alpha")
    top = (await svc.create("task", "beta")).item
    assert (await svc.store.load()).counter == top.sequence_id

    svc.paths.abspath(top.path).unlink()
    result = await svc.repair()

    assert result.db.counter == top.sequence_id, "counter must not regress after file loss"
    assert top.id in result.missing_ids


async def test_a_freed_sequence_number_is_never_reused_after_repair(svc):
    await svc.create("feature", "alpha")
    top = (await svc.create("task", "beta")).item

    svc.paths.abspath(top.path).unlink()
    await svc.repair()

    new_item = (await svc.create("bug", "new bug")).item
    assert new_item.sequence_id == top.sequence_id + 1


async def test_a_hand_regressed_counter_is_corrected_on_the_next_write(svc):
    await svc.create("feature", "f1")
    task = (await svc.create("task", "t1")).item

    async with svc.store.transaction() as db:
        db.counter = 1  # simulate a hand-edit that regressed the counter

    loaded = await svc.store.load()
    assert loaded.counter == task.sequence_id  # load() corrects the in-memory value ...

    new_item = (await svc.create("bug", "should follow the real max")).item
    assert new_item.sequence_id == task.sequence_id + 1


async def test_repair_renumber_resolves_a_sequence_collision(svc):
    """A collision like a git merge would produce: two items sharing one number."""
    await svc.create("task", "real task")
    bug = (await svc.create("bug", "real bug")).item
    feat_dir = svc.paths.folder_for("feature", spec=svc.spec)
    forged = feat_dir / "FEAT-000003-forged.md"
    forged.write_text(
        "---\nid: FEAT-000003\nsequence_id: 3\ntype: feature\ntitle: forged\nstatus: Draft\n"
        "created_at: '2026-01-01T00:00:00Z'\nupdated_at: '2026-01-01T00:00:00Z'\n---\n"
        "<!-- sq:body -->\n<!-- sq:body:end -->\n"
        "<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n",
        encoding="utf-8",
    )
    await svc.repair()  # index the forged item so a ref to it resolves
    await svc.add_ref(bug.id, "FEAT-000003")

    result = await svc.repair(renumber=True)
    db = result.db

    numbers = list(db.items)
    assert len(numbers) == len(set(numbers)), "no duplicate numbers remain"
    assert bug.sequence_id in db.items  # bug kept its number (sorts before the forged feature)
    new_feat = next(it.id for it in db.items.values() if it.id.startswith("FEAT-"))
    assert new_feat != "FEAT-000003"
    assert db.items[bug.sequence_id].refs == [new_feat]  # ref rewritten to the reassigned id


# --------------------------------------------------------------------------- idempotency, once


async def _seed_fresh(svc):
    await svc.create("task", "t")


async def _seed_with_seeded_skills(svc):
    await svc.seed_bundled_skills()


async def _seed_after_repad(svc):
    await svc.create("task", "t")
    await svc.repad(7)


@pytest.mark.parametrize("seed", [_seed_fresh, _seed_with_seeded_skills, _seed_after_repad])
async def test_repair_is_idempotent_after_a_variety_of_prior_mutations(svc, seed):
    await seed(svc)

    first = await svc.repair()
    before = {seq: it.model_dump(mode="json") for seq, it in first.db.items.items()}

    second = await svc.repair()
    after = {seq: it.model_dump(mode="json") for seq, it in second.db.items.items()}

    assert before == after, "a second repair must produce no diff"
    assert second.missing_ids == []
