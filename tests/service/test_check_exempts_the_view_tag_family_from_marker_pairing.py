"""``sq check``'s open/close balance arithmetic (``_marker_issues``) exempts the declared
unpaired view-tag family (``sq:view:<name>``) from the pairing count, by shape — through
``_models._markers.view_tag_name``, never a name list and never the ``"view:"`` prefix
re-spelled at this site.

The exemption is **narrow**: it drops only the "unclosed marker" pairing complaint for a tag
the recogniser accepts. A *duplicate* of the same named view tag is a distinct signal (a
doubled tag renders the view twice) and must still be reported — driven here explicitly so a
sloppy exemption ("anything starting with view") cannot pass unnoticed. A non-view unpaired
tag is the control: it must keep erroring exactly as it does today.

Table-driven over tag *position* in the body (start/middle/end, two tags naming different
views, adjacent to another region's markers) and *shape* (a balanced file with no view tag at
all), plus the control.
"""

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


async def _text(svc, item_id: str) -> str:
    path = svc.paths.abspath((await svc.get(item_id)).path)
    return path.read_text(encoding="utf-8")


async def _write_raw(svc, item_id: str, text: str) -> None:
    path = svc.paths.abspath((await svc.get(item_id)).path)
    path.write_text(text, encoding="utf-8")


async def _messages(svc) -> list[str]:
    return [i.message for i in await svc.check()]


def _unclosed_for(tag: str) -> str:
    return f"unclosed marker <!-- sq:{tag} -->"


def _reopen(project) -> Service:
    """A fresh ``Service`` bound to a just-written workflow override — ``self.spec`` is fixed
    at construction, so a view declared after ``svc`` was built needs a new instance."""
    return Service(project, spec=load_workflow_spec(squad_dir=project.squad_dir))


def _declare_second_view(squad_dir) -> None:
    """A subentity-source view over ``subtask`` -- the kind ``task`` (this module's host type
    throughout) actually hosts, so placing it stays a pure marker-pairing probe and does not
    also trip the source-applicability predicate this module isn't about."""
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    templates_dir = override_dir / "templates" / "views"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "second_view.md.j2").write_text("second view\n", encoding="utf-8")
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n"
        '[views.second_view]\nsource = { kind = "subentity", name = "subtask" }\n'
        'fields = [ { code = "id", label = "Id" } ]\n',
        encoding="utf-8",
    )
    invalidate_squad_dir(squad_dir)


# --------------------------------------------------------------------------- position


async def test_a_view_tag_at_the_start_of_the_body_is_not_reported_unclosed(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    tag = markers.view_tag(_BUNDLED_VIEW)
    text = await _text(svc, task.id)
    new_body = f"<!-- sq:{tag} -->\n\nProse after the tag."
    await _write_raw(svc, task.id, replace_section(text, markers.BODY, new_body))
    body = get_section(await _text(svc, task.id), markers.BODY) or ""
    assert body.strip().startswith(f"<!-- sq:{tag} -->")  # sanity: it really is at the start

    messages = await _messages(svc)
    assert not any(_unclosed_for(tag) in m for m in messages)


async def test_a_view_tag_in_the_middle_of_the_body_is_not_reported_unclosed(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    tag = markers.view_tag(_BUNDLED_VIEW)
    text = await _text(svc, task.id)
    new_body = f"Prose before.\n\n<!-- sq:{tag} -->\n\nProse after."
    await _write_raw(svc, task.id, replace_section(text, markers.BODY, new_body))

    messages = await _messages(svc)
    assert not any(_unclosed_for(tag) in m for m in messages)


async def test_a_view_tag_at_the_end_of_the_body_default_anchor_is_not_reported_unclosed(
    svc,
) -> None:
    task = (await create_item(svc, "task", "T")).item
    await svc.set_body(task.id, "Scope prose.")
    await svc.insert_view(task.id, _BUNDLED_VIEW)  # default anchor is the region's end
    tag = markers.view_tag(_BUNDLED_VIEW)
    body = get_section(await _text(svc, task.id), markers.BODY) or ""
    assert body.strip().endswith(f"<!-- sq:{tag} -->")  # sanity: it really is at the end

    messages = await _messages(svc)
    assert not any(_unclosed_for(tag) in m for m in messages)


async def test_two_view_tags_naming_different_views_neither_reports_unclosed(project) -> None:
    _declare_second_view(project.squad_dir)
    svc = _reopen(project)
    task = (await create_item(svc, "task", "T")).item

    await svc.insert_view(task.id, _BUNDLED_VIEW)
    await svc.insert_view(task.id, "second_view")

    messages = await _messages(svc)
    assert not any(_unclosed_for(markers.view_tag(_BUNDLED_VIEW)) in m for m in messages)
    assert not any(_unclosed_for(markers.view_tag("second_view")) in m for m in messages)


async def test_a_view_tag_adjacent_to_sub_entity_region_markers_is_not_reported_unclosed(
    svc,
) -> None:
    feat = (await create_item(svc, "feature", "F")).item
    await svc.add_story(feat.id, "a story")  # plants sub-entity region markers in the same file
    await svc.insert_view(feat.id, _BUNDLED_VIEW)

    messages = await _messages(svc)
    assert not any(_unclosed_for(markers.view_tag(_BUNDLED_VIEW)) in m for m in messages)
    # And the real sub-entity markers this planted are still balanced -- the exemption did not
    # spill onto a neighbouring family.
    assert not any("unclosed marker" in m and "story:" in m for m in messages)


# --------------------------------------------------------------------------- shape


async def test_a_balanced_file_with_no_view_tag_reports_no_marker_issues(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    await svc.set_body(task.id, "Ordinary prose, no view tag anywhere.")

    messages = await _messages(svc)
    assert not any("marker" in m for m in messages)


# -------------------------------------------------------------------------- duplicate: still errors


async def test_a_duplicate_of_the_same_named_view_tag_is_still_reported(svc) -> None:
    """The exemption is from the pairing count only -- a doubled tag renders the view twice,
    so it stays a reportable defect distinct from "unclosed"."""
    task = (await create_item(svc, "task", "T")).item
    await svc.insert_view(task.id, _BUNDLED_VIEW)
    tag = markers.view_tag(_BUNDLED_VIEW)
    text = await _text(svc, task.id)
    body = get_section(text, markers.BODY) or ""
    doubled = replace_section(text, markers.BODY, f"{body}<!-- sq:{tag} -->\n")
    await _write_raw(svc, task.id, doubled)

    messages = await _messages(svc)
    assert any(f"duplicate marker <!-- sq:{tag} -->" in m for m in messages), messages
    # And it must NOT also be reported as unclosed -- the exemption still holds for pairing.
    assert not any(_unclosed_for(tag) in m for m in messages)


# --------------------------------------------------------------------------- control: non-view


async def test_a_non_view_unpaired_tag_still_errors_exactly_as_it_does_today(svc) -> None:
    """Control proving the exemption is narrow: an ordinary sub-entity marker opened with no
    matching close is still reported "unclosed"."""
    feat = (await create_item(svc, "feature", "F")).item
    await svc.add_story(feat.id, "a story")
    tag = markers.discussion_tag("story:US1")
    await _write_raw(svc, feat.id, (await _text(svc, feat.id)) + f"\n{markers.open_marker(tag)}\n")

    messages = await _messages(svc)
    assert any(_unclosed_for(tag) in m for m in messages), messages
