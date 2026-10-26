"""A role item's definition is a projection of exactly one base, chosen from its stored facts in
the order ``template``, ``mission``, catalog; the per-slug file merges over the base; the item's
stored name, default designation and model win over every layer.

The catalog is never consulted to decide the kind, so a catalog entry that appears later cannot
swap a live role's definition. A base that does not resolve leaves the role to materialise from
what the item stores.
"""

from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from _helpers import catalog_of
from squads._models._attributes import AttributeKey as X
from squads._models._item import Item
from squads._roles._catalog import PREDEFINED
from squads._roles._resolver import (
    materialised_base,
    resolve_role_for_item,
    resolve_role_with_base,
    role_base_from_item,
    stored_values,
)

_NOW = datetime(2026, 1, 1, tzinfo=UTC)
_ARCHITECT = next(r for r in PREDEFINED if r.slug == "architect")


def _item(
    slug: str, attributes: Mapping[str, object], title: str | None = None, description: str = ""
) -> Item:
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
        attributes=dict(attributes),
        description=description,
    )


def _write(squad_dir: Path, relative: str, body: str) -> None:
    target = squad_dir / ".overrides" / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")


_DEFINITION = {X.JOB_TITLE: "SRE", X.MISSION: "Keep it up."}

#: (id, slug, stored attributes, description, resolved job title, resolved mission)
KIND_ROWS = [
    ("catalog", "architect", {}, "", _ARCHITECT.title, _ARCHITECT.mission),
    (
        "template",
        "rust-dev",
        {X.TEMPLATE: "dev", X.TECH: "rust"},
        "",
        "Rust developer",
        "Implement assigned tasks in Rust, following the project's guides, with tests.",
    ),
    ("item-defined", "sre", _DEFINITION, "Pager duty.", "SRE", "Keep it up."),
    (
        "item-defined-under-a-catalog-slug",
        "architect",
        _DEFINITION,
        "Mine.",
        "SRE",
        "Keep it up.",
    ),
]


@pytest.mark.parametrize(
    ("slug", "attributes", "description", "title", "mission"),
    [r[1:] for r in KIND_ROWS],
    ids=[r[0] for r in KIND_ROWS],
)
def test_each_kind_resolves_its_definition_from_its_own_base(
    slug: str, attributes: dict[str, object], description: str, title: str, mission: str
) -> None:
    item = _item(slug, attributes, description=description)

    role = resolve_role_for_item(item, None, catalog=catalog_of(None))

    assert (role.title, role.mission) == (title, mission)


def test_the_kind_is_stored_not_looked_up(tmp_path: Path) -> None:
    """An item-defined ``sre``, then a catalog entry ``sre`` with another mission: the item keeps
    its own mission."""
    item = _item("sre", _DEFINITION, description="Pager duty.")
    _write(
        tmp_path,
        "roles.toml",
        '[[roles]]\nslug = "sre"\nfull_name = "Catalog Sre"\ntitle = "t"\ndescription = "d"\n'
        'mission = "The catalog mission."\n\n[bundles]\n'
        'all = ["manager", "architect", "tech-lead", "reviewer", "qa", "devops", '
        '"product-owner", "tech-writer", "sre"]\n',
    )

    role = resolve_role_for_item(item, tmp_path, catalog=catalog_of(tmp_path))

    assert role.mission == "Keep it up."
    assert role.full_name == "sre"


def test_a_stored_template_wins_over_a_catalog_entry_of_the_same_slug(tmp_path: Path) -> None:
    item = _item("architect", {X.TEMPLATE: "dev", X.TECH: "go"})

    role = role_base_from_item(item, catalog_of(None))

    assert role is not None
    assert role.title == "Go developer"


#: (id, stored attributes, the base resolves)
UNRESOLVED_ROWS = [
    ("catalog-slug-the-catalog-lacks", {}, False),
    ("template-the-catalog-lacks", {X.TEMPLATE: "auditor"}, False),
    ("template-the-catalog-declares", {X.TEMPLATE: "dev", X.TECH: "go"}, True),
]


