"""``activate_role`` reads through the resolver at the point a role is actually instantiated into
the roster, for both bases it builds from (a catalog entry and a role template): a non-name field
(model, mission) reaches the created ROLE item's resolved definition; with no per-slug file the
bundled default (or the template's name pool) is used unchanged; a per-slug file that alone
declares a slug is a layer with no base and does not define a role; ``--name`` beats a per-slug
file's ``full_name``, which beats the template's name pattern.

"Reaches the created item" is asserted through :func:`~squads._roles._resolver
.resolve_role_for_item` -- the seam every reader of a role goes through. The item stores no copy
of a catalog or template definition, so asserting it there would be asserting something nothing
keeps and nothing reads.
"""

from pathlib import Path

import pytest

from _helpers import catalog_of
from squads._errors import SquadsError
from squads._models._attributes import AttributeKey as X
from squads._roles._catalog import PREDEFINED
from squads._roles._resolver import resolve_role_for_item

pytestmark = pytest.mark.anyio


def _resolved(svc, item):
    """*item*'s definition as every reader of it resolves one."""
    return resolve_role_for_item(item, svc.paths.squad_dir, catalog=catalog_of(svc.paths.squad_dir))


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


@pytest.mark.parametrize("complete", [False, True], ids=["partial", "complete"])
async def test_a_slug_only_a_per_slug_file_declares_is_not_a_role_to_activate(
    project, svc, complete: bool
):
    body = 'full_name = "Sam Security"\n'
    if complete:
        body += 'title = "security expert"\ndescription = "d"\nmission = "m"\n'
    _place_role_toml(project.squad_dir, "security-expert", body)
    with pytest.raises(SquadsError, match=r"sq role add security-expert --file"):
        await svc.activate_role("security-expert")
    assert await svc.roster_item("role", "security-expert") is None


async def test_activate_role_with_no_override_stores_no_definition(project, svc):
    item = await svc.activate_role("architect")
    bundled = next(x for x in PREDEFINED if x.slug == "architect")
    assert _resolved(svc, item).model == bundled.model
    assert _resolved(svc, item).mission == bundled.mission
    assert item.description == ""
    assert set(item.attributes) == {X.ORIGIN}


async def test_a_template_role_picks_up_a_per_slug_model_file(project, svc):
    _place_role_toml(project.squad_dir, "python-dev", 'model = "opus"\n')
    item = await svc.activate_role(None, from_template="dev", tech="python")
    assert _resolved(svc, item).model == "opus"
    assert item.attribute(X.MODEL) is None  # the model follows the file, it is not copied
    assert item.title  # auto-generated from the pool, non-empty


async def test_a_template_role_with_no_toml_falls_back_to_the_templates_name_pool(project, svc):
    item = await svc.activate_role(None, from_template="dev", tech="rust")
    assert item.title.endswith("Rust")


async def test_a_template_role_takes_a_per_slug_full_name_over_the_name_pattern(project, svc):
    _place_role_toml(project.squad_dir, "go-dev", 'full_name = "TOML Go Dev"\nmodel = "haiku"\n')
    item = await svc.activate_role(None, from_template="dev", tech="go")
    assert item.title == "TOML Go Dev"
    assert _resolved(svc, item).model == "haiku"


async def test_a_template_roles_explicit_name_wins_over_a_per_slug_full_name(project, svc):
    _place_role_toml(project.squad_dir, "go-dev", 'full_name = "TOML Go Dev"\nmodel = "haiku"\n')
    item = await svc.activate_role(None, from_template="dev", tech="go", name="Alice Go")
    assert item.title == "Alice Go"
    assert _resolved(svc, item).model == "haiku"  # non-name fields still apply


async def test_a_second_role_for_a_technology_already_registered_is_refused(svc):
    await svc.activate_role(None, from_template="dev", tech="dotnet")
    with pytest.raises(SquadsError, match="already exists"):
        await svc.activate_role(None, from_template="dev", tech="dotnet")
