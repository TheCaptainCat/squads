"""``resolve_role`` — the role-override merge for a bundled slug: only the fields a project
TOML actually sets change, everything else falls through to the bundled default; tuple-valued
fields (responsibilities/agreements) merge correctly; the ``slug`` key inside the TOML is
ignored (identity comes from the filename-derived registry entry, not the file content);
unknown keys are silently dropped (forward-compatible); a brand-new (non-bundled) slug can be
defined entirely by its own TOML; a new slug missing a required field raises; malformed TOML
raises; an unknown slug with no override raises; and ``squad_dir=None`` returns the bundled
entry unchanged.

Note: this is deliberately more permissive than the workflow-spec loader (which fails closed
on an unrecognized TOML key, tests/unit/test_workflow_capability_flags.py) — a design
asymmetry between "role override" and "workflow override", not asserted either way here.
"""

from pathlib import Path

import pytest

from squads._errors import RoleNotFoundError, SquadsError
from squads._roles._catalog import PREDEFINED
from squads._roles._resolver import resolve_role


def _place_role_toml(squad_dir: Path, slug: str, content: str) -> Path:
    target = squad_dir / ".overrides" / "roles" / f"{slug}.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def test_no_override_returns_the_bundled_entry_unchanged(tmp_path) -> None:
    bundled = next(x for x in PREDEFINED if x.slug == "architect")
    assert resolve_role("architect", tmp_path) == bundled


def test_squad_dir_none_returns_the_bundled_entry() -> None:
    bundled = next(x for x in PREDEFINED if x.slug == "manager")
    assert resolve_role("manager", None) == bundled


def test_an_unknown_slug_with_no_override_raises(tmp_path) -> None:
    with pytest.raises(RoleNotFoundError):
        resolve_role("nonexistent-slug", tmp_path)


def test_only_the_fields_actually_set_change_the_rest_fall_through_to_bundled(tmp_path) -> None:
    _place_role_toml(tmp_path, "architect", 'full_name = "Ada Lovelace"\nmodel = "haiku"\n')
    r = resolve_role("architect", tmp_path)
    assert r.full_name == "Ada Lovelace"
    assert r.model == "haiku"
    bundled = next(x for x in PREDEFINED if x.slug == "architect")
    assert r.mission == bundled.mission
    assert r.responsibilities == bundled.responsibilities
    assert r.agreements == bundled.agreements
    assert r.color == bundled.color


def test_tuple_valued_fields_override_correctly(tmp_path) -> None:
    _place_role_toml(
        tmp_path, "qa", 'responsibilities = ["Write acceptance tests", "Verify bug fixes"]\n'
    )
    r = resolve_role("qa", tmp_path)
    assert r.responsibilities == ("Write acceptance tests", "Verify bug fixes")


def test_a_slug_key_inside_the_toml_is_silently_ignored(tmp_path) -> None:
    _place_role_toml(tmp_path, "reviewer", 'slug = "something-else"\nfull_name = "Helen"\n')
    r = resolve_role("reviewer", tmp_path)
    assert r.slug == "reviewer"  # filename-derived registry slug wins
    assert r.full_name == "Helen"


def test_unknown_keys_in_the_toml_are_silently_dropped(tmp_path) -> None:
    _place_role_toml(tmp_path, "devops", 'full_name = "Hugo Custom"\nfuture_key = "ignored"\n')
    r = resolve_role("devops", tmp_path)
    assert r.full_name == "Hugo Custom"


def test_a_brand_new_slug_can_be_defined_entirely_by_its_own_toml(tmp_path) -> None:
    _place_role_toml(
        tmp_path,
        "security-expert",
        'full_name = "Sam Security"\ntitle = "security expert"\n'
        'description = "Keeps the system secure."\nmission = "Find and fix security issues."\n'
        'model = "opus"\n',
    )
    r = resolve_role("security-expert", tmp_path)
    assert r.slug == "security-expert"
    assert r.full_name == "Sam Security"
    assert r.model == "opus"


def test_a_new_slug_missing_a_required_field_raises(tmp_path) -> None:
    _place_role_toml(tmp_path, "new-role", 'full_name = "New Person"\n')  # missing title etc.
    with pytest.raises(SquadsError, match="missing required fields"):
        resolve_role("new-role", tmp_path)


def test_malformed_toml_raises_squads_error(tmp_path) -> None:
    bad = tmp_path / ".overrides" / "roles" / "manager.toml"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("this is not [ valid toml ={{", encoding="utf-8")
    with pytest.raises(SquadsError, match="malformed role override"):
        resolve_role("manager", tmp_path)
