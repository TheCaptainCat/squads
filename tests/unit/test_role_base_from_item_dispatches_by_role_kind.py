"""``role_base_from_item`` — the one seam every consumer that resolves against a live roster
item builds its ``resolve_role_with_base`` base through, for a bundled role and a developer
role alike. Proven here at the pure-function level, with no service involved.

The item supplies only the facts an operator sets through a dedicated verb (a bundled role's
``is_default``; a developer role's tech/name/model/``is_default``); every other field comes
from the *current* catalog layers. The stored name is pinned on top of the resolved role by
:func:`pinned_name_of`, which the table below crosses with the kinds of role.
"""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from _helpers import catalog_of, dev_role
from squads._models._attributes import AttributeKey as X
from squads._models._item import Item
from squads._roles._catalog import PREDEFINED
from squads._roles._resolver import (
    dev_base_from_item,
    pinned_name_of,
    resolve_role_with_base,
    role_base_from_item,
)

_NOW = datetime(2026, 1, 1, tzinfo=UTC)
_BUNDLED_ARCHITECT = next(r for r in PREDEFINED if r.slug == "architect")


def _item(slug: str, attributes: dict[str, object], title: str | None = None) -> Item:
    return Item(
        sequence_id=1,
        type="role",
        title=title if title is not None else slug,
        slug=slug,
        slug_in_file=True,
        status="Active",
        path=f"roles/ROLE-000001-{slug}.md",
        created_at=_NOW,
        updated_at=_NOW,
        attributes=attributes,
    )


# --------------------------------------------------------------------- bundled role


def test_a_bundled_roles_base_is_the_catalog_entry_whatever_name_the_item_stores() -> None:
    item = _item("architect", {}, title="Ada Lovelace")
    assert role_base_from_item(item, catalog_of(None)) == _BUNDLED_ARCHITECT


def test_every_bundled_field_comes_from_the_current_catalog_not_the_item() -> None:
    """A stale mission/responsibilities/model/colour stored on the item, as one created before a
    catalog text change carries, must not freeze them: only ``is_default`` has a dedicated verb
    that makes the item's stored value the operator's lasting answer."""
    item = _item(
        "architect",
        {
            X.MODEL: "haiku",
            X.IS_DEFAULT: False,
            "mission": "a long-obsolete mission statement",
            "color": "magenta",
        },
    )
    assert role_base_from_item(item, catalog_of(None)) == _BUNDLED_ARCHITECT


def test_a_bundled_roles_is_default_designation_is_carried_from_the_item() -> None:
    base = role_base_from_item(_item("architect", {X.IS_DEFAULT: True}), catalog_of(None))
    assert base is not None
    assert base.is_default is True
    assert _BUNDLED_ARCHITECT.is_default is False  # sanity: the catalog itself says otherwise


def test_a_project_catalog_document_reaches_an_already_activated_bundled_role(
    tmp_path: Path,
) -> None:
    override_dir = tmp_path / ".overrides"
    override_dir.mkdir()
    (override_dir / "roles.toml").write_text(
        '[[roles]]\nslug = "architect"\ntitle = "Chief Architect"\nfull_name = "Rita Catalog"\n',
        encoding="utf-8",
    )
    base = role_base_from_item(_item("architect", {}, title="Ada Lovelace"), catalog_of(tmp_path))

    assert base is not None
    assert base.title == "Chief Architect"
    assert base.full_name == "Rita Catalog"  # the base follows the catalog document
    assert base.mission == _BUNDLED_ARCHITECT.mission


# ------------------------------------------------------- the stored name, crossed with the layers

#: (id, stored title, roles.toml full_name, per-slug full_name, expected name): the stored name
#: wins over every layer; a blank one reads as unset and the layers answer.
NAME_ROWS = [
    ("stored-catalog-only", "Ada Lovelace", None, None, "Ada Lovelace"),
    ("stored-roles-toml", "Ada Lovelace", "Rita Catalog", None, "Ada Lovelace"),
    ("stored-per-slug", "Ada Lovelace", None, "Pat Perslug", "Ada Lovelace"),
    ("stored-both-layers", "Ada Lovelace", "Rita Catalog", "Pat Perslug", "Ada Lovelace"),
    ("blank-catalog-only", "   ", None, None, "Robert Architect"),
    ("blank-roles-toml", "   ", "Rita Catalog", None, "Rita Catalog"),
    ("blank-both-layers", "   ", "Rita Catalog", "Pat Perslug", "Pat Perslug"),
]


