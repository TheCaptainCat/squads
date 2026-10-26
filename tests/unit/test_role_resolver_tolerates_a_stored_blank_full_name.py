"""The read-boundary counterpart to ``tests/unit/test_role_def_refuses_a_blank_full_name.py``.

``RoleDef.__post_init__`` refuses a blank/whitespace-only ``full_name`` at construction, and
that refusal is correct at the two input boundaries that build one from an operator's raw CLI
string (``sq dev add --name``, ``sq role activate --name``). But a squad synced on an earlier
release could already have one of those values *stored* as the role item's ``title``, with
``sq check`` reporting no issues throughout.

The seams a role item's stored ``title`` passes through are :func:`role_base_from_item` and
:func:`stored_values` (both in ``squads._roles._resolver``, used by every reader of a role). None
of them must ever hand a stored blank to :class:`RoleDef.__post_init__` — that would turn an
input-side refusal against a stored value that ``sq sync`` accepts. Each must instead self-heal:
the catalog's name for a catalog role, the template's name pattern for a template role.

Builds real ``Item``s via the service and blanks the in-memory ``title`` copy directly: the
resolver functions take no service and touch no disk, so this is a pure seam-level pin,
independent of the corpus-level drive in
``tests/integration/test_a_stored_blank_role_name_reads_as_unset.py``.
"""

import pytest

from _helpers import catalog_of, dev_role
from squads._roles._catalog import PREDEFINED
from squads._roles._resolver import (
    resolve_role_for_item,
    role_base_from_item,
    stored_values,
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

    base = role_base_from_item(_blanked(item, blank), catalog_of(None))

    assert base is not None
    assert base.full_name == next(r for r in PREDEFINED if r.slug == "devops").full_name


@BLANKS
async def test_a_chosen_but_blank_stored_name_pins_nothing(svc, blank):
    item = await svc.activate_role("devops", name="Ada Lovelace")
    stored = _blanked(item, blank)

    values = stored_values(stored)
    assert values is not None
    assert values.name is None
    assert resolve_role_for_item(
        stored, svc.paths.squad_dir, catalog=catalog_of(svc.paths.squad_dir)
    ).full_name.strip()


@BLANKS
async def test_a_template_base_falls_back_to_the_templates_name_pattern(svc, blank):
    item = await svc.activate_role(None, from_template="dev", tech="python", name="Ada Python")

    base = role_base_from_item(_blanked(item, blank), catalog_of(None))

    assert base is not None
    assert base.full_name == dev_role("python").full_name


async def test_a_real_stored_name_is_kept_by_both_bases(svc):
    activated = await svc.activate_role("qa", name="Mara Tester")
    developer = await svc.activate_role(None, from_template="dev", tech="python", name="Ada Python")

    for item, name in ((activated, "Mara Tester"), (developer, "Ada Python")):
        values = stored_values(item)
        assert values is not None
        assert values.name == name
        assert (
            resolve_role_for_item(
                item, svc.paths.squad_dir, catalog=catalog_of(svc.paths.squad_dir)
            ).full_name
            == name
        )


async def test_a_role_item_type_still_exists_for_context(svc):
    """Sanity check the fixture set-up actually produced roster items, so a fixture regression
    can't make every test above vacuously pass on an empty roster."""
    await svc.activate_role("devops")
    assert await svc.list_items(item_type=ROSTER_ROLE)
