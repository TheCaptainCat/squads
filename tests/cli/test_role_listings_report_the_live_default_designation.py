"""The default-role designation as the two role listings report it.

``sq role <addr> set-default`` moves the designation onto a live roster item. The catalog
listing is scoped to the active squad ("...for the active squad", its own help), so its
``Default`` column has to answer with the squad's designation rather than the bundled
catalog's shipped one — the same answer ``sq role <slug> show --json`` and the compiled
default-role line already give. The roster listing carries the designation too, and is the
only one of the two that can name *every* holder: a developer role has a roster entry and no
catalog row.

The catalog's boolean column can only answer for the rows it has, so on its own an all-false
payload maps three different squads onto one answer. ``default_role`` /
``default_role_source`` carry the holder itself, and the tests below pin the four states
apart from each other on the wire rather than only in the rendering — the whole point of the
disclosure is that the mode a program reads carries it too.
"""

import json

import pytest

pytestmark = pytest.mark.anyio


def _catalog_row(output: str, slug: str) -> str:
    """The plain-table line for *slug*, from a catalog/roster listing."""
    return next(ln for ln in output.splitlines() if ln.split()[:1] == [slug])


async def _disclosure(invoke) -> tuple[str | None, str]:
    """The holder ``sq role catalog --json`` discloses, and where that answer came from.

    Asserted uniform across rows first: the payload is a bare array, so the disclosure repeats
    on every row and a consumer reading any single row must get the same answer.
    """
    r = await invoke(["role", "catalog", "--json"])
    assert r.exit_code == 0, r.output
    rows = json.loads(r.output)
    assert rows, "an empty catalog would make every assertion below vacuous"
    answers = {(row["default_role"], row["default_role_source"]) for row in rows}
    assert len(answers) == 1, f"the disclosure varies by row: {answers}"
    return next(iter(answers))


async def _designations(invoke, args: list[str]) -> set[str]:
    """The slugs a ``--json`` listing marks as holding the designation."""
    r = await invoke([*args, "--json"])
    assert r.exit_code == 0, r.output
    return {row["slug"] for row in json.loads(r.output) if row["is_default"]}


async def test_the_catalog_default_column_follows_a_move_to_a_bundled_role(project, invoke) -> None:
    assert await _designations(invoke, ["role", "catalog"]) == {"manager"}

    assert (await invoke(["role", "activate", "qa"])).exit_code == 0
    r = await invoke(["role", "qa", "set-default"])
    assert r.exit_code == 0, r.output

    assert await _designations(invoke, ["role", "catalog"]) == {"qa"}
    plain = await invoke(["role", "catalog"])
    assert plain.exit_code == 0, plain.output
    assert "✓" in _catalog_row(plain.output, "qa")
    assert "✓" not in _catalog_row(plain.output, "manager")


async def test_the_catalog_default_column_survives_sync_and_repair(project, invoke) -> None:
    """The designation lives in frontmatter; neither regeneration nor an index rebuild may
    put the listing back on the catalog's shipped answer."""
    assert (await invoke(["role", "activate", "qa"])).exit_code == 0
    assert (await invoke(["role", "qa", "set-default"])).exit_code == 0

    for maintenance in (["sync"], ["repair"]):
        r = await invoke(maintenance)
        assert r.exit_code == 0, r.output
        assert await _designations(invoke, ["role", "catalog"]) == {"qa"}


async def test_a_developer_role_holding_the_designation_leaves_no_catalog_row_marked(
    project, invoke
) -> None:
    """A developer role has no catalog row, so the honest catalog answer is "none of these" —
    never the shipped designation on a role that no longer holds it. The plain listing names
    the holder it cannot show."""
    assert (await invoke(["dev", "add", "--tech", "python"])).exit_code == 0
    r = await invoke(["role", "python-dev", "set-default"])
    assert r.exit_code == 0, r.output

    assert await _designations(invoke, ["role", "catalog"]) == set()
    plain = await invoke(["role", "catalog"])
    assert "✓" not in _catalog_row(plain.output, "manager")
    assert "python-dev" in plain.output

    for maintenance in (["sync"], ["repair"]):
        assert (await invoke(maintenance)).exit_code == 0
        assert await _designations(invoke, ["role", "catalog"]) == set()


