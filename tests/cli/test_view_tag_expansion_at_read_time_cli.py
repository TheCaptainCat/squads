"""``sq <type> <n> show``/``--raw``/``--json`` all inherit read-time view-tag expansion from
the one shared body-read boundary (``Service.read_body``) — no per-surface reimplementation.
Service-level table-driven coverage (position/shape, the two failure modes, no-recursion, the
read-only round trip) lives in
``tests/service/test_view_tag_expansion_at_read_time.py``; the TUI reader's inheritance is
covered in ``tests/tui/test_reader_screen.py``. This file drives the same mechanism through
each CLI surface end to end.
"""

import json

import pytest

from squads import __version__

pytestmark = pytest.mark.anyio

_BUNDLED_VIEW = "milestone_rollup"


async def test_show_raw_renders_the_view_in_place_of_the_tag(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    await invoke(["task", "2", "view", "add", _BUNDLED_VIEW])

    shown = await invoke(["task", "2", "show", "--raw"])

    assert shown.exit_code == 0, shown.output
    assert f"sq:view:{_BUNDLED_VIEW}" not in shown.output  # literal tag is gone
    assert "Outstanding" in shown.output  # the roll-up's own rendered heading is there instead


async def test_show_styled_renders_the_view_in_place_of_the_tag(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    await invoke(["task", "2", "view", "add", _BUNDLED_VIEW])

    shown = await invoke(["task", "2", "show"])

    assert shown.exit_code == 0, shown.output
    assert f"sq:view:{_BUNDLED_VIEW}" not in shown.output
    assert "Outstanding" in shown.output


async def test_show_json_body_field_carries_the_expanded_text_not_the_literal_tag(
    project, invoke
) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    await invoke(["task", "2", "view", "add", _BUNDLED_VIEW])

    shown = await invoke(["task", "2", "show", "--json"])

    assert shown.exit_code == 0, shown.output
    body = json.loads(shown.output)["body"]
    assert f"sq:view:{_BUNDLED_VIEW}" not in body
    assert "Outstanding" in body


async def test_a_body_with_no_tag_shows_unchanged_across_every_surface(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    await invoke(["task", "2", "body", "-m", "Plain prose, nothing marker-shaped."])

    raw = await invoke(["task", "2", "show", "--raw"])
    styled = await invoke(["task", "2", "show"])
    as_json = await invoke(["task", "2", "show", "--json"])

    assert "Plain prose, nothing marker-shaped." in raw.output
    assert "Plain prose, nothing marker-shaped." in styled.output
    assert json.loads(as_json.output)["body"] == "Plain prose, nothing marker-shaped."


async def test_a_dangling_view_name_stays_literal_and_show_still_exits_zero(
    project, invoke
) -> None:
    """Hand-editing the file to carry an undeclared name (the placement verb itself refuses
    one — see ``tests/cli/test_view_tag_placement_cli.py``) exercises the read path's own half
    of the two-failure-mode split: the read must keep working on a broken corpus."""
    await invoke(["create", "task", "T", "--author", "manager"])
    md = next(iter((project.squad_dir / "tasks").glob("TASK-*.md")))
    text = md.read_text(encoding="utf-8")
    md.write_text(
        text.replace("<!-- sq:body -->", "<!-- sq:body -->\n<!-- sq:view:no-such-view -->"),
        encoding="utf-8",
    )

    shown = await invoke(["task", "2", "show", "--raw"])

    assert shown.exit_code == 0, shown.output
    assert "sq:view:no-such-view" in shown.output  # stays literal


async def test_a_source_incompatible_view_tag_stays_literal_and_show_still_exits_zero(
    project, invoke
) -> None:
    """Driven end to end through the CLI: ``sq epic <n> show --raw`` on an item carrying a
    ``subentity``-source view tag its type doesn't host exits 0 with the tag left
    byte-for-byte literal, exactly like the dangling-name case above."""
    override_dir = project.squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    templates_dir = override_dir / "templates" / "views"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "story_board.md.j2").write_text("story board\n", encoding="utf-8")
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n"
        '[views.story_board]\nsource = { kind = "subentity", name = "story" }\n'
        'fields = [ { code = "id", label = "Id" } ]\n',
        encoding="utf-8",
    )

    await invoke(["create", "epic", "An epic", "--author", "manager"])
    md = next(iter((project.squad_dir / "epics").glob("EPIC-*.md")))
    text = md.read_text(encoding="utf-8")
    md.write_text(
        text.replace("<!-- sq:body -->", "<!-- sq:body -->\n<!-- sq:view:story_board -->"),
        encoding="utf-8",
    )

    shown = await invoke(["epic", "2", "show", "--raw"])

    assert shown.exit_code == 0, shown.output
    assert "sq:view:story_board" in shown.output  # stays literal, byte for byte
    as_json = await invoke(["epic", "2", "show", "--json"])
    assert as_json.exit_code == 0, as_json.output


async def test_a_declared_views_template_failure_exits_nonzero_with_a_clean_message(
    project, invoke
) -> None:
    override_dir = project.squad_dir / ".overrides"
    (override_dir / "templates" / "views").mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n"
        '[views.broken_view]\nsource = { kind = "subentity", name = "subtask" }\n'
        'fields = [ { code = "id", label = "Id" } ]\n',
        encoding="utf-8",
    )
    (override_dir / "templates" / "views" / "broken_view.md.j2").write_text(
        "{{ this_is_not_defined_anywhere }}\n", encoding="utf-8"
    )
    await invoke(["create", "task", "T", "--author", "manager"])
    added = await invoke(["task", "2", "view", "add", "broken_view"])
    assert added.exit_code == 0, added.output

    shown = await invoke(["task", "2", "show", "--raw"])

    assert shown.exit_code == 1
    assert "broken_view" in shown.output
