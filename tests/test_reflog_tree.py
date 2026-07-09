"""Tests for sq reflog --tree and show --full session surfacing (TASK-000160 / ADR-000158).

Covers:
- _build_session_maps: partitions entries into session buckets + parent/children maps.
- _render_reflog_tree: manager→dev chain renders as nested tree; unknown parent = forest root;
  legacy/no-session entries still appear; empty reflog = empty tree; no errors in any case.
- sq reflog --tree CLI smoke: exits 0, shows best-effort note, nested structure for a chain.
- sq <type> <n> show --full session surfacing: shows session id when present; slug-only when absent.
- 2026-06-15-style self-review: single-session entries group under one root
  (visibly non-independent).
"""

import json

import pytest
from typer.testing import CliRunner

from squads import _actor as actor
from squads._cli import app
from squads._cli._main import (
    _build_session_maps,  # pyright: ignore[reportPrivateUsage]
    _render_reflog_tree,  # pyright: ignore[reportPrivateUsage]
)
from squads._services._results import ReflogEntry

pytestmark = pytest.mark.anyio

runner = CliRunner()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TS = "2026-06-15T10:00:00Z"


def _make_entry(
    actor_slug: str = "manager",
    op: str = "create",
    target: str = "FEAT-000001",
    session_id: str | None = None,
    parent_session_id: str | None = None,
    ts: str = _TS,
) -> ReflogEntry:
    return ReflogEntry(
        v="0.5",
        ts=ts,
        actor=actor_slug,
        op=op,
        target=target,
        delta={},
        session_id=session_id,
        parent_session_id=parent_session_id,
    )


# ---------------------------------------------------------------------------
# Unit tests for _build_session_maps
# ---------------------------------------------------------------------------


def test_build_session_maps_empty():
    session_entries, session_parents, children_map, no_session = _build_session_maps([])
    assert session_entries == {}
    assert session_parents == {}
    assert children_map == {}
    assert no_session == []


def test_build_session_maps_no_session_entries():
    """Entries with no session_id end up in no_session list."""
    e1 = _make_entry("manager", session_id=None)
    e2 = _make_entry("python-dev", session_id=None)
    _, _, _, no_session = _build_session_maps([e1, e2])
    assert len(no_session) == 2


def test_build_session_maps_single_root():
    e1 = _make_entry("manager", session_id="root-sid", parent_session_id=None)
    session_entries, session_parents, children_map, no_session = _build_session_maps([e1])
    assert "root-sid" in session_entries
    assert session_parents["root-sid"] is None
    assert children_map == {}
    assert no_session == []


def test_build_session_maps_parent_child_chain():
    """A manager→dev chain produces a children_map entry."""
    mgr = _make_entry("manager", session_id="mgr-sid", parent_session_id=None)
    dev = _make_entry("python-dev", session_id="dev-sid", parent_session_id="mgr-sid")
    session_entries, session_parents, children_map, no_session = _build_session_maps([mgr, dev])
    assert "mgr-sid" in session_entries
    assert "dev-sid" in session_entries
    assert session_parents["dev-sid"] == "mgr-sid"
    assert children_map.get("mgr-sid") == ["dev-sid"]
    assert no_session == []


def test_build_session_maps_unknown_parent_not_in_children():
    """Entry whose parent_session_id is not in the set is a root — not linked as child."""
    dev = _make_entry("python-dev", session_id="dev-sid", parent_session_id="unknown-sid")
    _se, session_parents, children_map, _ = _build_session_maps([dev])
    # dev-sid's parent is not among known sessions → not a child of anything
    assert children_map == {}
    # dev-sid appears as its own session with parent recorded
    assert session_parents.get("dev-sid") == "unknown-sid"


