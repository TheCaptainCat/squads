"""``Service.add_view``/``disable_view``: place-or-re-enable and disable (never delete),
table-driven over tag position and body shape, plus the refusal paths and every positive
case's direct file assertion — valid frontmatter, intact markers, verbatim body."""

from pathlib import Path

import pytest

from _helpers import create_item
from squads import __version__
from squads import _sections as sections
from squads._errors import SquadsError
from squads._models import _markers as markers
from squads._rendering._engine import invalidate_squad_dir
from squads._services._service import Service
from squads._views import place_view_tags
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio

#: The one view that ships bundled with a resolvable template.
_BUNDLED_VIEW = "milestone_rollup"


async def _text(svc, item_id: str) -> str:
    path = svc.paths.abspath((await svc.get(item_id)).path)
    return path.read_text(encoding="utf-8")


async def _write_text(svc, item_id: str, text: str) -> None:
    path = svc.paths.abspath((await svc.get(item_id)).path)
    path.write_text(text, encoding="utf-8")


async def _seed_tag_directly(svc, item_id: str, name: str) -> None:
    """Place *name*'s tag through the real placement routine, bypassing ``add_view``'s own gate."""
    item = await svc.get(item_id)
    text = await _text(svc, item_id)
    region = sections.get_section(text, markers.BODY) or ""
    new_inner = place_view_tags(
        region,
        None,
        seeded=frozenset({name}),
        spec=svc.spec,
        item_type=item.type,
        addr=item.sequence_id,
    )
    await _write_text(svc, item_id, sections.replace_section(text, markers.BODY, new_inner))


def _declare_dangling_view(squad_dir: Path, name: str) -> None:
    """Declare a ``[views.<name>]`` entry with no presentation template anywhere."""
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n"
        f'[views.{name}]\nsource = {{ kind = "subentity", name = "finding" }}\n',
        encoding="utf-8",
    )
    invalidate_squad_dir(squad_dir)


def _declare_resolvable_subentity_view(squad_dir: Path, name: str, kind: str) -> None:
    """Declare a resolvable, templated ``[views.<name>]`` entry over sub-entity *kind*."""
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
    """A fresh ``Service`` bound to a just-written workflow override."""
    return Service(project, spec=load_workflow_spec(squad_dir=project.squad_dir))


# --------------------------------------------------------------------------- insert: shape


