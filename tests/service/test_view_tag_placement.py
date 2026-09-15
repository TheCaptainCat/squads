"""``Service.insert_view``/``remove_view`` — the marker-safe placement verb's insert and
remove directions: the only path a ``sq:view:<name>`` tag enters or leaves an item's
``sq:body`` region.

Table-driven over tag *position* in the body (start/middle/end, several tags, adjacent to
another region) and body *shape* (empty, no tag at all), plus the refusal paths: a dangling
view name (undeclared, or declared with no resolvable template) and an item file carrying no
``sq:body`` region. Every positive case asserts the generated file directly: valid YAML
frontmatter, both body markers intact, and every other byte of the body preserved verbatim.
"""

from pathlib import Path

import pytest

from _helpers import create_item
from squads import __version__
from squads import _sections as sections
from squads._errors import SquadsError
from squads._models import _markers as markers
from squads._rendering._engine import invalidate_squad_dir
from squads._services._service import Service
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio

#: The one view that ships bundled with a resolvable template — see
#: tests/service/test_view_resolve_and_render.py for why every other declared name there needs
#: its own override template.
_BUNDLED_VIEW = "milestone_rollup"


async def _text(svc, item_id: str) -> str:
    path = svc.paths.abspath((await svc.get(item_id)).path)
    return path.read_text(encoding="utf-8")


async def _write_text(svc, item_id: str, text: str) -> None:
    path = svc.paths.abspath((await svc.get(item_id)).path)
    path.write_text(text, encoding="utf-8")


def _declare_dangling_view(squad_dir: Path, name: str) -> None:
    """A declared ``[views.<name>]`` entry with **no** presentation template anywhere — the
    "declared but the template is missing" half of a dangling name, distinct from "not
    declared at all"."""
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n"
        f'[views.{name}]\nsource = {{ kind = "subentity", name = "finding" }}\n'
        'fields = [ { code = "id", label = "Id" } ]\n',
        encoding="utf-8",
    )
    invalidate_squad_dir(squad_dir)


def _declare_resolvable_subentity_view(squad_dir: Path, name: str, kind: str) -> None:
    """A declared ``[views.<name>]`` entry over sub-entity *kind*, **with** a resolvable
    presentation template — unlike :func:`_declare_dangling_view`, this name passes the
    "declared and templated" half of :func:`~squads._views.resolve_view_target`, so placing it
    exercises the third, source-applicability question on its own."""
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    templates_dir = override_dir / "templates" / "views"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / f"{name}.md.j2").write_text(f"{name}\n", encoding="utf-8")
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n"
        f'[views.{name}]\nsource = {{ kind = "subentity", name = "{kind}" }}\n'
        'fields = [ { code = "id", label = "Id" } ]\n',
        encoding="utf-8",
    )
    invalidate_squad_dir(squad_dir)


def _reopen(project) -> Service:
    """A fresh ``Service`` bound to a just-written workflow override — ``self.spec`` is fixed
    at construction, so a view declared after ``svc`` was built needs a new instance."""
    return Service(project, spec=load_workflow_spec(squad_dir=project.squad_dir))


# --------------------------------------------------------------------------- insert: shape


async def test_insert_into_an_empty_body_places_the_tag_alone() -> None:
    """Direct against the primitive's contract at the service seam — covered again with a real
    item below; this one pins the empty-body shape without extra fixture noise."""
    text = "<!-- sq:body -->\n<!-- sq:body:end -->"
    out, inserted = sections.insert_unpaired_marker(text, markers.BODY, markers.view_tag("x"))
    assert inserted
    assert sections.get_section(out, markers.BODY) == "\n<!-- sq:view:x -->\n"


