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

from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._roles._catalog import dev_role
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
        status="Active",
        path=f"roles/ROLE-000001-{slug}.md",
        created_at=_NOW,
        updated_at=_NOW,
        extra={
            **role.to_extra(),
            X.IS_DEV: True,
            X.TECH: tech,
        },
    )


def test_the_live_name_is_inherited_not_regenerated_from_the_pool() -> None:
    """Ada Typescript sits at pool index 1 — a second developer, not the first. Re-deriving the
    base from ``dev_role("typescript")`` at the default ``seq=0`` would return ``Elias
    Typescript`` instead; this must not."""
    item = _dev_item("typescript", "Ada Typescript")
    base = dev_base_from_item(item)
    assert base.full_name == "Ada Typescript"
    naive_regeneration = dev_role("typescript")  # seq=0 default — what a widening would call
    assert base.full_name != naive_regeneration.full_name


def test_the_stored_model_is_inherited() -> None:
    item = _dev_item("python", "Elias Python", model="opus")
    assert dev_base_from_item(item).model == "opus"


def test_the_slug_matches_the_stored_tech() -> None:
    item = _dev_item("dotnet", "Whoever Dotnet")
    assert dev_base_from_item(item).slug == "dotnet-dev"


def test_the_is_dev_and_tech_markers_are_not_part_of_the_returned_roledef() -> None:
    """``X.IS_DEV``/``X.TECH`` sit outside ``RoleDef.to_extra()`` by design, so a merge onto the
    item using this base's ``to_extra()`` output can never erase the markers this very function
    reads."""
    item = _dev_item("go", "Whoever Go")
    extra = dev_base_from_item(item).to_extra()
    assert X.IS_DEV not in extra
    assert X.TECH not in extra
