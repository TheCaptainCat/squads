"""``sq workflow views`` (the catalog) and ``sq workflow view <name> <id>`` (resolve one).

Default prints a human Rich table; ``--json`` emits the catalog / the projection. The
byte-identical golden for the catalog (the five bundled rows — ``milestone_rollup`` plus the
four non-relation views placed by a seeded tag rather than a type attachment:
``role_definition``, ``squads_skill``, ``greeting_skill``, ``memory_skill``) is pinned in
``tests/cli/test_json_output_shape.py`` (``tests/goldens/workflow_views.json``); this module
covers the field-set contract, the human table, and every declared-view/resolve/override path
via an override-declared view.
"""

import json
from pathlib import Path

import pytest

from squads import __version__
from squads._cli._workflow_cmd import VIEW_CATALOG_FIELDS, _view_catalog
from squads._models._schema import SCHEMA_VERSION
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


async def test_the_default_catalog_carries_only_the_bundled_views(project, invoke) -> None:
    """``milestone_rollup`` is the one *relation*-sourced bundled view; ``role_definition``/
    ``squads_skill``/``greeting_skill``/``memory_skill``/``item_skill`` are the five
    non-relation ones. All six are placed by a seeded ``sq:view:<name>`` tag in their host's
    creation template — no bundled type declares an ``items.<type>.views`` attachment any
    more — and an override-declared view is proven separately below rather than by asserting
    the catalog stays at six entries forever."""
    result = await invoke(["workflow", "views", "--json"])
    assert result.exit_code == 0
    rows = json.loads(result.output)
    assert {r["view"] for r in rows} == {
        "milestone_rollup",
        "role_definition",
        "squads_skill",
        "greeting_skill",
        "memory_skill",
        "item_skill",
    }


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

    # ``group.count`` is a template-side concept over a source's own resolved records — a
    # ``subentity`` view's ``--json`` is a bare array with no group in it at all (see
    # test_a_subentity_views_json_matches_the_per_kind_list_shape below), so the record count
    # the template renders is checked against the one record the equivalent list command
    # itself reports.
    findings_result = await invoke(["review", item_id, "findings", "--json"])
    assert len(json.loads(findings_result.output)) == 1


async def test_a_subentity_views_json_matches_the_per_kind_list_shape(project, invoke) -> None:
    """A ``subentity`` source's ``--json`` is a bare array, never a ``{fields, group_by,
    groups}`` envelope — the same shape ``sq <type> <n> <kind>s --json`` already emits for
    that kind, asserted equal against that command's own output rather than a hand-written
    shape."""
    item_id = await _review_with_a_finding(invoke)
    _declare_finding_view(project.squad_dir, "finding_summary")

    result = await invoke(["workflow", "view", "finding_summary", item_id, "--json"])
    assert result.exit_code == 0
    assert "|" not in result.output  # no table markup — presentation never ran
    payload = json.loads(result.output)

    findings_result = await invoke(["review", item_id, "findings", "--json"])
    assert payload == json.loads(findings_result.output)
    assert payload  # and it is not vacuously equal — there is a real row to compare
    for key in ("fields", "group_by", "groups"):
        assert not any(key in row for row in payload)  # no projection-envelope key on any row


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
    """``milestone_rollup`` is a bundled *relation*-sourced view attached the ordinary way
    (neither ``finding_summary`` nor ``finding_summary_line`` ships bundled at all — see
    :data:`_STAND_IN_TEMPLATES`), so it is a real one an override template can genuinely be
    shown winning over."""
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


# ─── per-source --json (ref/subtree/role/self/playbook) ─────────────────────────


async def _created_id(invoke, item_type: str, title: str, **flags: str) -> str:
    args = ["create", item_type, title, "--author", "manager"]
    for flag, value in flags.items():
        args += [f"--{flag}", value]
    r = await invoke(args)
    assert r.exit_code == 0, r.output
    return r.output.split("→")[0].removeprefix("created").strip()


async def test_a_ref_sourced_views_json_equals_sq_tree_jsons_own_output(project, invoke) -> None:
    """A ``ref`` source's ``--json`` is diffed against the real ``sq tree --json`` output for
    an equivalent query, never a hand-written expected shape — so a drift between the two
    paths shows up as a failing assertion, not a silent divergence. Every ``task`` in this
    fresh squad is one of the two created below, none carries a parent, so the ``task``-typed
    entries of the bare (unfiltered) forest and the ``ref`` source's own resolved set name the
    exact same two records — filtered to ``type == "task"`` in Python rather than via
    ``sq tree --type task``, because that CLI filter also prunes a matched node's own
    non-matching descendants, and one of the two now carries a real one: giving Task 0 a bug
    of its own is what proves each row's ``children`` field reflects the real tree rather than
    the flat default the source-widening review found (``children: []`` on every row)."""
    _write_workflow_override(
        project.squad_dir,
        '[views.by_target]\nsource = { kind = "ref", name = "targets" }\n'
        'fields = [ { code = "id", label = "Id" } ]\n',
    )
    milestone_id = await _created_id(invoke, "milestone", "A milestone")
    task_ids = []
    for i in range(2):
        task_id = await _created_id(invoke, "task", f"Task {i}")
        r = await invoke(["task", task_id, "ref", "add", milestone_id, "--kind", "targets"])
        assert r.exit_code == 0
        task_ids.append(task_id)
    await _created_id(invoke, "bug", "Found while working the first task", parent=task_ids[0])

    view_result = await invoke(["workflow", "view", "by_target", milestone_id, "--json"])
    assert view_result.exit_code == 0
    tree_result = await invoke(["tree", "--json"])  # unfiltered: no CLI-side descendant pruning
    assert tree_result.exit_code == 0

    view_payload = json.loads(view_result.output)
    tree_payload = [row for row in json.loads(tree_result.output) if row["type"] == "task"]
    assert len(view_payload) == 2  # not vacuously equal
    assert any(row["children"] for row in view_payload)  # the grandchild is real, not vacuous
    assert view_payload == tree_payload


