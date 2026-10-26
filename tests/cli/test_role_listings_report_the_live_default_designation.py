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

from squads._rendering._engine import invalidate_squad_dir

pytestmark = pytest.mark.anyio


async def _make_ghost_the_default(project, svc, invoke) -> None:
    """Create a role no catalog entry, template or stored definition backs and designate it: a
    live holder that matches no catalog row."""
    await svc.create("role", "Gwen Ghost", description="A ghost.", slug="ghost", author="ghost")
    assert (await invoke(["role", "ghost", "set-default"])).exit_code == 0
    invalidate_squad_dir(project.squad_dir)


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


async def test_a_holder_the_document_does_not_declare_has_its_own_marked_catalog_row(
    project, svc, invoke
) -> None:
    """A role whose definition is gone is not in the catalog document, and still gets the
    row that carries the designation."""
    await _make_ghost_the_default(project, svc, invoke)

    assert await _designations(invoke, ["role", "catalog"]) == {"ghost"}
    plain = await invoke(["role", "catalog"])
    assert "✓" in _catalog_row(plain.output, "ghost")
    assert "✓" not in _catalog_row(plain.output, "manager")

    for maintenance in (["sync"], ["repair"]):
        assert (await invoke(maintenance)).exit_code == 0
        assert await _designations(invoke, ["role", "catalog"]) == {"ghost"}


async def test_a_developer_holding_the_designation_has_its_own_marked_catalog_row(
    project, invoke
) -> None:
    assert (await invoke(["dev", "add", "--tech", "python"])).exit_code == 0
    assert (await invoke(["role", "python-dev", "set-default"])).exit_code == 0

    assert await _designations(invoke, ["role", "catalog"]) == {"python-dev"}
    plain = await invoke(["role", "catalog"])
    assert "✓" in _catalog_row(plain.output, "python-dev")
    assert "✓" not in _catalog_row(plain.output, "manager")


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


async def test_the_catalog_payload_names_the_holder_and_a_row_carries_it(
    project, svc, invoke
) -> None:
    assert await _disclosure(invoke) == ("manager", "roster")

    await _make_ghost_the_default(project, svc, invoke)

    assert await _disclosure(invoke) == ("ghost", "roster")
    assert await _designations(invoke, ["role", "catalog"]) == {"ghost"}


async def test_the_catalog_payload_tells_an_held_holder_from_no_holder(project, invoke) -> None:
    """A live holder and no live holder at all are told apart on the wire."""
    assert (await invoke(["dev", "add", "--tech", "python"])).exit_code == 0
    assert (await invoke(["role", "python-dev", "set-default"])).exit_code == 0
    held = await invoke(["role", "catalog", "--json"])
    assert await _disclosure(invoke) == ("python-dev", "roster")

    assert (await invoke(["role", "python-dev", "status", "Archived"])).exit_code == 0
    unheld = await invoke(["role", "catalog", "--json"])
    assert await _designations(invoke, ["role", "catalog"]) == set()
    assert await _disclosure(invoke) == (None, "roster")

    assert json.loads(held.output) != json.loads(unheld.output), (
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
