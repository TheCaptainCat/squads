"""``squads._services._maintenance._converge_body_tag`` — the one license the repair sweep's
backfill runs under, tested as a pure function rather than through a whole ``sq repair`` (the
end-to-end path, including the classification half —
``MaintenanceMixin._repair_body_tag`` — is
``tests/service/test_repair_strips_only_retired_regions.py``).

A role and a permanently-system skill share the same (non-strict) license: ``set_body`` refuses
both bodies unconditionally in current code, so nothing on disk today was authored there.
Whatever the region held before — empty, already the tag, or a plain-prose legacy rendering
left by a release that predates this tag mechanism — converges onto the tag the same way. What
stays loud is content that is itself marker-shaped: not the shape a legacy renderer produces, so
this sweep refuses to guess what it is.

A per-item-type skill (``item_skill``) passes ``strict_empty=True`` instead: unlike a role or a
permanently-system skill, its slug CAN have been genuinely custom before a matching type was
declared, so only empty or already-tagged may converge — anything else, marker-shaped or not,
is left untouched rather than guessed at. A ``sq-`` slug is not reserved, so an author can write
a real body under one before any type declares a matching skill; converging unconditionally over
non-empty content the moment that slug turns template-owned would destroy that authored work.
See ``tests/service/test_repair_strips_only_retired_regions.py::
test_declaring_an_item_type_does_not_delete_an_authored_skill_of_that_name`` for the same
guarantee proven end to end, through supported commands rather than as a pure function.
"""

import pytest

from squads._errors import SquadsError
from squads._models import _markers as markers
from squads._services._maintenance import _converge_body_tag

_EMPTY_BODY = f"{markers.open_marker(markers.BODY)}\n{markers.close_marker(markers.BODY)}\n"
_TAGGED_BODY = (
    f"{markers.open_marker(markers.BODY)}\n"
    f"{markers.open_marker(markers.view_tag('role_definition'))}\n"
    f"{markers.close_marker(markers.BODY)}\n"
)
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


@pytest.mark.parametrize("view_name", ["role_definition", "squads_skill"])
def test_an_empty_body_converges_onto_the_tag(view_name: str) -> None:
    out = _converge_body_tag(_EMPTY_BODY, view_name)
    assert markers.open_marker(markers.view_tag(view_name)) in out


def test_an_already_tagged_body_is_returned_byte_identical() -> None:
    out = _converge_body_tag(_TAGGED_BODY, "role_definition")
    assert out == _TAGGED_BODY


@pytest.mark.parametrize("view_name", ["role_definition", "squads_skill"])
def test_a_plain_prose_legacy_rendering_converges_onto_the_tag(view_name: str) -> None:
    """The shape a release predating this tag mechanism (or 0.14's stored-region retirement)
    would have left: rendered prose, no marker of its own. Admitted for both a role and a
    system skill — the same license, since neither writer can be blamed for authoring it."""
    out = _converge_body_tag(_LEGACY_BODY, view_name)
    assert "Stored Name" not in out
    assert markers.open_marker(markers.view_tag(view_name)) in out


@pytest.mark.parametrize("view_name", ["role_definition", "squads_skill"])
def test_marker_shaped_content_is_not_silently_overwritten(view_name: str) -> None:
    """Falsifies the guard itself: content carrying a well-formed marker of its own is not the
    plain-prose shape a legacy release produced, so it must stop the sweep rather than be
    guessed at. Remove the ``sections.find_markers`` check and this reddens — the exact same
    input would converge silently instead of raising, which is what makes this a real guard.
    Raises ``SquadsError``, the ordinary user-facing-error convention (``CLAUDE.md``), never a
    bare ``AssertionError`` — a caller catching only ``SquadsError`` must still see this."""
    with pytest.raises(SquadsError, match="found marker-shaped content"):
        _converge_body_tag(_MARKER_SHAPED_BODY, view_name)


# --------------------------------------------------------------------------- strict_empty
# (the per-item-type skill license: only empty or already-tagged may ever converge)


def test_an_empty_body_converges_onto_the_tag_under_strict_empty() -> None:
    out = _converge_body_tag(_EMPTY_BODY, "item_skill", strict_empty=True)
    assert markers.open_marker(markers.view_tag("item_skill")) in out


def test_an_already_tagged_body_is_returned_byte_identical_under_strict_empty() -> None:
    tagged = (
        f"{markers.open_marker(markers.BODY)}\n"
        f"{markers.open_marker(markers.view_tag('item_skill'))}\n"
        f"{markers.close_marker(markers.BODY)}\n"
    )
    out = _converge_body_tag(tagged, "item_skill", strict_empty=True)
    assert out == tagged


def test_a_plain_prose_body_is_left_untouched_under_strict_empty() -> None:
    """The regression this mode exists to close: under the non-strict license this exact input
    converges (see ``test_a_plain_prose_legacy_rendering_converges_onto_the_tag`` above) because
    a role/permanently-system skill can never have authored one. A per-item-type skill's slug
    can — an author's real runbook, written before its type existed — so strict_empty must
    leave it alone, byte for byte, rather than guess it is a stale legacy rendering."""
    out = _converge_body_tag(_LEGACY_BODY, "item_skill", strict_empty=True)
    assert out == _LEGACY_BODY
    assert "Stored Name" in out  # nothing was removed


def test_marker_shaped_content_is_also_left_untouched_under_strict_empty_never_raising() -> None:
    """The other half of the same asymmetry: non-strict raises on marker-shaped content (see
    ``test_marker_shaped_content_is_not_silently_overwritten`` above) because that shape is
    unexplained there. Under strict_empty it is simply more non-empty content this narrower
    license has no license to touch — left alone, not raised on, so an ordinary ``sq repair``
    over a squad carrying an author-customised per-type skill never aborts."""
    out = _converge_body_tag(_MARKER_SHAPED_BODY, "item_skill", strict_empty=True)
    assert out == _MARKER_SHAPED_BODY
