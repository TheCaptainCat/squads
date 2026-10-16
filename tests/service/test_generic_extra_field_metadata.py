"""``sq <type> update --set``/``--unset`` on a NON-badge, spec-declared ``extra`` field (a
review's ``target_ref``, a guide's ``tags``): coercion by declared kind (str/list), the
unknown-key rejection (with the dedicated-flag hint for a global field), and ``--unset``
clearing the key. The badge-field half of the same ``--set``/``--unset`` path (which routes
through ``Item.set_badge_value`` instead of ``extra``) is proven alongside it here too, since
it shares the same call site (``ItemsMixin._apply_attributes``).
"""

import pytest

from _helpers import create_item
from squads._errors import SquadsError

pytestmark = pytest.mark.anyio


async def test_set_a_generic_str_extra_field_on_the_type_that_declares_it(svc):
    rev = (await create_item(svc, "review", "r")).item
    updated = await svc.update(rev.id, set_attributes={"target_ref": "FEAT-2"})
    assert updated.attributes["target_ref"] == "FEAT-2"


async def test_set_a_generic_list_extra_field_coerces_a_comma_separated_string(svc):
    guide = (await create_item(svc, "guide", "g")).item
    updated = await svc.update(guide.id, set_attributes={"tags": "alpha, beta , gamma"})
    assert updated.attributes["tags"] == ["alpha", "beta", "gamma"]


async def test_set_an_undeclared_key_is_rejected_and_lists_the_valid_ones(svc):
    rev = (await create_item(svc, "review", "r")).item
    with pytest.raises(SquadsError, match="not a settable field"):
        await svc.update(rev.id, set_attributes={"bogus": "x"})


async def test_set_a_global_field_by_key_hints_at_the_dedicated_flag(svc):
    task = (await create_item(svc, "task", "t")).item
    with pytest.raises(SquadsError, match="use the dedicated --<flag>"):
        await svc.update(task.id, set_attributes={"title": "New title"})


async def test_unset_removes_a_previously_set_generic_attribute(svc):
    rev = (await create_item(svc, "review", "r")).item
    await svc.update(rev.id, set_attributes={"target_ref": "FEAT-2"})
    updated = await svc.update(rev.id, unset_attributes=["target_ref"])
    assert "target_ref" not in updated.attributes


async def test_set_and_unset_a_badge_field_by_key_routes_through_set_badge_value(svc):
    """``severity``/``priority`` are real ``Item`` fields (not attributes), so the
    ``--set``/``--unset`` path for them takes ``Item.set_badge_value``'s ``hasattr`` branch —
    distinct from every other declared field, which stores into ``extra`` instead."""
    bug = (await create_item(svc, "bug", "b")).item
    set_high = await svc.update(bug.id, set_attributes={"severity": "high"})
    assert set_high.severity == "high"

    cleared = await svc.update(bug.id, unset_attributes=["severity"])
    assert cleared.severity is None


async def test_setting_a_role_field_is_refused_and_the_pointer_is_unchanged(svc, project):
    """A role's content is authored in its role document, so a generic ``--set`` on a role is
    refused and the generated pointer keeps the catalog's answer."""
    pointer_path = project.root / ".claude" / "agents" / "manager.md"
    before = pointer_path.read_text(encoding="utf-8")

    with pytest.raises(SquadsError, match="authoring surface"):
        await svc.update("ROLE-000001", set_attributes={"model": "haiku"})

    assert "model" not in (await svc.get("ROLE-000001")).attributes
    assert pointer_path.read_text(encoding="utf-8") == before


async def test_a_role_field_that_moved_to_the_catalog_is_refused_with_where_it_lives_now(svc):
    """A key an operator could once ``--set`` on a role, and that is now resolved from the role
    catalog, is refused with the place it is declared instead — not reported as an unknown
    field with no remedy. Someone reaching for ``--set mission=`` has a real intent."""
    with pytest.raises(SquadsError, match=r"\.overrides/roles\.toml"):
        await svc.update("ROLE-000001", set_attributes={"mission": "a new mission"})

    with pytest.raises(SquadsError, match=r"roles/<slug>\.toml"):
        await svc.update("ROLE-000001", set_attributes={"color": "magenta"})


async def test_a_roles_name_is_refused_with_the_verb_that_actually_sets_it(svc):
    """A role's content verbs are refused with its authoring surface, ``full_name`` included."""
    with pytest.raises(SquadsError, match="authoring surface"):
        await svc.update("ROLE-000001", set_attributes={"full_name": "Someone Else"})


async def test_a_skill_is_not_sent_to_a_role_override_document(svc):
    """The key names are not role-only. A skill's own ``title``/``description``/``model`` must
    never be refused with a remedy that names a *role* override file."""
    skill = await svc.add_skill("Custom Helper")
    with pytest.raises(SquadsError) as exc:
        await svc.update(skill.id, set_attributes={"description": "x"})
    assert ".overrides/roles" not in str(exc.value)
