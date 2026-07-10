"""``sq <type> update --set``/``--unset`` on a NON-badge, spec-declared ``extra`` field (a
review's ``target_ref``, a guide's ``tags``): coercion by declared kind (str/list), the
unknown-key rejection (with the dedicated-flag hint for a global field), and ``--unset``
clearing the key. The badge-field half of the same ``--set``/``--unset`` path (which routes
through ``Item.set_badge_value`` instead of ``extra``) is proven alongside it here too, since
it shares the same call site (``ItemsMixin._apply_extra``).
"""

import pytest

from squads._errors import SquadsError

pytestmark = pytest.mark.anyio


async def test_set_a_generic_str_extra_field_on_the_type_that_declares_it(svc):
    rev = (await svc.create("review", "r")).item
    updated = await svc.update(rev.id, set_extra={"target_ref": "FEAT-2"})
    assert updated.extra["target_ref"] == "FEAT-2"


async def test_set_a_generic_list_extra_field_coerces_a_comma_separated_string(svc):
    guide = (await svc.create("guide", "g")).item
    updated = await svc.update(guide.id, set_extra={"tags": "alpha, beta , gamma"})
    assert updated.extra["tags"] == ["alpha", "beta", "gamma"]


async def test_set_an_undeclared_key_is_rejected_and_lists_the_valid_ones(svc):
    rev = (await svc.create("review", "r")).item
    with pytest.raises(SquadsError, match="not a settable field"):
        await svc.update(rev.id, set_extra={"bogus": "x"})


async def test_set_a_global_field_by_key_hints_at_the_dedicated_flag(svc):
    task = (await svc.create("task", "t")).item
    with pytest.raises(SquadsError, match="use the dedicated --<flag>"):
        await svc.update(task.id, set_extra={"title": "New title"})


async def test_unset_removes_a_previously_set_generic_extra_field(svc):
    rev = (await svc.create("review", "r")).item
    await svc.update(rev.id, set_extra={"target_ref": "FEAT-2"})
    updated = await svc.update(rev.id, unset_extra=["target_ref"])
    assert "target_ref" not in updated.extra


async def test_set_and_unset_a_badge_field_by_key_routes_through_set_badge_value(svc):
    """``severity``/``priority`` are real ``Item`` attributes (not ``extra`` entries), so the
    ``--set``/``--unset`` path for them takes ``Item.set_badge_value``'s ``hasattr`` branch —
    distinct from every other declared field, which stores into ``extra`` instead."""
    bug = (await svc.create("bug", "b")).item
    set_high = await svc.update(bug.id, set_extra={"severity": "high"})
    assert set_high.severity == "high"

    cleared = await svc.update(bug.id, unset_extra=["severity"])
    assert cleared.severity is None


async def test_setting_a_role_extra_field_regenerates_its_claude_pointer(svc, project):
    # the minimal roster registers `manager` as ROLE-000001 with a generated .claude pointer.
    await svc.update("ROLE-000001", set_extra={"color": "magenta"})
    assert (await svc.get("ROLE-000001")).extra["color"] == "magenta"
    pointer = (project.root / ".claude" / "agents" / "manager.md").read_text(encoding="utf-8")
    assert "color: magenta" in pointer  # regenerated from the edited config, not stale
