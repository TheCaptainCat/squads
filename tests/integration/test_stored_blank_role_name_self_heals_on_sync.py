"""A role item whose *stored* ``full_name`` is already blank, planted directly into the
frontmatter and index, self-heals on ``sync`` for both a bundled and a developer role."""

import pytest

from squads import _sections as sections
from squads._itemfile import read_frontmatter
from squads._models._extras import ExtraKey as X
from squads._workflow import ROSTER_ROLE

pytestmark = pytest.mark.anyio


async def _plant_stored_blank_full_name(svc, item) -> None:
    """Overwrite ``title``/``extra.full_name`` with a whitespace-only value directly on both
    the frontmatter file and the index, bypassing the service entirely."""
    path = svc.paths.abspath(item.path)
    text = path.read_text(encoding="utf-8")
    fm = read_frontmatter(text=text)
    fm["title"] = "   "
    fm["extra"]["full_name"] = "   "
    path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")

    async with svc.store.transaction() as db:
        stored = db.items[item.sequence_id]
        stored.title = "   "
        stored.extra[X.FULL_NAME] = "   "


async def _role_stored_name(svc, slug: str) -> str:
    """The role's stored name, read where it lives: the item's own ``title`` field."""
    roles = await svc.list_items(item_type=ROSTER_ROLE)
    role = next(it for it in roles if it.extra.get(X.SLUG) == slug)
    return role.title


# ------------------------------------------------------------------------------- bundled role


async def test_sync_self_heals_a_stored_blank_name_on_a_bundled_role(project, svc, invoke):
    item = await svc.activate_role("devops")
    await _plant_stored_blank_full_name(svc, item)

    synced = await invoke(["sync"])
    assert synced.exit_code == 0, synced.output

    healed = await _role_stored_name(svc, "devops")
    assert healed.strip()
    assert healed == "Hugo Ops"  # the bundled catalog's own name for this slug

    checked = await invoke(["check"])
    assert checked.exit_code == 0, checked.output


async def test_role_show_tolerates_a_stored_blank_name_on_a_bundled_role_before_any_sync(
    project, svc, invoke
):
    item = await svc.activate_role("devops")
    await _plant_stored_blank_full_name(svc, item)

    shown = await invoke(["role", "devops", "show"])
    assert shown.exit_code == 0, shown.output
    assert "Hugo Ops" in shown.output


async def test_role_regen_tolerates_a_stored_blank_name_on_a_bundled_role_before_any_sync(
    project, svc, invoke
):
    item = await svc.activate_role("devops")
    await _plant_stored_blank_full_name(svc, item)

    regenned = await invoke(["role", "devops", "regen"])
    assert regenned.exit_code == 0, regenned.output


async def test_check_stays_clean_with_a_stored_blank_name_on_a_bundled_role(project, svc, invoke):
    item = await svc.activate_role("devops")
    await _plant_stored_blank_full_name(svc, item)

    checked = await invoke(["check"])
    assert checked.exit_code == 0, checked.output


# --------------------------------------------------------------------------------- developer role


async def test_sync_self_heals_a_stored_blank_name_on_a_developer_role(project, svc, invoke):
    item = await svc.add_dev("python", name="Elias Python")
    await _plant_stored_blank_full_name(svc, item)

    synced = await invoke(["sync"])
    assert synced.exit_code == 0, synced.output

    healed = await _role_stored_name(svc, "python-dev")
    assert healed.strip()

    checked = await invoke(["check"])
    assert checked.exit_code == 0, checked.output


async def test_role_show_tolerates_a_stored_blank_name_on_a_developer_role_before_any_sync(
    project, svc, invoke
):
    item = await svc.add_dev("python", name="Elias Python")
    await _plant_stored_blank_full_name(svc, item)

    shown = await invoke(["role", "python-dev", "show"])
    assert shown.exit_code == 0, shown.output


async def test_role_regen_tolerates_a_stored_blank_name_on_a_developer_role_before_any_sync(
    project, svc, invoke
):
    item = await svc.add_dev("python", name="Elias Python")
    await _plant_stored_blank_full_name(svc, item)

    regenned = await invoke(["role", "python-dev", "regen"])
    assert regenned.exit_code == 0, regenned.output


async def test_check_stays_clean_with_a_stored_blank_name_on_a_developer_role(project, svc, invoke):
    item = await svc.add_dev("python", name="Elias Python")
    await _plant_stored_blank_full_name(svc, item)

    checked = await invoke(["check"])
    assert checked.exit_code == 0, checked.output


# ------------------------------------------------------------------------ neither remedy is needed


async def test_a_second_sync_after_the_first_heal_is_silent(project, svc, invoke):
    """A second sync after the heal makes no further change and reports nothing."""
    item = await svc.add_dev("python", name="Elias Python")
    await _plant_stored_blank_full_name(svc, item)

    first = await invoke(["sync"])
    assert first.exit_code == 0

    second = await invoke(["sync"])
    assert second.exit_code == 0
    assert "python-dev" not in second.output


async def test_the_role_is_never_purged_by_any_of_this(project, svc, invoke):
    """Self-healing recovers the role entry; it never discards it."""
    item = await svc.activate_role("qa")
    await _plant_stored_blank_full_name(svc, item)

    await invoke(["sync"])

    roles = await svc.list_items(item_type=ROSTER_ROLE)
    assert any(it.extra.get(X.SLUG) == "qa" for it in roles)
