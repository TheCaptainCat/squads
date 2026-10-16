"""`blocked_has_blocker` at spec load: it takes no parameter, a type whose lifecycle holds no
status of a role declaring `blocked = true` cannot select it, and neither can any type in a spec
that declares no dependency-role ref kind. Each refusal names the type, the entry and the
declaration that is missing, and the check is accepted once the declaration exists.
"""

import pytest

from squads._errors import SquadsError
from squads._workflow import bundled_spec
from squads._workflow._models import ItemSpec, RefKindSpec, RoleSpec, StatusSpec, WorkflowSpec


def _load(
    item_type: str,
    entries: list[str],
    *,
    lifecycle: str | None = None,
    roles: dict[str, RoleSpec] | None = None,
    statuses: dict[str, StatusSpec] | None = None,
    ref_kinds: dict[str, RefKindSpec] | None = None,
) -> WorkflowSpec:
    base = bundled_spec()
    update: dict[str, object] = {"validators": entries}
    if lifecycle is not None:
        update["lifecycle"] = lifecycle
    items: dict[str, ItemSpec] = {
        **base.items,
        item_type: base.items[item_type].model_copy(update=update),
    }
    return WorkflowSpec.model_validate(
        {
            "items": items,
            "statuses": dict(base.statuses) if statuses is None else statuses,
            "lifecycles": dict(base.lifecycles),
            "prefix_to_type": dict(base.prefix_to_type),
            "alias_to_type": dict(base.alias_to_type),
            "collections": dict(base.collections),
            "subentity_kinds": dict(base.subentity_kinds),
            "roles": dict(base.roles) if roles is None else roles,
            "ref_kinds": dict(base.ref_kinds) if ref_kinds is None else ref_kinds,
            "views": dict(base.views),
        }
    )


_BUNDLED_ROLES = bundled_spec().roles
_WITHOUT_DEPENDENCY_KINDS = {
    kind: spec for kind, spec in bundled_spec().ref_kinds.items() if spec.role != "dependency"
}


def test_the_entry_takes_no_parameter() -> None:
    with pytest.raises(SquadsError, match="takes no param"):
        _load("task", ["blocked_has_blocker:blocked"])


@pytest.mark.parametrize(
    ("item_type", "accepted"),
    [
        ("epic", True),
        ("feature", True),
        ("task", True),
        ("bug", True),
        ("review", False),
        ("decision", False),
        ("contract", False),
        ("milestone", False),
        ("guide", False),
    ],
)
def test_a_type_is_accepted_exactly_when_its_lifecycle_holds_a_blocked_status(
    item_type: str, accepted: bool
) -> None:
    if accepted:
        _load(item_type, ["blocked_has_blocker"])
        return
    with pytest.raises(SquadsError) as raised:
        _load(item_type, ["blocked_has_blocker"])
    text = str(raised.value)
    assert f"item {item_type!r}" in text
    assert "'blocked_has_blocker'" in text
    assert "blocked = true" in text


@pytest.mark.parametrize("item_type", ["review", "decision", "contract", "milestone", "guide"])
def test_the_same_type_is_accepted_once_its_lifecycle_has_a_blocked_status(
    item_type: str,
) -> None:
    _load(item_type, ["blocked_has_blocker"], lifecycle="work")


def test_a_squad_whose_roles_flag_none_is_refused_naming_the_flag() -> None:
    unflagged = {
        name: role.model_copy(update={"blocked": False}) for name, role in _BUNDLED_ROLES.items()
    }
    with pytest.raises(SquadsError, match="blocked = true"):
        _load("task", ["blocked_has_blocker"], roles=unflagged)


def test_it_loads_once_a_role_of_the_squads_own_declares_the_flag() -> None:
    unflagged = {
        name: role.model_copy(update={"blocked": False}) for name, role in _BUNDLED_ROLES.items()
    }
    waiting = _BUNDLED_ROLES["blocked"].model_copy(update={"blocked": True})
    statuses = {
        **bundled_spec().statuses,
        "Blocked": bundled_spec().statuses["Blocked"].model_copy(update={"role": "waiting"}),
    }
    spec = _load(
        "task", ["blocked_has_blocker"], roles={**unflagged, "waiting": waiting}, statuses=statuses
    )
    assert spec.role_for("Blocked").blocked is True


@pytest.mark.parametrize("item_type", ["epic", "feature", "task", "bug"])
def test_a_spec_with_no_dependency_ref_kind_refuses_every_selecting_type(item_type: str) -> None:
    with pytest.raises(SquadsError) as raised:
        _load(item_type, ["blocked_has_blocker"], ref_kinds=_WITHOUT_DEPENDENCY_KINDS)
    text = str(raised.value)
    assert f"item {item_type!r}" in text
    assert "'blocked_has_blocker'" in text
    assert 'role = "dependency"' in text


def test_a_spec_with_no_dependency_ref_kind_loads_when_no_type_selects_the_check() -> None:
    _load("task", [], ref_kinds=_WITHOUT_DEPENDENCY_KINDS)