async def test_the_roster_listing_names_the_holder_for_a_bundled_and_a_developer_role(
    project, invoke
) -> None:
    assert await _designations(invoke, ["role", "list"]) == {"manager"}

    assert (await invoke(["role", "activate", "qa"])).exit_code == 0
    assert (await invoke(["role", "qa", "set-default"])).exit_code == 0
    assert await _designations(invoke, ["role", "list"]) == {"qa"}

    assert (await invoke(["dev", "add", "--tech", "python"])).exit_code == 0
    assert (await invoke(["role", "python-dev", "set-default"])).exit_code == 0
    assert await _designations(invoke, ["role", "list"]) == {"python-dev"}

    plain = await invoke(["role", "list"])
    assert plain.exit_code == 0, plain.output
    assert "Default" in plain.output
    assert "✓" in _catalog_row(plain.output, "python-dev")

    for maintenance in (["sync"], ["repair"]):
        assert (await invoke(maintenance)).exit_code == 0
        assert await _designations(invoke, ["role", "list"]) == {"python-dev"}


async def test_outside_a_squad_the_catalog_reports_its_own_declared_designation(
    tmp_path, monkeypatch, invoke
) -> None:
    """With no roster to ask, the catalog document's own designation is the honest answer —
    and the listing still works at all, as it always has outside a squad."""
    monkeypatch.chdir(tmp_path)
    assert await _designations(invoke, ["role", "catalog"]) == {"manager"}


async def test_the_catalog_payload_names_a_holder_that_matches_no_row(project, invoke) -> None:
    """The footer's disclosure, on the wire: a developer role holds it, no row can be marked,
    and the payload names the holder anyway — a program branching on the boolean alone would
    read "nobody is the default here", which is false."""
    assert await _disclosure(invoke) == ("manager", "roster")

    assert (await invoke(["dev", "add", "--tech", "python"])).exit_code == 0
    assert (await invoke(["role", "python-dev", "set-default"])).exit_code == 0

    assert await _designations(invoke, ["role", "catalog"]) == set()
    holder, source = await _disclosure(invoke)
    assert (holder, source) == ("python-dev", "roster")

    r = await invoke(["role", "catalog", "--json"])
    assert all(row["slug"] != holder for row in json.loads(r.output)), (
        "the point of the field is that the holder need not be one of the rows"
    )


async def test_the_catalog_payload_tells_an_unshowable_holder_from_no_holder(
    project, invoke
) -> None:
    """The two states the boolean column collapses: a holder this listing cannot show, and no
    live holder at all. Both leave every row false; only the disclosure separates them."""
    assert (await invoke(["dev", "add", "--tech", "python"])).exit_code == 0
    assert (await invoke(["role", "python-dev", "set-default"])).exit_code == 0
    unshowable = await invoke(["role", "catalog", "--json"])
    assert await _disclosure(invoke) == ("python-dev", "roster")

    assert (await invoke(["role", "python-dev", "status", "Archived"])).exit_code == 0
    none_live = await invoke(["role", "catalog", "--json"])
    assert await _designations(invoke, ["role", "catalog"]) == set()
    assert await _disclosure(invoke) == (None, "roster")

    assert json.loads(unshowable.output) != json.loads(none_live.output), (
        "two different squad states must not produce one payload"
    )


async def test_outside_a_squad_the_catalog_payload_marks_its_answer_a_fallback(
    project, invoke, tmp_path_factory, monkeypatch
) -> None:
    """Outside a squad there is no roster to ask and the catalog document's own declaration is
    the honest answer — but on the wire it is otherwise identical to a squad that designates
    the same slug for real, so the payload says which it is.

    The second directory comes from ``tmp_path_factory`` rather than ``tmp_path``: the
    ``project`` fixture's squad *is* ``tmp_path``, so chdir'ing there stays inside a squad and
    the test would pass on the in-squad answer without ever reaching the fallback.
    """
    assert await _disclosure(invoke) == ("manager", "roster")

    monkeypatch.chdir(tmp_path_factory.mktemp("outside-any-squad"))
    assert await _designations(invoke, ["role", "catalog"]) == {"manager"}
    assert await _disclosure(invoke) == ("manager", "catalog")
