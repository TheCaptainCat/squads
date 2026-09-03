"""``sq <type> update --set``/``--unset`` on a NON-badge, spec-declared ``extra`` field (a
review's ``target_ref``, a guide's ``tags``): coercion by declared kind (str/list), the
unknown-key rejection (with the dedicated-flag hint for a global field), and ``--unset``
clearing the key. The badge-field half of the same ``--set``/``--unset`` path (which routes
through ``Item.set_badge_value`` instead of ``extra``) is proven alongside it here too, since
it shares the same call site (``ItemsMixin._apply_extra``).
"""

import pytest

from _helpers import create_item
from squads._errors import SquadsError

pytestmark = pytest.mark.anyio


async def test_set_a_generic_str_extra_field_on_the_type_that_declares_it(svc):
    rev = (await create_item(svc, "review", "r")).item
    updated = await svc.update(rev.id, set_extra={"target_ref": "FEAT-2"})
    assert updated.extra["target_ref"] == "FEAT-2"


async def test_set_a_generic_list_extra_field_coerces_a_comma_separated_string(svc):
    guide = (await create_item(svc, "guide", "g")).item
    updated = await svc.update(guide.id, set_extra={"tags": "alpha, beta , gamma"})
    assert updated.extra["tags"] == ["alpha", "beta", "gamma"]


async def test_set_an_undeclared_key_is_rejected_and_lists_the_valid_ones(svc):
    rev = (await create_item(svc, "review", "r")).item
    with pytest.raises(SquadsError, match="not a settable field"):
        await svc.update(rev.id, set_extra={"bogus": "x"})


async def test_set_a_global_field_by_key_hints_at_the_dedicated_flag(svc):
    task = (await create_item(svc, "task", "t")).item
    with pytest.raises(SquadsError, match="use the dedicated --<flag>"):
        await svc.update(task.id, set_extra={"title": "New title"})


async def test_unset_removes_a_previously_set_generic_extra_field(svc):
    rev = (await create_item(svc, "review", "r")).item
    await svc.update(rev.id, set_extra={"target_ref": "FEAT-2"})
    updated = await svc.update(rev.id, unset_extra=["target_ref"])
    assert "target_ref" not in updated.extra


async def test_set_and_unset_a_badge_field_by_key_routes_through_set_badge_value(svc):
    """``severity``/``priority`` are real ``Item`` attributes (not ``extra`` entries), so the
    ``--set``/``--unset`` path for them takes ``Item.set_badge_value``'s ``hasattr`` branch —
    distinct from every other declared field, which stores into ``extra`` instead."""
    bug = (await create_item(svc, "bug", "b")).item
    set_high = await svc.update(bug.id, set_extra={"severity": "high"})
    assert set_high.severity == "high"

    cleared = await svc.update(bug.id, unset_extra=["severity"])
    assert cleared.severity is None


async def test_setting_a_role_extra_field_regenerates_its_claude_pointer(svc, project):
    """``color`` has no dedicated verb (unlike ``full_name``/``is_default``), so a generic
    ``--set`` still lands on the item's own ``extra`` — the write itself is unaffected — but
    the pointer regen this triggers resolves the role through the catalog rather than reading
    that value back, and the catalog's own answer is what reaches the pointer. That is not
    stale: the reconciler ('sq sync', via ``_refresh_catalog_extra``) already treats a
    generically ``--set`` role field as staleness to converge, never a designation to
    preserve, and the regen agreeing with it from the start is a currency win, not a bug: the
    value the next sync would land on is the value the pointer already carries."""
    # the minimal roster registers `manager` as ROLE-000001 with a generated .claude pointer.
    await svc.update("ROLE-000001", set_extra={"color": "magenta"})
    assert (await svc.get("ROLE-000001")).extra["color"] == "magenta"  # the write itself lands
    pointer = (project.root / ".claude" / "agents" / "manager.md").read_text(encoding="utf-8")
    assert "color: cyan" in pointer  # the catalog's own answer, not the ad-hoc extra write
    assert "color: magenta" not in pointer
