"""``Service.resolve_view``/``render_view`` — the one seam that loads the index and hands it to
``squads._views``. Only ``milestone_rollup`` ships bundled; every other view here — including
the two named ``finding_summary``/``finding_summary_line``, chosen to read like real
presentation names rather than to match a shipped file — is declared via a workflow override and
rendered against a test-authored stand-in template placed at
``.overrides/templates/views/<name>.md.j2`` (:func:`_declare_finding_view`), then resolved
through a freshly reconstructed ``Service`` (``self.spec`` is fixed at construction, so a view
declared after ``svc`` was built needs a new instance).
"""

from pathlib import Path
from typing import cast

import pytest

from _helpers import create_item
from squads import __version__
from squads._errors import SquadsError
from squads._rendering._engine import invalidate_squad_dir
from squads._services._service import Service
from squads._views import projection_json
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio


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


def _place_view_template_override(squad_dir: Path, name: str, content: str) -> None:
    target = squad_dir / ".overrides" / "templates" / "views" / f"{name}.md.j2"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    invalidate_squad_dir(squad_dir)


#: Table / non-tabular stand-ins for the two scenarios below — neither ``finding_summary`` nor
#: ``finding_summary_line`` ships bundled (only ``milestone_rollup`` does).
_TABLE_TEMPLATE = (
    "{% for group in groups %}{% for record in group.records %}"
    "{{ record.values['id'].text }} — {{ record.values['title'].text }}\n"
    "{% endfor %}{% endfor %}"
)
_LINE_TEMPLATE = (
    "{% for group in groups %}{% for record in group.records %}"
    "* {{ record.values['id'].text }}\n"
    "{% endfor %}{% endfor %}"
)
_STAND_IN_TEMPLATES = {"finding_summary": _TABLE_TEMPLATE, "finding_summary_line": _LINE_TEMPLATE}


def _declare_finding_view(squad_dir: Path, name: str) -> None:
    """A subentity-source view over ``finding``, named to match one of the two test-authored
    stand-in templates (:data:`_STAND_IN_TEMPLATES`), placed as a project override — no view
    ships bundled under either name, so resolving one always needs a template of its own."""
    _write_workflow_override(
        squad_dir,
        f'[views.{name}]\nsource = {{ kind = "subentity", name = "finding" }}\n\n'
        + _FINDING_FIELDS.format(name=name),
    )
    if name in _STAND_IN_TEMPLATES:
        _place_view_template_override(squad_dir, name, _STAND_IN_TEMPLATES[name])


async def _review_with_findings(svc):
    review = (await create_item(svc, "review", "A review")).item
    await svc.add_finding(review.id, "First finding", severity="high")
    await svc.add_finding(review.id, "Second finding")
    return review


def _reopen(project) -> Service:
    """A fresh ``Service`` bound to the just-written workflow override — ``self.spec`` is
    fixed at construction, so a view declared after ``svc`` was built needs a new instance."""
    return Service(project, spec=load_workflow_spec(squad_dir=project.squad_dir))


async def test_resolve_view_returns_the_declared_projection(project, svc) -> None:
    review = await _review_with_findings(svc)
    _declare_finding_view(project.squad_dir, "finding_summary")

    projection = await _reopen(project).resolve_view("finding_summary", review.id)
    payload = projection_json(projection)
    (group,) = cast("list[dict[str, object]]", payload["groups"])
    records = cast("list[dict[str, object]]", group["records"])
    assert [r["id"] for r in records] == ["F1", "F2"]


async def test_render_view_renders_the_declared_presentation_template(project, svc) -> None:
    review = await _review_with_findings(svc)
    _declare_finding_view(project.squad_dir, "finding_summary")

    out = await _reopen(project).render_view("finding_summary", review.id)
    assert "F1" in out
    assert "First finding" in out


async def test_two_presentations_of_the_same_projection_render_differently(project, svc) -> None:
    review = await _review_with_findings(svc)
    _write_workflow_override(
        project.squad_dir,
        '[views.finding_summary]\nsource = { kind = "subentity", name = "finding" }\n\n'
        + _FINDING_FIELDS.format(name="finding_summary")
        + '\n[views.finding_summary_line]\nsource = { kind = "subentity", name = "finding" }\n\n'
        + _FINDING_FIELDS.format(name="finding_summary_line"),
    )
    _place_view_template_override(project.squad_dir, "finding_summary", _TABLE_TEMPLATE)
    _place_view_template_override(project.squad_dir, "finding_summary_line", _LINE_TEMPLATE)
    reopened = _reopen(project)

    table = await reopened.render_view("finding_summary", review.id)
    line = await reopened.render_view("finding_summary_line", review.id)
    assert table != line
    assert "—" in table  # the table stand-in
    assert "—" not in line  # the line stand-in


async def test_an_undeclared_view_name_is_refused(svc) -> None:
    review = await _review_with_findings(svc)
    with pytest.raises(SquadsError, match="no declared view"):
        await svc.resolve_view("no-such-view", review.id)


async def test_a_view_over_the_wrong_source_item_type_is_refused(project, svc) -> None:
    task = (await create_item(svc, "task", "A task")).item
    _declare_finding_view(project.squad_dir, "finding_summary")
    with pytest.raises(SquadsError, match="hosts"):
        await _reopen(project).resolve_view("finding_summary", task.id)


# --------------------------------------------------------------------------- a `ref` source
# projecting a field only some declared item types carry


