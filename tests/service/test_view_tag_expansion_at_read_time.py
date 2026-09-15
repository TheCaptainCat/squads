"""``Service.read_body`` — read-time expansion of a ``sq:view:<name>`` tag to that view's
rendered output, at the one shared body-read boundary every read surface inherits from
(``sq show``, ``--raw``, ``--json``'s body field, the TUI, the operator pane, the skill read;
CLI-level coverage of that inheritance lives in
``tests/cli/test_view_tag_expansion_at_read_time_cli.py``).

Table-driven over tag *position* in the body (start/middle/end, several tags, a tag adjacent to
a neighbouring region) and body *shape* (empty, no tag at all, a non-view unpaired tag as a
control), plus the two failure modes kept deliberately distinct (a dangling name stays literal and
the read succeeds; a declared view whose template raises propagates as ``SquadsError``), the
no-recursion property, and the read-only round trip that keeps expanded bytes off disk.

A view declared via a fresh ``.overrides/workflow.toml`` is invisible to a ``svc`` fixture
already constructed (``self.spec`` is fixed at construction — see
``tests/service/test_view_resolve_and_render.py``), so any test that declares one reopens a
fresh ``Service`` afterwards (:func:`_reopen`); tests that only use the one view that ships
bundled (``milestone_rollup``) use the shared ``svc`` fixture directly, same as
``tests/service/test_view_tag_placement.py``.
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

#: The one view that ships bundled with a resolvable template. Resolved against a plain task
#: with no ``targets`` refs, its render is deterministic (three empty groups) and real
#: production output — not a test-authored stand-in — so the expected substitution text is
#: always computed fresh via ``svc.render_view`` rather than hardcoded.
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
    """Write *body_text* into ``sq:body`` verbatim, bypassing ``set_body``/``reject_markers``.

    The placement verb (``insert_view``) only ever anchors at the region's end, so building the
    *start*/*middle*/*several-tags* fixtures this table needs requires placing marker text at
    an arbitrary position directly — legitimate for fixture construction (as
    ``tests/service/test_view_tag_placement.py`` already does the same way), even though no
    production verb writes a body this way itself.
    """
    text = await _text(svc, item_id)
    new_text = sections.replace_section(text, markers.BODY, body_text)
    await _write_text(svc, item_id, new_text)


def _append_view_declaration(squad_dir: Path, name: str, kind: str = "subtask") -> None:
    """Add ``[views.<name>]`` to the squad's ``.overrides/workflow.toml``, **preserving**
    whatever the file already declares — a test building several views in one squad (e.g. the
    "several tags in one body" shape) calls this once per view; overwriting the file on a
    second call would silently drop the first view's declaration.

    *kind* defaults to ``subtask`` (every ``task`` hosts it, so no fixture data is needed for
    the position/shape tables that don't care about applicability); a source-applicability test
    passes a different kind deliberately, to declare a view a plain task does *not* host."""
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    path = override_dir / "workflow.toml"
    existing = (
        path.read_text(encoding="utf-8")
        if path.is_file()
        else (f"# squads:override-base:{__version__}\n")
    )
    path.write_text(
        existing + f'\n[views.{name}]\nsource = {{ kind = "subentity", name = "{kind}" }}\n'
        'fields = [ { code = "id", label = "Id" } ]\n',
        encoding="utf-8",
    )
    invalidate_squad_dir(squad_dir)


def _declare_static_view(
    squad_dir: Path, name: str, template_text: str, *, kind: str = "subtask"
) -> None:
    """A subentity-source view over *kind* (``subtask`` by default — any task hosts it, so no
    fixture data is needed) whose template ignores every context variable and emits
    *template_text* verbatim — deterministic, distinguishable output for position/shape
    assertions that don't care about projected records."""
    _append_view_declaration(squad_dir, name, kind)
    target = squad_dir / ".overrides" / "templates" / "views" / f"{name}.md.j2"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(template_text, encoding="utf-8")
    invalidate_squad_dir(squad_dir)


def _declare_dangling_view(squad_dir: Path, name: str) -> None:
    """A declared ``[views.<name>]`` entry with **no** presentation template anywhere — the
    "declared but the template is missing" half of a dangling name."""
    _append_view_declaration(squad_dir, name)


def _assert_in_order(text: str, *substrings: str) -> None:
    """Every *substrings* entry occurs in *text*, each strictly after the previous one ends —
    the position-preservation check every table row below needs, without hardcoding the exact
    whitespace a real anchor (``insert_view``'s own, in particular) leaves behind."""
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

    assert body == expected


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
    await svc.insert_view(task.id, _BUNDLED_VIEW)  # insert_view's own anchor: the region's end
    expected = await svc.render_view(_BUNDLED_VIEW, task.id)

    body = await svc.read_body(task.id)

    assert markers.view_tag(_BUNDLED_VIEW) not in body
    _assert_in_order(body, "prose before.", expected)


async def test_several_tags_in_one_body_each_expand_independently_in_place(project) -> None:
    _declare_static_view(project.squad_dir, "alpha_view", "ALPHA-OUTPUT")
    _declare_static_view(project.squad_dir, "beta_view", "BETA-OUTPUT")
    svc = _reopen(project)
    task = (await create_item(svc, "task", "T")).item
    alpha = f"<!-- sq:{markers.view_tag('alpha_view')} -->"
    beta = f"<!-- sq:{markers.view_tag('beta_view')} -->"
    await _set_raw_body(svc, task.id, f"start.\n{alpha}\nmiddle.\n{beta}\nend.")

    body = await svc.read_body(task.id)

    assert body == "start.\nALPHA-OUTPUT\nmiddle.\nBETA-OUTPUT\nend."


async def test_the_same_view_tag_repeated_expands_at_each_of_its_own_positions(project) -> None:
    """The same name, twice — a shape the placement verb never produces itself (it's
    idempotent) but a hand-edited or migrated file could carry; expansion must still handle it
    positionally rather than assuming at most one occurrence."""
    _declare_static_view(project.squad_dir, "repeated_view", "R")
    svc = _reopen(project)
    task = (await create_item(svc, "task", "T")).item
    tag = f"<!-- sq:{markers.view_tag('repeated_view')} -->"
    await _set_raw_body(svc, task.id, f"one {tag} two {tag} three")

    body = await svc.read_body(task.id)

    assert body == "one R two R three"


async def test_a_view_tag_adjacent_to_the_neighbouring_discussion_region_leaves_it_untouched(
    svc,
) -> None:
    """Expansion is scoped to ``sq:body`` alone: a marker-shaped tag sitting in the
    *neighbouring* ``sq:discussion`` region (reachable only by writing the file directly —
    ``comment`` itself goes through ``reject_markers``) must never be touched by
    ``read_body``'s expansion, and ``read_discussion`` must never expand it either — there is
    exactly one expansion site, and this is not it."""
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

    assert body == expected  # the body's own tag still expanded
    assert tag_line in discussion  # the discussion region's copy stays completely literal


async def test_a_non_view_unpaired_tag_is_left_exactly_as_is_the_control(svc) -> None:
    """A marker-shaped tag from *outside* the view family (any bare ``sq:<word>`` the
    recogniser doesn't claim) must be untouched, proving expansion is selective to the
    declared family rather than to "any unpaired-looking marker"."""
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
    await svc.insert_view(task.id, "broken_view")

    with pytest.raises(SquadsError, match="broken_view"):
        await svc.read_body(task.id)


async def test_a_render_failure_does_not_swallow_or_degrade_to_an_empty_expansion(
    project,
) -> None:
    """The other half of the same assertion, driven with a control: a *working* view on the
    same item still expands normally, so the raise above is specifically about the broken
    template — not some blanket refusal that also breaks a valid one."""
    _declare_static_view(project.squad_dir, "healthy_view", "OK")
    svc = _reopen(project)
    task = (await create_item(svc, "task", "T")).item
    healthy_tag = f"<!-- sq:{markers.view_tag('healthy_view')} -->"
    await _set_raw_body(svc, task.id, healthy_tag)

    body = await svc.read_body(task.id)

    assert body == "OK"


# --------------------------------------------------------------------------- source applicability


async def test_a_source_incompatible_tag_stays_literal_and_the_read_succeeds(project) -> None:
    """A declared, templated ``subentity``-source view over ``finding`` placed on a ``task``
    (which hosts ``subtask``, not ``finding``) leaves the tag exactly as authored and the read
    succeeds -- the same quiet disposition an undeclared name or a missing template already
    get, generalised to the third reason."""
    _declare_static_view(project.squad_dir, "story_board", "SHOULD-NEVER-RENDER", kind="finding")
    svc = _reopen(project)
    task = (await create_item(svc, "task", "T")).item
    tag_line = f"<!-- sq:{markers.view_tag('story_board')} -->"
    await _set_raw_body(svc, task.id, f"prose.\n{tag_line}")

    body = await svc.read_body(task.id)

    assert body == f"prose.\n{tag_line}"  # byte for byte -- not stripped, not emptied, not rendered


async def test_the_same_view_on_its_hosting_type_renders_normally_the_positive_control(
    project,
) -> None:
    """Control proving the quiet skip above is specific to the incompatible host, not the view
    itself: the identical declaration, resolved against a ``review`` (which hosts ``finding``),
    still renders."""
    _declare_static_view(project.squad_dir, "story_board", "RENDERED", kind="finding")
    svc = _reopen(project)
    review = (await create_item(svc, "review", "A review")).item
    await _set_raw_body(svc, review.id, f"<!-- sq:{markers.view_tag('story_board')} -->")

    body = await svc.read_body(review.id)

    assert body == "RENDERED"


async def test_a_hosting_type_with_zero_members_renders_empty_not_a_failure(project) -> None:
    """The emptiness clause, at the read boundary: a review with no findings still hosts the
    kind, so the tag expands to whatever its template renders for zero records -- empty output
    from an empty ``groups`` list, never the quiet-skip (still-literal) disposition, and never
    a raise."""
    _declare_static_view(
        project.squad_dir,
        "finding_count",
        "{% for group in groups %}{% for r in group.records %}{{ r.values['id'].text }}"
        "{% endfor %}{% endfor %}",
        kind="finding",
    )
    svc = _reopen(project)
    review = (await create_item(svc, "review", "A review")).item  # no findings added
    await _set_raw_body(svc, review.id, f"<!-- sq:{markers.view_tag('finding_count')} -->")

    body = await svc.read_body(review.id)

    assert body == ""  # rendered (empty), not left literal
    assert markers.view_tag("finding_count") not in body


async def test_source_applicability_table_driven_over_host_type_by_kind(project) -> None:
    """Table-driven over host type x declared sub-entity kind, mirroring the placement table in
    ``tests/service/test_view_tag_placement.py`` — the same classification, exercised at the
    read boundary instead of the placement door."""
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
    """Control: the bundled ``ref``-source view carries no host constraint, so it expands
    regardless of host type, proving the applicability predicate does not affect a
    ref-sourced view."""
    task = (await create_item(svc, "task", "T")).item
    await _set_raw_body(svc, task.id, f"<!-- sq:{markers.view_tag(_BUNDLED_VIEW)} -->")
    expected = await svc.render_view(_BUNDLED_VIEW, task.id)

    body = await svc.read_body(task.id)

    assert body == expected


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
    await svc.insert_view(task.id, "quoting_view")

    body = await svc.read_body(task.id)

    assert body == f"outer text {inner_tag} more outer text"  # never re-scanned, stays literal


async def test_scanning_happens_once_against_the_original_text_not_after_each_substitution(
    project,
) -> None:
    """A stronger version of the no-recursion proof: a view whose *own name* appears, spelled
    as a marker, inside its own rendered output would recurse forever under a naive
    re-scanning implementation. It terminates and returns the single-pass result instead."""
    self_tag = f"<!-- sq:{markers.view_tag('self_quoting_view')} -->"
    _declare_static_view(project.squad_dir, "self_quoting_view", self_tag)
    svc = _reopen(project)
    task = (await create_item(svc, "task", "T")).item
    await _set_raw_body(svc, task.id, "")
    await svc.insert_view(task.id, "self_quoting_view")

    body = await svc.read_body(task.id)

    assert body == self_tag


# --------------------------------------------------------------------------- read-only round trip


async def test_appending_after_a_tag_leaves_the_tag_literal_on_disk_no_rendered_bytes_anywhere(
    svc,
) -> None:
    """The central invariant: expansion must never reach a write path. Read an item whose body
    carries a tag (confirming the read is already expanded), append to that body, then assert
    the stored file still carries the literal tag — and nothing the view rendered — anywhere on
    disk."""
    task = (await create_item(svc, "task", "T")).item
    await _set_raw_body(svc, task.id, f"<!-- sq:{markers.view_tag(_BUNDLED_VIEW)} -->")
    expanded_before_append = await svc.read_body(task.id)
    assert markers.view_tag(_BUNDLED_VIEW) not in expanded_before_append  # read-time: expanded

    await svc.set_body(task.id, "Appended after the tag.", append=True)

    stored = await _text(svc, task.id)
    stored_body = sections.get_section(stored, markers.BODY)
    assert stored_body is not None
    assert f"<!-- sq:{markers.view_tag(_BUNDLED_VIEW)} -->" in stored_body  # literal, survives
    assert "Appended after the tag." in stored_body
    rendered = await svc.render_view(_BUNDLED_VIEW, task.id)
    assert rendered not in stored  # the rendered output is nowhere in the file

    # And the read keeps expanding it in place, appended prose following the expansion.
    body_after_append = await svc.read_body(task.id)
    _assert_in_order(body_after_append, expanded_before_append, "Appended after the tag.")


async def test_replacing_a_body_that_carries_a_tag_drops_it_like_any_other_authored_text(
    svc,
) -> None:
    """A body *replace* (not append) overwrites the whole region, tag included, like any
    other authored text — covered here only to confirm the write path's own behaviour is
    untouched by expansion."""
    task = (await create_item(svc, "task", "T")).item
    await svc.insert_view(task.id, _BUNDLED_VIEW)

    await svc.set_body(task.id, "Completely new prose.", force=True)

    stored_body = sections.get_section(await _text(svc, task.id), markers.BODY)
    assert stored_body is not None
    assert markers.view_tag(_BUNDLED_VIEW) not in stored_body
    body = await svc.read_body(task.id)
    assert body == "Completely new prose."


# --------------------------------------------------------------------------- single boundary


def test_expand_view_tags_has_exactly_one_caller_the_shared_body_read_boundary() -> None:
    """Grep-provable: expansion lives at one call site — ``ItemsMixin.read_body`` — and no
    other module reimplements it. A second call site would mean a second read surface growing
    its own expander, which the task's placement constraint forbids."""
    src_root = Path(__file__).resolve().parents[2] / "src" / "squads"
    call_sites = [
        p.relative_to(src_root).as_posix()
        for p in src_root.rglob("*.py")
        for line in p.read_text(encoding="utf-8").splitlines()
        if "expand_view_tags(" in line and "def expand_view_tags(" not in line
    ]
    assert call_sites == ["_services/_items.py"]