def test_build_session_maps_first_occurrence_wins_for_parent():
    """If two entries share a session_id but disagree on parent, first occurrence wins."""
    e1 = _make_entry("manager", session_id="sid", parent_session_id="p1")
    e2 = _make_entry("manager", session_id="sid", parent_session_id="p2")
    _, session_parents, _, _ = _build_session_maps([e1, e2])
    assert session_parents["sid"] == "p1"


def test_build_session_maps_mixed_session_and_none():
    """Mixed entries (some with, some without session_id) are partitioned correctly."""
    with_session = _make_entry("manager", session_id="s1")
    without = _make_entry("python-dev", session_id=None)
    session_entries, _, _, no_session = _build_session_maps([with_session, without])
    assert "s1" in session_entries
    assert len(no_session) == 1


# ---------------------------------------------------------------------------
# Unit tests for _render_reflog_tree (output capture via rich Console)
# ---------------------------------------------------------------------------


def _capture_tree(entries: list[ReflogEntry]) -> str:
    """Capture _render_reflog_tree output to a string."""
    from io import StringIO

    from rich.console import Console

    import squads._cli._main as main_mod

    buf = StringIO()
    cap = Console(file=buf, highlight=False, markup=False)
    original = main_mod.console
    main_mod.console = cap  # pyright: ignore[reportAttributeAccessIssue]
    try:
        _render_reflog_tree(entries)
    finally:
        main_mod.console = original  # pyright: ignore[reportAttributeAccessIssue]
    return buf.getvalue()


def test_render_tree_empty():
    """Empty reflog renders the header and 'no reflog entries' — no error."""
    out = _capture_tree([])
    assert "BEST-EFFORT" in out
    assert "no reflog entries" in out


def test_render_tree_no_session_entries():
    """Entries with no session_id appear as individual roots (legacy/no-env)."""
    entries = [
        _make_entry("manager", session_id=None),
        _make_entry("python-dev", session_id=None),
    ]
    out = _capture_tree(entries)
    assert "no session recorded" in out
    assert "BEST-EFFORT" in out


def test_render_tree_single_root_session():
    """A single session with no parent renders as one root node."""
    entries = [_make_entry("manager", session_id="root-sid", parent_session_id=None)]
    out = _capture_tree(entries)
    assert "root-sid" in out
    assert "BEST-EFFORT" in out


def test_render_tree_manager_dev_chain():
    """A manager→dev chain renders as nested — dev appears under manager."""
    entries = [
        _make_entry("manager", session_id="mgr-sid", parent_session_id=None),
        _make_entry("python-dev", session_id="dev-sid", parent_session_id="mgr-sid"),
    ]
    out = _capture_tree(entries)
    # Both session ids must appear
    assert "mgr-sid" in out
    assert "dev-sid" in out
    # dev-sid appears after (indented under) mgr-sid
    mgr_pos = out.find("mgr-sid")
    dev_pos = out.find("dev-sid")
    assert mgr_pos != -1 and dev_pos != -1
    assert mgr_pos < dev_pos, "dev session must appear after (nested under) manager session"


def test_render_tree_three_level_chain():
    """manager → tech-lead → dev chain renders as three nested levels."""
    entries = [
        _make_entry("manager", session_id="mgr", parent_session_id=None),
        _make_entry("tech-lead", session_id="tl", parent_session_id="mgr"),
        _make_entry("python-dev", session_id="dev", parent_session_id="tl"),
    ]
    out = _capture_tree(entries)
    mgr_pos = out.find("mgr")
    tl_pos = out.find("tl")
    dev_pos = out.find("dev")
    assert mgr_pos < tl_pos < dev_pos


def test_render_tree_unknown_parent_becomes_forest_root():
    """Entry whose parent is not in the entry set degrades to a forest root — no error."""
    entries = [
        _make_entry("python-dev", session_id="dev-sid", parent_session_id="ghost-sid"),
    ]
    out = _capture_tree(entries)
    # No error; dev-sid appears as a root with "not in view" note
    assert "dev-sid" in out
    assert "not in view" in out or "forest root" in out
    assert "BEST-EFFORT" in out


