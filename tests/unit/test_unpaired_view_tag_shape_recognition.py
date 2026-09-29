"""``view_tag`` composes the unpaired view-tag family's bare tag; ``view_tag_parts``
recognises it in either bare or on-disk form and refuses a close-marker spelling, since the
family has no closing counterpart by design."""

from squads import _sections as sections
from squads._models import _markers as markers


def test_view_tag_composes_the_bare_tag_naming_the_view() -> None:
    assert markers.view_tag("milestone_rollup") == "view:milestone_rollup"


def test_view_tag_composes_the_disabled_form() -> None:
    assert markers.view_tag("milestone_rollup", disabled=True) == "view:milestone_rollup:disabled"
    assert markers.view_tag("milestone_rollup", disabled=False) == "view:milestone_rollup"


def test_view_tag_parts_recognises_a_well_formed_member_and_extracts_name_and_state() -> None:
    parts = markers.view_tag_parts("view:milestone_rollup")
    assert parts == markers.ViewTagParts("milestone_rollup", False)
    parts = markers.view_tag_parts("view:my-project_view2")
    assert parts == markers.ViewTagParts("my-project_view2", False)


def test_view_tag_parts_recognises_the_disabled_form() -> None:
    parts = markers.view_tag_parts("view:milestone_rollup:disabled")
    assert parts == markers.ViewTagParts("milestone_rollup", True)


def test_view_tag_parts_also_recognises_the_full_on_disk_prefixed_form() -> None:
    """``view_tag_parts`` also recognises the full on-disk, ``sq:``-prefixed form."""
    assert markers.view_tag_parts("sq:view:milestone_rollup") == markers.ViewTagParts(
        "milestone_rollup", False
    )
    assert markers.view_tag_parts("sq:view:my-project_view2") == markers.ViewTagParts(
        "my-project_view2", False
    )
    assert markers.view_tag_parts("sq:view:milestone_rollup:disabled") == markers.ViewTagParts(
        "milestone_rollup", True
    )


def test_view_tag_parts_recognises_the_form_find_markers_and_iter_marker_spans_emit() -> None:
    """``view_tag_parts`` recognises the exact form ``find_markers``/``iter_marker_spans`` emit."""
    for disabled in (False, True):
        on_disk = markers.open_marker(markers.view_tag("milestone_rollup", disabled=disabled))

        (produced,) = sections.find_markers(on_disk)
        assert produced == f"sq:view:milestone_rollup{':disabled' if disabled else ''}"
        assert markers.view_tag_parts(produced) == markers.ViewTagParts(
            "milestone_rollup", disabled
        )

        ((span_tag, _start, _end),) = sections.iter_marker_spans(on_disk)
        assert span_tag == produced
        assert markers.view_tag_parts(span_tag) == markers.ViewTagParts(
            "milestone_rollup", disabled
        )


def test_view_tag_parts_round_trips_through_view_tag() -> None:
    for name in ("milestone_rollup", "a", "role_definition", "x-y_z"):
        for disabled in (False, True):
            composed = markers.view_tag(name, disabled=disabled)
            assert markers.view_tag_parts(composed) == markers.ViewTagParts(name, disabled)
            assert markers.view_tag_parts(f"{markers.PREFIX}{composed}") == markers.ViewTagParts(
                name, disabled
            )


def test_view_tag_parts_rejects_tags_from_other_families() -> None:
    """``view_tag_parts`` rejects tags from other families, in both bare and on-disk form."""
    for tag in ("body", "discussion", markers.story_tag("US1"), "subtask:ST1:head"):
        assert markers.view_tag_parts(tag) is None
        assert markers.view_tag_parts(f"{markers.PREFIX}{tag}") is None


def test_view_tag_parts_rejects_a_close_marker_spelling() -> None:
    """A tag ending in ``:end`` is never recognised as naming a view."""
    assert markers.view_tag_parts("view:milestone_rollup:end") is None
    assert markers.view_tag_parts(f"{markers.view_tag('x')}:end") is None
    assert markers.view_tag_parts("sq:view:milestone_rollup:end") is None
    assert markers.view_tag_parts(f"{markers.PREFIX}{markers.view_tag('x')}:end") is None


def test_a_name_of_end_is_refused_at_spec_load_not_by_this_recogniser() -> None:
    """A view literally named ``end`` is refused at spec load, not by this recogniser."""
    assert markers.view_tag_parts("view:end") is None
    assert markers.view_tag_parts("view:end:disabled") == markers.ViewTagParts("end", True)


def test_view_tag_parts_rejects_a_bare_or_malformed_namespace() -> None:
    assert markers.view_tag_parts("view") is None
    assert markers.view_tag_parts("view:") is None
    assert markers.view_tag_parts("viewpoint:x") is None
    assert markers.view_tag_parts("sq:view") is None
    assert markers.view_tag_parts("sq:view:") is None
    assert markers.view_tag_parts("sq:viewpoint:x") is None


def test_the_markers_module_declares_no_closing_counterpart_for_the_view_family() -> None:
    """The markers module declares no closing counterpart for the view family."""
    view_names = [n for n in vars(markers) if n.startswith("VIEW") and n.isupper()]
    assert view_names == ["VIEW"]
