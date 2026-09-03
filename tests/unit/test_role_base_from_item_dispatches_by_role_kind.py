"""``role_base_from_item`` — the one seam every consumer that resolves against a live roster
item builds its ``resolve_role_with_base`` base through, for a bundled role and a developer
role alike. Proven here at the pure-function level, with no service involved.

The property that matters: the item is authoritative for exactly the fields an operator can
set on it (a bundled role's ``full_name``/``is_default``; a developer role's
tech/full_name/model/``is_default``) and for no others — every other field still comes from the
*current* catalog, not whatever the item happened to carry, so a ``RoleDef`` field added after
the item was created still reaches it.

``full_name`` is read from ``item.title`` — the uniform record's own copy of the resolved
name — never from ``extra.full_name``, so a caller resolves correctly whether or not the
``extra`` mirror carries the key at all. ``is_default`` has no such uniform-record home and is
read from ``extra.is_default``, the one value in this operator-settable set that still depends
on the mirror.
"""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._roles._catalog import PREDEFINED, dev_role
from squads._roles._resolver import dev_base_from_item, role_base_from_item

_NOW = datetime(2026, 1, 1, tzinfo=UTC)
_BUNDLED_ARCHITECT = next(r for r in PREDEFINED if r.slug == "architect")


def _item(slug: str, extra: dict[str, object], title: str | None = None) -> Item:
    return Item(
        sequence_id=1,
        type="role",
        title=title if title is not None else str(extra.get(X.FULL_NAME, slug)),
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
    """An item carrying a stale mission/responsibilities/model/color (as one created before a
    catalog text change would, or one a generic ``sq role update --set`` touched) must not
    freeze them — only ``full_name`` and ``is_default`` have a dedicated verb that makes the
    item's own stored value the operator's lasting answer; every other field is reachable only
    through the generic ``--set`` escape hatch, which the reconciler already treats as
    staleness to converge on the next sync rather than a designation to preserve, and this
    base must not fight that by freezing one of them here first."""
    item = _item(
        "architect",
        {
            X.SLUG: "architect",
            X.FULL_NAME: "Ada Lovelace",
            X.MISSION: "a long-obsolete mission statement",
            X.RESPONSIBILITIES: ["an obsolete responsibility"],
            X.MODEL: "haiku",
            X.COLOR: "magenta",
            X.CAN_SPAWN: not _BUNDLED_ARCHITECT.can_spawn,
            X.AGREEMENTS: ["a stray stored agreement"],
        },
    )
    base = role_base_from_item(item)
    assert base is not None
    assert base.full_name == "Ada Lovelace"
    assert base.mission == _BUNDLED_ARCHITECT.mission
    assert base.responsibilities == _BUNDLED_ARCHITECT.responsibilities
    assert base.model == _BUNDLED_ARCHITECT.model
    assert base.color == _BUNDLED_ARCHITECT.color
    assert base.can_spawn == _BUNDLED_ARCHITECT.can_spawn
    assert base.agreements == _BUNDLED_ARCHITECT.agreements


def test_a_bundled_role_with_no_stored_full_name_falls_back_to_the_catalog_default() -> None:
    item = _item("architect", {X.SLUG: "architect"}, title="   ")
    base = role_base_from_item(item)
    assert base == _BUNDLED_ARCHITECT


def test_a_bundled_role_whose_stored_name_already_matches_returns_the_catalog_entry_as_is() -> None:
    item = _item("architect", {X.SLUG: "architect", X.FULL_NAME: _BUNDLED_ARCHITECT.full_name})
    assert role_base_from_item(item) == _BUNDLED_ARCHITECT


# --------------------------------------------------- the name source is item.title, not extra


def test_a_bundled_roles_full_name_comes_from_item_title_not_extra_full_name() -> None:
    """The mirror and the uniform record are made to disagree on purpose — proves the read
    goes through ``item.title``, not ``extra.full_name``, which the item building helper keeps
    in step by default everywhere else in this module."""
    item = _item(
        "architect",
        {X.SLUG: "architect", X.FULL_NAME: "a stale mirrored name"},
        title="Ada Lovelace",
    )
    base = role_base_from_item(item)
    assert base is not None
    assert base.full_name == "Ada Lovelace"


def test_a_bundled_role_with_no_extra_full_name_at_all_resolves_from_item_title() -> None:
    """The item is the sole source now, so a role item whose ``extra`` mirror never carried
    ``full_name`` (or has lost it) still resolves correctly rather than falling back to the
    catalog default."""
    item = _item("architect", {X.SLUG: "architect"}, title="Ada Lovelace")
    assert X.FULL_NAME not in item.extra
    base = role_base_from_item(item)
    assert base is not None
    assert base.full_name == "Ada Lovelace"


def test_a_blank_item_title_still_falls_back_to_the_catalog_default() -> None:
    """The read-boundary tolerance moves with the source: a blank/whitespace-only title is
    treated exactly like an absent one used to be, never handed to ``RoleDef`` to refuse."""
    item = _item("architect", {X.SLUG: "architect"}, title="   ")
    assert role_base_from_item(item) == _BUNDLED_ARCHITECT


# ----------------------------------------------- is_default joins the operator-settable set


def test_a_bundled_roles_is_default_designation_is_carried_from_the_item() -> None:
    """The fix for the revert: the operator's ``sq role set-default`` designation is the base's
    now, not the catalog's stale answer."""
    item = _item("architect", {X.SLUG: "architect", X.IS_DEFAULT: True})
    base = role_base_from_item(item)
    assert base is not None
    assert base.is_default is True
    assert _BUNDLED_ARCHITECT.is_default is False  # sanity: the catalog itself says otherwise


def test_a_bundled_role_with_no_stored_is_default_falls_back_to_the_catalog_default() -> None:
    item = _item("architect", {X.SLUG: "architect"}, title=_BUNDLED_ARCHITECT.full_name)
    assert X.IS_DEFAULT not in item.extra
    base = role_base_from_item(item)
    assert base == _BUNDLED_ARCHITECT


# ------------------------------------------------- squad_dir: the catalog-document layer


def test_with_no_squad_dir_the_bundled_catalog_alone_is_unchanged() -> None:
    """The default (``squad_dir=None``) is byte-identical to today's behaviour — an existing
    caller that has not been updated to pass a squad_dir keeps its current answer."""
    item = _item("architect", {X.SLUG: "architect"}, title="   ")
    assert role_base_from_item(item) == _BUNDLED_ARCHITECT
    assert role_base_from_item(item, None) == _BUNDLED_ARCHITECT


def test_a_project_catalog_document_reaches_an_already_activated_bundled_role(
    tmp_path: Path,
) -> None:
    """A catalog-document field override must reach ``role_base_from_item`` (the activated-item
    path) exactly as it reaches ``resolve_role`` (the not-yet-activated path): the base built
    here must resolve through the catalog, not read the bundled tuple directly."""
    override_dir = tmp_path / ".overrides"
    override_dir.mkdir()
    (override_dir / "roles.toml").write_text(
        '[[roles]]\nslug = "architect"\ntitle = "Chief Architect"\n', encoding="utf-8"
    )
    item = _item("architect", {X.SLUG: "architect", X.FULL_NAME: "Ada Lovelace"})

    base = role_base_from_item(item, tmp_path)

    assert base is not None
    assert base.title == "Chief Architect"  # the document's value, not the bundled one
    assert base.full_name == "Ada Lovelace"  # the item's own operator-settable field, untouched
    assert base.mission == _BUNDLED_ARCHITECT.mission  # untouched field still falls through


def test_a_squad_with_no_catalog_document_resolves_exactly_as_before(tmp_path: Path) -> None:
    item = _item("architect", {X.SLUG: "architect"}, title="   ")
    assert role_base_from_item(item, tmp_path) == _BUNDLED_ARCHITECT


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


def test_a_developer_roles_full_name_comes_from_item_title_not_extra_full_name() -> None:
    role = dev_role("typescript", name="a stale mirrored name", model="opus")
    item = _item(
        "typescript-dev",
        {**role.to_extra(), X.IS_DEV: True, X.TECH: "typescript"},
        title="Ada Typescript",
    )
    base = role_base_from_item(item)
    assert base is not None
    assert base.full_name == "Ada Typescript"


def test_a_developer_role_with_no_extra_full_name_at_all_resolves_from_item_title() -> None:
    """The bare-subscript read this used to be would raise ``KeyError`` here; reading
    ``item.title`` instead makes this the cheap, non-raising path it always should have been."""
    role = dev_role("typescript", model="opus")
    extra: dict[str, object] = {**role.to_extra(), X.IS_DEV: True, X.TECH: "typescript"}
    del extra[X.FULL_NAME]
    item = _item("typescript-dev", extra, title="Ada Typescript")
    assert X.FULL_NAME not in item.extra
    base = role_base_from_item(item)
    assert base is not None
    assert base.full_name == "Ada Typescript"


def test_a_developer_roles_is_default_designation_is_carried_from_the_item() -> None:
    role = dev_role("typescript", name="Ada Typescript", model="opus")
    item = _item(
        "typescript-dev",
        {**role.to_extra(), X.IS_DEV: True, X.TECH: "typescript", X.IS_DEFAULT: True},
    )
    base = role_base_from_item(item)
    assert base is not None
    assert base.is_default is True


def test_a_developer_role_with_no_stored_is_default_falls_back_to_false() -> None:
    role = dev_role("typescript", name="Ada Typescript", model="opus")
    item = _item("typescript-dev", {**role.to_extra(), X.IS_DEV: True, X.TECH: "typescript"})
    base = role_base_from_item(item)
    assert base is not None
    assert base.is_default is False


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