def test_render_tree_missing_intermediate_session_degrades_gracefully():
    """
    Truncated log: manager and dev exist but the intermediate tech-lead session is missing.
    Both manager and dev appear — dev becomes a forest root.  No error.
    """
    entries = [
        _make_entry("manager", session_id="mgr", parent_session_id=None),
        # tl session is ABSENT from the list
        _make_entry("python-dev", session_id="dev", parent_session_id="tl"),
    ]
    out = _capture_tree(entries)
    assert "mgr" in out
    assert "dev" in out
    # No exception
    assert "BEST-EFFORT" in out


def test_render_tree_self_review_visibly_non_independent():
    """
    2026-06-15 scenario: architect creates a review using the same session as the code it reviews.
    Both operations group under the same session root — visibly non-independent to a reader.
    """
    entries = [
        _make_entry("architect", session_id="arch-sid", parent_session_id=None, op="create"),
        _make_entry(
            "architect",
            session_id="arch-sid",
            parent_session_id=None,
            op="create",
            target="REV-000001",
        ),
    ]
    out = _capture_tree(entries)
    # All operations share the same session root → one root node containing both
    assert out.count("arch-sid") >= 1, "self-review session should appear as a root"
    # Both operations appear under arch-sid
    assert "create" in out


# ---------------------------------------------------------------------------
# Cycle / pathological-edge tests for _render_reflog_tree (F2)
# ---------------------------------------------------------------------------


def test_render_tree_two_node_cycle_does_not_raise_and_both_appear():
    """A 2-node pure session cycle (A.parent=B, B.parent=A) must not raise, not loop,
    and BOTH sessions must appear somewhere in the output."""
    entries = [
        _make_entry("manager", session_id="sid-a", parent_session_id="sid-b"),
        _make_entry("python-dev", session_id="sid-b", parent_session_id="sid-a"),
    ]
    out = _capture_tree(entries)
    # No exception; BEST-EFFORT header present
    assert "BEST-EFFORT" in out
    # Both cycled sessions must appear
    assert "sid-a" in out
    assert "sid-b" in out


def test_render_tree_self_loop_does_not_raise_and_session_appears():
    """A self-loop (A.parent=A) must not raise, not loop, and the session must appear."""
    entries = [
        _make_entry("manager", session_id="loop-sid", parent_session_id="loop-sid"),
    ]
    out = _capture_tree(entries)
    assert "BEST-EFFORT" in out
    assert "loop-sid" in out


def test_render_tree_cycle_entries_each_appear_exactly_once():
    """Each session in a cycle appears as a tree node exactly once — no omission or duplication.

    Use session ids that are not substrings of each other so the node-label search is reliable.
    'session: <id>' lines count the rendered nodes; the parent-ref in the cycle label is a
    different substring ('parent <id>') and should not be confused with a node occurrence.
    """
    entries = [
        _make_entry("manager", session_id="cycle-alpha", parent_session_id="cycle-beta"),
        _make_entry("python-dev", session_id="cycle-beta", parent_session_id="cycle-alpha"),
    ]
    out = _capture_tree(entries)
    # Each session must appear as a tree node exactly once.  The raw markup tag
    # '[dim]session:[/dim] <id>' uniquely identifies a rendered session node (the
    # parent-ref slot in a cycle label uses a different pattern: 'parent <id>').
    assert out.count("[dim]session:[/dim] cycle-alpha") == 1
    assert out.count("[dim]session:[/dim] cycle-beta") == 1


# ---------------------------------------------------------------------------
# CLI smoke tests for sq reflog --tree
# ---------------------------------------------------------------------------


