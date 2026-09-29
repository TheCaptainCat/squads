"""``Service.read_body``'s read-time expansion of a ``sq:view:<name>`` tag, table-driven over
tag position and body shape, the two dangling-name/render-failure modes, no-recursion, and
the read-only round trip that keeps expanded bytes off disk."""

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

#: The one view that ships bundled with a resolvable template.
_BUNDLED_VIEW = "milestone_rollup"


def _reopen(project) -> Service:
    """A fresh ``Service`` bound to whatever workflow override is on disk right now."""
    return Service(project, spec=load_workflow_spec(squad_dir=project.squad_dir))


async def _text(svc, item_id: str) -> str:
    path = svc.paths.abspath((await svc.get(item_id)).path)
    return path.read_text(encoding="utf-8")


async def _write_text(svc, item_id: str, text: str) -> None:
    path = svc.paths.abspath((await svc.get(item_id)).path)
    path.write_text(text, encoding="utf-8")


async def _set_raw_body(svc, item_id: str, body_text: str) -> None:
    """Write *body_text* into ``sq:body`` verbatim, bypassing ``set_body``/``reject_markers``."""
    text = await _text(svc, item_id)
    new_text = sections.replace_section(text, markers.BODY, body_text)
    await _write_text(svc, item_id, new_text)


def _append_view_declaration(squad_dir: Path, name: str, kind: str = "subtask") -> None:
    """Add ``[views.<name>]`` to the squad's ``.overrides/workflow.toml``, preserving whatever
    the file already declares."""
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    path = override_dir / "workflow.toml"
    existing = (
        path.read_text(encoding="utf-8")
        if path.is_file()
        else (f"# squads:override-base:{__version__}\n")
    )
    path.write_text(
        existing + f'\n[views.{name}]\nsource = {{ kind = "subentity", name = "{kind}" }}\n',
        encoding="utf-8",
    )
    invalidate_squad_dir(squad_dir)


def _declare_static_view(
    squad_dir: Path, name: str, template_text: str, *, kind: str = "subtask"
) -> None:
    """A subentity-source view over *kind* whose template emits *template_text* verbatim."""
    _append_view_declaration(squad_dir, name, kind)
    target = squad_dir / ".overrides" / "templates" / "views" / f"{name}.md.j2"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(template_text, encoding="utf-8")
    invalidate_squad_dir(squad_dir)


def _declare_dangling_view(squad_dir: Path, name: str) -> None:
    """Declare a ``[views.<name>]`` entry with no presentation template anywhere."""
    _append_view_declaration(squad_dir, name)


def _assert_in_order(text: str, *substrings: str) -> None:
    """Every *substrings* entry occurs in *text*, each strictly after the previous one ends."""
    pos = -1
    for s in substrings:
        idx = text.find(s, pos + 1)
        assert idx > pos, f"{s!r} not found in order in {text!r}"
        pos = idx + len(s)


# --------------------------------------------------------------------------- position x shape


