"""``sq retype`` preserves a ``sq:view:<name>`` tag's bytes and position verbatim onto an
item's new type, readable throughout; landing on a type incompatible with the tag's source
still reads successfully, left byte-for-byte literal, with ``sq check`` reporting it."""

from pathlib import Path

import pytest

from _helpers import create_item
from squads import __version__
from squads._models import _markers as markers
from squads._rendering._engine import invalidate_squad_dir
from squads._sections import get_section, replace_section
from squads._services._service import Service
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio

_BUNDLED_VIEW = "milestone_rollup"


def _declare_resolvable_subentity_view(squad_dir: Path, name: str, kind: str) -> None:
    """A declared, templated ``subentity``-source view over sub-entity *kind*."""
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    templates_dir = override_dir / "templates" / "views"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / f"{name}.md.j2").write_text(f"{name}\n", encoding="utf-8")
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n"
        f'[views.{name}]\nsource = {{ kind = "subentity", name = "{kind}" }}\n',
        encoding="utf-8",
    )
    invalidate_squad_dir(squad_dir)


def _reopen(project) -> Service:
    return Service(project, spec=load_workflow_spec(squad_dir=project.squad_dir))


async def test_retype_carries_the_view_tag_bytes_and_position_verbatim(svc) -> None:
    task = (await create_item(svc, "task", "task")).item
    await svc.set_body(task.id, "Prose kept across the retype.")
    await svc.add_view(task.id, _BUNDLED_VIEW)
    before_text = (svc.paths.abspath((await svc.get(task.id)).path)).read_text(encoding="utf-8")
    before_body = get_section(before_text, markers.BODY)
    assert before_body is not None

    res = await svc.retype(task.id, "bug")

    after_text = svc.paths.abspath(res.item.path).read_text(encoding="utf-8")
    after_body = get_section(after_text, markers.BODY)
    assert after_body is not None
    assert after_body == before_body
    assert f"<!-- sq:{markers.view_tag(_BUNDLED_VIEW)} -->" in after_body


async def test_sq_check_stays_clean_after_a_retype_carrying_a_view_tag(svc) -> None:
    """A view name, not type-scoped, still resolves against the new type after a retype."""
    task = (await create_item(svc, "task", "task")).item
    await svc.add_view(task.id, _BUNDLED_VIEW)
    body_before = await svc.read_body(task.id)

    res = await svc.retype(task.id, "bug")

    issues = await svc.check()
    assert not any(_BUNDLED_VIEW in i.message for i in issues), [i.message for i in issues]
    assert res.item.type == "bug"
    body_after = await svc.read_body(res.item.id)
    assert body_after == body_before


async def test_a_dangling_view_tag_still_reports_after_retype_the_check_is_not_suppressed(
    svc,
) -> None:
    """A tag already dangling before the retype is still reported, not suppressed, after it."""
    task = (await create_item(svc, "task", "task")).item
    text = svc.paths.abspath((await svc.get(task.id)).path).read_text(encoding="utf-8")
    seeded = replace_section(text, markers.BODY, f"<!-- sq:{markers.view_tag('no-such-view')} -->")
    svc.paths.abspath((await svc.get(task.id)).path).write_text(seeded, encoding="utf-8")

    res = await svc.retype(task.id, "bug")

    issues = await svc.check()
    assert any("no-such-view" in i.message for i in issues), [i.message for i in issues]
    assert res.item.type == "bug"


# ------------------------------------------------------------------- source applicability


async def test_retype_onto_a_non_hosting_type_reads_literal_and_check_reports_it(
    project,
) -> None:
    """A subentity-source view rides along, unchanged, onto a type that does not host the
    projected kind: the read succeeds with the tag left byte-for-byte literal."""
    _declare_resolvable_subentity_view(project.squad_dir, "story_board", "story")
    svc = _reopen(project)
    feature = (await create_item(svc, "feature", "A feature")).item
    await svc.add_view(feature.id, "story_board")
    valid_body = await svc.read_body(feature.id)
    assert "<!-- sq:view:story_board -->" not in valid_body

    res = await svc.retype(feature.id, "epic")

    assert res.item.type == "epic"
    tag_line = f"<!-- sq:{markers.view_tag('story_board')} -->"
    stored_text = svc.paths.abspath(res.item.path).read_text(encoding="utf-8")
    stored_body = get_section(stored_text, markers.BODY)
    assert stored_body is not None
    assert tag_line in stored_body

    body_after = await svc.read_body(res.item.id)
    assert tag_line in body_after
    assert body_after.strip() == stored_body.strip()

    issues = await svc.check()
    matches = [i for i in issues if "story_board" in i.message]
    assert matches, [i.message for i in issues]
    assert all(i.level == "error" for i in matches)
    assert any("hosts" in i.message for i in matches)
