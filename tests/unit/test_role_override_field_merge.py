"""``resolve_role`` — the role-override merge for a bundled slug: only the fields a project
TOML actually sets change, everything else falls through to the bundled default; tuple-valued
fields (responsibilities/agreements) merge correctly; identity comes from the filename, so a
``slug`` key must agree with it; an unknown key is refused by name; a brand-new (non-bundled)
slug can be defined entirely by its own TOML; a new slug missing a required field raises;
malformed TOML raises; an unknown slug with no override raises; and ``squad_dir=None`` returns
the bundled entry unchanged.

This document is held to the same standard as the workflow override, not a looser one — same
merge engine, same typed validation, same closed top-level key space. The asymmetry that used
to sit here (silently discarded keys, untyped assignment) mattered more than it looked: a role
is materialised into the agent hosts' own files, so a value nothing validates writes a broken
agent definition rather than an odd view.
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


def test_a_slug_key_agreeing_with_the_filename_is_accepted(tmp_path) -> None:
    _place_role_toml(tmp_path, "reviewer", 'slug = "reviewer"\nfull_name = "Helen"\n')
    r = resolve_role("reviewer", tmp_path)
    assert r.slug == "reviewer"
    assert r.full_name == "Helen"


def test_a_slug_key_disagreeing_with_the_filename_is_refused(tmp_path) -> None:
    """The filename is canonical, so a disagreeing `slug` key can only ever be a declaration
    that does nothing — and the document has no other way to say what it meant."""
    _place_role_toml(tmp_path, "reviewer", 'slug = "something-else"\nfull_name = "Helen"\n')
    with pytest.raises(SquadsError) as excinfo:
        resolve_role("reviewer", tmp_path)
    assert "something-else" in str(excinfo.value)
    assert "filename" in str(excinfo.value)


def test_an_unknown_key_in_the_toml_is_refused_by_name(tmp_path) -> None:
    """A key the model does not declare was silently discarded on a forward-compatibility
    argument. In practice that made every typo a no-op with no signal: the adopter's edit
    simply had no effect. The accepted key set is derived from the model, so it still grows
    with the model — leniency was never what bought forward compatibility."""
    _place_role_toml(tmp_path, "devops", 'full_name = "Hugo Custom"\nfuture_key = "ignored"\n')
    with pytest.raises(SquadsError) as excinfo:
        resolve_role("devops", tmp_path)
    message = str(excinfo.value)
    assert "future_key" in message
    # Refused at the document's own closed key space, which names the accepted set — so a typo
    # is fixable from the message alone. Leaving the top level open would still refuse (the
    # model forbids extras) but would only say the input was not permitted.
    assert "full_name" in message and "can_spawn" in message


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
