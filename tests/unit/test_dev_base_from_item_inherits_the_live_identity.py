"""``dev_base_from_item`` — the dev-role merge base for a developer role that already exists on
the roster. It reads the item's own stored tech/full_name/model, so ``dev_role()`` *inherits*
the live name instead of re-rolling one from the pool.

This is the risk the whole design exists to avoid: a squad's second developer for a given tech
sits at a non-zero pool position (e.g. ``Ada Typescript`` at index 1), and re-deriving the base
from the slug alone — ``dev_role(tech)`` at the default ``seq=0`` — silently renames her to
``Elias Typescript``. Proven here at the pure-function level with no service involved; the same
property end-to-end through ``sq sync`` is tests/service/test_partial_dev_role_override_is_
honoured_by_sync.py.
"""

from datetime import UTC, datetime

from _helpers import catalog_of, dev_role
from squads._models._attributes import AttributeKey as X
from squads._models._item import Item
from squads._roles._resolver import dev_base_from_item

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _dev_item(tech: str, full_name: str, *, model: str | None = "sonnet") -> Item:
    """A minimal ``Item`` shaped like one ``add_dev`` would have created — enough for
    ``dev_base_from_item`` to read from, without going through the service."""
    role = dev_role(tech, name=full_name, model=model)
    slug = role.slug
    return Item(
        sequence_id=1,
        type="role",
        title=full_name,
        slug=slug,
        slug_in_file=True,
        status="Active",
        path=f"roles/ROLE-000001-{slug}.md",
        created_at=_NOW,
        updated_at=_NOW,
        attributes={
            **role.to_attributes(templated=True),
            X.TECH: tech,
        },
    )


def test_the_live_name_is_inherited_not_regenerated_from_the_pool() -> None:
    """Ada Typescript sits at pool index 1 — a second developer, not the first. Re-deriving the
    base from ``dev_role("typescript")`` at the default ``seq=0`` would return ``Elias
    Typescript`` instead; this must not."""
    item = _dev_item("typescript", "Ada Typescript")
    base = dev_base_from_item(item, catalog_of(None))
    assert base.full_name == "Ada Typescript"
    naive_regeneration = dev_role("typescript")  # seq=0 default — what a widening would call
    assert base.full_name != naive_regeneration.full_name


def test_the_stored_model_is_inherited() -> None:
    item = _dev_item("python", "Elias Python", model="opus")
    assert dev_base_from_item(item, catalog_of(None)).model == "opus"


def test_the_slug_matches_the_stored_tech() -> None:
    item = _dev_item("dotnet", "Whoever Dotnet")
    assert dev_base_from_item(item, catalog_of(None)).slug == "dotnet-dev"


def test_the_tech_marker_is_not_part_of_the_returned_roledef() -> None:
    """``X.TECH`` sits outside ``RoleDef.to_attributes()`` by design, so a merge onto
    the item using this base's ``to_attributes()`` output can never erase the markers this very
    function reads."""
    item = _dev_item("go", "Whoever Go")
    extra = dev_base_from_item(item, catalog_of(None)).to_attributes()
    assert X.TECH not in extra


def test_the_name_comes_from_item_title() -> None:
    item = _dev_item("python", "Elias Python")
    assert "full_name" not in item.attributes  # nothing stores a second copy of the name
    assert dev_base_from_item(item, catalog_of(None)).full_name == "Elias Python"


def test_the_is_default_designation_is_carried_from_the_item() -> None:
    item = _dev_item("python", "Elias Python")
    item.attributes[X.IS_DEFAULT] = True
    assert dev_base_from_item(item, catalog_of(None)).is_default is True


def test_with_no_stored_is_default_it_falls_back_to_false() -> None:
    """``is_default`` is written only by ``sq role set-default``, so a developer role created
    and never designated carries no key at all — the shape ``_dev_item`` produces."""
    item = _dev_item("python", "Elias Python")
    assert X.IS_DEFAULT not in item.attributes
    assert dev_base_from_item(item, catalog_of(None)).is_default is False
