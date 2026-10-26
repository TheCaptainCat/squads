"""``sq sync``'s catalog-refresh honours a partial ``<tech>-dev.toml``: the merge base for a
developer role that already exists on the roster is built from *that item's own stored
identity* (:func:`~squads._roles._resolver.role_base_from_item`), never re-derived from
``dev_role(tech)`` at its default ``seq=0``.

The rename is the risk, so it is the first test below: a squad's second developer sits at a
non-zero pool position, and re-deriving the base from the slug alone would silently roll her
name back to the pool's first entry. Everything else here is the same property from other
angles -- the omit/declare pair (both leave the name alone), a complete
override, and the two refusal shapes (an invalid value, a slug/filename mismatch) that must
still refuse exactly like any other role override does.
"""

from pathlib import Path

import pytest

from _helpers import catalog_of
from squads import _itemfile as itemfile
from squads._errors import SquadsError
from squads._index._resolver import item_file
from squads._models._attributes import AttributeKey as X
from squads._roles._resolver import resolve_role_for_item

pytestmark = pytest.mark.anyio


def _resolved(svc, item):
    """*item*'s definition as every reader of it resolves one -- the role's own fields are
    catalog answers, never a copy stored in its ``extra``."""
    return resolve_role_for_item(item, svc.paths.squad_dir, catalog=catalog_of(svc.paths.squad_dir))


def _place_dev_toml(squad_dir: Path, slug: str, content: str) -> None:
    target = squad_dir / ".overrides" / "roles" / f"{slug}.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _on_disk_full_name(svc, item) -> str:
    """The name as the *file* carries it -- ``title``, the uniform-record field the resolved
    full name is stored on, which is also where ``role_base_from_item`` reads it back from."""
    fm = itemfile.read_frontmatter(text=item_file(svc.paths, item).read_text(encoding="utf-8"))
    return fm["title"]


async def test_a_second_developers_full_name_survives_two_syncs_with_a_partial_override(
    project, svc
):
    """Two developers; the *second* one (pool index 1, "Ada <tech>") gets a partial override
    that never mentions ``full_name``. Two consecutive syncs must leave her name exactly as it
    was, in frontmatter and in the index both.
    """
    await svc.activate_role(None, from_template="dev", tech="python")  # seq=0 -> pool[0]
    second = await svc.activate_role(
        None, from_template="dev", tech="typescript"
    )  # seq=1 -> pool[1] ("Ada Typescript")
    assert second.title == "Ada Typescript"

    _place_dev_toml(project.squad_dir, "typescript-dev", 'title = "Senior TypeScript developer"\n')

    await svc.sync()
    after_first_sync = await svc.get(second.id)
    assert after_first_sync.title == "Ada Typescript"
    assert _on_disk_full_name(svc, after_first_sync) == "Ada Typescript"

    await svc.sync()
    after_second_sync = await svc.get(second.id)
    assert after_second_sync.title == "Ada Typescript"
    assert _on_disk_full_name(svc, after_second_sync) == "Ada Typescript"

    # The override itself did apply -- this is not "sync ignored the file".
    assert _resolved(svc, after_second_sync).title == "Senior TypeScript developer"


async def test_omitting_full_name_preserves_the_live_name(project, svc):
    await svc.activate_role(None, from_template="dev", tech="python")
    second = await svc.activate_role(None, from_template="dev", tech="typescript")

    _place_dev_toml(project.squad_dir, "typescript-dev", 'title = "Senior TypeScript developer"\n')
    await svc.sync()

    reloaded = await svc.get(second.id)
    assert reloaded.title == second.title
    assert _on_disk_full_name(svc, reloaded) == second.title


async def test_declaring_full_name_does_not_rename_the_live_dev_role(project, svc):
    """A role's stored name is its name: a file that declares ``full_name`` after the role was
    created changes the name nowhere."""
    await svc.activate_role(None, from_template="dev", tech="python")
    second = await svc.activate_role(None, from_template="dev", tech="typescript")

    _place_dev_toml(project.squad_dir, "typescript-dev", 'full_name = "Zara Typescript"\n')
    await svc.sync()

    reloaded = await svc.get(second.id)
    assert reloaded.title == second.title
    assert _on_disk_full_name(svc, reloaded) == second.title
    assert _resolved(svc, reloaded).full_name == second.title


async def test_a_complete_dev_override_applies_every_declared_field(project, svc):
    dev = await svc.activate_role(None, from_template="dev", tech="rust")
    _place_dev_toml(
        project.squad_dir,
        "rust-dev",
        'full_name = "Priya Rust"\ntitle = "Staff Rust developer"\n'
        'mission = "Own the Rust surface end to end."\nmodel = "opus"\n',
    )
    await svc.sync()

    reloaded = await svc.get(dev.id)
    assert reloaded.title == dev.title  # the name was set at creation
    resolved = _resolved(svc, reloaded)
    assert resolved.full_name == dev.title
    assert resolved.title == "Staff Rust developer"
    assert resolved.mission == "Own the Rust surface end to end."
    assert resolved.model == "opus"
    # The model follows the file; only an explicit `--model` stores one on the item.
    assert reloaded.attribute(X.MODEL) is None


async def test_sync_still_refuses_a_dev_override_with_an_off_whitelist_model(project, svc):
    dev = await svc.activate_role(None, from_template="dev", tech="go")
    _place_dev_toml(project.squad_dir, "go-dev", 'model = "opuss"\n')

    with pytest.raises(SquadsError, match="opuss"):
        await svc.sync()

    # Nothing was mutated by the refused attempt.
    reloaded = await svc.get(dev.id)
    assert reloaded.attribute(X.MODEL) != "opuss"


async def test_sync_still_refuses_a_dev_override_whose_slug_disagrees_with_its_filename(
    project, svc
):
    dev = await svc.activate_role(None, from_template="dev", tech="elixir")
    before = item_file(svc.paths, dev).read_text(encoding="utf-8")
    _place_dev_toml(project.squad_dir, "elixir-dev", 'slug = "other-dev"\ntitle = "x"\n')

    with pytest.raises(SquadsError, match="filename"):
        await svc.sync()

    # Nothing was mutated by the refused attempt. Asserted on the file's own bytes rather than
    # through a resolve: the override that made this refuse is still on disk, so resolving the
    # item would raise the same refusal again and prove nothing about what was written.
    assert item_file(svc.paths, dev).read_text(encoding="utf-8") == before


async def test_sync_materialises_a_role_whose_catalog_entry_vanished_from_what_it_stores(
    project, svc
):
    """A catalog role whose entry is gone (its backing definition vanished after activation)
    resolves to nothing from the catalog; sync neither raises nor skips it, and its pointer is
    written from what the item stores."""
    from squads._errors import RoleNotFoundError
    from squads._roles._resolver import resolve_role

    role = (
        await svc.create(
            "role",
            "Sam Security",
            description="Protect the project.",
            slug="compliance-officer",
            author="compliance-officer",
        )
    ).item

    # Confirm the fixture is broken as intended: genuinely unresolvable now.
    with pytest.raises(RoleNotFoundError):
        resolve_role("compliance-officer", project.squad_dir, catalog=catalog_of(project.squad_dir))

    skipped = await svc.sync()  # must not raise

    assert not any(role.id in msg for msg in skipped)
    pointer = project.root / ".claude" / "agents" / "compliance-officer.md"
    assert "Sam Security" in pointer.read_text(encoding="utf-8")
