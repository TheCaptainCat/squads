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
    """``model`` is settable on a role because a *developer's* model has no catalog answer, so
    a generic ``--set`` still lands on the item's own ``extra`` — the write itself is
    unaffected. For a **bundled** role the catalog does answer it, and the pointer regen this
    triggers resolves the role rather than reading the stored value back, so the catalog's own
    answer is what reaches the pointer. That is not stale: the reconciler (``sq sync``, via
    ``_refresh_catalog_extra``) already treats a generically ``--set`` field on a bundled role
    as staleness to ignore, never a designation to preserve, and the regen agreeing with it
    from the start is a currency win, not a bug."""
    # the minimal roster registers `manager` as ROLE-000001 with a generated .claude pointer.
    await svc.update("ROLE-000001", set_extra={"model": "haiku"})
    assert (await svc.get("ROLE-000001")).extra["model"] == "haiku"  # the write itself lands
    pointer = (project.root / ".claude" / "agents" / "manager.md").read_text(encoding="utf-8")
    assert "model: opus" in pointer  # the catalog's own answer, not the ad-hoc extra write
    assert "model: haiku" not in pointer


async def test_a_role_field_that_moved_to_the_catalog_is_refused_with_where_it_lives_now(svc):
    """A key an operator could once ``--set`` on a role, and that is now resolved from the role
    catalog, is refused with the place it is declared instead — not reported as an unknown
    field with no remedy. Someone reaching for ``--set mission=`` has a real intent."""
    with pytest.raises(SquadsError, match=r"\.overrides/roles\.toml"):
        await svc.update("ROLE-000001", set_extra={"mission": "a new mission"})

    with pytest.raises(SquadsError, match=r"roles/<slug>\.toml"):
        await svc.update("ROLE-000001", set_extra={"color": "magenta"})


async def test_a_roles_name_is_refused_with_the_verb_that_actually_sets_it(svc):
    """``full_name`` is the one moved key whose home is not an override document: the name is
    the item's own ``title``, set through the activate/add verbs."""
    with pytest.raises(SquadsError, match="the item's own `title` field"):
        await svc.update("ROLE-000001", set_extra={"full_name": "Someone Else"})


async def test_a_skill_is_not_sent_to_a_role_override_document(svc):
    """The key names are not role-only. A skill's own ``title``/``description``/``model`` must
    never be refused with a remedy that names a *role* override file."""
    skill = await svc.add_skill("Custom Helper")
    with pytest.raises(SquadsError) as exc:
        await svc.update(skill.id, set_extra={"description": "x"})
    assert ".overrides/roles" not in str(exc.value)