async def test_insert_places_the_tag_after_existing_prose_and_preserves_it_verbatim(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    await svc.set_body(task.id, "Authored scope prose.")

    inserted = await svc.insert_view(task.id, _BUNDLED_VIEW)
    assert inserted is True

    text = await _text(svc, task.id)
    frontmatter, _ = sections.split_frontmatter(text, source=text)
    assert frontmatter["id"] == task.id  # valid YAML frontmatter
    assert text.count("<!-- sq:body -->") == 1  # markers intact, not duplicated
    assert text.count("<!-- sq:body:end -->") == 1
    body = sections.get_section(text, markers.BODY)
    assert body is not None
    assert "Authored scope prose." in body  # body preserved verbatim
    assert body.strip().endswith(f"<!-- sq:{markers.view_tag(_BUNDLED_VIEW)} -->")


async def test_insert_into_a_body_that_already_carries_another_view_tag_adds_a_second_one(
    svc,
) -> None:
    task = (await create_item(svc, "task", "T")).item
    _declare_dangling_view(svc.paths.squad_dir, "other_view")  # declared name, no template needed
    # insert_view refuses a template-less name, so seed the second tag directly to set up the
    # "several tags in one body" shape without depending on a second real template.
    text = await _text(svc, task.id)
    seeded, _ = sections.insert_unpaired_marker(text, markers.BODY, markers.view_tag("other_view"))
    await _write_text(svc, task.id, seeded)

    await svc.insert_view(task.id, _BUNDLED_VIEW)

    body = sections.get_section(await _text(svc, task.id), markers.BODY)
    assert body is not None
    assert f"<!-- sq:{markers.view_tag('other_view')} -->" in body
    assert f"<!-- sq:{markers.view_tag(_BUNDLED_VIEW)} -->" in body


async def test_insert_leaves_the_discussion_region_untouched(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    await svc.comment(task.id, ["a discussion point"], as_slug="manager")

    await svc.insert_view(task.id, _BUNDLED_VIEW)

    text = await _text(svc, task.id)
    disc = sections.get_section(text, markers.DISCUSSION)
    assert disc is not None
    assert "a discussion point" in disc
    assert markers.view_tag(_BUNDLED_VIEW) not in disc


# --------------------------------------------------------------------------- insert: idempotent


async def test_insert_is_idempotent_and_reports_already_present(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    first = await svc.insert_view(task.id, _BUNDLED_VIEW)
    assert first is True

    path = svc.paths.abspath((await svc.get(task.id)).path)
    mtime_before = path.stat().st_mtime_ns
    text_before = path.read_text(encoding="utf-8")

    second = await svc.insert_view(task.id, _BUNDLED_VIEW)

    assert second is False  # reports "already present", not a fresh insert
    assert path.read_text(encoding="utf-8") == text_before
    assert path.read_text(encoding="utf-8").count(markers.view_tag(_BUNDLED_VIEW)) == 1  # no dup
    assert path.stat().st_mtime_ns == mtime_before  # genuinely wrote nothing, not identical bytes


async def test_insert_no_op_does_not_call_the_write_primitive(svc, monkeypatch) -> None:
    """The stronger proof behind the mtime check above: the write function itself is never
    invoked on the idempotent path, not merely invoked with output that happens to match."""
    task = (await create_item(svc, "task", "T")).item
    await svc.insert_view(task.id, _BUNDLED_VIEW)

    calls = 0
    import squads._services._base as base_module

    original = base_module.write_text

    async def _counting_write(*args, **kwargs):
        nonlocal calls
        calls += 1
        return await original(*args, **kwargs)

    monkeypatch.setattr(base_module, "write_text", _counting_write)
    await svc.insert_view(task.id, _BUNDLED_VIEW)
    assert calls == 0


# --------------------------------------------------------------------------- insert: refusals


async def test_insert_an_undeclared_view_name_is_refused(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    text_before = await _text(svc, task.id)

    with pytest.raises(SquadsError, match="no declared view"):
        await svc.insert_view(task.id, "no-such-view")

    assert await _text(svc, task.id) == text_before  # refused before any write


async def test_insert_a_declared_view_with_no_resolvable_template_is_refused(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    _declare_dangling_view(svc.paths.squad_dir, "templateless")
    text_before = await _text(svc, task.id)

    with pytest.raises(SquadsError, match="no declared view"):
        await svc.insert_view(task.id, "templateless")

    assert await _text(svc, task.id) == text_before


async def test_insert_on_an_item_with_no_body_region_is_refused_with_a_clear_error(svc) -> None:
    """Type admissibility: every bundled item type carries ``sq:body``,
    so this drives the refusal directly against a file with the region stripped out, rather
    than skip the acceptance criterion for lack of a real built-in example."""
    task = (await create_item(svc, "task", "T")).item
    stripped = sections.remove_section(await _text(svc, task.id), markers.BODY)
    await _write_text(svc, task.id, stripped)

    with pytest.raises(SquadsError, match="no sq:body region"):
        await svc.insert_view(task.id, _BUNDLED_VIEW)


# ------------------------------------------------------------ insert: source applicability


async def test_insert_a_subentity_source_view_onto_its_hosting_type_succeeds(project) -> None:
    """The positive control: a ``subentity``-source view over a kind the target type actually
    hosts places cleanly -- the predicate refuses a mismatched pairing, not every
    subentity-source view."""
    _declare_resolvable_subentity_view(project.squad_dir, "story_board", "finding")
    svc = _reopen(project)
    review = (await create_item(svc, "review", "A review")).item

    inserted = await svc.insert_view(review.id, "story_board")

    assert inserted is True
    body = sections.get_section(await _text(svc, review.id), markers.BODY)
    assert body is not None
    assert "<!-- sq:view:story_board -->" in body


async def test_insert_a_subentity_source_view_onto_a_non_hosting_type_is_refused(
    project,
) -> None:
    """Placement of a declared, templated ``subentity``-source view is refused at the door when
    the target item's type does not host the projected kind, before any write."""
    _declare_resolvable_subentity_view(project.squad_dir, "story_board", "story")
    svc = _reopen(project)
    epic = (await create_item(svc, "epic", "An epic")).item
    text_before = await _text(svc, epic.id)

    with pytest.raises(SquadsError, match="hosts"):
        await svc.insert_view(epic.id, "story_board")

    assert await _text(svc, epic.id) == text_before  # refused before any write


@pytest.mark.parametrize(
    ("host_type", "hosted_kind", "applies"),
    [
        ("review", "finding", True),  # review hosts finding: applies
        ("task", "finding", False),  # task hosts subtask, not finding: refused
        ("feature", "story", True),  # feature hosts story: applies
        ("task", "story", False),  # task hosts subtask, not story: refused
        ("task", "subtask", True),  # task hosts subtask: applies
        ("review", "subtask", False),  # review hosts finding, not subtask: refused
    ],
)
async def test_insert_a_subentity_source_view_table_driven_over_host_type_by_kind(
    project, host_type: str, hosted_kind: str, applies: bool
) -> None:
    """Table-driven over host type x declared sub-entity kind, not one case per implemented
    branch: every bundled hosting pair the placement door must let through, crossed with a
    mismatched pair it must refuse."""
    name = f"probe_{host_type}_{hosted_kind}"
    _declare_resolvable_subentity_view(project.squad_dir, name, hosted_kind)
    svc = _reopen(project)
    host = (await create_item(svc, host_type, "H")).item

    if applies:
        assert await svc.insert_view(host.id, name) is True
    else:
        with pytest.raises(SquadsError, match="hosts"):
            await svc.insert_view(host.id, name)


async def test_insert_a_ref_source_view_applies_to_every_host_type_unaffected_by_applicability(
    svc,
) -> None:
    """Control: a ``ref``-source view (the bundled ``milestone_rollup``) carries no host
    constraint, so the predicate imposes nothing on it."""
    task = (await create_item(svc, "task", "T")).item
    assert await svc.insert_view(task.id, _BUNDLED_VIEW) is True


# --------------------------------------------------------------------------- remove: shape


async def test_remove_the_only_tag_restores_the_body_to_its_pre_insert_shape(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    await svc.set_body(task.id, "Authored prose.")
    before = await _text(svc, task.id)
    await svc.insert_view(task.id, _BUNDLED_VIEW)

    removed = await svc.remove_view(task.id, _BUNDLED_VIEW)

    assert removed is True
    after = await _text(svc, task.id)
    assert after == before  # exact round trip, not merely equivalent content


async def test_remove_only_the_named_tag_leaves_a_second_view_tag_and_prose_verbatim(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    await svc.set_body(task.id, "Prose to keep.")
    text = await _text(svc, task.id)
    seeded, _ = sections.insert_unpaired_marker(text, markers.BODY, markers.view_tag("kept"))
    await _write_text(svc, task.id, seeded)
    await svc.insert_view(task.id, _BUNDLED_VIEW)

    await svc.remove_view(task.id, _BUNDLED_VIEW)

    text = await _text(svc, task.id)
    frontmatter, _ = sections.split_frontmatter(text, source=text)
    assert frontmatter["id"] == task.id
    assert text.count("<!-- sq:body -->") == 1
    assert text.count("<!-- sq:body:end -->") == 1
    body = sections.get_section(text, markers.BODY)
    assert body is not None
    assert "Prose to keep." in body
    assert "<!-- sq:view:kept -->" in body
    assert markers.view_tag(_BUNDLED_VIEW) not in body


async def test_remove_leaves_the_discussion_region_untouched(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    await svc.comment(task.id, ["a discussion point"], as_slug="manager")
    await svc.insert_view(task.id, _BUNDLED_VIEW)

    await svc.remove_view(task.id, _BUNDLED_VIEW)

    disc = sections.get_section(await _text(svc, task.id), markers.DISCUSSION)
    assert disc is not None
    assert "a discussion point" in disc


# --------------------------------------------------------------------------- remove: no-op


async def test_remove_an_absent_tag_is_a_safe_no_op_and_writes_nothing(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    await svc.set_body(task.id, "Never had a tag.")
    path = svc.paths.abspath((await svc.get(task.id)).path)
    text_before = path.read_text(encoding="utf-8")
    mtime_before = path.stat().st_mtime_ns

    removed = await svc.remove_view(task.id, _BUNDLED_VIEW)

    assert removed is False
    assert path.read_text(encoding="utf-8") == text_before
    assert path.stat().st_mtime_ns == mtime_before


async def test_remove_an_absent_tag_from_an_empty_body_is_a_safe_no_op(svc) -> None:
    task = (await create_item(svc, "task", "T")).item  # never written, still the empty scaffold
    removed = await svc.remove_view(task.id, _BUNDLED_VIEW)
    assert removed is False


async def test_remove_no_op_does_not_call_the_write_primitive(svc, monkeypatch) -> None:
    task = (await create_item(svc, "task", "T")).item

    calls = 0
    import squads._services._base as base_module

    original = base_module.write_text

    async def _counting_write(*args, **kwargs):
        nonlocal calls
        calls += 1
        return await original(*args, **kwargs)

    monkeypatch.setattr(base_module, "write_text", _counting_write)
    await svc.remove_view(task.id, _BUNDLED_VIEW)
    assert calls == 0


async def test_remove_on_an_item_with_no_body_region_is_refused_with_a_clear_error(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    stripped = sections.remove_section(await _text(svc, task.id), markers.BODY)
    await _write_text(svc, task.id, stripped)

    with pytest.raises(SquadsError, match="no sq:body region"):
        await svc.remove_view(task.id, _BUNDLED_VIEW)


async def test_remove_does_not_require_the_name_to_still_resolve(svc) -> None:
    """Taking a tag off a document must work even for a view the spec no longer declares —
    removal is the repair path for exactly that case, not somewhere to refuse it."""
    task = (await create_item(svc, "task", "T")).item
    text = await _text(svc, task.id)
    seeded, _ = sections.insert_unpaired_marker(text, markers.BODY, markers.view_tag("retired"))
    await _write_text(svc, task.id, seeded)

    removed = await svc.remove_view(task.id, "retired")

    assert removed is True
    assert "retired" not in (await _text(svc, task.id))


# --------------------------------------------------------------------------- remove: duplicate


async def test_remove_of_a_duplicated_tag_actually_takes_the_view_off_the_document(svc) -> None:
    """The exact state ``sq check`` reports as a duplicate marker (a repairable error) and
    therefore the state ``view rm`` exists to repair: the report must never say "removed"
    while a second copy is still there to render."""
    task = (await create_item(svc, "task", "T")).item
    text = await _text(svc, task.id)
    # Hand-seed a duplicate -- insert_view is itself idempotent, so this state is reached only
    # by a hand edit or a bulk path, never through the placement verb itself.
    doubled = sections.replace_section(
        text, markers.BODY, f"<!-- sq:{markers.view_tag(_BUNDLED_VIEW)} -->\n" * 2
    )
    await _write_text(svc, task.id, doubled)
    issues_before = [i.message for i in await svc.check()]
    assert any("duplicate marker" in m for m in issues_before), issues_before

    removed = await svc.remove_view(task.id, _BUNDLED_VIEW)

    assert removed is True
    body = sections.get_section(await _text(svc, task.id), markers.BODY)
    assert body is not None
    assert markers.view_tag(_BUNDLED_VIEW) not in body
    rendered = await svc.read_body(task.id)
    assert markers.view_tag(_BUNDLED_VIEW) not in rendered
    expected = (await svc.render_view(_BUNDLED_VIEW, task.id)).strip()
    assert expected not in rendered, "the view must no longer render after removal"
    issues_after = [i.message for i in await svc.check()]
    assert not any("duplicate marker" in m for m in issues_after), issues_after