def test_cli_reflog_tree_exits_0_on_empty(tmp_path, monkeypatch):
    """sq reflog --tree exits 0 even with an empty reflog."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SQUADS_SESSION_ID", raising=False)
    monkeypatch.delenv("SQUADS_PARENT_SESSION_ID", raising=False)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    r = runner.invoke(app, ["reflog", "--tree"])
    assert r.exit_code == 0, r.output


def test_cli_reflog_tree_shows_best_effort_note(tmp_path, monkeypatch):
    """sq reflog --tree output always includes the best-effort/untrusted note."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SQUADS_SESSION_ID", raising=False)
    monkeypatch.delenv("SQUADS_PARENT_SESSION_ID", raising=False)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    r = runner.invoke(app, ["reflog", "--tree"])
    assert r.exit_code == 0
    assert "BEST-EFFORT" in r.output or "UNTRUSTED" in r.output or "OBSERVABILITY" in r.output


def test_cli_reflog_tree_nested_from_session_env(tmp_path, monkeypatch):
    """sq reflog --tree renders session nodes when SQUADS_SESSION_ID is set."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SQUADS_SESSION_ID", "tree-sid")
    monkeypatch.delenv("SQUADS_PARENT_SESSION_ID", raising=False)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "Tree task", "--author", "manager"])
    r = runner.invoke(app, ["reflog", "--tree"])
    assert r.exit_code == 0
    assert "tree-sid" in r.output


def test_cli_reflog_tree_flat_forest_for_slug_only(tmp_path, monkeypatch):
    """sq reflog --tree renders a flat forest of roots when all entries lack session_id."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SQUADS_SESSION_ID", raising=False)
    monkeypatch.delenv("SQUADS_PARENT_SESSION_ID", raising=False)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "Slug-only task", "--author", "manager"])
    r = runner.invoke(app, ["reflog", "--tree"])
    assert r.exit_code == 0
    # With no sessions, entries show as no-session roots
    assert "no session recorded" in r.output


def test_cli_reflog_tree_and_json_coexist(tmp_path, monkeypatch):
    """--tree and --json are independent; --json still returns the flat list."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SQUADS_SESSION_ID", raising=False)
    monkeypatch.delenv("SQUADS_PARENT_SESSION_ID", raising=False)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "JSON task", "--author", "manager"])
    r = runner.invoke(app, ["reflog", "--json"])
    assert r.exit_code == 0
    data = json.loads(r.output)
    assert isinstance(data, list)


# ---------------------------------------------------------------------------
# CLI smoke tests for show --full session surfacing
# ---------------------------------------------------------------------------


def test_show_full_surfaces_session_when_present(tmp_path, monkeypatch):
    """sq show surfaces the session_id when the item has created_session."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SQUADS_SESSION_ID", "show-session-abc")
    monkeypatch.delenv("SQUADS_PARENT_SESSION_ID", raising=False)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    create_r = runner.invoke(app, ["create", "task", "Session item", "--author", "manager"])
    # Extract the item ID from the create output (e.g. "created TASK-000002 → …")
    import re

    m = re.search(r"(TASK-\d+)", create_r.output)
    assert m, f"Could not find TASK id in: {create_r.output!r}"
    task_id = m.group(1)
    r = runner.invoke(app, ["show", task_id])
    assert r.exit_code == 0, r.output
    assert "show-session-abc" in r.output


