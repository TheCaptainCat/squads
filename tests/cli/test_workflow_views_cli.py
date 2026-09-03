"""``sq workflow views`` (the catalog) and ``sq workflow view <name> <id>`` (resolve one).

Default prints a human Rich table; ``--json`` emits the catalog / the projection. The
byte-identical golden for the catalog (one bundled row, ``milestone_rollup``) is pinned in
``tests/cli/test_json_output_shape.py`` (``tests/goldens/workflow_views.json``); this module
covers the field-set contract, the human table, and every declared-view/resolve/override path
via an override-declared view.
"""

import json
from pathlib import Path

import pytest

from squads import __version__
from squads._cli._workflow_cmd import VIEW_CATALOG_FIELDS, _view_catalog
from squads._rendering._engine import invalidate_squad_dir
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio


async def _review_with_a_finding(invoke) -> str:
    r = await invoke(["create", "review", "A review", "--author", "manager"])
    assert r.exit_code == 0
    item_id = r.output.split("→")[0].removeprefix("created").strip()
    r = await invoke(["review", item_id, "add-finding", "A finding", "--severity", "high"])
    assert r.exit_code == 0
    return item_id


def _write_workflow_override(squad_dir: Path, body: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{body}", encoding="utf-8"
    )
    invalidate_squad_dir(squad_dir)


_FINDING_FIELDS = (
    '[[views.{name}.fields]]\ncode = "id"\nlabel = "Finding"\n\n'
    '[[views.{name}.fields]]\ncode = "status"\nlabel = "Status"\n\n'
    '[[views.{name}.fields]]\ncode = "assignee"\nlabel = "Assignee"\n\n'
    '[[views.{name}.fields]]\ncode = "title"\nlabel = "Title"\n'
)


def _declare_finding_view(squad_dir: Path, name: str) -> None:
    """A subentity-source view over ``finding``, named to match one of the two bundled
    presentation templates so resolving it exercises the real bundled ``.md.j2`` file."""
    _write_workflow_override(
        squad_dir,
        f'[views.{name}]\nsource = {{ kind = "subentity", name = "finding" }}\n\n'
        + _FINDING_FIELDS.format(name=name),
    )


# ─── sq workflow views (catalog) ─────────────────────────────────────────────────


async def test_the_default_catalog_carries_only_the_bundled_milestone_rollup(
    project, invoke
) -> None:
    """``milestone_rollup`` is the one bundled view (attached to ``items.milestone.views``);
    every other bundled type declares none, and an override-declared view is proven separately
    below rather than by asserting the catalog stays empty."""
    result = await invoke(["workflow", "views", "--json"])
    assert result.exit_code == 0
    rows = json.loads(result.output)
    assert [r["view"] for r in rows] == ["milestone_rollup"]


async def test_default_output_is_a_human_table_with_every_declared_view(project, invoke) -> None:
    _declare_finding_view(project.squad_dir, "finding_summary")
    result = await invoke(["workflow", "views"])
    assert result.exit_code == 0
    for col in ("View", "Source kind", "Source name", "Fields", "Group by"):
        assert col in result.output
    assert "finding_summary" in result.output


async def test_json_emits_a_bare_array_in_ascending_view_name_order(project, invoke) -> None:
    _declare_finding_view(project.squad_dir, "finding_summary")
    _write_workflow_override(
        project.squad_dir,
        '[views.finding_summary]\nsource = { kind = "subentity", name = "finding" }\n\n'
        + _FINDING_FIELDS.format(name="finding_summary")
        + '\n[views.abc_first]\nsource = { kind = "ref", name = "related" }\n'
        'fields = [ { code = "id", label = "Id" } ]\n',
    )
    result = await invoke(["workflow", "views", "--json"])
    assert result.exit_code == 0
    rows = json.loads(result.output)
    names = [r["view"] for r in rows]
    assert names == sorted(names)
    assert "finding_summary" in names
    assert "abc_first" in names


async def test_json_every_row_carries_the_frozen_field_set(project, invoke) -> None:
    _declare_finding_view(project.squad_dir, "finding_summary")
    result = await invoke(["workflow", "views", "--json"])
    rows = json.loads(result.output)
    for row in rows:
        assert set(row.keys()) == set(VIEW_CATALOG_FIELDS)


