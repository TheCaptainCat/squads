"""A role item whose *stored* name is already blank, planted directly into the frontmatter and
index, reads as unset: ``sync``, ``show``, ``regen`` and ``check`` resolve the catalog's (or the
template's) name for both a bundled and a developer role, and never refuse."""

import pytest

from squads import _sections as sections
from squads._itemfile import read_frontmatter
from squads._workflow import ROSTER_ROLE

pytestmark = pytest.mark.anyio


async def _plant_stored_blank_full_name(svc, item) -> None:
    """Overwrite ``title`` with a whitespace-only value directly on both the frontmatter file
    and the index, bypassing the service entirely."""
    path = svc.paths.abspath(item.path)
    text = path.read_text(encoding="utf-8")
    fm = read_frontmatter(text=text)
    fm["title"] = "   "
    path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")

    async with svc.store.transaction() as db:
        stored = db.items[item.sequence_id]
        stored.title = "   "


# ------------------------------------------------------------------------------- bundled role


async def test_sync_resolves_a_stored_blank_name_on_a_bundled_role(project, svc, invoke):
    item = await svc.activate_role("devops")
    await _plant_stored_blank_full_name(svc, item)

    synced = await invoke(["sync"])
    assert synced.exit_code == 0, synced.output

    pointer = project.root / ".claude" / "agents" / "devops.md"
    assert "Hugo Ops" in pointer.read_text(encoding="utf-8")  # the catalog's own name

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


async def test_sync_resolves_a_stored_blank_name_on_a_developer_role(project, svc, invoke):
    item = await svc.activate_role(None, from_template="dev", tech="python", name="Elias Python")
    await _plant_stored_blank_full_name(svc, item)

    synced = await invoke(["sync"])
    assert synced.exit_code == 0, synced.output

    pointer = project.root / ".claude" / "agents" / "python-dev.md"
    assert "Elias Python" in pointer.read_text(encoding="utf-8")  # the template's name pattern

    checked = await invoke(["check"])
    assert checked.exit_code == 0, checked.output


async def test_role_show_tolerates_a_stored_blank_name_on_a_developer_role_before_any_sync(
    project, svc, invoke
):
    item = await svc.activate_role(None, from_template="dev", tech="python", name="Elias Python")
    await _plant_stored_blank_full_name(svc, item)

    shown = await invoke(["role", "python-dev", "show"])
    assert shown.exit_code == 0, shown.output


async def test_role_regen_tolerates_a_stored_blank_name_on_a_developer_role_before_any_sync(
    project, svc, invoke
):
    item = await svc.activate_role(None, from_template="dev", tech="python", name="Elias Python")
    await _plant_stored_blank_full_name(svc, item)

    regenned = await invoke(["role", "python-dev", "regen"])
    assert regenned.exit_code == 0, regenned.output


async def test_check_stays_clean_with_a_stored_blank_name_on_a_developer_role(project, svc, invoke):
    item = await svc.activate_role(None, from_template="dev", tech="python", name="Elias Python")
    await _plant_stored_blank_full_name(svc, item)

    checked = await invoke(["check"])
    assert checked.exit_code == 0, checked.output


# ------------------------------------------------------------------------ neither remedy is needed


async def test_a_second_sync_is_silent(project, svc, invoke):
    """A second sync makes no further change and reports nothing."""
    item = await svc.activate_role(None, from_template="dev", tech="python", name="Elias Python")
    await _plant_stored_blank_full_name(svc, item)

    first = await invoke(["sync"])
    assert first.exit_code == 0

    second = await invoke(["sync"])
    assert second.exit_code == 0
    assert "python-dev" not in second.output


async def test_the_role_is_never_purged_by_any_of_this(project, svc, invoke):
    """Reading a blank name as unset keeps the role entry; it never discards it."""
    item = await svc.activate_role("qa")
    await _plant_stored_blank_full_name(svc, item)

    await invoke(["sync"])

    roles = await svc.list_items(item_type=ROSTER_ROLE)
    assert any(it.slug == "qa" for it in roles)
