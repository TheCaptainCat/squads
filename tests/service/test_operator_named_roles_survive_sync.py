"""An operator-set role name must survive `sq sync`, not only a project override's
``full_name``.

The existing role-override test file (``test_partial_dev_role_override_is_honoured_by_sync.py``)
covers the override-input path only -- exactly the shape that shipped with this defect: a
projection that discards ``--name`` still passes it clean. This file covers the other input:
a name set through ``sq init --name``/``[init.names]`` or `sq role activate --name`, which
never creates an override file at all.

Two structural causes had to be fixed together for any of this to hold:

1. The caller (`_refresh_catalog_extra`) supplying no merge base for a non-dev role
   (unconditionally ``None``).
2. `resolve_role_with_base` discarding whatever base the caller *did* supply, whenever the
   slug is in ``PREDEFINED`` -- so even a correct base from (1) never reached the merge.

Both are exercised together by every test below (an integration test can't isolate one from
the other): reverting either site by hand while developing this fix turned every ``--name``
test in this file red, and restoring either one alone was not enough to turn them green again.
"""

from dataclasses import replace as dc_replace
from datetime import timedelta
from pathlib import Path

import pytest

from squads import __version__
from squads import _itemfile as itemfile
from squads._context import bind_context, get_context
from squads._index._reflog import read_lines, reflog_path
from squads._models._extras import ExtraKey as X
from squads._roles._catalog import PREDEFINED
from squads._roles._resolver import dev_base_for_slug, resolve_role_with_base
from squads._services import _service as service
from squads._workflow import ROSTER_ROLE

pytestmark = pytest.mark.anyio

_BUNDLED_ARCHITECT = next(r for r in PREDEFINED if r.slug == "architect")


def _place_override(squad_dir: Path, slug: str, content: str) -> None:
    target = squad_dir / ".overrides" / "roles" / f"{slug}.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"# squads:override-base:{__version__}\n{content}", encoding="utf-8")


def _on_disk_frontmatter(svc, item) -> dict[str, object]:
    from squads._index._resolver import item_file

    return itemfile.read_frontmatter(text=item_file(svc.paths, item).read_text(encoding="utf-8"))


def _claude_md(project) -> str:
    return (project.root / "CLAUDE.md").read_text(encoding="utf-8")


def _pointer_text(project, slug: str) -> str:
    return (project.root / ".claude" / "agents" / f"{slug}.md").read_text(encoding="utf-8")


async def _list_title(svc, item_id: str) -> str:
    items = await svc.list_items(item_type=ROSTER_ROLE)
    return next(it.title for it in items if it.id == item_id)


# --------------------------------------------------------------------------------------------
# The `sq role activate --name` path -- fresh squad, no override files anywhere.
# --------------------------------------------------------------------------------------------


async def test_a_bundled_roles_activate_name_survives_two_consecutive_syncs(project, svc):
    """`project`/`svc` init with ``--roles minimal`` (manager only): `architect` is not yet
    live, so activating it is a real create, not the documented activate-an-already-live-role
    no-op."""
    role = await svc.activate_role("architect", name="Ada Lovelace")
    assert role.title == "Ada Lovelace"
    assert role.extra[X.FULL_NAME] == "Ada Lovelace"

    for _ in range(2):  # two consecutive syncs, not one
        issues = await svc.check()
        assert not issues
        skipped = await svc.sync()
        assert not skipped

        reloaded = await svc.get(role.id)
        assert reloaded.title == "Ada Lovelace"
        assert reloaded.extra[X.FULL_NAME] == "Ada Lovelace"
        assert _on_disk_frontmatter(svc, reloaded)["title"] == "Ada Lovelace"
        assert await _list_title(svc, role.id) == "Ada Lovelace"
        assert "Ada Lovelace" in _claude_md(project)
        assert "Ada Lovelace" in _pointer_text(project, "architect")
        assert "Robert Architect" not in _claude_md(project)

        issues_after = await svc.check()
        assert not issues_after


async def test_a_developer_roles_name_survives_two_consecutive_syncs(project, svc):
    """The developer side of the same mechanism (unified, not a parallel code path): a
    developer named at creation must be just as durable through `role_base_from_item` as it
    was through the old dev-only special case."""
    dev = await svc.add_dev("python", name="Hank Python")
    assert dev.extra[X.FULL_NAME] == "Hank Python"

    for _ in range(2):
        skipped = await svc.sync()
        assert not skipped
        reloaded = await svc.get(dev.id)
        assert reloaded.title == "Hank Python"
        assert reloaded.extra[X.FULL_NAME] == "Hank Python"
        assert "Hank Python" in _claude_md(project)