def test_frozen_field_set_is_exactly_the_declared_shape() -> None:
    assert VIEW_CATALOG_FIELDS == (
        "view",
        "source_kind",
        "source_name",
        "fields",
        "group_by",
        "order_by",
    )


def test_every_catalog_row_has_exactly_the_frozen_field_set() -> None:
    spec = load_workflow_spec()
    for row in _view_catalog(spec):
        assert set(row.keys()) == set(VIEW_CATALOG_FIELDS)


async def test_an_override_declared_view_joins_the_catalog(project, invoke) -> None:
    _write_workflow_override(
        project.squad_dir,
        "[views.by_related]\n"
        'source = { kind = "ref", name = "related" }\n'
        'fields = [ { code = "id", label = "Id" } ]\n',
    )

    result = await invoke(["workflow", "views", "--json"])
    assert result.exit_code == 0
    rows = {r["view"]: r for r in json.loads(result.output)}
    assert "by_related" in rows
    assert rows["by_related"]["source_kind"] == "ref"
    assert rows["by_related"]["source_name"] == "related"


# ─── sq workflow view <name> <id> (resolve + render one) ────────────────────────


async def test_default_renders_the_declared_presentation_template(project, invoke) -> None:
    item_id = await _review_with_a_finding(invoke)
    _declare_finding_view(project.squad_dir, "finding_summary")

    result = await invoke(["workflow", "view", "finding_summary", item_id])
    assert result.exit_code == 0
    assert "| Finding | Status | Assignee | Title |" in result.output
    assert "A finding" in result.output


async def test_json_emits_the_projection_and_skips_presentation(project, invoke) -> None:
    item_id = await _review_with_a_finding(invoke)
    _declare_finding_view(project.squad_dir, "finding_summary")

    result = await invoke(["workflow", "view", "finding_summary", item_id, "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert set(payload) == {"fields", "group_by", "groups"}
    assert "|" not in result.output  # no table markup — presentation never ran


async def test_two_declared_presentations_of_one_projection_render_differently(
    project, invoke
) -> None:
    item_id = await _review_with_a_finding(invoke)
    _write_workflow_override(
        project.squad_dir,
        '[views.finding_summary]\nsource = { kind = "subentity", name = "finding" }\n\n'
        + _FINDING_FIELDS.format(name="finding_summary")
        + '\n[views.finding_summary_line]\nsource = { kind = "subentity", name = "finding" }\n\n'
        + _FINDING_FIELDS.format(name="finding_summary_line"),
    )

    table = await invoke(["workflow", "view", "finding_summary", item_id])
    line = await invoke(["workflow", "view", "finding_summary_line", item_id])
    assert table.output != line.output
    assert "|" in table.output
    assert "|" not in line.output


async def test_an_undeclared_view_name_exits_nonzero_with_a_clean_message(project, invoke) -> None:
    item_id = await _review_with_a_finding(invoke)
    result = await invoke(["workflow", "view", "no-such-view", item_id])
    assert result.exit_code == 1
    assert "no declared view" in result.output


async def test_an_unknown_item_id_exits_nonzero(project, invoke) -> None:
    _declare_finding_view(project.squad_dir, "finding_summary")
    result = await invoke(["workflow", "view", "finding_summary", "REV-999"])
    assert result.exit_code == 1


def _place_view_template_override(squad_dir: Path, name: str, content: str) -> None:
    target = squad_dir / ".overrides" / "templates" / "views" / f"{name}.md.j2"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    invalidate_squad_dir(squad_dir)


async def test_a_project_override_template_wins_over_the_bundled_one(project, invoke) -> None:
    item_id = await _review_with_a_finding(invoke)
    _declare_finding_view(project.squad_dir, "finding_summary")
    _place_view_template_override(
        project.squad_dir, "finding_summary", "PROJECT OVERRIDE RENDERING\n"
    )

    result = await invoke(["workflow", "view", "finding_summary", item_id])
    assert result.exit_code == 0
    assert "PROJECT OVERRIDE RENDERING" in result.output
    assert "| Finding |" not in result.output