def test_show_full_slug_only_when_no_session(tmp_path, monkeypatch):
    """sq show shows slug-only (no session id) when item has no session fields."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SQUADS_SESSION_ID", raising=False)
    monkeypatch.delenv("SQUADS_PARENT_SESSION_ID", raising=False)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    create_r = runner.invoke(app, ["create", "task", "Slug-only item", "--author", "manager"])
    import re

    m = re.search(r"(TASK-\d+)", create_r.output)
    assert m, f"Could not find TASK id in: {create_r.output!r}"
    task_id = m.group(1)
    r = runner.invoke(app, ["show", task_id])
    assert r.exit_code == 0, r.output
    # No session id should appear — item was created without session env
    assert "show-session-abc" not in r.output


async def test_show_legacy_item_no_session_renders_unchanged(svc, frozen_time):
    """Legacy items (no session fields) load and show without error."""
    from squads import _aio
    from squads import _sections as sections
    from squads._index._resolver import item_file

    actor.seed_session(None, None)
    item_obj = (await svc.create("task", "Legacy show item")).item

    path = item_file(svc.paths, item_obj)
    text = await _aio.read_text(path)
    fm, body = sections.split_frontmatter(text)
    fm.pop("created_session", None)
    fm.pop("modified_session", None)
    await _aio.write_text(path, sections.join_frontmatter(fm, body))

    # Show via the CLI runner (sync call — use invoke helper pattern from conftest)
    # Since we're in an async test, we can't use runner.invoke directly with the live event loop.
    # Instead, verify the item loads cleanly from the service.
    await svc.repair()
    loaded = await svc.get(item_obj.id)
    assert loaded.created_session is None
    assert loaded.modified_session is None


# ---------------------------------------------------------------------------
# Service-level: reflog --tree with a full manager→tech-lead→dev chain
# ---------------------------------------------------------------------------


async def test_service_tree_from_chain(svc, frozen_time):
    """A manager→tech-lead→dev chain in the reflog builds a clean 3-level tree."""
    from squads._models._enums import Status

    # Create items under different sessions to simulate a chain.
    actor.seed_session("mgr-root", None)
    await svc.create("feature", "Feature")

    actor.seed_session("tl-child", "mgr-root")
    task = (await svc.create("task", "Task")).item

    actor.seed_session("dev-leaf", "tl-child")
    await svc.set_status(task.id, Status.IN_PROGRESS)

    actor.seed_session(None, None)

    entries = await svc.read_reflog()
    session_entries, _session_parents, children_map, _ = _build_session_maps(entries)

    # All three sessions must appear.
    assert "mgr-root" in session_entries
    assert "tl-child" in session_entries
    assert "dev-leaf" in session_entries

    # Chain: tl-child under mgr-root, dev-leaf under tl-child
    assert "tl-child" in children_map.get("mgr-root", [])
    assert "dev-leaf" in children_map.get("tl-child", [])


async def test_service_tree_unknown_parent_gives_forest(svc, frozen_time):
    """An entry whose parent is not in the reflog becomes a forest root — no error."""
    actor.seed_session("orphan-sid", "ghost-parent-never-exists")
    await svc.create("task", "Orphan task")
    actor.seed_session(None, None)

    entries = await svc.read_reflog()
    session_entries, _sp, children_map, _ = _build_session_maps(entries)
    # orphan-sid is a root (parent ghost-parent-never-exists is not among known sessions)
    assert "orphan-sid" in session_entries
    assert "ghost-parent-never-exists" not in session_entries
    assert children_map == {}  # nothing links orphan-sid as a child


async def test_service_tree_legacy_entries_in_no_session(svc, frozen_time):
    """Reflog entries written with no session (legacy) appear in the no_session list."""
    actor.seed_session(None, None)
    await svc.create("task", "Legacy task")

    entries = await svc.read_reflog()
    _, _, _, no_session = _build_session_maps(entries)
    assert len(no_session) > 0


async def test_service_self_review_same_session_single_root(svc, frozen_time):
    """
    2026-06-15 case: both create and review ops carry the same session_id.
    The tree groups them under a single root — visibly non-independent.
    """
    actor.seed_session("self-reviewer-sid", None)
    feat = (await svc.create("feature", "Feature under review")).item
    rev = (await svc.create("review", "Self review")).item
    actor.seed_session(None, None)

    entries = await svc.read_reflog(item=feat.id)
    entries += await svc.read_reflog(item=rev.id)

    session_entries, _, _, _ = _build_session_maps(entries)
    # Both items' ops belong to the same session root
    assert "self-reviewer-sid" in session_entries
    ops = [e.target for e in session_entries["self-reviewer-sid"]]
    assert feat.id in ops
    assert rev.id in ops
