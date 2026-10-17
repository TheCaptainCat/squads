"""The read-boundary counterpart to ``tests/unit/test_role_def_refuses_a_blank_full_name.py``.

``RoleDef.__post_init__`` refuses a blank/whitespace-only ``full_name`` at construction, and
that refusal is correct at the two input boundaries that build one from an operator's raw CLI
string (``sq dev add --name``, ``sq role activate --name``). But a squad synced on an earlier
release could already have one of those values *stored* as the role item's ``title``, with
``sq check`` reporting no issues throughout.

The seams a role item's stored ``title`` passes through are :func:`role_base_from_item` and
:func:`dev_base_from_item` (both in ``squads._roles._resolver``, used by ``sq sync``'s catalog
refresh and ``sq role <slug> show``) and :func:`pinned_name_of`. None of them must ever hand a
stored blank to :class:`RoleDef.__post_init__` — that would weaponise an input-side refusal
against a fact this codebase itself used to write and call healthy. Each must instead self-heal
to the value the next full ``sq sync`` converges the item onto: the catalog's name for a
predefined role, the generated pool name for a developer role.

Builds real ``Item``s via the service (``activate_role``/``add_dev``) and blanks the in-memory
``title`` copy directly: the resolver functions take no service and touch no disk, so this is a
pure seam-level pin, independent of the corpus-level drive in
``tests/integration/test_stored_blank_role_name_self_heals_on_sync.py``.
"""

import pytest

from squads._roles._catalog import PREDEFINED, dev_role
from squads._roles._resolver import (
    dev_base_from_item,
    pinned_name_of,
    resolve_role_for_item,
    role_base_from_item,
)
from squads._workflow import ROSTER_ROLE

pytestmark = pytest.mark.anyio

BLANKS = pytest.mark.parametrize(
    "blank", ["", "   ", "\t\n"], ids=["empty", "spaces", "tab-newline"]
)


def _blanked(item, blank):
    """A deep copy of *item* whose stored name is *blank* — the in-memory equivalent of the
    planted-on-disk shape. ``title`` refuses an empty string at assignment, so it is set
    around the validator."""
    blanked = item.model_copy(deep=True)
    object.__setattr__(blanked, "title", blank)
    return blanked


@BLANKS
async def test_a_bundled_roles_base_ignores_a_stored_blank_name(svc, blank):
    item = await svc.activate_role("devops", name="Ada Lovelace")

    base = role_base_from_item(_blanked(item, blank))

    assert base is not None
    assert base.full_name == next(r for r in PREDEFINED if r.slug == "devops").full_name


@BLANKS
async def test_a_chosen_but_blank_stored_name_pins_nothing(svc, blank):
    item = await svc.activate_role("devops", name="Ada Lovelace")
    stored = _blanked(item, blank)

    assert pinned_name_of(stored) is None
    assert resolve_role_for_item(stored, svc.paths.squad_dir).full_name.strip()


@BLANKS
async def test_a_developer_base_falls_back_to_the_generated_pool_name(svc, blank):
    item = await svc.add_dev("python", name="Elias Python")

    base = dev_base_from_item(_blanked(item, blank))

    assert base.full_name == dev_role("python").full_name


async def test_a_real_stored_name_is_kept_by_both_bases(svc):
    activated = await svc.activate_role("qa", name="Mara Tester")
    developer = await svc.add_dev("python", name="Elias Python")

    assert pinned_name_of(activated) == "Mara Tester"
    assert resolve_role_for_item(activated, svc.paths.squad_dir).full_name == "Mara Tester"
    assert dev_base_from_item(developer).full_name == "Elias Python"


async def test_a_role_item_type_still_exists_for_context(svc):
    """Sanity check the fixture set-up actually produced roster items, so a fixture regression
    can't make every test above vacuously pass on an empty roster."""
    await svc.activate_role("devops")
    assert await svc.list_items(item_type=ROSTER_ROLE)