async def test_insert_places_the_tag_after_existing_prose_and_preserves_it_verbatim(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    await svc.set_body(task.id, "Authored scope prose.")

    inserted = await svc.add_view(task.id, _BUNDLED_VIEW)
    assert inserted is True

    text = await _text(svc, task.id)
    frontmatter, _ = sections.split_frontmatter(text, source=text)
    assert frontmatter["id"] == task.id
    assert text.count("<!-- sq:body -->") == 1
    assert text.count("<!-- sq:body:end -->") == 1
    body = sections.get_section(text, markers.BODY)
    assert body is not None
    assert "Authored scope prose." in body
    assert body.strip().endswith(f"<!-- sq:{markers.view_tag(_BUNDLED_VIEW)} -->")


async def test_insert_into_a_body_that_already_carries_another_view_tag_adds_a_second_one(
    svc,
) -> None:
    task = (await create_item(svc, "task", "T")).item
    _declare_dangling_view(svc.paths.squad_dir, "other_view")
    await _seed_tag_directly(svc, task.id, "other_view")

    await svc.add_view(task.id, _BUNDLED_VIEW)

    body = sections.get_section(await _text(svc, task.id), markers.BODY)
    assert body is not None
    assert f"<!-- sq:{markers.view_tag('other_view')} -->" in body
    assert f"<!-- sq:{markers.view_tag(_BUNDLED_VIEW)} -->" in body


async def test_insert_leaves_the_discussion_region_untouched(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    await svc.comment(task.id, ["a discussion point"], as_slug="manager")

    await svc.add_view(task.id, _BUNDLED_VIEW)

    text = await _text(svc, task.id)
    disc = sections.get_section(text, markers.DISCUSSION)
    assert disc is not None
    assert "a discussion point" in disc
    assert markers.view_tag(_BUNDLED_VIEW) not in disc


# --------------------------------------------------------------------------- insert: idempotent


async def test_insert_is_idempotent_and_reports_already_present(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    first = await svc.add_view(task.id, _BUNDLED_VIEW)
    assert first is True

    path = svc.paths.abspath((await svc.get(task.id)).path)
    mtime_before = path.stat().st_mtime_ns
    text_before = path.read_text(encoding="utf-8")

    second = await svc.add_view(task.id, _BUNDLED_VIEW)

    assert second is False
    assert path.read_text(encoding="utf-8") == text_before
    assert path.read_text(encoding="utf-8").count(markers.view_tag(_BUNDLED_VIEW)) == 1
    assert path.stat().st_mtime_ns == mtime_before


async def test_insert_no_op_does_not_call_the_write_primitive(svc, monkeypatch) -> None:
    """The write function itself is never invoked on the idempotent path."""
    task = (await create_item(svc, "task", "T")).item
    await svc.add_view(task.id, _BUNDLED_VIEW)

    calls = 0
    import squads._services._base as base_module
    from squads._itemfile import write_text as original

    async def _counting_write(*args, **kwargs):
        nonlocal calls
        calls += 1
        return await original(*args, **kwargs)

    monkeypatch.setattr(base_module, "write_text", _counting_write)
    await svc.add_view(task.id, _BUNDLED_VIEW)
    assert calls == 0


# --------------------------------------------------------------------------- insert: refusals


async def test_insert_an_undeclared_view_name_is_refused(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    text_before = await _text(svc, task.id)

    with pytest.raises(SquadsError, match="no declared view"):
        await svc.add_view(task.id, "no-such-view")

    assert await _text(svc, task.id) == text_before


async def test_insert_a_declared_view_with_no_resolvable_template_is_refused(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    _declare_dangling_view(svc.paths.squad_dir, "templateless")
    text_before = await _text(svc, task.id)

    with pytest.raises(SquadsError, match="no declared view"):
        await svc.add_view(task.id, "templateless")

    assert await _text(svc, task.id) == text_before


async def test_insert_on_an_item_with_no_body_region_is_refused_with_a_clear_error(svc) -> None:
    """Insert on an item with no body region is refused with a clear error."""
    task = (await create_item(svc, "task", "T")).item
    stripped = sections.remove_section(await _text(svc, task.id), markers.BODY)
    await _write_text(svc, task.id, stripped)

    with pytest.raises(SquadsError, match="no sq:body region"):
        await svc.add_view(task.id, _BUNDLED_VIEW)


# ------------------------------------------------------------ insert: source applicability


async def test_insert_a_subentity_source_view_onto_its_hosting_type_succeeds(project) -> None:
    """A subentity-source view over a kind the target type actually hosts places cleanly."""
    _declare_resolvable_subentity_view(project.squad_dir, "story_board", "finding")
    svc = _reopen(project)
    review = (await create_item(svc, "review", "A review")).item

    inserted = await svc.add_view(review.id, "story_board")

    assert inserted is True
    body = sections.get_section(await _text(svc, review.id), markers.BODY)
    assert body is not None
    assert "<!-- sq:view:story_board -->" in body


async def test_insert_a_subentity_source_view_onto_a_non_hosting_type_is_refused(
    project,
) -> None:
    """A subentity-source view onto a non-hosting type is refused at the door, before any write."""
    _declare_resolvable_subentity_view(project.squad_dir, "story_board", "story")
    svc = _reopen(project)
    epic = (await create_item(svc, "epic", "An epic")).item
    text_before = await _text(svc, epic.id)

    with pytest.raises(SquadsError, match="hosts"):
        await svc.add_view(epic.id, "story_board")

    assert await _text(svc, epic.id) == text_before


@pytest.mark.parametrize(
    ("host_type", "hosted_kind", "applies"),
    [
        ("review", "finding", True),
        ("task", "finding", False),
        ("feature", "story", True),
        ("task", "story", False),
        ("task", "subtask", True),
        ("review", "subtask", False),
    ],
)
async def test_insert_a_subentity_source_view_table_driven_over_host_type_by_kind(
    project, host_type: str, hosted_kind: str, applies: bool
) -> None:
    """Source applicability is table-driven over host type by declared sub-entity kind."""
    name = f"probe_{host_type}_{hosted_kind}"
    _declare_resolvable_subentity_view(project.squad_dir, name, hosted_kind)
    svc = _reopen(project)
    host = (await create_item(svc, host_type, "H")).item

    if applies:
        assert await svc.add_view(host.id, name) is True
    else:
        with pytest.raises(SquadsError, match="hosts"):
            await svc.add_view(host.id, name)


async def test_insert_a_ref_source_view_applies_to_every_host_type_unaffected_by_applicability(
    svc,
) -> None:
    """A ref-source view applies to every host type, unaffected by applicability."""
    task = (await create_item(svc, "task", "T")).item
    assert await svc.add_view(task.id, _BUNDLED_VIEW) is True


# --------------------------------------------------------------------------- disable: shape


async def test_disable_turns_the_tag_disabled_in_place_not_removed(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    await svc.set_body(task.id, "Authored prose.")
    await svc.add_view(task.id, _BUNDLED_VIEW)

    disabled = await svc.disable_view(task.id, _BUNDLED_VIEW)

    assert disabled is True
    body = sections.get_section(await _text(svc, task.id), markers.BODY)
    assert body is not None
    assert "Authored prose." in body
    assert f"<!-- sq:{markers.view_tag(_BUNDLED_VIEW, disabled=True)} -->" in body
    assert f"<!-- sq:{markers.view_tag(_BUNDLED_VIEW)} -->" not in body


async def test_disable_only_the_named_tag_leaves_a_second_view_tag_and_prose_verbatim(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    await svc.set_body(task.id, "Prose to keep.")
    await _seed_tag_directly(svc, task.id, "kept")
    await svc.add_view(task.id, _BUNDLED_VIEW)

    await svc.disable_view(task.id, _BUNDLED_VIEW)

    text = await _text(svc, task.id)
    frontmatter, _ = sections.split_frontmatter(text, source=text)
    assert frontmatter["id"] == task.id
    assert text.count("<!-- sq:body -->") == 1
    assert text.count("<!-- sq:body:end -->") == 1
    body = sections.get_section(text, markers.BODY)
    assert body is not None
    assert "Prose to keep." in body
    assert "<!-- sq:view:kept -->" in body
    assert markers.view_tag(_BUNDLED_VIEW, disabled=True) in body


async def test_disable_leaves_the_discussion_region_untouched(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    await svc.comment(task.id, ["a discussion point"], as_slug="manager")
    await svc.add_view(task.id, _BUNDLED_VIEW)

    await svc.disable_view(task.id, _BUNDLED_VIEW)

    disc = sections.get_section(await _text(svc, task.id), markers.DISCUSSION)
    assert disc is not None
    assert "a discussion point" in disc


# --------------------------------------------------------------------------- disable: no-op


async def test_disable_an_absent_tag_places_it_disabled(svc) -> None:
    """``view disable`` places the tag disabled when it was never there at all."""
    task = (await create_item(svc, "task", "T")).item
    await svc.set_body(task.id, "Never had a tag.")

    disabled = await svc.disable_view(task.id, _BUNDLED_VIEW)

    assert disabled is True
    body = sections.get_section(await _text(svc, task.id), markers.BODY)
    assert body is not None
    assert markers.view_tag(_BUNDLED_VIEW, disabled=True) in body


async def test_disable_an_already_disabled_tag_is_a_safe_no_op(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    await svc.disable_view(task.id, _BUNDLED_VIEW)
    path = svc.paths.abspath((await svc.get(task.id)).path)
    text_before = path.read_text(encoding="utf-8")
    mtime_before = path.stat().st_mtime_ns

    disabled = await svc.disable_view(task.id, _BUNDLED_VIEW)

    assert disabled is False
    assert path.read_text(encoding="utf-8") == text_before
    assert path.stat().st_mtime_ns == mtime_before


async def test_disable_no_op_does_not_call_the_write_primitive(svc, monkeypatch) -> None:
    task = (await create_item(svc, "task", "T")).item
    await svc.disable_view(task.id, _BUNDLED_VIEW)

    calls = 0
    import squads._services._base as base_module
    from squads._itemfile import write_text as original

    async def _counting_write(*args, **kwargs):
        nonlocal calls
        calls += 1
        return await original(*args, **kwargs)

    monkeypatch.setattr(base_module, "write_text", _counting_write)
    await svc.disable_view(task.id, _BUNDLED_VIEW)
    assert calls == 0


async def test_disable_on_an_item_with_no_body_region_is_refused_with_a_clear_error(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    stripped = sections.remove_section(await _text(svc, task.id), markers.BODY)
    await _write_text(svc, task.id, stripped)

    with pytest.raises(SquadsError, match="no sq:body region"):
        await svc.disable_view(task.id, _BUNDLED_VIEW)


async def test_disable_does_not_require_the_name_to_still_resolve(svc) -> None:
    """Disabling a tag works even for a view the spec no longer declares."""
    task = (await create_item(svc, "task", "T")).item
    await _seed_tag_directly(svc, task.id, "retired")

    disabled = await svc.disable_view(task.id, "retired")

    assert disabled is True
    body = await _text(svc, task.id)
    assert markers.open_marker(markers.view_tag("retired", disabled=True)) in body
    assert markers.open_marker(markers.view_tag("retired")) not in body


# --------------------------------------------------------------------------- disable: duplicate


async def test_disable_of_a_duplicated_tag_collapses_every_copy_to_one_disabled_tag(svc) -> None:
    """Disabling a duplicated tag collapses every copy into one disabled tag."""
    task = (await create_item(svc, "task", "T")).item
    text = await _text(svc, task.id)
    doubled = sections.replace_section(
        text, markers.BODY, f"<!-- sq:{markers.view_tag(_BUNDLED_VIEW)} -->\n" * 2
    )
    await _write_text(svc, task.id, doubled)
    issues_before = [i.message for i in await svc.check()]
    assert any(f"duplicate sq:view:{_BUNDLED_VIEW} tag" in m for m in issues_before), issues_before

    disabled = await svc.disable_view(task.id, _BUNDLED_VIEW)

    assert disabled is True
    body = sections.get_section(await _text(svc, task.id), markers.BODY)
    assert body is not None
    assert body.count(_BUNDLED_VIEW) == 1
    assert markers.view_tag(_BUNDLED_VIEW, disabled=True) in body
    rendered = await svc.read_body(task.id)
    assert markers.view_tag(_BUNDLED_VIEW) not in rendered
    expected = (await svc.render_view(_BUNDLED_VIEW, task.id)).strip()
    assert expected not in rendered, "a disabled view must no longer render"
    issues_after = [i.message for i in await svc.check()]
    assert not any("duplicate" in m for m in issues_after), issues_after


async def test_add_view_on_two_enabled_copies_collapses_to_one_not_a_no_op(svc) -> None:
    """Two already-enabled copies collapse to one on ``view add``, not a no-op."""
    task = (await create_item(svc, "task", "T")).item
    text = await _text(svc, task.id)
    doubled = sections.replace_section(
        text, markers.BODY, f"<!-- sq:{markers.view_tag(_BUNDLED_VIEW)} -->\n" * 2
    )
    await _write_text(svc, task.id, doubled)

    placed = await svc.add_view(task.id, _BUNDLED_VIEW)

    assert placed is True, "two same-state copies are not the settled state view add reports"
    body = sections.get_section(await _text(svc, task.id), markers.BODY)
    assert body is not None
    assert body.count(_BUNDLED_VIEW) == 1
    issues_after = [i.message for i in await svc.check()]
    assert not any("duplicate" in m for m in issues_after), issues_after


async def test_disable_view_on_two_disabled_copies_collapses_to_one_not_a_no_op(svc) -> None:
    """Two already-disabled copies collapse to one on ``view disable``, not a no-op."""
    task = (await create_item(svc, "task", "T")).item
    text = await _text(svc, task.id)
    doubled = sections.replace_section(
        text,
        markers.BODY,
        f"<!-- sq:{markers.view_tag(_BUNDLED_VIEW, disabled=True)} -->\n" * 2,
    )
    await _write_text(svc, task.id, doubled)

    disabled = await svc.disable_view(task.id, _BUNDLED_VIEW)

    assert disabled is True, "two same-state copies are not the settled state view disable reports"
    body = sections.get_section(await _text(svc, task.id), markers.BODY)
    assert body is not None
    assert body.count(_BUNDLED_VIEW) == 1
    issues_after = [i.message for i in await svc.check()]
    assert not any("duplicate" in m for m in issues_after), issues_after


async def test_add_view_on_a_single_enabled_copy_stays_a_true_no_op(svc) -> None:
    """A single enabled copy stays a true no-op, byte-unchanged."""
    task = (await create_item(svc, "task", "T")).item
    await svc.add_view(task.id, _BUNDLED_VIEW)
    before = await _text(svc, task.id)

    placed = await svc.add_view(task.id, _BUNDLED_VIEW)

    assert placed is False
    assert await _text(svc, task.id) == before


async def test_a_tag_sharing_a_line_with_prose_never_rewrites_that_prose(svc) -> None:
    """A tag sharing a line with prose never rewrites that prose on a later write."""
    task = (await create_item(svc, "task", "T")).item
    hand_edited = sections.replace_section(
        await _text(svc, task.id),
        markers.BODY,
        f"Some notes here <!-- sq:{markers.view_tag(_BUNDLED_VIEW)} -->\nmore notes.",
    )
    await _write_text(svc, task.id, hand_edited)

    await svc.set_body(task.id, "Appended line.", append=True)

    body = sections.get_section(await _text(svc, task.id), markers.BODY)
    assert body is not None
    assert body.strip("\n") == (
        "Some notes here\nmore notes.\n\nAppended line.\n\n"
        f"<!-- sq:{markers.view_tag(_BUNDLED_VIEW)} -->"
    )