@pytest.mark.parametrize(
    ("title", "catalog_name", "slug_name", "expected"),
    [r[1:] for r in NAME_ROWS],
    ids=[r[0] for r in NAME_ROWS],
)
def test_a_bundled_roles_stored_name_wins_over_every_layer(
    tmp_path: Path,
    title: str,
    catalog_name: str | None,
    slug_name: str | None,
    expected: str,
) -> None:
    overrides = tmp_path / ".overrides"
    (overrides / "roles").mkdir(parents=True)
    if catalog_name:
        (overrides / "roles.toml").write_text(
            f'[[roles]]\nslug = "architect"\nfull_name = "{catalog_name}"\n', encoding="utf-8"
        )
    if slug_name:
        (overrides / "roles" / "architect.toml").write_text(
            f'full_name = "{slug_name}"\n', encoding="utf-8"
        )
    item = _item("architect", {}, title=title)

    resolved = resolve_role_with_base(
        "architect",
        tmp_path,
        base=role_base_from_item(item, catalog_of(tmp_path)),
        pinned_name=pinned_name_of(item),
        catalog=catalog_of(tmp_path),
    )

    assert resolved.full_name == expected


# --------------------------------------------------------------------- developer role


def _dev(attributes: dict[str, object], title: str) -> Item:
    return _item("typescript-dev", {X.TECH: "typescript", **attributes}, title)


def test_a_developer_role_delegates_to_dev_base_from_item() -> None:
    role = dev_role("python", name="Elias Python", model="opus")
    item = _item(
        "python-dev",
        {**role.to_attributes(templated=True), X.TECH: "python"},
        title=role.full_name,
    )
    assert role_base_from_item(item, catalog_of(None)) == dev_base_from_item(item, catalog_of(None))


def test_a_developer_roles_name_and_model_come_from_the_item_not_the_pool() -> None:
    base = role_base_from_item(_dev({X.MODEL: "opus"}, "Ada Typescript"), catalog_of(None))
    assert base is not None
    assert base.full_name == "Ada Typescript"
    assert base.model == "opus"
    assert base.full_name != dev_role("typescript").full_name


def test_a_developer_roles_is_default_designation_is_carried_from_the_item() -> None:
    assert (
        dev_base_from_item(
            _dev({X.IS_DEFAULT: True}, "Ada Typescript"), catalog_of(None)
        ).is_default
        is True
    )
    assert dev_base_from_item(_dev({}, "Ada Typescript"), catalog_of(None)).is_default is False


#: (id, per-slug full_name, expected): a developer role keeps its stored name whatever a
#: per-slug file declares.
DEV_NAME_ROWS = [
    ("no-file", None, "Ada Typescript"),
    ("per-slug", "Pat Perslug", "Ada Typescript"),
]


@pytest.mark.parametrize(
    ("slug_name", "expected"),
    [r[1:] for r in DEV_NAME_ROWS],
    ids=[r[0] for r in DEV_NAME_ROWS],
)
def test_a_developer_roles_stored_name_is_never_rerolled(
    tmp_path: Path, slug_name: str | None, expected: str
) -> None:
    (tmp_path / ".overrides" / "roles").mkdir(parents=True)
    if slug_name:
        (tmp_path / ".overrides" / "roles" / "typescript-dev.toml").write_text(
            f'full_name = "{slug_name}"\n', encoding="utf-8"
        )
    item = _dev({}, "Ada Typescript")

    resolved = resolve_role_with_base(
        "typescript-dev",
        tmp_path,
        base=role_base_from_item(item, catalog_of(tmp_path)),
        pinned_name=pinned_name_of(item),
        catalog=catalog_of(tmp_path),
    )

    assert resolved.full_name == expected


# --------------------------------------------------------------------- neither: no catalog, no dev


def test_a_wholly_custom_role_with_no_catalog_entry_and_no_dev_shape_returns_none() -> None:
    assert (
        role_base_from_item(_item("compliance-officer", {}, title="Sam Security"), catalog_of(None))
        is None
    )


def test_a_non_dev_role_whose_slug_merely_ends_in_dev_returns_none_not_a_crash() -> None:
    assert (
        role_base_from_item(_item("data-dev", {}, title="Dana Analyst"), catalog_of(None)) is None
    )


# --------------------------------------------------------------------- pinned_name_of

#: (id, title, expected)
PIN_ROWS = [
    ("stored", "Ada Lovelace", "Ada Lovelace"),
    ("blank", "   ", None),
]


@pytest.mark.parametrize(
    ("title", "expected"), [r[1:] for r in PIN_ROWS], ids=[r[0] for r in PIN_ROWS]
)
def test_a_non_blank_stored_name_is_pinned(title: str, expected: str | None) -> None:
    assert pinned_name_of(_item("architect", {}, title)) == expected


def test_the_bundled_predefined_entry_is_never_mutated_by_building_a_base() -> None:
    original = replace(_BUNDLED_ARCHITECT)
    role_base_from_item(
        _item("architect", {X.IS_DEFAULT: True}, title="Ada Lovelace"), catalog_of(None)
    )
    assert next(r for r in PREDEFINED if r.slug == "architect") == original
