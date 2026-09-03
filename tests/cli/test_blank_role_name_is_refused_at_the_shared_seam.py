"""A blank/whitespace-only operator-supplied ``--name`` is refused on both roster-creating CLI
commands, driven through the actual command wiring.

Both ``sq dev add --name`` and ``sq role activate --name`` build a ``RoleDef`` directly (never
through ``.overrides/roles/<slug>.toml``'s ``_apply_override``/``_refuse_blank_strings``), so the
override path's existing blank-string refusal never used to fire for either of them. The fix is
a single seam both converge on (``RoleDef.__post_init__``) rather than a check copied at each call
site -- see ``tests/unit/test_role_def_refuses_a_blank_full_name.py`` for that seam pinned
directly.

Both empty (``""``) and whitespace-only (``"   "``) are driven on both commands separately: the
two commands did not agree on what an empty string did before this fix (``dev_role`` tested
``if name:``, falling through to a pool name; ``activate_role`` tested ``if name is not None:``,
which did not), so the empty case is not safe to generalise from the whitespace case or from one
command to the other.
"""

import pytest

from squads._models._extras import ExtraKey as X
from squads._workflow import ROSTER_ROLE

pytestmark = pytest.mark.anyio


async def _no_role_for_slug(svc, slug: str) -> bool:
    from squads._models._extras import ExtraKey as X

    roles = await svc.list_items(item_type=ROSTER_ROLE)
    return not any(it.extra.get(X.SLUG) == slug for it in roles)


# --------------------------------------------------------------------------------------- dev add


@pytest.mark.parametrize("blank", ["", "   "], ids=["empty", "whitespace"])
async def test_dev_add_refuses_a_blank_name(project, svc, invoke, blank):
    r = await invoke(["dev", "add", "--tech", "go", "--name", blank])

    assert r.exit_code != 0
    assert "full_name" in r.output
    assert await _no_role_for_slug(svc, "go-dev")
    assert not (project.root / ".claude" / "agents" / "go-dev.md").is_file()


# ----------------------------------------------------------------------------------- role activate


@pytest.mark.parametrize("blank", ["", "   "], ids=["empty", "whitespace"])
async def test_role_activate_refuses_a_blank_name(project, svc, invoke, blank):
    r = await invoke(["role", "activate", "architect", "--name", blank])

    assert r.exit_code != 0
    assert "full_name" in r.output
    assert await _no_role_for_slug(svc, "architect")
    assert not (project.root / ".claude" / "agents" / "architect.md").is_file()


# ------------------------------------------------------------------ sq check stays clean


async def test_sq_check_is_clean_after_a_refused_blank_name_on_both_commands(project, invoke):
    await invoke(["dev", "add", "--tech", "go", "--name", "   "])
    await invoke(["role", "activate", "architect", "--name", ""])

    checked = await invoke(["check"])
    assert checked.exit_code == 0


# -------------------------------------------------------------- a real name still works


async def test_dev_add_with_internal_whitespace_still_works(project, svc, invoke):
    r = await invoke(["dev", "add", "--tech", "go", "--name", "Ada Lovelace"])
    assert r.exit_code == 0

    roles = await svc.list_items(item_type=ROSTER_ROLE)
    dev = next(it for it in roles if it.extra.get(X.SLUG) == "go-dev")
    assert dev.title == "Ada Lovelace"


async def test_role_activate_with_internal_whitespace_still_works(project, svc, invoke):
    r = await invoke(["role", "activate", "architect", "--name", "Ada Lovelace"])
    assert r.exit_code == 0

    role = await svc.roster_item(ROSTER_ROLE, "architect")
    assert role is not None
    assert role.title == "Ada Lovelace"


async def test_leading_and_trailing_whitespace_around_real_content_is_preserved_not_trimmed(
    project, svc, invoke
):
    """Decision: a name that is blank/whitespace-only is refused, but padding around real
    content is accepted *as-is* -- the same choice the override path's own
    ``_refuse_blank_strings`` already makes (it only ``.strip()``s to test for blankness, never
    to normalise a stored value)."""
    r = await invoke(["role", "activate", "qa", "--name", "  Ada Lovelace  "])
    assert r.exit_code == 0

    role = await svc.roster_item(ROSTER_ROLE, "qa")
    assert role is not None
    assert role.title == "  Ada Lovelace  "
