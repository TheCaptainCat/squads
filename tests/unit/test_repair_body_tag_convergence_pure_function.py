"""``_converge_body_tag``, tested as a pure function: strict unconditionally, only a genuinely
empty region converges, and any other non-empty content is left untouched, silently, never
raised on — routed through the one placement function for the empty case."""

import pytest

from squads._models import _markers as markers
from squads._sections import get_section
from squads._services._maintenance import _converge_body_tag
from squads._views import place_view_tags
from squads._workflow import bundled_spec

_SPEC = bundled_spec()

_EMPTY_BODY = f"{markers.open_marker(markers.BODY)}\n{markers.close_marker(markers.BODY)}\n"
_LEGACY_BODY = (
    f"{markers.open_marker(markers.BODY)}\n"
    "# Stored Name\n\nA stale pre-tag rendering, plain prose only.\n"
    f"{markers.close_marker(markers.BODY)}\n"
)
_MARKER_SHAPED_BODY = (
    f"{markers.open_marker(markers.BODY)}\n"
    f"SOME STRAY CONTENT {markers.open_marker('something-unexpected')}\n"
    f"{markers.close_marker(markers.BODY)}\n"
)


def _tagged_body(view_name: str, *, disabled: bool = False) -> str:
    return (
        f"{markers.open_marker(markers.BODY)}\n"
        f"{markers.open_marker(markers.view_tag(view_name, disabled=disabled))}\n"
        f"{markers.close_marker(markers.BODY)}\n"
    )


@pytest.mark.parametrize("view_name", ["role_definition", "squads_skill", "item_skill"])
def test_an_empty_body_converges_onto_the_enabled_tag(view_name: str) -> None:
    out = _converge_body_tag(_EMPTY_BODY, view_name, _SPEC, "role", "some-slug")
    assert markers.open_marker(markers.view_tag(view_name)) in out
    assert markers.open_marker(markers.view_tag(view_name, disabled=True)) not in out


@pytest.mark.parametrize("view_name", ["role_definition", "squads_skill", "item_skill"])
def test_an_already_enabled_tagged_body_is_returned_byte_identical(view_name: str) -> None:
    tagged = _tagged_body(view_name)
    out = _converge_body_tag(tagged, view_name, _SPEC, "role", "some-slug")
    assert out == tagged


@pytest.mark.parametrize("view_name", ["role_definition", "squads_skill", "item_skill"])
def test_a_disabled_tagged_body_is_returned_byte_identical(view_name: str) -> None:
    """A disabled tagged body is returned byte identical, never re-enabled or rewritten."""
    tagged = _tagged_body(view_name, disabled=True)
    out = _converge_body_tag(tagged, view_name, _SPEC, "role", "some-slug")
    assert out == tagged


@pytest.mark.parametrize("view_name", ["role_definition", "squads_skill", "item_skill"])
def test_a_plain_prose_legacy_body_is_left_untouched(view_name: str) -> None:
    """A plain-prose legacy body is left untouched, regardless of which view it is."""
    out = _converge_body_tag(_LEGACY_BODY, view_name, _SPEC, "role", "some-slug")
    assert out == _LEGACY_BODY
    assert "Stored Name" in out


@pytest.mark.parametrize("view_name", ["role_definition", "squads_skill", "item_skill"])
def test_marker_shaped_content_is_left_untouched_never_raising(view_name: str) -> None:
    """Marker-shaped content is left untouched, never raising."""
    out = _converge_body_tag(_MARKER_SHAPED_BODY, view_name, _SPEC, "role", "some-slug")
    assert out == _MARKER_SHAPED_BODY


_FRONTMATTER = "---\nid: ROLE-1\ntype: role\n---\n"
_TAIL = "\n## Discussion\n\n<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n"


@pytest.mark.parametrize("view_name", ["role_definition", "squads_skill", "item_skill"])
def test_an_absent_body_pair_with_only_the_tag_in_the_way_converges_instead_of_crashing(
    view_name: str,
) -> None:
    """A hand-deleted body pair with only the tag in the way converges instead of crashing."""
    corrupted = f"{_FRONTMATTER}{markers.open_marker(markers.view_tag(view_name))}{_TAIL}"
    out = _converge_body_tag(corrupted, view_name, _SPEC, "role", "some-slug")
    assert get_section(out, markers.BODY) is not None
    assert markers.open_marker(markers.view_tag(view_name)) in (
        get_section(out, markers.BODY) or ""
    )
    assert "## Discussion" in out


def test_an_absent_body_pair_with_no_tag_at_all_converges_onto_a_fresh_empty_region() -> None:
    """An absent body pair with no tag at all converges onto a fresh empty region."""
    corrupted = f"{_FRONTMATTER}{_TAIL}"
    out = _converge_body_tag(corrupted, "role_definition", _SPEC, "role", "some-slug")
    assert get_section(out, markers.BODY) is not None
    assert markers.open_marker(markers.view_tag("role_definition")) in (
        get_section(out, markers.BODY) or ""
    )


def test_an_absent_body_pair_with_real_prose_in_the_way_is_left_untouched_never_raising() -> None:
    """Real, unheaded prose in the absent region's span is left untouched, never raising."""
    corrupted = f"{_FRONTMATTER}Some hand-typed replacement text, no tag at all.{_TAIL}"
    out = _converge_body_tag(corrupted, "role_definition", _SPEC, "role", "some-slug")
    assert out == corrupted


def test_the_empty_case_is_byte_identical_to_the_placement_routine() -> None:
    """Converging an empty region produces exactly what ``place_view_tags`` would."""
    out = _converge_body_tag(_EMPTY_BODY, "role_definition", _SPEC, "role", "dev-agent")
    direct = place_view_tags(
        "",
        None,
        seeded=frozenset({"role_definition"}),
        spec=_SPEC,
        item_type="role",
        addr="dev-agent",
    )
    assert (get_section(out, markers.BODY) or "").strip("\n") == direct
