"""An item whose ``.md`` carries no ``created_at``/``updated_at`` — a hand-authored file, or
one taken over by ``sq adopt`` — must stay mutable, and the first mutation must heal the file.

The failure this pins is a permanent one, not a transient refusal: because the absent value was
re-invented on every read, the on-disk side could never equal the index, so every write seam
refused with a "run ``sq repair``" pointer that repair cannot honour — it rebuilds the index
from markdown and never rewrites markdown, so a repair-then-retry loop never terminates.

The clock is advanced between writing the file and mutating it, deliberately: under a single
frozen instant the invented placeholder coincides with the item's real creation time and the
whole class is invisible, which is how it survived a passing suite.
"""

from datetime import timedelta

import pytest

from _helpers import create_item
from squads import _clock as clock
from squads import _itemfile as itemfile
from squads._sections import join_frontmatter, split_frontmatter

pytestmark = pytest.mark.anyio


async def _strip(svc, item_id: str, *fields: str):
    """Remove *fields* from the item's on-disk frontmatter, as a hand-edit would."""
    path = svc.paths.abspath((await svc.get(item_id)).path)
    data, body = split_frontmatter(path.read_text(encoding="utf-8"))
    for field in fields:
        data.pop(field, None)
    path.write_text(join_frontmatter(data, body), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "fields",
    [("created_at",), ("updated_at",), ("created_at", "updated_at")],
    ids=["created", "updated", "both"],
)
async def test_a_mutation_succeeds_and_heals_the_file(svc, frozen_time, fields):
    task = (await create_item(svc, "task", "hand authored")).item
    created_at = (await svc.get(task.id)).created_at
    path = await _strip(svc, task.id, *fields)

    clock.set_now(frozen_time + timedelta(days=3))
    await svc.comment(task.id, ["still mutable"], as_slug="manager")

    data, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    assert data["created_at"] == clock.iso(created_at)  # healed from the index, not re-invented
    assert data["updated_at"] == clock.iso(clock.now())
    assert itemfile.frontmatter_skew(path.read_text(encoding="utf-8"), await svc.get(task.id)) == []


async def test_a_second_mutation_after_the_heal_still_works(svc, frozen_time):
    """The repair-then-retry loop that never terminated, run forwards: once healed, the item
    behaves like any other, including on a later read at a later instant."""
    task = (await create_item(svc, "task", "hand authored")).item
    await _strip(svc, task.id, "created_at", "updated_at")

    clock.set_now(frozen_time + timedelta(days=1))
    await svc.comment(task.id, ["first"], as_slug="manager")
    clock.set_now(frozen_time + timedelta(days=2))
    await svc.set_body(task.id, "second")

    assert "second" in await svc.read_body(task.id)


async def test_repair_then_mutate_converges_instead_of_refusing_forever(svc, frozen_time):
    """The exact sequence the refusal's own message prescribes. It used to loop: repair
    rebuilds the index (re-inventing a value on its own read), the markdown stays untouched,
    and the next read invents a different one again."""
    task = (await create_item(svc, "task", "hand authored")).item
    await _strip(svc, task.id, "created_at")

    clock.set_now(frozen_time + timedelta(hours=1))
    await svc.repair()
    clock.set_now(frozen_time + timedelta(hours=2))
    await svc.comment(task.id, ["after repair"], as_slug="manager")

    assert [i for i in await svc.check() if i.level == "error"] == []


async def test_check_warns_about_the_absent_timestamp_before_anything_heals_it(svc):
    """Reported rather than silently re-invented: until a write lands, every read of the file
    reports a date it does not contain, so ``check`` names it. A warning, not an error — the
    item is fully usable and any mutation fixes it."""
    task = (await create_item(svc, "task", "hand authored")).item
    await _strip(svc, task.id, "created_at")

    warnings = [i for i in await svc.check() if i.level == "warning" and "created_at" in i.message]
    assert len(warnings) == 1, [i.message for i in await svc.check()]

    await svc.comment(task.id, ["heals it"], as_slug="manager")
    assert await svc.check() == []


async def test_a_genuinely_diverged_timestamp_is_still_refused(svc, frozen_time):
    """The exemption must not have blunted the guard: a *present* on-disk timestamp that
    disagrees with the index is a real skew and must still refuse."""
    from squads._errors import SquadsError

    task = (await create_item(svc, "task", "t")).item
    path = svc.paths.abspath((await svc.get(task.id)).path)
    data, body = split_frontmatter(path.read_text(encoding="utf-8"))
    data["created_at"] = clock.iso(frozen_time - timedelta(days=400))
    path.write_text(join_frontmatter(data, body), encoding="utf-8")

    with pytest.raises(SquadsError, match="diverged"):
        await svc.comment(task.id, ["should refuse"], as_slug="manager")


# ─── repair must not fabricate over what the index already holds ───────────────


@pytest.mark.parametrize(
    "fields",
    [("created_at",), ("updated_at",), ("created_at", "updated_at")],
    ids=["created", "updated", "both"],
)
async def test_repair_keeps_the_indexed_timestamp_rather_than_inventing_one(
    svc, frozen_time, fields
):
    """Rebuilding the index re-reads every field from markdown, and an absent timestamp does
    not read as absent — the loader substitutes ``clock.now()``. Committing that would overwrite
    a value the index already held correctly."""
    task = (await create_item(svc, "task", "hand authored")).item
    before = await svc.get(task.id)
    await _strip(svc, task.id, *fields)

    clock.set_now(frozen_time + timedelta(days=5))
    await svc.repair()

    after = await svc.get(task.id)
    for field in fields:
        assert getattr(after, field) == getattr(before, field), field


async def test_a_repair_then_heal_round_trip_restores_the_real_instant(svc, frozen_time):
    """The whole sequence end to end, which is where the damage used to become permanent: the
    fabricated index value was healed back into the markdown as if it were recovered truth, and
    the item's real creation time survived in neither artifact."""
    task = (await create_item(svc, "task", "hand authored")).item
    created_at = (await svc.get(task.id)).created_at
    path = await _strip(svc, task.id, "created_at")

    clock.set_now(frozen_time + timedelta(days=5))
    await svc.repair()
    clock.set_now(frozen_time + timedelta(days=6))
    await svc.comment(task.id, ["heals it"], as_slug="manager")

    data, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    assert data["created_at"] == clock.iso(created_at)
    assert await svc.check() == []


async def test_a_never_indexed_item_still_gets_a_placeholder_rather_than_failing(svc):
    """There is nothing to carry forward for a file the index has never seen, so the invented
    placeholder stands — the carry-forward narrows the damage, it does not pretend to recover
    what was never recorded. Repair must still succeed and index the item."""
    task = (await create_item(svc, "task", "will be forgotten")).item
    await _strip(svc, task.id, "created_at")
    (svc.paths.index_path).unlink()

    await svc.repair()
    assert (await svc.get(task.id)) is not None


async def test_the_check_warning_does_not_promise_a_value_that_may_not_exist(svc):
    """The warning has to describe what the heal will actually write — the index's current
    value — rather than 'the real value', which is a promise this code cannot keep once a
    repair has run over a file that was already missing the field."""
    task = (await create_item(svc, "task", "hand authored")).item
    await _strip(svc, task.id, "created_at")

    messages = [i.message for i in await svc.check() if "created_at" in i.message]
    assert len(messages) == 1
    assert "the value the index holds" in messages[0]
    assert "the real value" not in messages[0]
