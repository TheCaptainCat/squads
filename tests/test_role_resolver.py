"""Tests for the role override resolver (TASK-000088).

Verifies:
- A project roles/<slug>.toml overrides a bundled role field-wise (only the fields it sets;
  missing fields are inherited from PREDEFINED).
- A brand-new slug defined entirely in a TOML becomes a valid RoleDef.
- Bundled-only behaviour is unchanged when no override exists.
- activate_role and add_dev read through the resolver.
- full_name in a TOML seeds the name on activate_role.
- Malformed TOML raises SquadsError.
- New-slug TOML missing required fields raises SquadsError.
- Attempting to override the slug field is silently ignored (slugs are canonical).
"""

from pathlib import Path

import pytest

from squads._errors import RoleNotFoundError, SquadsError
from squads._models._extras import ExtraKey as X
from squads._roles._catalog import PREDEFINED
from squads._roles._resolver import resolve_dev_role, resolve_role
from squads._services import (
    _service as service,
)

pytestmark = pytest.mark.anyio

# ------------------------------------------------------------------ helpers


def _roles_dir(squad_dir: Path) -> Path:
    return squad_dir / ".overrides" / "roles"


def _place_role_toml(squad_dir: Path, slug: str, content: str) -> Path:
    target = _roles_dir(squad_dir) / f"{slug}.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


# ------------------------------------------------------------------ bundled baseline


async def test_resolve_role_no_override_returns_bundled(project):
    """With no override file, resolve_role returns the PREDEFINED entry unchanged."""
    r = resolve_role("architect", project.squad_dir)
    bundled = next(x for x in PREDEFINED if x.slug == "architect")
    assert r == bundled


async def test_resolve_role_unknown_slug_no_override_raises(project):
    """An unknown slug with no override file raises RoleNotFoundError."""
    with pytest.raises(RoleNotFoundError):
        resolve_role("nonexistent-slug", project.squad_dir)


def test_resolve_role_none_squad_dir_returns_bundled():
    """When squad_dir is None (e.g. no project), resolve_role returns the bundled entry."""
    r = resolve_role("manager", None)
    bundled = next(x for x in PREDEFINED if x.slug == "manager")
    assert r == bundled


# ------------------------------------------------------------------ field-wise merge (bundled slug)


async def test_field_wise_override_changes_only_set_fields(project):
    """A TOML for a bundled slug overrides only the fields it specifies; rest are inherited."""
    _place_role_toml(
        project.squad_dir,
        "architect",
        'full_name = "Ada Lovelace"\nmodel = "haiku"\n',
    )
    r = resolve_role("architect", project.squad_dir)

    # Overridden fields:
    assert r.full_name == "Ada Lovelace"
    assert r.model == "haiku"

    # Inherited from PREDEFINED:
    bundled = next(x for x in PREDEFINED if x.slug == "architect")
    assert r.mission == bundled.mission
    assert r.title == bundled.title
    assert r.description == bundled.description
    assert r.responsibilities == bundled.responsibilities
    assert r.agreements == bundled.agreements
    assert r.color == bundled.color
    assert r.is_default == bundled.is_default


async def test_field_wise_override_tuple_fields(project):
    """Responsibilities and agreements in TOML produce correct tuples on the RoleDef."""
    _place_role_toml(
        project.squad_dir,
        "qa",
        'responsibilities = ["Write acceptance tests", "Verify bug fixes"]\n',
    )
    r = resolve_role("qa", project.squad_dir)
    assert r.responsibilities == ("Write acceptance tests", "Verify bug fixes")

    # Unchanged fields still come from PREDEFINED:
    bundled = next(x for x in PREDEFINED if x.slug == "qa")
    assert r.mission == bundled.mission


async def test_slug_field_in_toml_is_ignored(project):
    """A slug key in the TOML is silently ignored; the filename-derived slug is canonical."""
    _place_role_toml(
        project.squad_dir,
        "reviewer",
        'slug = "something-else"\nfull_name = "Helen Reviewer"\n',
    )
    r = resolve_role("reviewer", project.squad_dir)
    assert r.slug == "reviewer"  # canonical slug preserved
    assert r.full_name == "Helen Reviewer"


async def test_unknown_keys_in_toml_are_ignored(project):
    """Extra keys in the TOML that don't map to RoleDef fields are silently dropped."""
    _place_role_toml(
        project.squad_dir,
        "devops",
        'full_name = "Hugo Custom"\nfuture_key = "ignored"\n',
    )
    r = resolve_role("devops", project.squad_dir)
    assert r.full_name == "Hugo Custom"
    # No error — forward-compatible


# ------------------------------------------------------------------ new-slug admission


async def test_new_slug_toml_defines_whole_role(project):
    """A TOML for a slug not in PREDEFINED defines a brand-new RoleDef."""
    _place_role_toml(
        project.squad_dir,
        "security-expert",
        (
            'full_name = "Sam Security"\n'
            'title = "security expert"\n'
            'description = "Keeps the system secure."\n'
            'mission = "Find and fix security issues."\n'
            'model = "opus"\n'
        ),
    )
    r = resolve_role("security-expert", project.squad_dir)
    assert r.slug == "security-expert"
    assert r.full_name == "Sam Security"
    assert r.title == "security expert"
    assert r.model == "opus"
    assert r.mission == "Find and fix security issues."


async def test_new_slug_missing_required_field_raises(project):
    """A new-slug TOML missing a required field raises SquadsError."""
    _place_role_toml(
        project.squad_dir,
        "new-role",
        # Missing: title, description, mission
        'full_name = "New Person"\n',
    )
    with pytest.raises(SquadsError, match="missing required fields"):
        resolve_role("new-role", project.squad_dir)