@pytest.mark.parametrize(
    ("attributes", "resolves"),
    [r[1:] for r in UNRESOLVED_ROWS],
    ids=[r[0] for r in UNRESOLVED_ROWS],
)
def test_a_base_that_does_not_resolve_materialises_from_what_the_item_stores(
    attributes: dict[str, object], resolves: bool
) -> None:
    item = _item("guardian", attributes, title="Gwen Guardian", description="Guards the gate.")

    assert (role_base_from_item(item, catalog_of(None)) is not None) is resolves
    role = resolve_role_for_item(item, None, catalog=catalog_of(None))

    assert role.full_name == "Gwen Guardian"
    if not resolves:
        assert (role.title, role.mission) == ("Gwen Guardian", "Guards the gate.")


#: (id, stored attributes, per-slug file body, expected is_default, expected model)
STORED_ROWS = [
    ("none-stored", {}, 'model = "haiku"\n', False, "haiku"),
    ("model-wins-over-the-file", {X.MODEL: "opus"}, 'model = "haiku"\n', False, "opus"),
    ("default-wins-over-the-file", {X.IS_DEFAULT: True}, "is_default = false\n", True, "opus"),
    ("default-cleared-wins-over-the-catalog", {X.IS_DEFAULT: False}, "", False, "opus"),
]


@pytest.mark.parametrize("kind", ["catalog", "template", "item-defined"])
@pytest.mark.parametrize(
    ("attributes", "file_body", "default", "model"),
    [r[1:] for r in STORED_ROWS],
    ids=[r[0] for r in STORED_ROWS],
)
def test_stored_per_role_values_win_over_every_layer_for_every_kind(
    tmp_path: Path,
    kind: str,
    attributes: dict[str, object],
    file_body: str,
    default: bool,
    model: str,
) -> None:
    slug, base = {
        "catalog": ("manager", {}),
        "template": ("rust-dev", {X.TEMPLATE: "dev", X.TECH: "rust"}),
        "item-defined": ("sre", dict(_DEFINITION)),
    }[kind]
    _write(tmp_path, f"roles/{slug}.toml", file_body)
    item = _item(slug, {**base, **attributes}, description="d")

    role = resolve_role_for_item(item, tmp_path, catalog=catalog_of(tmp_path))

    expected_default = default or (kind == "catalog" and X.IS_DEFAULT not in attributes)
    assert role.is_default is expected_default
    if X.MODEL in attributes or "model" in file_body:
        assert role.model == (attributes.get(X.MODEL) or "haiku")


def test_the_stored_name_wins_over_the_file_and_the_catalog(tmp_path: Path) -> None:
    _write(tmp_path, "roles.toml", '[[roles]]\nslug = "architect"\nfull_name = "Rita Catalog"\n')
    _write(tmp_path, "roles/architect.toml", 'full_name = "Pat Perslug"\n')
    item = _item("architect", {}, title="Ada Lovelace")

    role = resolve_role_for_item(item, tmp_path, catalog=catalog_of(tmp_path))

    assert role.full_name == "Ada Lovelace"


def test_a_blank_stored_name_reads_as_unset() -> None:
    item = _item("architect", {}, title="Ada Lovelace")
    object.__setattr__(item, "title", "   ")

    values = stored_values(item)

    assert values is not None
    assert values.name is None
    assert materialised_base(item, catalog_of(None)).full_name == _ARCHITECT.full_name


def test_a_per_slug_file_alone_is_no_base(tmp_path: Path) -> None:
    from squads._errors import RoleNotFoundError

    _write(tmp_path, "roles/sre.toml", 'full_name = "Sam"\n')

    with pytest.raises(RoleNotFoundError):
        resolve_role_with_base("sre", tmp_path, base=None, catalog=catalog_of(tmp_path))


def test_building_a_base_never_mutates_the_bundled_entry() -> None:
    original = replace(_ARCHITECT)

    role_base_from_item(_item("architect", {X.IS_DEFAULT: True}, title="Ada"), catalog_of(None))

    assert next(r for r in PREDEFINED if r.slug == "architect") == original
