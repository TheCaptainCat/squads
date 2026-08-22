"""``sq sync``'s catalog-refresh honours a partial ``<tech>-dev.toml``: the merge base for a
developer role that already exists on the roster is built from *that item's own stored
identity* (:func:`~squads._roles._resolver.dev_base_from_item`), never re-derived from
``dev_role(tech)`` at its default ``seq=0``.

The rename is the risk, so it is the first test below: a squad's second developer sits at a
non-zero pool position, and re-deriving the base from the slug alone would silently roll her
name back to the pool's first entry. Everything else here is the same property from other
angles -- the omit/declare pair (opposite expectations, so two tests, never one), a complete
override, and the two refusal shapes (an invalid value, a slug/filename mismatch) that must
still refuse exactly like any other role override does.
"""

from pathlib import Path

import pytest

from squads import _itemfile as itemfile
from squads._errors import SquadsError
from squads._index._resolver import item_file
from squads._models._extras import ExtraKey as X

pytestmark = pytest.mark.anyio


def _place_dev_toml(squad_dir: Path, slug: str, content: str) -> None:
    target = squad_dir / ".overrides" / "roles" / f"{slug}.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _on_disk_full_name(svc, item) -> str:
    fm = itemfile.read_frontmatter(text=item_file(svc.paths, item).read_text(encoding="utf-8"))
    return fm["extra"]["full_name"]


async def test_a_second_developers_full_name_survives_two_syncs_with_a_partial_override(
    project, svc
):
    """Two developers; the *second* one (pool index 1, "Ada <tech>") gets a partial override
    that never mentions ``full_name``. Two consecutive syncs must leave her name exactly as it
    was, in frontmatter and in the index both.
    """
    await svc.add_dev("python")  # seq=0 -> pool[0]
    second = await svc.add_dev("typescript")  # seq=1 -> pool[1] ("Ada Typescript")
    assert second.extra[X.FULL_NAME] == "Ada Typescript"

    _place_dev_toml(project.squad_dir, "typescript-dev", 'title = "Senior TypeScript developer"\n')

    await svc.sync()
    after_first_sync = await svc.get(second.id)
    assert after_first_sync.extra[X.FULL_NAME] == "Ada Typescript"
    assert _on_disk_full_name(svc, after_first_sync) == "Ada Typescript"

    await svc.sync()
    after_second_sync = await svc.get(second.id)
    assert after_second_sync.extra[X.FULL_NAME] == "Ada Typescript"
    assert _on_disk_full_name(svc, after_second_sync) == "Ada Typescript"

    # The override itself did apply -- this is not "sync ignored the file".
    assert after_second_sync.extra[X.TITLE] == "Senior TypeScript developer"


async def test_omitting_full_name_preserves_the_live_name(project, svc):
    await svc.add_dev("python")
    second = await svc.add_dev("typescript")

    _place_dev_toml(project.squad_dir, "typescript-dev", 'title = "Senior TypeScript developer"\n')
    await svc.sync()

    reloaded = await svc.get(second.id)
    assert reloaded.extra[X.FULL_NAME] == second.extra[X.FULL_NAME]
    assert _on_disk_full_name(svc, reloaded) == second.extra[X.FULL_NAME]


async def test_declaring_full_name_renames_the_live_dev_role(project, svc):
    """A file that *declares* ``full_name`` renames the role -- that is what a declaration
    means, and it is exactly what a bundled-slug override already does. This is the opposite
    expectation from the omit case above; one test cannot cover both."""
    await svc.add_dev("python")
    second = await svc.add_dev("typescript")
    assert second.extra[X.FULL_NAME] != "Zara Typescript"

    _place_dev_toml(project.squad_dir, "typescript-dev", 'full_name = "Zara Typescript"\n')
    await svc.sync()

    reloaded = await svc.get(second.id)
    assert reloaded.extra[X.FULL_NAME] == "Zara Typescript"
    assert _on_disk_full_name(svc, reloaded) == "Zara Typescript"


async def test_a_complete_dev_override_applies_every_declared_field(project, svc):
    dev = await svc.add_dev("rust")
    _place_dev_toml(
        project.squad_dir,
        "rust-dev",
        'full_name = "Priya Rust"\ntitle = "Staff Rust developer"\n'
        'mission = "Own the Rust surface end to end."\nmodel = "opus"\n',
    )
    await svc.sync()

    reloaded = await svc.get(dev.id)
    assert reloaded.extra[X.FULL_NAME] == "Priya Rust"
    assert reloaded.extra[X.TITLE] == "Staff Rust developer"
    assert reloaded.extra[X.MISSION] == "Own the Rust surface end to end."
    assert reloaded.extra[X.MODEL] == "opus"


async def test_sync_still_refuses_a_dev_override_with_an_off_whitelist_model(project, svc):
    dev = await svc.add_dev("go")
    _place_dev_toml(project.squad_dir, "go-dev", 'model = "opuss"\n')

    with pytest.raises(SquadsError, match="opuss"):
        await svc.sync()

    # Nothing was mutated by the refused attempt.
    reloaded = await svc.get(dev.id)
    assert reloaded.extra[X.MODEL] != "opuss"


async def test_sync_still_refuses_a_dev_override_whose_slug_disagrees_with_its_filename(
    project, svc
):
    dev = await svc.add_dev("elixir")
    _place_dev_toml(project.squad_dir, "elixir-dev", 'slug = "other-dev"\ntitle = "x"\n')

    with pytest.raises(SquadsError, match="filename"):
        await svc.sync()

    reloaded = await svc.get(dev.id)
    assert reloaded.extra[X.TITLE] != "x"


async def test_sync_no_ops_on_an_orphaned_custom_role_item(project, svc):
    """A role item with neither a catalog entry nor a project override (its backing definition
    vanished after activation) is the one case still meant to hit the narrowed
    ``RoleNotFoundError`` catch -- a genuine skip, not a refusal. This is what makes that catch
    honest: it no longer also catches every unmodified developer role, only this."""
    from squads._errors import RoleNotFoundError
    from squads._roles._resolver import resolve_role

    _place_dev_toml(
        project.squad_dir,
        "compliance-officer",
        'full_name = "Sam Security"\ntitle = "security analyst"\n'
        'description = "Keeps compliance."\nmission = "Protect the project."\n',
    )
    role = await svc.activate_role("compliance-officer")
    (project.squad_dir / ".overrides" / "roles" / "compliance-officer.toml").unlink()

    # Confirm the fixture is broken as intended: genuinely unresolvable now.
    with pytest.raises(RoleNotFoundError):
        resolve_role("compliance-officer", project.squad_dir)

    skipped = await svc.sync()  # must not raise

    assert not any(role.id in msg for msg in skipped)  # no-op, not even reported as a skip