async def test_a_ref_source_field_renders_identically_null_absent_or_unset(project, svc) -> None:
    """The payload ruling this amendment turns on: a record of a type that cannot carry the
    field, and a record of a type that carries it but has it unset, must be indistinguishable
    — one absence, not two. Declares ``impact`` on ``task`` alone (``bug`` never declares it),
    points one of each at a hub item via ``related``, and projects ``impact`` through a
    ``ref``-source view over that hub."""
    _write_workflow_override(
        project.squad_dir,
        '[collections.impact]\nlabel = "Impact"\nordered = true\n'
        'badges = [ { code = "low", label = "Low" }, { code = "high", label = "High" } ]\n\n'
        '[[items.task.fields]]\ncode = "impact"\nlabel = "Impact"\ncollection = "impact"\n\n'
        '[views.by_related]\nsource = { kind = "ref", name = "related" }\n\n'
        '[[views.by_related.fields]]\ncode = "id"\nlabel = "Id"\n\n'
        '[[views.by_related.fields]]\ncode = "type"\nlabel = "Type"\n\n'
        '[[views.by_related.fields]]\ncode = "impact"\nlabel = "Impact"\n',
    )
    reopened = _reopen(project)
    hub = (await create_item(reopened, "guide", "Hub")).item
    task = (await create_item(reopened, "task", "Has the field, unset")).item
    bug = (await create_item(reopened, "bug", "Has no such field")).item
    await reopened.add_ref(task.id, hub.id, kind="related")
    await reopened.add_ref(bug.id, hub.id, kind="related")

    projection = await reopened.resolve_view("by_related", hub.id)
    payload = projection_json(projection)
    (group,) = cast("list[dict[str, object]]", payload["groups"])
    records = {cast(str, r["id"]): r for r in cast("list[dict[str, object]]", group["records"])}

    assert records[task.id]["impact"] is None
    assert records[bug.id]["impact"] is None


# --------------------------------------------------------------------------- override wins


async def test_a_project_override_template_wins_over_the_bundled_one_and_renders(
    project, svc
) -> None:
    """``milestone_rollup`` is the one view that actually ships bundled — neither
    ``finding_summary`` nor ``finding_summary_line`` does, see :func:`_declare_finding_view` —
    so it is the one an override template can genuinely be shown winning over."""
    milestone = (await create_item(svc, "milestone", "A milestone")).item
    task = (await create_item(svc, "task", "Targets the milestone")).item
    await svc.add_ref(task.id, milestone.id, kind="targets")
    _place_view_template_override(
        project.squad_dir,
        "milestone_rollup",
        "PROJECT OVERRIDE\n"
        "{% for group in groups %}{% for record in group.records %}"
        "{{ record.values['id'].text }}!\n"
        "{% endfor %}{% endfor %}",
    )

    out = await svc.render_view("milestone_rollup", milestone.id)

    assert "PROJECT OVERRIDE" in out
    assert f"{task.id}!" in out
    assert "## Delivered" not in out  # the bundled roll-up markup is gone


# --------------------------------------------------------------------------- one index load


async def test_render_view_costs_one_index_load(project, svc, monkeypatch) -> None:
    review = await _review_with_findings(svc)
    _declare_finding_view(project.squad_dir, "finding_summary")
    reopened = _reopen(project)

    calls = 0
    original_load = reopened.store.load

    async def _counting_load(*args, **kwargs):
        nonlocal calls
        calls += 1
        return await original_load(*args, **kwargs)

    monkeypatch.setattr(reopened.store, "load", _counting_load)
    await reopened.render_view("finding_summary", review.id)
    assert calls == 1


# --------------------------------------------------------------------------- ref/subtree sources


async def test_a_declared_ref_source_view_resolves_against_a_real_corpus(project, svc) -> None:
    _write_workflow_override(
        project.squad_dir,
        '[views.related_to]\nsource = { kind = "ref", name = "related" }\n'
        'fields = [ { code = "id", label = "Id" }, { code = "title", label = "Title" } ]\n',
    )

    feature = (await create_item(svc, "feature", "Umbrella feature")).item
    referencer = (await create_item(svc, "task", "Refers to the feature")).item
    await svc.add_ref(referencer.id, feature.id)

    projection = await _reopen(project).resolve_view("related_to", feature.id)
    payload = projection_json(projection)
    (group,) = cast("list[dict[str, object]]", payload["groups"])
    records = cast("list[dict[str, object]]", group["records"])
    assert [r["id"] for r in records] == [referencer.id]


async def test_a_declared_subtree_source_view_resolves_against_a_real_corpus(project, svc) -> None:
    _write_workflow_override(
        project.squad_dir,
        '[views.feature_tasks]\nsource = { kind = "subtree", name = "task" }\n'
        'fields = [ { code = "id", label = "Id" } ]\n'
        'order_by = ["id"]\n',
    )

    feature = (await create_item(svc, "feature", "Umbrella feature")).item
    t1 = (await create_item(svc, "task", "Task A", parent=feature.id)).item
    t2 = (await create_item(svc, "task", "Task B", parent=feature.id)).item

    projection = await _reopen(project).resolve_view("feature_tasks", feature.id)
    payload = projection_json(projection)
    (group,) = cast("list[dict[str, object]]", payload["groups"])
    records = cast("list[dict[str, object]]", group["records"])
    assert {r["id"] for r in records} == {t1.id, t2.id}