# --------------------------------------------------------------------------------------------
# The `sq init --name <slug>=<Name>` path -- the name never goes through `activate_role`'s
# explicit `name=` kwarg from a live call site; it flows in through `init`'s own `names` map,
# exactly like `[init.names]`/the interactive prompt (all three merge into the same map).
# --------------------------------------------------------------------------------------------


async def test_init_time_name_survives_two_consecutive_syncs(tmp_path, frozen_time):
    result = await service.init(
        root=tmp_path,
        roles_spec="architect",
        names={"architect": "Ada Lovelace"},
        _skip_skill_seed=True,
    )
    svc2 = service.Service(result.paths)

    role = next(it for it in await svc2.list_items(item_type=ROSTER_ROLE) if it.slug == "architect")
    assert role.title == "Ada Lovelace"

    for _ in range(2):
        skipped = await svc2.sync()
        assert not skipped
        reloaded = await svc2.get(role.id)
        assert reloaded.title == "Ada Lovelace"
        assert reloaded.extra[X.FULL_NAME] == "Ada Lovelace"
        assert "Ada Lovelace" in (result.paths.root / "CLAUDE.md").read_text(encoding="utf-8")


# --------------------------------------------------------------------------------------------
# The sharpest regression: one squad, `architect` named only via `--name`, `qa` named via
# `--name` *plus* an override file for `qa` only. One sync. Both must survive -- a fix that
# only wires the override path through the item leaves `architect` reverted here.
# --------------------------------------------------------------------------------------------


async def test_name_only_and_name_plus_override_both_survive_the_same_sync(tmp_path, frozen_time):
    result = await service.init(
        root=tmp_path,
        roles_spec="architect,qa",
        names={"architect": "Ada Lovelace", "qa": "Sam Reeves"},
        _skip_skill_seed=True,
    )
    svc2 = service.Service(result.paths)
    _place_override(result.paths.squad_dir, "qa", 'full_name = "Sam Reeves"\n')

    skipped = await svc2.sync()
    assert not skipped

    roles = {it.slug: it for it in await svc2.list_items(item_type=ROSTER_ROLE)}
    assert roles["architect"].title == "Ada Lovelace"  # --name only, no override file
    assert roles["qa"].title == "Sam Reeves"  # --name AND an override file


# --------------------------------------------------------------------------------------------
# Tier 1 still wins: a declared override full_name renames the role even over an item that
# already carries a *different* operator-set name -- both role kinds.
# --------------------------------------------------------------------------------------------


async def test_a_declared_override_still_renames_over_the_items_own_different_name_bundled(
    project, svc
):
    role = await svc.activate_role("architect", name="Ada Lovelace")
    _place_override(project.squad_dir, "architect", 'full_name = "Marie Curie"\n')

    await svc.sync()

    reloaded = await svc.get(role.id)
    assert reloaded.title == "Marie Curie"
    assert reloaded.extra[X.FULL_NAME] == "Marie Curie"


async def test_a_declared_override_still_renames_over_the_items_own_different_name_dev(
    project, svc
):
    dev = await svc.add_dev("python", name="Hank Python")
    _place_override(project.squad_dir, "python-dev", 'full_name = "Grace Hopper"\n')

    await svc.sync()

    reloaded = await svc.get(dev.id)
    assert reloaded.title == "Grace Hopper"
    assert reloaded.extra[X.FULL_NAME] == "Grace Hopper"


# --------------------------------------------------------------------------------------------
# Tier 3 still applies: no item and no override resolves to the bundled default (bundled) or
# the generated pool name (a dev slug with no item).
# --------------------------------------------------------------------------------------------


async def test_tier_3_bundled_default_and_dev_pool_name_with_no_item_and_no_override(project):
    resolved = resolve_role_with_base("architect", project.squad_dir, base=None)
    assert resolved.full_name == _BUNDLED_ARCHITECT.full_name

    pool_base = dev_base_for_slug("rust-dev")
    resolved_dev = resolve_role_with_base("rust-dev", project.squad_dir, base=pool_base)
    assert resolved_dev.full_name == pool_base.full_name  # the generated pool pick, not a stub


