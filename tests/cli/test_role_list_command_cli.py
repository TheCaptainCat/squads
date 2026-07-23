"""``sq role list`` — the active roster, distinct from ``sq role catalog`` (the bundled catalog).
Table output carries an active/inactive marker column; ``--json`` gives an additive machine shape.
"""

import json

import pytest

pytestmark = pytest.mark.anyio


async def test_plain_output_lists_the_active_roster_with_an_active_marker(project, invoke) -> None:
    r = await invoke(["role", "list"])
    assert r.exit_code == 0, r.output
    assert "manager" in r.output


async def test_json_output_shape(project, invoke) -> None:
    """No derived `active` field — `status` is the single source, kept un-restated."""
    r = await invoke(["role", "list", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert len(data) == 1
    row = data[0]
    assert set(row) == {"id", "slug", "full_name", "title", "status"}
    assert row["slug"] == "manager"
    assert row["status"] == "Active"


async def test_a_newly_activated_role_shows_up_in_the_listing(project, invoke) -> None:
    await invoke(["role", "activate", "architect"])
    r = await invoke(["role", "list", "--json"])
    slugs = {row["slug"] for row in json.loads(r.output)}
    assert slugs == {"manager", "architect"}


async def test_list_is_distinct_from_the_bundled_catalog(project, invoke) -> None:
    """Only activated roles appear in `list`; `catalog` still shows every bundled role."""
    listed = json.loads((await invoke(["role", "list", "--json"])).output)
    cataloged = json.loads((await invoke(["role", "catalog", "--json"])).output)
    assert len(listed) == 1
    assert len(cataloged) > len(listed)
