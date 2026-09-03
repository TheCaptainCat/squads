"""``Service.resolve_view``/``render_view`` — the one seam that loads the index and hands it to
``squads._views``. No view ships bundled (see ``squads._views``' own module docstring for why),
so every scenario here declares its own via a workflow override, then reconstructs the
``Service`` against the freshly loaded spec (``self.spec`` is fixed at construction).

The two views named ``finding_summary``/``finding_summary_line`` deliberately match the two
bundled presentation templates' own filenames, so resolving them exercises the real bundled
``_rendering/templates/views/*.md.j2`` files, not template-file stand-ins authored in the test.
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


def _declare_finding_view(squad_dir: Path, name: str) -> None:
    """A subentity-source view over ``finding``, named to match one of the two bundled
    presentation templates so resolving it exercises the real bundled ``.md.j2`` file."""
    _write_workflow_override(
        squad_dir,
        f'[views.{name}]\nsource = {{ kind = "subentity", name = "finding" }}\n\n'
        + _FINDING_FIELDS.format(name=name),
    )


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


async def test_render_view_renders_the_bundled_table_template(project, svc) -> None:
    review = await _review_with_findings(svc)
    _declare_finding_view(project.squad_dir, "finding_summary")

    out = await _reopen(project).render_view("finding_summary", review.id)
    assert "| Finding | Status | Assignee | Title |" in out
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
    reopened = _reopen(project)

    table = await reopened.render_view("finding_summary", review.id)
    line = await reopened.render_view("finding_summary_line", review.id)
    assert table != line
    assert "|" in table  # tabular
    assert "|" not in line  # non-tabular


async def test_an_undeclared_view_name_is_refused(svc) -> None:
    review = await _review_with_findings(svc)
    with pytest.raises(SquadsError, match="no declared view"):
        await svc.resolve_view("no-such-view", review.id)


async def test_a_view_over_the_wrong_source_item_type_is_refused(project, svc) -> None:
    task = (await create_item(svc, "task", "A task")).item
    _declare_finding_view(project.squad_dir, "finding_summary")
    with pytest.raises(SquadsError, match="hosts"):
        await _reopen(project).resolve_view("finding_summary", task.id)


# --------------------------------------------------------------------------- override wins


def _place_view_template_override(squad_dir: Path, name: str, content: str) -> None:
    target = squad_dir / ".overrides" / "templates" / "views" / f"{name}.md.j2"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    invalidate_squad_dir(squad_dir)


async def test_a_project_override_template_wins_over_the_bundled_one_and_renders(
    project, svc
) -> None:
    review = await _review_with_findings(svc)
    _declare_finding_view(project.squad_dir, "finding_summary")
    _place_view_template_override(
        project.squad_dir,
        "finding_summary",
        "PROJECT OVERRIDE\n"
        "{% for group in groups %}{% for record in group.records %}"
        "{{ record.values['id'].text }}!\n"
        "{% endfor %}{% endfor %}",
    )

    out = await _reopen(project).render_view("finding_summary", review.id)

    assert "PROJECT OVERRIDE" in out
    assert "F1!" in out
    assert "F2!" in out
    assert "|" not in out  # the bundled table markup is gone, proving the override rendered


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
