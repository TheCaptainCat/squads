"""The read-boundary counterpart to ``tests/unit/test_role_def_refuses_a_blank_full_name.py``.

``RoleDef.__post_init__`` refuses a blank/whitespace-only ``full_name`` at construction, and
that refusal is correct at the two input boundaries that build one from an operator's raw CLI
string (``sq dev add --name``, ``sq role activate --name``). But a squad synced on v0.13.0 could
already have one of those values *stored* -- that release's own ``sq dev add --tech python
--name "   "`` succeeded, and the value survived repeated syncs, with ``sq check`` reporting no
issues throughout.

The three functions below are the read-boundary seams a role item's own stored ``extra`` passes
through: :func:`role_base_from_item` and :func:`dev_base_from_item` (both in
``squads._roles._resolver``, used by ``sq sync``'s catalog refresh and ``sq role <slug> show``),
and :meth:`RoleDef.from_extra_or_item` (in ``squads._roles._catalog``, the boundary a role item
that resolves against nothing is read through). None of them must ever hand a stored
blank to :class:`RoleDef.__post_init__` -- that would weaponise an input-side refusal against a
fact this codebase itself used to write and call healthy. Each must instead self-heal to the
value the next full ``sq sync`` would converge the item onto: the bundled catalog's own name for
a predefined role, the generated pool name for a developer role.

Builds real ``Item``s via the service (``activate_role``/``add_dev``) rather than hand-rolling
one, then mutates the in-memory ``extra`` copy directly -- the resolver functions themselves take
no service and touch no disk, so this is a pure seam-level pin, independent of the corpus-level
drive in ``tests/integration/test_stored_blank_role_name_self_heals_on_sync.py``.
"""

import pytest

from squads._models._extras import ExtraKey as X
from squads._roles._catalog import RoleDef
from squads._roles._resolver import dev_base_from_item, role_base_from_item
from squads._workflow import ROSTER_ROLE

pytestmark = pytest.mark.anyio


def _blanked(item, **fields):
    """A deep copy of *item* with the given ``extra``/top-level fields overwritten -- the
    in-memory equivalent of the planted-on-disk shape, for testing a resolver function alone."""
    blanked = item.model_copy(deep=True)
    for key, value in fields.items():
        blanked.extra[key] = value
    return blanked


# --------------------------------------------------------------------------------- bundled role


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"], ids=["empty", "spaces", "tab-newline"])
async def test_role_base_from_item_tolerates_a_stored_blank_full_name(svc, blank):
    item = await svc.activate_role("devops")
    stored = _blanked(item, **{X.FULL_NAME: blank})

    base = role_base_from_item(stored)

    assert base is not None
    assert base.full_name.strip()


async def test_role_base_from_item_falls_back_to_the_catalog_default(svc):
    item = await svc.activate_role("devops")
    stored = _blanked(item, **{X.FULL_NAME: "   "})

    base = role_base_from_item(stored)

    from squads._roles._catalog import PREDEFINED

    predefined = next(r for r in PREDEFINED if r.slug == "devops")
    assert base is not None
    assert base.full_name == predefined.full_name


async def test_role_base_from_item_with_a_real_name_is_unaffected(svc):
    item = await svc.activate_role("devops", name="Ada Lovelace")
    base = role_base_from_item(item)
    assert base is not None
    assert base.full_name == "Ada Lovelace"


# ----------------------------------------------------------------------------------- dev role


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"], ids=["empty", "spaces", "tab-newline"])
async def test_dev_base_from_item_tolerates_a_stored_blank_full_name(svc, blank):
    item = await svc.add_dev("python", name="Elias Python")
    stored = _blanked(item, **{X.FULL_NAME: blank})

    base = dev_base_from_item(stored)

    assert base.full_name.strip()


async def test_dev_base_from_item_falls_back_to_the_generated_pool_name(svc):
    item = await svc.add_dev("python", name="Elias Python")
    stored = _blanked(item, **{X.FULL_NAME: "   "})

    base = dev_base_from_item(stored)

    from squads._roles._catalog import dev_role

    pool_default = dev_role("python").full_name
    assert base.full_name == pool_default


async def test_dev_base_from_item_with_a_real_name_is_unaffected(svc):
    item = await svc.add_dev("python", name="Elias Python")
    base = dev_base_from_item(item)
    assert base.full_name == "Elias Python"


# ------------------------------------------------------------------ RoleDef.from_extra_or_item


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"], ids=["empty", "spaces", "tab-newline"])
async def test_from_extra_or_item_tolerates_a_stored_blank_full_name_bundled(svc, blank):
    item = await svc.activate_role("devops")
    stored_extra = dict(item.extra)
    stored_extra[X.FULL_NAME] = blank

    role = RoleDef.from_extra_or_item(
        stored_extra, title=item.title, slug=item.slug, description=item.description
    )

    assert role.full_name.strip()


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"], ids=["empty", "spaces", "tab-newline"])
async def test_from_extra_or_item_tolerates_a_stored_blank_full_name_dev(svc, blank):
    item = await svc.add_dev("python", name="Elias Python")
    stored_extra = dict(item.extra)
    stored_extra[X.FULL_NAME] = blank

    role = RoleDef.from_extra_or_item(
        stored_extra, title=item.title, slug=item.slug, description=item.description
    )

    assert role.full_name.strip()


async def test_from_extra_or_item_tolerates_the_key_being_absent_entirely(svc):
    """The other corpus shape this boundary has to take: an item whose ``extra`` carries no
    ``full_name`` at all, which is what the current write path produces. A subscript here
    would raise on every such role -- the failure a read boundary must never introduce."""
    item = await svc.activate_role("devops")
    assert X.FULL_NAME not in item.extra  # the shape under test, asserted not assumed

    role = RoleDef.from_extra_or_item(
        item.extra, title=item.title, slug=item.slug, description=item.description
    )

    assert role.full_name == item.title


async def test_from_extra_or_item_with_a_real_stored_name_is_unaffected(svc):
    """The legacy shape: an ``extra`` that still carries the mirror a previous release wrote
    is read from, not ignored."""
    item = await svc.activate_role("qa", name="Mara Tester")
    stored_extra = {**item.extra, X.FULL_NAME: "Mara Tester"}

    role = RoleDef.from_extra_or_item(
        stored_extra, title="something else", slug=item.slug, description=item.description
    )

    assert role.full_name == "Mara Tester"


async def test_a_role_item_type_still_exists_for_context(svc):
    """Sanity check the fixture set-up actually produced roster items, so a fixture regression
    can't make every test above vacuously pass on an empty roster."""
    roles = await svc.list_items(item_type=ROSTER_ROLE)
    assert roles