async def test_a_body_with_no_tag_at_all_reads_back_byte_identical(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    await svc.set_body(task.id, "Plain prose, nothing marker-shaped.")

    before = await svc.read_body(task.id)
    after = await svc.read_body(task.id)

    assert before == after == "Plain prose, nothing marker-shaped."


async def test_an_empty_body_reads_back_as_empty(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    await _set_raw_body(svc, task.id, "")

    assert (await svc.read_body(task.id)) == ""


async def test_a_tag_alone_in_an_otherwise_empty_body_expands_to_exactly_the_rendered_output(
    svc,
) -> None:
    task = (await create_item(svc, "task", "T")).item
    await _set_raw_body(svc, task.id, f"<!-- sq:{markers.view_tag(_BUNDLED_VIEW)} -->")
    expected = await svc.render_view(_BUNDLED_VIEW, task.id)

    body = await svc.read_body(task.id)

    assert body == expected.strip("\n")


async def test_a_tag_at_the_start_of_the_body_expands_in_place_prose_after_survives(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    tag_line = f"<!-- sq:{markers.view_tag(_BUNDLED_VIEW)} -->"
    await _set_raw_body(svc, task.id, f"{tag_line}\nprose after.")
    expected = await svc.render_view(_BUNDLED_VIEW, task.id)

    body = await svc.read_body(task.id)

    assert markers.view_tag(_BUNDLED_VIEW) not in body
    _assert_in_order(body, expected, "prose after.")


async def test_a_tag_in_the_middle_of_the_body_expands_in_place_prose_before_and_after_survive(
    svc,
) -> None:
    task = (await create_item(svc, "task", "T")).item
    tag_line = f"<!-- sq:{markers.view_tag(_BUNDLED_VIEW)} -->"
    await _set_raw_body(svc, task.id, f"prose before.\n{tag_line}\nprose after.")
    expected = await svc.render_view(_BUNDLED_VIEW, task.id)

    body = await svc.read_body(task.id)

    assert markers.view_tag(_BUNDLED_VIEW) not in body
    _assert_in_order(body, "prose before.", expected, "prose after.")


async def test_a_tag_at_the_end_of_the_body_expands_in_place_prose_before_survives(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    await _set_raw_body(svc, task.id, "prose before.")
    await svc.add_view(task.id, _BUNDLED_VIEW)
    expected = await svc.render_view(_BUNDLED_VIEW, task.id)

    body = await svc.read_body(task.id)

    assert markers.view_tag(_BUNDLED_VIEW) not in body
    _assert_in_order(body, "prose before.", expected.strip("\n"))


async def test_several_tags_in_one_body_each_expand_independently_in_place(project) -> None:
    _declare_static_view(project.squad_dir, "alpha_view", "ALPHA-OUTPUT")
    _declare_static_view(project.squad_dir, "beta_view", "BETA-OUTPUT")
    svc = _reopen(project)
    task = (await create_item(svc, "task", "T")).item
    alpha = f"<!-- sq:{markers.view_tag('alpha_view')} -->"
    beta = f"<!-- sq:{markers.view_tag('beta_view')} -->"
    await _set_raw_body(svc, task.id, f"start.\n{alpha}\nmiddle.\n{beta}\nend.")

    body = await svc.read_body(task.id)

    assert body == "start.\n\nALPHA-OUTPUT\n\nmiddle.\n\nBETA-OUTPUT\n\nend."


async def test_the_same_view_tag_repeated_expands_at_each_of_its_own_positions(project) -> None:
    """A repeated tag, a shape a hand edit could carry, expands positionally, not just once."""
    _declare_static_view(project.squad_dir, "repeated_view", "R")
    svc = _reopen(project)
    task = (await create_item(svc, "task", "T")).item
    tag = f"<!-- sq:{markers.view_tag('repeated_view')} -->"
    await _set_raw_body(svc, task.id, f"one {tag} two {tag} three")

    body = await svc.read_body(task.id)

    assert body == "one \n\nR\n\n two \n\nR\n\n three"


async def test_a_view_tag_adjacent_to_the_neighbouring_discussion_region_leaves_it_untouched(
    svc,
) -> None:
    """Expansion is scoped to ``sq:body`` alone; a tag in the neighbouring discussion region
    is never touched by either read."""
    task = (await create_item(svc, "task", "T")).item
    await _set_raw_body(svc, task.id, f"<!-- sq:{markers.view_tag(_BUNDLED_VIEW)} -->")
    expected = await svc.render_view(_BUNDLED_VIEW, task.id)
    text = await _text(svc, task.id)
    disc = sections.get_section(text, markers.DISCUSSION) or ""
    tag_line = f"<!-- sq:{markers.view_tag(_BUNDLED_VIEW)} -->"
    new_text = sections.replace_section(text, markers.DISCUSSION, f"{disc}\n{tag_line}")
    await _write_text(svc, task.id, new_text)

    body = await svc.read_body(task.id)
    discussion = await svc.read_discussion(task.id)

    assert body == expected.strip("\n")
    assert tag_line in discussion


async def test_a_non_view_unpaired_tag_is_left_exactly_as_is_the_control(svc) -> None:
    """A marker-shaped tag from outside the view family is left exactly as is, the control."""
    task = (await create_item(svc, "task", "T")).item
    foreign = "<!-- sq:some_other_tag -->"
    await _set_raw_body(svc, task.id, f"prose.\n{foreign}\nmore prose.")

    body = await svc.read_body(task.id)

    assert body == f"prose.\n{foreign}\nmore prose."


# --------------------------------------------------------------------------- failure modes


async def test_a_tag_naming_an_undeclared_view_stays_literal_and_the_read_succeeds(svc) -> None:
    task = (await create_item(svc, "task", "T")).item
    tag_line = f"<!-- sq:{markers.view_tag('no-such-view')} -->"
    await _set_raw_body(svc, task.id, f"prose.\n{tag_line}")

    body = await svc.read_body(task.id)

    assert body == f"prose.\n{tag_line}"


async def test_a_tag_naming_a_declared_view_with_no_resolvable_template_stays_literal(
    project,
) -> None:
    _declare_dangling_view(project.squad_dir, "templateless")
    svc = _reopen(project)
    task = (await create_item(svc, "task", "T")).item
    tag_line = f"<!-- sq:{markers.view_tag('templateless')} -->"
    await _set_raw_body(svc, task.id, f"prose.\n{tag_line}")

    body = await svc.read_body(task.id)

    assert body == f"prose.\n{tag_line}"


async def test_a_declared_view_whose_template_raises_under_strict_undefined_propagates(
    project,
) -> None:
    _declare_static_view(project.squad_dir, "broken_view", "{{ this_is_not_defined_anywhere }}")
    svc = _reopen(project)
    task = (await create_item(svc, "task", "T")).item
    await svc.add_view(task.id, "broken_view")

    with pytest.raises(SquadsError, match="broken_view"):
        await svc.read_body(task.id)


async def test_a_render_failure_does_not_swallow_or_degrade_to_an_empty_expansion(
    project,
) -> None:
    """A working view on the same item still expands normally; a render failure never
    degrades to an empty expansion for it too."""
    _declare_static_view(project.squad_dir, "healthy_view", "OK")
    svc = _reopen(project)
    task = (await create_item(svc, "task", "T")).item
    healthy_tag = f"<!-- sq:{markers.view_tag('healthy_view')} -->"
    await _set_raw_body(svc, task.id, healthy_tag)

    body = await svc.read_body(task.id)

    assert body == "OK"


# --------------------------------------------------------------------------- source applicability


async def test_a_source_incompatible_tag_stays_literal_and_the_read_succeeds(project) -> None:
    """A source-incompatible tag stays literal and the read succeeds, quietly, like an
    undeclared name or a missing template."""
    _declare_static_view(project.squad_dir, "story_board", "SHOULD-NEVER-RENDER", kind="finding")
    svc = _reopen(project)
    task = (await create_item(svc, "task", "T")).item
    tag_line = f"<!-- sq:{markers.view_tag('story_board')} -->"
    await _set_raw_body(svc, task.id, f"prose.\n{tag_line}")

    body = await svc.read_body(task.id)

    assert body == f"prose.\n{tag_line}"


async def test_the_same_view_on_its_hosting_type_renders_normally_the_positive_control(
    project,
) -> None:
    """The same view resolved against a compatible host still renders, the positive control."""
    _declare_static_view(project.squad_dir, "story_board", "RENDERED", kind="finding")
    svc = _reopen(project)
    review = (await create_item(svc, "review", "A review")).item
    await _set_raw_body(svc, review.id, f"<!-- sq:{markers.view_tag('story_board')} -->")

    body = await svc.read_body(review.id)

    assert body == "RENDERED"


async def test_a_hosting_type_with_zero_members_renders_empty_not_a_failure(project) -> None:
    """A hosting type with zero members renders empty output, never the quiet-skip disposition."""
    _declare_static_view(
        project.squad_dir,
        "finding_count",
        "{% for r in source %}{{ r.local_id }}{% endfor %}",
        kind="finding",
    )
    svc = _reopen(project)
    review = (await create_item(svc, "review", "A review")).item
    await _set_raw_body(svc, review.id, f"<!-- sq:{markers.view_tag('finding_count')} -->")

    body = await svc.read_body(review.id)

    assert body == ""
    assert markers.view_tag("finding_count") not in body


async def test_source_applicability_table_driven_over_host_type_by_kind(project) -> None:
    """Source applicability is table-driven over host type by declared sub-entity kind,
    exercised at the read boundary."""
    table = [
        ("review", "finding", True),
        ("task", "finding", False),
        ("feature", "story", True),
        ("task", "story", False),
        ("task", "subtask", True),
        ("review", "subtask", False),
    ]
    for host_type, hosted_kind, applies in table:
        name = f"probe_{host_type}_{hosted_kind}"
        _declare_static_view(project.squad_dir, name, "PROBE-OUTPUT", kind=hosted_kind)
        svc = _reopen(project)
        host = (await create_item(svc, host_type, "H")).item
        tag_line = f"<!-- sq:{markers.view_tag(name)} -->"
        await _set_raw_body(svc, host.id, tag_line)

        body = await svc.read_body(host.id)

        if applies:
            assert body == "PROBE-OUTPUT", (host_type, hosted_kind)
        else:
            assert body == tag_line, (host_type, hosted_kind)


async def test_a_ref_source_tag_is_unaffected_by_source_applicability_the_control(svc) -> None:
    """A ref-source tag is unaffected by source applicability, the control."""
    task = (await create_item(svc, "task", "T")).item
    await _set_raw_body(svc, task.id, f"<!-- sq:{markers.view_tag(_BUNDLED_VIEW)} -->")
    expected = await svc.render_view(_BUNDLED_VIEW, task.id)

    body = await svc.read_body(task.id)

    assert body == expected.strip("\n")


# --------------------------------------------------------------------------- no recursion


async def test_a_well_formed_tag_inside_a_views_own_output_stays_literal_not_re_expanded(
    project,
) -> None:
    inner_tag = f"<!-- sq:{markers.view_tag(_BUNDLED_VIEW)} -->"
    _declare_static_view(
        project.squad_dir, "quoting_view", f"outer text {inner_tag} more outer text"
    )
    svc = _reopen(project)
    task = (await create_item(svc, "task", "T")).item
    await _set_raw_body(svc, task.id, "")
    await svc.add_view(task.id, "quoting_view")

    body = await svc.read_body(task.id)

    assert body == f"outer text {inner_tag} more outer text"


async def test_scanning_happens_once_against_the_original_text_not_after_each_substitution(
    project,
) -> None:
    """A view whose own name appears inside its own rendered output terminates, not recurses."""
    self_tag = f"<!-- sq:{markers.view_tag('self_quoting_view')} -->"
    _declare_static_view(project.squad_dir, "self_quoting_view", self_tag)
    svc = _reopen(project)
    task = (await create_item(svc, "task", "T")).item
    await _set_raw_body(svc, task.id, "")
    await svc.add_view(task.id, "self_quoting_view")

    body = await svc.read_body(task.id)

    assert body == self_tag


# --------------------------------------------------------------------------- read-only round trip


async def test_appending_after_a_tag_leaves_the_tag_literal_on_disk_no_rendered_bytes_anywhere(
    svc,
) -> None:
    """Expansion never reaches a write path: appending to a tagged body still leaves the
    literal tag, never rendered output, on disk."""
    task = (await create_item(svc, "task", "T")).item
    await _set_raw_body(svc, task.id, f"<!-- sq:{markers.view_tag(_BUNDLED_VIEW)} -->")
    expanded_before_append = await svc.read_body(task.id)
    assert markers.view_tag(_BUNDLED_VIEW) not in expanded_before_append

    await svc.set_body(task.id, "Appended after the tag.", append=True)

    stored = await _text(svc, task.id)
    stored_body = sections.get_section(stored, markers.BODY)
    assert stored_body is not None
    assert f"<!-- sq:{markers.view_tag(_BUNDLED_VIEW)} -->" in stored_body
    assert "Appended after the tag." in stored_body
    rendered = await svc.render_view(_BUNDLED_VIEW, task.id)
    assert rendered not in stored

    body_after_append = await svc.read_body(task.id)
    _assert_in_order(body_after_append, "Appended after the tag.", expanded_before_append)


async def test_replacing_a_body_that_carries_a_tag_re_places_it_rather_than_dropping_it(
    svc,
) -> None:
    """A body replace re-places a hand-placed tag rather than dropping it."""
    task = (await create_item(svc, "task", "T")).item
    await svc.add_view(task.id, _BUNDLED_VIEW)

    await svc.set_body(task.id, "Completely new prose.", force=True)

    stored_body = sections.get_section(await _text(svc, task.id), markers.BODY)
    assert stored_body is not None
    assert markers.view_tag(_BUNDLED_VIEW) in stored_body
    body = await svc.read_body(task.id)
    assert body.startswith("Completely new prose.")
    assert body != "Completely new prose."


# --------------------------------------------------------------------------- read-time padding


async def test_a_mid_paragraph_tag_pads_out_rather_than_merging_into_the_prose(project) -> None:
    """A mid-paragraph tag pads out to a full blank line on each side, never merging into prose."""
    _declare_static_view(project.squad_dir, "notes", "NOTES-OUTPUT")
    svc = _reopen(project)
    task = (await create_item(svc, "task", "T")).item
    tag = f"<!-- sq:{markers.view_tag('notes')} -->"
    await _set_raw_body(svc, task.id, f"Line one.\n{tag}\nLine two.")

    body = await svc.read_body(task.id)

    assert body == "Line one.\n\nNOTES-OUTPUT\n\nLine two."


async def test_padding_never_doubles_an_already_blank_neighbour(project) -> None:
    """Padding never doubles an already-blank neighbour."""
    _declare_static_view(project.squad_dir, "notes", "NOTES-OUTPUT")
    svc = _reopen(project)
    task = (await create_item(svc, "task", "T")).item
    tag = f"<!-- sq:{markers.view_tag('notes')} -->"
    await _set_raw_body(svc, task.id, f"Line one.\n\n{tag}\n\nLine two.")

    body = await svc.read_body(task.id)

    assert body == "Line one.\n\nNOTES-OUTPUT\n\nLine two."


async def test_padding_never_appears_at_the_bodys_own_edges(project) -> None:
    """Padding never appears at the body's own edges."""
    _declare_static_view(project.squad_dir, "notes", "NOTES-OUTPUT")
    svc = _reopen(project)
    task = (await create_item(svc, "task", "T")).item
    tag = f"<!-- sq:{markers.view_tag('notes')} -->"
    await _set_raw_body(svc, task.id, f"{tag}\nLine two.")

    body = await svc.read_body(task.id)

    assert body == "NOTES-OUTPUT\n\nLine two."


@pytest.mark.parametrize(
    ("body_text", "expected"),
    [
        pytest.param("Line one.\n{tag}\nLine two.", "Line one.\nLine two.", id="mid-paragraph"),
        pytest.param(
            "Line one.\n\n{tag}\n\nLine two.", "Line one.\n\nLine two.", id="own-paragraph"
        ),
        pytest.param("{tag}\nLine two.", "Line two.", id="body-start"),
        pytest.param("Line one.\n{tag}", "Line one.", id="body-end"),
        pytest.param("Line one {tag} two.", "Line one two.", id="shared-line-with-prose"),
    ],
)
async def test_a_disabled_tag_is_removed_like_a_stripped_marker_never_a_blank_line(
    project, body_text: str, expected: str
) -> None:
    """A disabled tag is removed the way ``strip_marker_lines`` removes a marker: joining its
    neighbours with their own separator, never leaving a stray blank line behind."""
    _declare_static_view(project.squad_dir, "notes", "NOTES-OUTPUT")
    svc = _reopen(project)
    task = (await create_item(svc, "task", "T")).item
    disabled_tag = f"<!-- sq:{markers.view_tag('notes', disabled=True)} -->"
    await _set_raw_body(svc, task.id, body_text.format(tag=disabled_tag))

    body = await svc.read_body(task.id)

    assert body == expected


# --------------------------------------------------------------------------- single boundary


def test_expand_view_tags_has_exactly_one_caller_the_shared_body_read_boundary() -> None:
    """Expansion lives at exactly one call site, the shared body-read boundary."""
    src_root = Path(__file__).resolve().parents[2] / "src" / "squads"
    call_sites = [
        p.relative_to(src_root).as_posix()
        for p in src_root.rglob("*.py")
        for line in p.read_text(encoding="utf-8").splitlines()
        if "expand_view_tags(" in line and "def expand_view_tags(" not in line
    ]
    assert call_sites == ["_services/_items.py"]
