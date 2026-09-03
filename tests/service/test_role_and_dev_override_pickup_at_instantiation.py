"""``activate_role``/``add_dev`` read through the resolver at the point a role/dev is actually
instantiated into the roster — not just proven at load time (tests/unit/test_role_override_
field_merge.py): a non-name field (model/mission) reaches the created ROLE item; a brand-new
slug's TOML admits it; with no TOML, the bundled default (or the dev-name pool) is used
unchanged; ``resolve_dev_role`` itself picks up a dev-slug TOML override.

"Reaches the created item" is asserted through :func:`~squads._roles._resolver
.resolve_role_for_item` -- the seam every reader of a role goes through -- plus the item's own
uniform-record fields (``title`` from the resolved full name, ``description`` from the resolved
mission). The definition is not mirrored into the item's ``extra``, so asserting it there would
be asserting a copy nothing keeps and nothing reads.

The explicit-``--name``-wins-over-a-TOML-``full_name`` half of this same mechanism is proven at
tests/service/test_agent_naming_precedence.py for ``activate_role`` — but ``add_dev`` reads
through the *different* ``resolve_dev_role`` resolver, so that half of the precedence rule is
re-proven here for the dev-specific code path.
"""

from pathlib import Path

import pytest

from squads._models._extras import ExtraKey as X
from squads._roles._catalog import PREDEFINED
from squads._roles._resolver import resolve_dev_role, resolve_role_for_item

pytestmark = pytest.mark.anyio


def _resolved(svc, item):
    """*item*'s definition as every reader of it resolves one."""
    return resolve_role_for_item(item, svc.paths.squad_dir)


def _place_role_toml(squad_dir: Path, slug: str, content: str) -> Path:
    target = squad_dir / ".overrides" / "roles" / f"{slug}.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


async def test_activate_role_applies_a_toml_model_and_full_name_override(project, svc):
    _place_role_toml(
        project.squad_dir, "reviewer", 'full_name = "Helen Reviewer"\nmodel = "haiku"\n'
    )
    item = await svc.activate_role("reviewer")
    assert item.title == "Helen Reviewer"
    assert _resolved(svc, item).full_name == "Helen Reviewer"
    assert _resolved(svc, item).model == "haiku"
    bundled = next(x for x in PREDEFINED if x.slug == "reviewer")
    assert _resolved(svc, item).mission == bundled.mission  # inherited, not overridden


async def test_activate_role_admits_a_brand_new_slug_defined_only_in_a_project_toml(project, svc):
    _place_role_toml(
        project.squad_dir,
        "security-expert",
        'full_name = "Sam Security"\ntitle = "security expert"\n'
        'description = "Keeps the system secure."\nmission = "Find and fix security issues."\n',
    )
    item = await svc.activate_role("security-expert")
    assert item.type == "role"
    assert item.title == "Sam Security"
    assert _resolved(svc, item).full_name == "Sam Security"
    assert item.extra.get(X.SLUG) == "security-expert"


async def test_activate_role_with_no_override_produces_the_standard_bundled_extra(project, svc):
    item = await svc.activate_role("architect")
    bundled = next(x for x in PREDEFINED if x.slug == "architect")
    assert _resolved(svc, item).model == bundled.model
    assert _resolved(svc, item).mission == bundled.mission
    assert item.description == bundled.mission


async def test_add_dev_applies_a_dev_toml_model_override(project, svc):
    _place_role_toml(project.squad_dir, "python-dev", 'model = "opus"\n')
    item = await svc.add_dev("python")
    assert _resolved(svc, item).model == "opus"
    assert item.extra.get(X.MODEL) == "opus"  # a dev's model is stored: it has no catalog answer
    assert item.title  # auto-generated from the pool, non-empty


async def test_add_dev_with_no_toml_falls_back_to_the_bundled_dev_name_pool(project, svc):
    item = await svc.add_dev("rust")
    assert item.title.endswith("Rust")


async def test_resolve_dev_role_applies_a_toml_override_directly(project):
    _place_role_toml(project.squad_dir, "dotnet-dev", 'model = "opus"\n')
    r = resolve_dev_role("dotnet", seq=0, squad_dir=project.squad_dir)
    assert r.slug == "dotnet-dev"
    assert r.model == "opus"


def test_resolve_dev_role_with_no_squad_dir_returns_the_vanilla_pool_output() -> None:
    r = resolve_dev_role("dotnet", seq=0, squad_dir=None)
    assert r.slug == "dotnet-dev"
    assert r.full_name.endswith("Dotnet")


async def test_add_dev_explicit_name_wins_over_a_toml_full_name_override(project, svc):
    _place_role_toml(project.squad_dir, "go-dev", 'full_name = "TOML Go Dev"\nmodel = "haiku"\n')
    item = await svc.add_dev("go", name="Alice Go")
    # The explicit name is what is *stored*, on the item's own uniform-record field. (A
    # declared `full_name` still renames over it at resolve time -- that is the documented
    # precedence, pinned in tests/service/test_operator_named_roles_survive_sync.py.)
    assert item.title == "Alice Go"
    assert _resolved(svc, item).model == "haiku"  # non-name fields still apply


async def test_add_dev_rejects_a_second_dev_for_a_technology_already_registered(svc):
    from squads._errors import SquadsError

    await svc.add_dev("dotnet")
    with pytest.raises(SquadsError, match="already exists"):
        await svc.add_dev("dotnet")
