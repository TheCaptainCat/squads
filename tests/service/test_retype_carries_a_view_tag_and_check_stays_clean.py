"""``sq retype`` preserves the whole body verbatim, so a ``sq:view:<name>`` tag rides along to
an item's new type unchanged — accepted, named behaviour, not a bug to fix later. A view's
*name* is not type-scoped, so it still resolves under the new type exactly as it did under the
old one; a ``subentity`` source's *applicability* to its host IS type-scoped, so a retype that
lands the tag on a non-hosting type is read successfully with the tag left byte-for-byte
literal, and ``sq check`` reports it. Retype's own behaviour is unchanged either way — only the
outcome for a non-hosting landing type changes, from a clean check on an unreadable item to a
readable item with a reported finding.

Every positive-path test here also asserts ``read_body`` succeeds, not just the stored bytes and
a clean check — this class of defect reached review specifically because this suite asserted
the first two and never called ``read_body`` at all, so a retype landing on a non-hosting type
produced a clean check on an item that raised on every read.
"""

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
    await svc.insert_view(task.id, _BUNDLED_VIEW)
    before_text = (svc.paths.abspath((await svc.get(task.id)).path)).read_text(encoding="utf-8")
    before_body = get_section(before_text, markers.BODY)
    assert before_body is not None

    res = await svc.retype(task.id, "bug")

    after_text = svc.paths.abspath(res.item.path).read_text(encoding="utf-8")
    after_body = get_section(after_text, markers.BODY)
    assert after_body is not None
    # The tag's bytes AND position survive: the retype only appends a system discussion
    # comment naming both ids (see test_retype_appends_a_system_comment_naming_both_ids in
    # tests/service/test_retype.py) -- the body region itself is untouched.
    assert after_body == before_body
    assert f"<!-- sq:{markers.view_tag(_BUNDLED_VIEW)} -->" in after_body


async def test_sq_check_stays_clean_after_a_retype_carrying_a_view_tag(svc) -> None:
    """The finding correctly does not fire post-retype: a view is not type-scoped, so the name
    still resolves against the new type just as it did the old one, and the item stays
    readable throughout."""
    task = (await create_item(svc, "task", "task")).item
    await svc.insert_view(task.id, _BUNDLED_VIEW)
    body_before = await svc.read_body(task.id)

    res = await svc.retype(task.id, "bug")

    issues = await svc.check()
    assert not any(_BUNDLED_VIEW in i.message for i in issues), [i.message for i in issues]
    assert res.item.type == "bug"
    body_after = await svc.read_body(res.item.id)
    assert body_after == body_before  # unchanged: a ref source, unaffected by the retype either


async def test_a_dangling_view_tag_still_reports_after_retype_the_check_is_not_suppressed(
    svc,
) -> None:
    """Control: retype must not accidentally suppress the finding altogether -- a tag that was
    already dangling before the retype is still dangling, and still reported, after it."""
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
    """A ``subentity``-source view valid on its original (hosting) type rides along, unchanged, to a
    type that does not host the projected kind: the read succeeds with the tag left
    byte-for-byte literal, and ``sq check`` reports the applicability finding. Retype's own
    behaviour — verbatim body preservation, no refusal — is unaffected."""
    _declare_resolvable_subentity_view(project.squad_dir, "story_board", "story")
    svc = _reopen(project)
    feature = (await create_item(svc, "feature", "A feature")).item  # feature hosts "story"
    await svc.insert_view(feature.id, "story_board")
    valid_body = await svc.read_body(feature.id)  # sanity: readable and rendered before retype
    assert "<!-- sq:view:story_board -->" not in valid_body

    res = await svc.retype(feature.id, "epic")  # epic hosts no sub-entity kind at all

    assert res.item.type == "epic"
    tag_line = f"<!-- sq:{markers.view_tag('story_board')} -->"
    stored_text = svc.paths.abspath(res.item.path).read_text(encoding="utf-8")
    stored_body = get_section(stored_text, markers.BODY)
    assert stored_body is not None
    assert tag_line in stored_body  # bytes survive verbatim, exactly as ruled

    body_after = await svc.read_body(res.item.id)  # the read succeeds -- this is the whole point
    assert tag_line in body_after  # left byte-for-byte literal, not stripped, emptied, or rendered
    assert body_after.strip() == stored_body.strip()  # nothing else changed either

    issues = await svc.check()
    matches = [i for i in issues if "story_board" in i.message]
    assert matches, [i.message for i in issues]
    assert all(i.level == "error" for i in matches)
    assert any("hosts" in i.message for i in matches)