# --------------------------------------------------------------------------------------------
# Catalog refresh still works: a RoleDef field an operator never sets (mission,
# responsibilities, can_spawn) still reaches an item whose stored copy is stale, in the very
# same sync that also preserves the operator's own name. A fix that simply froze the whole
# definition to the item would pass every test above and fail only this one.
# --------------------------------------------------------------------------------------------


async def test_catalog_refresh_still_reaches_a_stale_item_alongside_a_preserved_name(project, svc):
    role = await svc.activate_role("architect", name="Ada Lovelace")

    from squads._index._resolver import item_file
    from squads._itemfile import update_frontmatter

    current = await svc.get(role.id)
    base = current.model_copy(deep=True)
    stale = current.model_copy(deep=True)
    stale.extra[X.MISSION] = "a long-obsolete mission statement"
    stale.description = "a long-obsolete mission statement"
    stale.extra[X.RESPONSIBILITIES] = ["an obsolete responsibility"]
    stale.extra[X.CAN_SPAWN] = not _BUNDLED_ARCHITECT.can_spawn
    async with svc.store.transaction() as db:
        await update_frontmatter(
            item_file(svc.paths, stale), stale, base, default_kind=svc.spec.default_ref_kind()
        )
        db.add(stale)

    skipped = await svc.sync()
    assert not skipped

    healed = await svc.get(role.id)
    # Non-operator-settable fields reconverge to the *current* catalog value.
    assert healed.extra[X.MISSION] == _BUNDLED_ARCHITECT.mission
    assert healed.description == _BUNDLED_ARCHITECT.mission
    assert list(healed.extra[X.RESPONSIBILITIES]) == list(_BUNDLED_ARCHITECT.responsibilities)
    assert healed.extra[X.CAN_SPAWN] == _BUNDLED_ARCHITECT.can_spawn
    # The operator's own name is untouched by the very same sync.
    assert healed.title == "Ada Lovelace"
    assert healed.extra[X.FULL_NAME] == "Ada Lovelace"


# --------------------------------------------------------------------------------------------
# `[init.names]` is read by no resolver and no sync path: a stale or absent entry changes
# nothing about what a resolve produces.
# --------------------------------------------------------------------------------------------


async def test_init_names_presence_or_absence_changes_no_resolve(project, svc):
    role = await svc.activate_role("architect", name="Ada Lovelace")

    # A [init.names] entry that actively disagrees with the item -- as A2 notes it legitimately
    # will, the moment a name changes through any other sanctioned route.
    cfg = svc.paths.config.model_copy(update={"init_names": {"architect": "Someone Else"}})
    svc.paths.config_path.write_text(cfg.to_toml(), encoding="utf-8")

    for _ in range(2):
        await svc.sync()
        reloaded = await svc.get(role.id)
        assert reloaded.title == "Ada Lovelace"  # untouched by the disagreeing table

    # Absence changes nothing either.
    cfg_empty = svc.paths.config.model_copy(update={"init_names": {}})
    svc.paths.config_path.write_text(cfg_empty.to_toml(), encoding="utf-8")
    await svc.sync()
    reloaded = await svc.get(role.id)
    assert reloaded.title == "Ada Lovelace"


# --------------------------------------------------------------------------------------------
# A change through this writer is visible: updated_at moves, modified_session is set, and one
# "update" reflog entry is appended -- while the role's own "create" entry stays readable.
# --------------------------------------------------------------------------------------------


async def test_a_rename_through_this_writer_is_visible_and_the_create_entry_survives(
    project, svc, frozen_time
):
    from squads import _actor as actor

    actor.seed_session("sid-activate", None)
    role = await svc.activate_role("architect", name="Ada Lovelace")
    original_updated_at = role.updated_at

    _place_override(project.squad_dir, "architect", 'full_name = "Marie Curie"\n')

    later = frozen_time + timedelta(hours=1)
    bind_context(dc_replace(get_context(), clock_override=later))
    actor.seed_session("sid-sync", None)
    skipped = await svc.sync()
    assert not skipped

    reloaded = await svc.get(role.id)
    assert reloaded.title == "Marie Curie"
    assert reloaded.updated_at == later
    assert reloaded.updated_at != original_updated_at
    assert reloaded.modified_session == "sid-sync"

    lines = await read_lines(reflog_path(project.squad_dir))
    role_lines = [ln for ln in lines if ln.target == role.id]
    assert [ln.op for ln in role_lines] == ["create", "update"]  # append-only, in order
    assert role_lines[0].delta.get("title") == "Ada Lovelace"  # the create entry, untouched
