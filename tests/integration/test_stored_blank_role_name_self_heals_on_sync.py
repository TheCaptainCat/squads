"""The corpus-level counterpart the reviewer flagged as missing: neither existing blank-name
test file (``tests/unit/test_role_def_refuses_a_blank_full_name.py``,
``tests/cli/test_blank_role_name_is_refused_at_the_shared_seam.py``) drives a role item whose
*stored* ``full_name`` is already blank -- only the input side (an operator's raw CLI string).

A squad synced on v0.13.0 could reach exactly that state: that release's ``sq dev add --tech
python --name "   "`` and ``sq role activate <slug> --name "   "`` both succeeded at exit 0, and
the value survived repeated syncs with ``sq check`` reporting no issues throughout. This file
plants that same shape directly into a current-release squad's frontmatter *and* index --
bypassing every input-side refusal this release added, the only way left to reconstruct a fact
an earlier release wrote and called healthy -- then drives every surface that reads it.

Both role shapes are covered, because they fail through different code
(``squads._roles._resolver.role_base_from_item`` for a bundled role,
``squads._roles._resolver.dev_base_from_item`` for a developer role) and a fix to one does not
imply the other is fixed.
"""

import pytest

from squads import _sections as sections
from squads._itemfile import read_frontmatter
from squads._models._extras import ExtraKey as X
from squads._workflow import ROSTER_ROLE

pytestmark = pytest.mark.anyio


async def _plant_stored_blank_full_name(svc, item) -> None:
    """Overwrite ``title``/``extra.full_name`` with a whitespace-only value on BOTH the
    frontmatter file and the index -- directly, bypassing the service entirely. This is not a
    mutation any current-release command can produce (every input boundary now refuses it); it
    reconstructs the one a past release already wrote to disk and called healthy.
    """
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
    """The role's stored name, read where it lives: the item's own ``title`` field. The
    ``extra.full_name`` copy the planting helper still writes is what a pre-0.14 corpus
    carries, and nothing reads it."""
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
    """Once ``sq sync`` has healed the stored value, the corpus is ordinary again -- a
    following sync makes no further change and reports nothing about this role."""
    item = await svc.add_dev("python", name="Elias Python")
    await _plant_stored_blank_full_name(svc, item)

    first = await invoke(["sync"])
    assert first.exit_code == 0

    second = await invoke(["sync"])
    assert second.exit_code == 0
    assert "python-dev" not in second.output


async def test_the_role_is_never_purged_by_any_of_this(project, svc, invoke):
    """The only documented remedy before this fix was ``sq role <slug> rm --purge``. After the
    fix, the role must still be there -- self-healing recovers the entry, it does not discard
    it."""
    item = await svc.activate_role("qa")
    await _plant_stored_blank_full_name(svc, item)

    await invoke(["sync"])

    roles = await svc.list_items(item_type=ROSTER_ROLE)
    assert any(it.extra.get(X.SLUG) == "qa" for it in roles)
