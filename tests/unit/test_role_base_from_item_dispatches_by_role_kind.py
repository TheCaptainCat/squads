"""``role_base_from_item`` — the one seam every consumer that resolves against a live roster
item builds its ``resolve_role_with_base`` base through, for a bundled role and a developer
role alike. Proven here at the pure-function level, with no service involved.

The property that matters: the item is authoritative for exactly the fields an operator can
set on it (a bundled role's ``full_name`` alone; a developer role's tech/full_name/model) and
for no others — every other field still comes from the *current* catalog, not whatever the item
happened to carry, so a ``RoleDef`` field added after the item was created still reaches it.
"""

from dataclasses import replace
from datetime import UTC, datetime

from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._roles._catalog import PREDEFINED, dev_role
from squads._roles._resolver import dev_base_from_item, role_base_from_item

_NOW = datetime(2026, 1, 1, tzinfo=UTC)
_BUNDLED_ARCHITECT = next(r for r in PREDEFINED if r.slug == "architect")


def _item(slug: str, extra: dict[str, object]) -> Item:
    return Item(
        sequence_id=1,
        type="role",
        title=str(extra.get(X.FULL_NAME, slug)),
        slug=slug,
        status="Active",
        path=f"roles/ROLE-000001-{slug}.md",
        created_at=_NOW,
        updated_at=_NOW,
        extra=extra,
    )


# --------------------------------------------------------------------- bundled role


def test_a_bundled_roles_full_name_is_taken_from_the_item() -> None:
    item = _item("architect", {X.SLUG: "architect", X.FULL_NAME: "Ada Lovelace"})
    base = role_base_from_item(item)
    assert base is not None
    assert base.full_name == "Ada Lovelace"


def test_every_other_bundled_field_still_comes_from_the_current_catalog_not_the_item() -> None:
    """An item carrying a stale mission/responsibilities (as one created before a catalog text
    change would) must not freeze them — only ``full_name`` is the item's to keep."""
    item = _item(
        "architect",
        {
            X.SLUG: "architect",
            X.FULL_NAME: "Ada Lovelace",
            X.MISSION: "a long-obsolete mission statement",
            X.RESPONSIBILITIES: ["an obsolete responsibility"],
            X.CAN_SPAWN: not _BUNDLED_ARCHITECT.can_spawn,
        },
    )
    base = role_base_from_item(item)
    assert base is not None
    assert base.full_name == "Ada Lovelace"
    assert base.mission == _BUNDLED_ARCHITECT.mission
    assert base.responsibilities == _BUNDLED_ARCHITECT.responsibilities
    assert base.can_spawn == _BUNDLED_ARCHITECT.can_spawn


def test_a_bundled_role_with_no_stored_full_name_falls_back_to_the_catalog_default() -> None:
    item = _item("architect", {X.SLUG: "architect"})
    base = role_base_from_item(item)
    assert base == _BUNDLED_ARCHITECT


def test_a_bundled_role_whose_stored_name_already_matches_returns_the_catalog_entry_as_is() -> None:
    item = _item("architect", {X.SLUG: "architect", X.FULL_NAME: _BUNDLED_ARCHITECT.full_name})
    assert role_base_from_item(item) == _BUNDLED_ARCHITECT


# --------------------------------------------------------------------- developer role


def test_a_developer_role_delegates_to_dev_base_from_item() -> None:
    role = dev_role("python", name="Elias Python", model="opus")
    item = _item("python-dev", {**role.to_extra(), X.IS_DEV: True, X.TECH: "python"})
    assert role_base_from_item(item) == dev_base_from_item(item)


def test_a_developer_roles_full_name_and_model_come_from_the_item_not_the_pool() -> None:
    role = dev_role("typescript", name="Ada Typescript", model="opus")
    item = _item("typescript-dev", {**role.to_extra(), X.IS_DEV: True, X.TECH: "typescript"})
    base = role_base_from_item(item)
    assert base is not None
    assert base.full_name == "Ada Typescript"
    assert base.model == "opus"
    naive_regeneration = dev_role("typescript")  # seq=0 default — what a widening would call
    assert base.full_name != naive_regeneration.full_name


# --------------------------------------------------------------------- neither: no catalog, no dev


def test_a_wholly_custom_role_with_no_catalog_entry_and_no_dev_shape_returns_none() -> None:
    """No catalog to draw the non-operator-settable fields from -- the orphaned-custom-role
    item that ``_refresh_catalog_extra`` already skips via ``RoleNotFoundError``, unaffected by
    this returning ``None`` for it."""
    item = _item("compliance-officer", {X.SLUG: "compliance-officer", X.FULL_NAME: "Sam Security"})
    assert role_base_from_item(item) is None


def test_a_non_dev_role_whose_slug_merely_ends_in_dev_returns_none_not_a_crash() -> None:
    """A slug shaped like a dev slug but not one (no ``extra.is_dev``, no ``extra.tech``) must
    not attempt ``dev_base_from_item`` and KeyError on the missing ``tech`` key."""
    item = _item("data-dev", {X.SLUG: "data-dev", X.FULL_NAME: "Dana Analyst"})
    assert X.TECH not in item.extra
    assert role_base_from_item(item) is None


# --------------------------------------------------------------------- immutability of the input

_ORIGINAL_ARCHITECT = replace(_BUNDLED_ARCHITECT)


def test_the_bundled_predefined_entry_is_never_mutated_by_building_a_base() -> None:
    item = _item("architect", {X.SLUG: "architect", X.FULL_NAME: "Ada Lovelace"})
    role_base_from_item(item)
    still_bundled = next(r for r in PREDEFINED if r.slug == "architect")
    assert still_bundled == _ORIGINAL_ARCHITECT
