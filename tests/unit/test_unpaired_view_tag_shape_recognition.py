"""The unpaired view-tag family's constructor and recogniser (``_models/_markers.py``):
``view_tag`` composes the bare tag naming a view, ``view_tag_name`` answers whether either the
bare tag or the full on-disk (``sq:``-prefixed) form belongs to that family and, if so, which
view it names. No close-marker counterpart exists for this family — that is the binding
invariant, not an implementation detail — so the recogniser must refuse a close-marker spelling
and the module must never grow a ``close_marker``-shaped constant for it.
"""

from squads import _sections as sections
from squads._models import _markers as markers


def test_view_tag_composes_the_bare_tag_naming_the_view() -> None:
    assert markers.view_tag("milestone_rollup") == "view:milestone_rollup"


def test_view_tag_name_recognises_a_well_formed_member_and_extracts_the_name() -> None:
    assert markers.view_tag_name("view:milestone_rollup") == "milestone_rollup"
    assert markers.view_tag_name("view:my-project_view2") == "my-project_view2"


def test_view_tag_name_also_recognises_the_full_on_disk_prefixed_form() -> None:
    """The shape :func:`~squads._sections.find_markers`/:func:`~squads._sections
    .iter_marker_spans` actually emit -- the ``sq:`` prefix still attached -- alongside the
    bare form above, so neither producer needs a hand-strip before calling this."""
    assert markers.view_tag_name("sq:view:milestone_rollup") == "milestone_rollup"
    assert markers.view_tag_name("sq:view:my-project_view2") == "my-project_view2"


def test_view_tag_name_recognises_the_form_find_markers_and_iter_marker_spans_emit() -> None:
    """Driven straight against the two producers' own output, not a hand-typed string, so a
    future producer change that stopped emitting the ``sq:`` prefix — or started — would
    reopen the mismatch here rather than pass silently."""
    on_disk = markers.open_marker(markers.view_tag("milestone_rollup"))

    (produced,) = sections.find_markers(on_disk)
    assert produced == "sq:view:milestone_rollup"
    assert markers.view_tag_name(produced) == "milestone_rollup"

    ((span_tag, _start, _end),) = sections.iter_marker_spans(on_disk)
    assert span_tag == produced
    assert markers.view_tag_name(span_tag) == "milestone_rollup"


def test_view_tag_name_round_trips_through_view_tag() -> None:
    for name in ("milestone_rollup", "a", "role_definition", "x-y_z"):
        assert markers.view_tag_name(markers.view_tag(name)) == name
        # ... and through the full on-disk producer form too.
        assert markers.view_tag_name(f"{markers.PREFIX}{markers.view_tag(name)}") == name


def test_view_tag_name_rejects_tags_from_other_families() -> None:
    """The control: unpaired-family recognition must be shape-blind to every *other* tag this
    module already declares — a top-level region, a sub-entity region, and a retired
    sub-entity ``:head`` badge tag all return None, not a name — in both the bare form and the
    ``sq:``-prefixed on-disk form :func:`~squads._sections.find_markers` actually produces for
    them."""
    for tag in ("body", "discussion", markers.story_tag("US1"), "subtask:ST1:head"):
        assert markers.view_tag_name(tag) is None
        assert markers.view_tag_name(f"{markers.PREFIX}{tag}") is None


def test_view_tag_name_rejects_a_close_marker_spelling() -> None:
    """The binding invariant, driven with a control: this family has no closing counterpart,
    so a tag ending in ``:end`` must never be recognised as naming a view — not even one whose
    prefix would otherwise match."""
    assert markers.view_tag_name("view:milestone_rollup:end") is None
    assert markers.view_tag_name(f"{markers.view_tag('x')}:end") is None
    assert markers.view_tag_name("sq:view:milestone_rollup:end") is None
    assert markers.view_tag_name(f"{markers.PREFIX}{markers.view_tag('x')}:end") is None


def test_view_tag_name_rejects_a_bare_or_malformed_namespace() -> None:
    assert markers.view_tag_name("view") is None  # no ":" at all
    assert markers.view_tag_name("view:") is None  # empty name
    assert markers.view_tag_name("viewpoint:x") is None  # prefix collision, not a match
    assert markers.view_tag_name("sq:view") is None  # prefixed, but still no ":" for a name
    assert markers.view_tag_name("sq:view:") is None  # prefixed, empty name
    assert markers.view_tag_name("sq:viewpoint:x") is None  # prefixed prefix collision


def test_the_markers_module_declares_no_closing_counterpart_for_the_view_family() -> None:
    """``_models/_markers.py`` must never gain a ``close_marker``-shaped constant for this
    family — the binding invariant behind its "unpaired by design" property — checked
    structurally rather than trusting a docstring: no module-level name starts with ``VIEW``
    other than the namespace constant
    itself, so a future ``VIEW_CLOSE``/``VIEW_END`` addition fails this test on sight."""
    view_names = [n for n in vars(markers) if n.startswith("VIEW")]
    assert view_names == ["VIEW"]
