"""``resolve_role_with_base`` — the sibling to ``resolve_role`` that lets a caller supply the
merge base for a slug outside ``PREDEFINED``, instead of leaving new-slug validation to demand
every required field.

``resolve_role`` itself is untouched (still proven at tests/unit/test_role_override_field_
merge.py); this file covers the new seam: ``base=None`` reproduces ``resolve_role`` exactly
(falling back to a bundled slug's own catalog entry when there is nothing else), a *supplied*
base wins over that catalog entry regardless of whether the slug is in ``PREDEFINED`` (a
caller that already knows a role's live identity must be able to make it the merge base for a
bundled role too, not only for a developer slug), and a supplied base merges field-wise
exactly like the bundled-slug case does. ``dev_base_for_slug`` — the builder for a
``<tech>-dev.toml`` with no matching roster entry — is covered here too, since it needs no live
item. The item-backed builder, ``dev_base_from_item``, is covered separately (tests/unit/
test_dev_base_from_item_inherits_the_live_identity.py) because it needs an ``Item`` to read
from; ``role_base_from_item`` (the seam that dispatches between a developer's
``dev_base_from_item`` and a bundled role's item-carried ``full_name``) is covered at
tests/unit/test_role_base_from_item_dispatches_by_role_kind.py.
"""

from pathlib import Path

import pytest

from squads._errors import RoleNotFoundError, SquadsError
from squads._roles._catalog import PREDEFINED, dev_role
from squads._roles._resolver import dev_base_for_slug, resolve_role, resolve_role_with_base


def _place_role_toml(squad_dir: Path, slug: str, content: str) -> Path:
    target = squad_dir / ".overrides" / "roles" / f"{slug}.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


# --------------------------------------------------------------------- base=None parity


def test_base_none_reproduces_resolve_role_for_a_bundled_slug(tmp_path) -> None:
    _place_role_toml(tmp_path, "architect", 'model = "haiku"\n')
    assert resolve_role_with_base("architect", tmp_path, base=None) == resolve_role(
        "architect", tmp_path
    )


def test_base_none_reproduces_resolve_roles_missing_fields_error_for_a_new_slug(tmp_path) -> None:
    _place_role_toml(tmp_path, "new-role", 'full_name = "New Person"\n')
    with pytest.raises(SquadsError, match="missing required fields") as via_base:
        resolve_role_with_base("new-role", tmp_path, base=None)
    with pytest.raises(SquadsError, match="missing required fields") as via_plain:
        resolve_role("new-role", tmp_path)
    assert str(via_base.value) == str(via_plain.value)


def test_base_none_reproduces_role_not_found_for_an_unknown_slug_with_no_override(tmp_path) -> None:
    with pytest.raises(RoleNotFoundError):
        resolve_role_with_base("nonexistent-slug", tmp_path, base=None)


# --------------------------------------------------------------------- a supplied base wins,
# even for a bundled slug


def test_a_supplied_base_wins_over_a_bundled_slugs_own_catalog_entry(tmp_path) -> None:
    """The discard this used to assert was the defect: a caller that supplies a base for a
    bundled slug — the seam an already-live item's own operator-set name goes through — must
    have that base reach the merge, not have it silently replaced by the catalog default."""
    from dataclasses import replace

    bundled = next(x for x in PREDEFINED if x.slug == "architect")
    renamed_base = replace(bundled, full_name="Ada Lovelace")
    r = resolve_role_with_base("architect", tmp_path, base=renamed_base)
    assert r.full_name == "Ada Lovelace"
    assert r.mission == bundled.mission  # every other field still the catalog's own


def test_base_none_still_falls_back_to_the_bundled_catalog_entry(tmp_path) -> None:
    r = resolve_role_with_base("architect", tmp_path, base=None)
    bundled = next(x for x in PREDEFINED if x.slug == "architect")
    assert r == bundled


# --------------------------------------------------------------------- dev_base_for_slug


def test_dev_base_for_slug_matches_the_generated_pool_role(tmp_path) -> None:
    assert dev_base_for_slug("python-dev") == dev_role("python")


def test_dev_base_for_slug_strips_only_the_dev_suffix() -> None:
    assert dev_base_for_slug("dotnet-dev").slug == "dotnet-dev"
    assert dev_base_for_slug("dotnet-dev").full_name.endswith("Dotnet")


# --------------------------------------------------------------------- supplied base + override


def test_no_override_file_returns_the_supplied_base_unchanged(tmp_path) -> None:
    base = dev_base_for_slug("python-dev")
    assert resolve_role_with_base("python-dev", tmp_path, base=base) == base


def test_a_partial_override_merges_field_wise_over_the_supplied_base(tmp_path) -> None:
    base = dev_base_for_slug("python-dev")
    _place_role_toml(tmp_path, "python-dev", 'title = "Senior Python developer"\n')
    r = resolve_role_with_base("python-dev", tmp_path, base=base)
    assert r.title == "Senior Python developer"
    assert r.full_name == base.full_name  # inherited, not disturbed
    assert r.mission == base.mission
    assert r.model == base.model


def test_a_complete_override_sets_every_field_it_declares(tmp_path) -> None:
    base = dev_base_for_slug("python-dev")
    _place_role_toml(
        tmp_path,
        "python-dev",
        'full_name = "Priya Python"\ntitle = "Staff Python developer"\n'
        'description = "Owns the Python surface."\n'
        'mission = "Ship and maintain the Python codebase."\n'
        'model = "opus"\n',
    )
    r = resolve_role_with_base("python-dev", tmp_path, base=base)
    assert r.full_name == "Priya Python"
    assert r.title == "Staff Python developer"
    assert r.mission == "Ship and maintain the Python codebase."
    assert r.model == "opus"


def test_an_invalid_model_still_refuses_with_a_supplied_base(tmp_path) -> None:
    base = dev_base_for_slug("python-dev")
    _place_role_toml(tmp_path, "python-dev", 'model = "opuss"\n')
    with pytest.raises(SquadsError, match="opuss"):
        resolve_role_with_base("python-dev", tmp_path, base=base)


def test_a_slug_disagreeing_with_the_filename_still_refuses_with_a_supplied_base(tmp_path) -> None:
    base = dev_base_for_slug("python-dev")
    _place_role_toml(tmp_path, "python-dev", 'slug = "other-dev"\ntitle = "x"\n')
    with pytest.raises(SquadsError, match="filename"):
        resolve_role_with_base("python-dev", tmp_path, base=base)