async def test_a_subtree_sourced_views_json_equals_the_hosts_own_tree_children(
    project, invoke
) -> None:
    """The same equality discipline for ``subtree``: its ``--json`` is diffed against the
    ``children`` of the host's own node in ``sq tree <host> --json`` — the real command's
    output navigated to the comparable slice, never a hand-written expected shape. One of the
    two matched tasks carries a real child of its own (a bug, not itself a ``task`` — so it
    stays out of ``subtree``'s own flat matched-type set while still being a real descendant
    both sides must agree the matched task has), proving each row's ``children`` field
    reflects the real tree rather than the flat default the source-widening review found. No
    ``--type`` filter on the tree side: an explicit root already scopes the comparison to this
    one host's own subtree, and (as in the ``ref`` case above) that filter would prune the
    bug out from under its parent on the tree side while this source's own children-population
    stays unconditional, breaking the equality this test exists to hold."""
    _write_workflow_override(
        project.squad_dir,
        '[views.child_tasks]\nsource = { kind = "subtree", name = "task" }\n'
        'fields = [ { code = "id", label = "Id" } ]\n',
    )
    feature_id = await _created_id(invoke, "feature", "A feature")
    task_ids = [await _created_id(invoke, "task", f"Task {i}", parent=feature_id) for i in range(2)]
    await _created_id(invoke, "bug", "Found while working the first task", parent=task_ids[0])

    view_result = await invoke(["workflow", "view", "child_tasks", feature_id, "--json"])
    assert view_result.exit_code == 0
    tree_result = await invoke(["tree", feature_id, "--json"])
    assert tree_result.exit_code == 0

    view_payload = json.loads(view_result.output)
    (root_node,) = json.loads(tree_result.output)
    assert root_node["id"] == feature_id
    assert len(view_payload) == 2
    assert any(row["children"] for row in view_payload)  # the grandchild is real, not vacuous
    assert view_payload == root_node["children"]


async def test_a_ref_sourced_views_json_is_an_empty_list_with_no_matching_refs(
    project, invoke
) -> None:
    """Emptiness is a success, not a refusal — the same clause the module docstring's
    applicability predicates already document, exercised here through the ``--json`` path."""
    _write_workflow_override(
        project.squad_dir,
        '[views.by_target]\nsource = { kind = "ref", name = "targets" }\n'
        'fields = [ { code = "id", label = "Id" } ]\n',
    )
    milestone_id = await _created_id(invoke, "milestone", "A lonely milestone")

    result = await invoke(["workflow", "view", "by_target", milestone_id, "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output) == []


async def test_a_subentity_sourced_views_json_is_an_empty_list_with_no_sub_entities(
    project, invoke
) -> None:
    _declare_finding_view(project.squad_dir, "finding_summary")
    review_id = await _created_id(invoke, "review", "A review with nothing found")

    result = await invoke(["workflow", "view", "finding_summary", review_id, "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output) == []


async def test_a_role_sourced_views_json_matches_role_show_json(project, invoke) -> None:
    _write_workflow_override(project.squad_dir, '[views.role_card]\nsource = { kind = "role" }\n')
    activate = await invoke(["role", "activate", "tech-writer"])
    assert activate.exit_code == 0
    role_id = json.loads((await invoke(["role", "tech-writer", "show", "--json"])).output)["id"]

    view_result = await invoke(["workflow", "view", "role_card", role_id, "--json"])
    assert view_result.exit_code == 0
    show_result = await invoke(["role", "tech-writer", "show", "--json"])
    assert show_result.exit_code == 0

    assert json.loads(view_result.output) == json.loads(show_result.output)


async def test_a_self_sourced_views_json_matches_show_json_plus_spec_identity(
    project, invoke
) -> None:
    _write_workflow_override(project.squad_dir, '[views.self_card]\nsource = { kind = "self" }\n')
    task_id = await _created_id(invoke, "task", "A task")

    view_result = await invoke(["workflow", "view", "self_card", task_id, "--json"])
    assert view_result.exit_code == 0
    show_result = await invoke(["task", task_id, "show", "--json"])
    assert show_result.exit_code == 0

    payload = json.loads(view_result.output)
    spec_identity = payload.pop("spec")
    assert payload == json.loads(show_result.output)
    # An ``.overrides/workflow.toml`` is in force (it declares ``self_card`` itself), so a
    # client reading this payload can tell a customised spec resolved it.
    assert spec_identity == {"schema_version": SCHEMA_VERSION, "override": True}


async def test_a_playbook_sourced_views_json_carries_the_lane_and_roster(project, invoke) -> None:
    _write_workflow_override(
        project.squad_dir, '[views.lane_card]\nsource = { kind = "playbook" }\n'
    )
    task_id = await _created_id(invoke, "task", "A task")

    result = await invoke(["workflow", "view", "lane_card", task_id, "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)

    assert payload["type"] == "task"
    assert payload["lane"] is not None
    assert payload["lane"]["overview"]
    assert payload["lane"]["lifecycle"]
    assert payload["lane"]["commands"]
    assert all(
        {"slug", "enter", "do", "handoff", "watch", "authors"} <= set(rg)
        for rg in payload["lane"]["roles"]
    )
    assert isinstance(payload["roster"], list)
    for envelope_key in ("fields", "group_by", "groups"):
        assert envelope_key not in payload
        assert envelope_key not in (payload["lane"] or {})