# ------------------------------------------------------------------ malformed TOML


async def test_malformed_toml_raises_squads_error(project):
    """A TOML file with a parse error raises SquadsError with a clear message."""
    bad = _roles_dir(project.squad_dir) / "manager.toml"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("this is not [ valid toml ={{", encoding="utf-8")
    with pytest.raises(SquadsError, match="malformed role override"):
        resolve_role("manager", project.squad_dir)


# ------------------------------------------------------------------ service-level: activate_role


async def test_activate_role_picks_up_field_override(project, svc):
    """activate_role reads through the resolver; a TOML full_name seeds the ROLE item."""
    _place_role_toml(
        project.squad_dir,
        "reviewer",
        'full_name = "Helen Reviewer"\nmodel = "haiku"\n',
    )
    # reviewer is not activated yet (project fixture uses roles_spec="minimal" → manager only).
    svc2 = service.Service(project)
    item = await svc2.activate_role("reviewer")

    assert item.extra.get(X.FULL_NAME) == "Helen Reviewer"
    assert item.extra.get(X.MODEL) == "haiku"
    # Mission is inherited from PREDEFINED.
    bundled = next(x for x in PREDEFINED if x.slug == "reviewer")
    assert item.extra.get(X.MISSION) == bundled.mission


async def test_activate_role_new_slug_creates_item(project):
    """activate_role admits a brand-new slug defined only in a project TOML."""
    _place_role_toml(
        project.squad_dir,
        "security-expert",
        (
            'full_name = "Sam Security"\n'
            'title = "security expert"\n'
            'description = "Keeps the system secure."\n'
            'mission = "Find and fix security issues."\n'
        ),
    )
    svc = service.Service(project)
    item = await svc.activate_role("security-expert")

    assert item.type == "role"
    assert item.extra.get(X.FULL_NAME) == "Sam Security"
    assert item.extra.get(X.SLUG) == "security-expert"


async def test_activate_role_bundled_no_override_unchanged(project):
    """activate_role with no override produces the standard bundled extra for the role."""
    svc = service.Service(project)
    # Activate architect (not activated in minimal project fixture).
    item = await svc.activate_role("architect")
    bundled = next(x for x in PREDEFINED if x.slug == "architect")

    assert item.extra.get(X.FULL_NAME) == bundled.full_name
    assert item.extra.get(X.MODEL) == bundled.model
    assert item.extra.get(X.MISSION) == bundled.mission


# ------------------------------------------------------------------ service-level: add_dev


async def test_add_dev_picks_up_dev_toml_override(project):
    """add_dev reads through resolve_dev_role; a TOML model override is applied."""
    _place_role_toml(
        project.squad_dir,
        "python-dev",
        'model = "opus"\n',
    )
    svc = service.Service(project)
    item = await svc.add_dev("python")

    assert item.extra.get(X.MODEL) == "opus"
    # full_name still auto-generated from pool (no name kwarg, no full_name in TOML).
    assert item.extra.get(X.FULL_NAME)  # non-empty


async def test_add_dev_explicit_name_wins_over_toml_full_name(project):
    """Explicit name kwarg to add_dev takes precedence over full_name in the TOML."""
    _place_role_toml(
        project.squad_dir,
        "go-dev",
        'full_name = "TOML Go Dev"\nmodel = "haiku"\n',
    )
    svc = service.Service(project)
    item = await svc.add_dev("go", name="Alice Go")

    assert item.extra.get(X.FULL_NAME) == "Alice Go"
    assert item.extra.get(X.MODEL) == "haiku"  # model override still applied


async def test_add_dev_no_toml_uses_pool_name(project):
    """add_dev with no TOML override uses the DEV_NAME_POOL name as before."""
    svc = service.Service(project)
    item = await svc.add_dev("rust")

    full_name: str = item.extra.get(X.FULL_NAME, "")
    assert full_name.endswith("Rust")  # pool-first-name + tech surname


# ------------------------------------------------------------------ resolve_dev_role unit


def test_resolve_dev_role_no_override():
    """resolve_dev_role with squad_dir=None returns the vanilla dev_role output."""
    r = resolve_dev_role("dotnet", seq=0, squad_dir=None)
    assert r.slug == "dotnet-dev"
    assert r.full_name.endswith("Dotnet")


async def test_resolve_dev_role_with_override(project):
    """resolve_dev_role applies TOML overrides when present."""
    _place_role_toml(project.squad_dir, "dotnet-dev", 'model = "opus"\n')
    r = resolve_dev_role("dotnet", seq=0, squad_dir=project.squad_dir)
    assert r.slug == "dotnet-dev"
    assert r.model == "opus"


# ------------------------------------------------------------------ CLI smoke test


async def test_cli_activate_role_with_toml_override(project, invoke):
    """CLI: `sq role activate` picks up the TOML override and reports the custom name."""

    _place_role_toml(
        project.squad_dir,
        "reviewer",
        'full_name = "Helen Reviewer"\n',
    )
    result = await invoke(["role", "activate", "reviewer"])
    assert result.exit_code == 0, result.output
    assert "Helen Reviewer" in result.output


async def test_cli_activate_new_slug_role(project, invoke):
    """CLI: `sq role activate` can activate a brand-new slug defined in a project TOML."""

    _place_role_toml(
        project.squad_dir,
        "security-expert",
        (
            'full_name = "Sam Security"\n'
            'title = "security expert"\n'
            'description = "Keeps the system secure."\n'
            'mission = "Find and fix security issues."\n'
        ),
    )
    result = await invoke(["role", "activate", "security-expert"])
    assert result.exit_code == 0, result.output
    assert "Sam Security" in result.output
