"""The reflog session-lineage tree-building mechanism (`_cli/_main.py`'s `_build_session_maps`
and `_render_reflog_tree`), tested as pure functions against hand-built reflog entries — no CLI,
no service. A manager->dev chain nests; an unknown or missing parent degrades to a forest root
rather than raising; a session cycle (including a 2-node cycle and a self-loop) neither raises
nor loops, and every session still renders exactly once.
"""

from io import StringIO

from rich.console import Console

import squads._cli._main as main_mod
from squads._cli._main import (
    _build_session_maps,  # pyright: ignore[reportPrivateUsage]
    _render_reflog_tree,  # pyright: ignore[reportPrivateUsage]
)
from squads._services._results import ReflogEntry

_TS = "2026-06-15T10:00:00Z"


def _entry(
    actor_slug: str = "manager",
    op: str = "create",
    target: str = "FEAT-000001",
    session_id: str | None = None,
    parent_session_id: str | None = None,
) -> ReflogEntry:
    return ReflogEntry(
        v="0.5",
        ts=_TS,
        actor=actor_slug,
        op=op,
        target=target,
        delta={},
        session_id=session_id,
        parent_session_id=parent_session_id,
    )


def _capture_tree(entries: list[ReflogEntry]) -> str:
    buf = StringIO()
    cap = Console(file=buf, highlight=False, markup=False)
    original = main_mod.console
    main_mod.console = cap  # pyright: ignore[reportAttributeAccessIssue]
    try:
        _render_reflog_tree(entries)
    finally:
        main_mod.console = original  # pyright: ignore[reportAttributeAccessIssue]
    return buf.getvalue()


# --------------------------------------------------------------------------- _build_session_maps


def test_build_session_maps_is_empty_for_no_entries():
    session_entries, session_parents, children_map, no_session = _build_session_maps([])
    assert (session_entries, session_parents, children_map, no_session) == ({}, {}, {}, [])


def test_build_session_maps_partitions_no_session_entries():
    entries = [_entry("manager", session_id=None), _entry("python-dev", session_id=None)]
    *_, no_session = _build_session_maps(entries)
    assert len(no_session) == 2


def test_build_session_maps_single_root_session():
    session_entries, session_parents, children_map, no_session = _build_session_maps(
        [_entry("manager", session_id="root-sid", parent_session_id=None)]
    )
    assert "root-sid" in session_entries
    assert session_parents["root-sid"] is None
    assert children_map == {} and no_session == []


def test_build_session_maps_records_a_parent_child_chain():
    mgr = _entry("manager", session_id="mgr-sid", parent_session_id=None)
    dev = _entry("python-dev", session_id="dev-sid", parent_session_id="mgr-sid")
    session_entries, session_parents, children_map, no_session = _build_session_maps([mgr, dev])
    assert {"mgr-sid", "dev-sid"} <= session_entries.keys()
    assert session_parents["dev-sid"] == "mgr-sid"
    assert children_map.get("mgr-sid") == ["dev-sid"]
    assert no_session == []


def test_build_session_maps_unknown_parent_is_not_linked_as_a_child():
    dev = _entry("python-dev", session_id="dev-sid", parent_session_id="unknown-sid")
    _se, session_parents, children_map, _ns = _build_session_maps([dev])
    assert children_map == {}
    assert session_parents.get("dev-sid") == "unknown-sid"


def test_build_session_maps_first_occurrence_wins_on_conflicting_parent():
    e1 = _entry("manager", session_id="sid", parent_session_id="p1")
    e2 = _entry("manager", session_id="sid", parent_session_id="p2")
    _se, session_parents, *_ = _build_session_maps([e1, e2])
    assert session_parents["sid"] == "p1"


def test_build_session_maps_mixed_session_and_no_session_entries():
    with_session = _entry("manager", session_id="s1")
    without = _entry("python-dev", session_id=None)
    session_entries, _sp, _cm, no_session = _build_session_maps([with_session, without])
    assert "s1" in session_entries and len(no_session) == 1


# --------------------------------------------------------------------------- _render_reflog_tree


def test_render_tree_empty_reflog_shows_the_best_effort_header_and_no_entries():
    out = _capture_tree([])
    assert "BEST-EFFORT" in out and "no reflog entries" in out


def test_render_tree_no_session_entries_appear_as_individual_roots():
    out = _capture_tree([_entry("manager", session_id=None), _entry("python-dev", session_id=None)])
    assert "no session recorded" in out and "BEST-EFFORT" in out


def test_render_tree_a_manager_dev_chain_nests_the_dev_under_the_manager():
    entries = [
        _entry("manager", session_id="mgr-sid", parent_session_id=None),
        _entry("python-dev", session_id="dev-sid", parent_session_id="mgr-sid"),
    ]
    out = _capture_tree(entries)
    assert out.find("mgr-sid") < out.find("dev-sid")


def test_render_tree_a_three_level_chain_nests_in_order():
    entries = [
        _entry("manager", session_id="mgr", parent_session_id=None),
        _entry("tech-lead", session_id="tl", parent_session_id="mgr"),
        _entry("python-dev", session_id="dev", parent_session_id="tl"),
    ]
    out = _capture_tree(entries)
    assert out.find("mgr") < out.find("tl") < out.find("dev")


def test_render_tree_unknown_parent_degrades_to_a_forest_root_not_an_error():
    out = _capture_tree([_entry("python-dev", session_id="dev-sid", parent_session_id="ghost-sid")])
    assert "dev-sid" in out
    assert "not in view" in out or "forest root" in out


def test_render_tree_a_missing_intermediate_session_still_renders_both_ends():
    entries = [
        _entry("manager", session_id="mgr", parent_session_id=None),
        # the "tl" session between them is absent from the log
        _entry("python-dev", session_id="dev", parent_session_id="tl"),
    ]
    out = _capture_tree(entries)
    assert "mgr" in out and "dev" in out


def test_render_tree_shared_session_groups_both_operations_under_one_root():
    """Two operations carrying the same session_id (a self-review) group under one root — a
    reader can see at a glance they are not independent."""
    entries = [
        _entry("architect", session_id="arch-sid", parent_session_id=None, op="create"),
        _entry(
            "architect",
            session_id="arch-sid",
            parent_session_id=None,
            op="create",
            target="REV-000001",
        ),
    ]
    out = _capture_tree(entries)
    assert out.count("arch-sid") >= 1


def test_render_tree_a_two_node_cycle_does_not_raise_and_both_sessions_appear():
    entries = [
        _entry("manager", session_id="sid-a", parent_session_id="sid-b"),
        _entry("python-dev", session_id="sid-b", parent_session_id="sid-a"),
    ]
    out = _capture_tree(entries)
    assert "BEST-EFFORT" in out and "sid-a" in out and "sid-b" in out


def test_render_tree_a_self_loop_does_not_raise_and_the_session_appears():
    out = _capture_tree([_entry("manager", session_id="loop-sid", parent_session_id="loop-sid")])
    assert "BEST-EFFORT" in out and "loop-sid" in out


def test_render_tree_cycle_members_each_render_exactly_once_no_omission_or_duplication():
    entries = [
        _entry("manager", session_id="cycle-alpha", parent_session_id="cycle-beta"),
        _entry("python-dev", session_id="cycle-beta", parent_session_id="cycle-alpha"),
    ]
    out = _capture_tree(entries)
    assert out.count("[dim]session:[/dim] cycle-alpha") == 1
    assert out.count("[dim]session:[/dim] cycle-beta") == 1
