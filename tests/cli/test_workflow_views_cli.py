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

#: Neither ships bundled — no declared view names either, so nothing shipped can reach them
#: (see ``squads._views``' module docstring). Table/non-tabular stand-ins authored here, placed
#: as a project override template, so a test can still exercise two different presentations of
#: one projection.
_TABLE_TEMPLATE = (
    "{% for group in groups %}\n"
    "{% if group.key is not none %}\n"
    "### {{ group.key }}\n\n"
    "{% endif %}\n"
    '| {{ fields | map(attribute="label") | join(" | ") }} |\n'
    "| {% for f in fields %}---{% if not loop.last %} | {% endif %}{% endfor %} |\n"
    "{% for record in group.records %}\n"
    "| {% for f in fields %}{{ record.values[f.code].text }}"
    "{% if not loop.last %} | {% endif %}{% endfor %} |\n"
    "{% endfor %}\n"
    "{% endfor %}\n"
)
_LINE_TEMPLATE = (
    "{% for group in groups %}\n"
    "{% if group.key is not none %}**{{ group.key }}** ({{ group.records | length }})\n"
    "{% endif %}\n"
    "{% for record in group.records %}\n"
    "- {% for f in fields %}{{ record.values[f.code].text }}"
    "{% if not loop.last %} — {% endif %}{% endfor %}\n\n"
    "{% endfor %}\n"
    "{% endfor %}\n"
)
_STAND_IN_TEMPLATES = {"finding_summary": _TABLE_TEMPLATE, "finding_summary_line": _LINE_TEMPLATE}


def _declare_finding_view(squad_dir: Path, name: str) -> None:
    """A subentity-source view over ``finding``, named to match one of the two test-authored
    stand-in presentation templates (:data:`_STAND_IN_TEMPLATES`) placed as a project override —
    no view ships bundled, so resolving one always needs an override template of its own."""
    _write_workflow_override(
        squad_dir,
        f'[views.{name}]\nsource = {{ kind = "subentity", name = "finding" }}\n\n'
        + _FINDING_FIELDS.format(name=name),
    )
    if name in _STAND_IN_TEMPLATES:
        _place_view_template_override(squad_dir, name, _STAND_IN_TEMPLATES[name])


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


async def test_group_count_renders_in_a_template_and_matches_the_json_value(
    project, invoke
) -> None:
    """``docs/workflow.md`` documents ``group.count`` as part of the template context;
    ``StrictUndefined`` used to turn that into an ``UndefinedError`` the moment a template
    actually read it."""
    item_id = await _review_with_a_finding(invoke)
    _write_workflow_override(
        project.squad_dir,
        '[views.by_status]\nsource = { kind = "subentity", name = "finding" }\n'
        'group_by = "status"\n'
        'fields = [ { code = "id", label = "Id" }, { code = "status", label = "Status" } ]\n',
    )
    _place_view_template_override(
        project.squad_dir,
        "by_status",
        "{% for group in groups %}{{ group.key }}: {{ group.count }}\n{% endfor %}",
    )

    result = await invoke(["workflow", "view", "by_status", item_id])
    assert result.exit_code == 0
    assert "Open: 1" in result.output

    json_result = await invoke(["workflow", "view", "by_status", item_id, "--json"])
    (json_group,) = json.loads(json_result.output)["groups"]
    assert json_group["count"] == 1


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
    _place_view_template_override(project.squad_dir, "finding_summary", _TABLE_TEMPLATE)
    _place_view_template_override(project.squad_dir, "finding_summary_line", _LINE_TEMPLATE)

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


async def test_a_view_with_no_presentation_template_fails_clean_not_a_traceback(
    project, invoke
) -> None:
    """A view can be structurally coherent — every axis a load-time spec check can see — and
    still have no template on disk: the one axis only the render boundary can catch. Drives it
    through the CLI end to end, never a raw ``jinja2.TemplateNotFound``."""
    item_id = await _review_with_a_finding(invoke)
    _write_workflow_override(
        project.squad_dir,
        '[views.no_template_view]\nsource = { kind = "subentity", name = "finding" }\n\n'
        + _FINDING_FIELDS.format(name="no_template_view"),
    )

    result = await invoke(["workflow", "view", "no_template_view", item_id])

    assert result.exit_code == 1
    assert "Traceback" not in result.output
    assert "no presentation template" in result.output
    assert "templates/views/no_template_view.md.j2" in result.output
    assert ".overrides/templates/views/no_template_view.md.j2" in result.output

    # --json is unaffected — it skips presentation and stays a clean success.
    json_result = await invoke(["workflow", "view", "no_template_view", item_id, "--json"])
    assert json_result.exit_code == 0


def _place_view_template_override(squad_dir: Path, name: str, content: str) -> None:
    """Write the override template. No cache eviction needed here: `invoke`'s per-call reset
    (tests/conftest.py) clears the whole render-engine environment cache before every command
    this module drives, which is what used to require a manual `invalidate_squad_dir` call."""
    target = squad_dir / ".overrides" / "templates" / "views" / f"{name}.md.j2"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


async def test_a_project_override_template_wins_over_the_bundled_one(project, invoke) -> None:
    """``milestone_rollup`` is the one view that actually ships bundled (neither
    ``finding_summary`` nor ``finding_summary_line`` does — see :data:`_STAND_IN_TEMPLATES`),
    so it is the one an override template can genuinely be shown winning over."""
    r = await invoke(["create", "milestone", "A milestone", "--author", "manager"])
    assert r.exit_code == 0
    milestone_id = r.output.split("→")[0].removeprefix("created").strip()
    r = await invoke(["create", "task", "Targets the milestone", "--author", "manager"])
    assert r.exit_code == 0
    task_id = r.output.split("→")[0].removeprefix("created").strip()
    r = await invoke(["task", task_id, "ref", "add", milestone_id, "--kind", "targets"])
    assert r.exit_code == 0
    _place_view_template_override(
        project.squad_dir, "milestone_rollup", "PROJECT OVERRIDE RENDERING\n"
    )

    result = await invoke(["workflow", "view", "milestone_rollup", milestone_id])
    assert result.exit_code == 0
    assert "PROJECT OVERRIDE RENDERING" in result.output
    assert "## Delivered" not in result.output
