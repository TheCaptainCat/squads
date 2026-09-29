"""``place_view_tags``'s position x body-shape matrix, driven directly against the pure
function: three declared views (top/bottom/after-match) cross every position shape, each
case asserting the full region bytes, with idempotence checked wherever it is meaningful."""

import pytest

from squads._errors import SquadsError
from squads._models import _markers as markers
from squads._views import ConflictingViewStateError, place_view_tags, view_placement_invocation
from squads._workflow import bundled_spec
from squads._workflow._models import ViewSource, ViewSpec

_TAG = {n: markers.open_marker(markers.view_tag(n)) for n in ("alpha", "beta", "gamma")}
_DISABLED = {n: markers.open_marker(markers.view_tag(n, disabled=True)) for n in _TAG}


def _spec():
    return bundled_spec().model_copy(
        update={
            "views": {
                "alpha": ViewSpec(source=ViewSource(kind="self"), position="top"),
                "beta": ViewSpec(source=ViewSource(kind="self"), position="bottom"),
                "gamma": ViewSpec(source=ViewSource(kind="self"), position="after(^## Marker\\n)"),
            }
        }
    )


def _place(region: str, edit: str | None, *, seeded: frozenset[str] = frozenset(), **kw) -> str:
    return place_view_tags(
        region, edit, seeded=seeded, spec=_spec(), item_type="task", addr=5, **kw
    )


# --------------------------------------------------------------------------------- body shape


def test_empty_region_seeds_every_declared_view_enabled() -> None:
    out = _place("", None, seeded=frozenset({"alpha", "beta"}))
    assert out == f"{_TAG['alpha']}\n\n{_TAG['beta']}"


def test_a_tag_only_region_is_left_byte_identical_on_a_no_op_write() -> None:
    tag_only = _TAG["beta"]
    out = _place(tag_only, None, seeded=frozenset({"beta"}))
    assert out == tag_only


def test_prose_above_a_bottom_tag_is_preserved_verbatim() -> None:
    region = f"Some prose.\n\n{_TAG['beta']}"
    out = _place(region, None, seeded=frozenset({"beta"}))
    assert out == region


def test_prose_below_a_top_tag_is_preserved_verbatim() -> None:
    region = f"{_TAG['alpha']}\n\nSome prose."
    out = _place(region, None, seeded=frozenset({"alpha"}))
    assert out == region


def test_prose_on_both_sides_of_an_after_tag_lands_right_after_the_matched_line() -> None:
    """Prose on both sides of an after-tag lands right after the matched line, no blank line
    manufactured."""
    out = _place("", "Before.\n\n## Marker\nline\n\nAfter.", seeded=frozenset({"gamma"}))
    assert out == f"Before.\n\n## Marker\n{_TAG['gamma']}\nline\n\nAfter."


def test_two_views_at_the_same_position_place_in_declaration_order() -> None:
    """Two views at the same position place in declaration order, not insertion or sort order."""
    spec = bundled_spec().model_copy(
        update={
            "views": {
                "alpha": ViewSpec(source=ViewSource(kind="self"), position="top"),
                "zeta": ViewSpec(source=ViewSource(kind="self"), position="top"),
            }
        }
    )
    out = place_view_tags(
        "", None, seeded=frozenset({"alpha", "zeta"}), spec=spec, item_type="task", addr=5
    )
    assert out == f"{_TAG['alpha']}\n\n{markers.open_marker(markers.view_tag('zeta'))}"


def test_two_views_at_different_positions_each_land_at_their_own() -> None:
    out = _place("", None, seeded=frozenset({"alpha", "beta"}))
    assert out == f"{_TAG['alpha']}\n\n{_TAG['beta']}"
    lines = out.splitlines()
    assert lines[0] == _TAG["alpha"]
    assert lines[-1] == _TAG["beta"]


def test_a_disabled_tag_is_re_placed_disabled_at_its_own_position() -> None:
    region = _DISABLED["beta"]
    out = _place(region, None, seeded=frozenset({"beta"}))
    assert out == region


def test_two_undeclared_tags_go_after_every_declared_one_keeping_their_own_order() -> None:
    region = (
        f"{markers.open_marker(markers.view_tag('second_undeclared'))}\n\n"
        f"{_TAG['alpha']}\n\n"
        f"{markers.open_marker(markers.view_tag('first_undeclared'))}"
    )
    out = _place(region, None, seeded=frozenset({"alpha"}))
    assert out == (
        f"{_TAG['alpha']}\n\n"
        f"{markers.open_marker(markers.view_tag('second_undeclared'))}\n\n"
        f"{markers.open_marker(markers.view_tag('first_undeclared'))}"
    ), "undeclared tags must keep their own original relative order, first-seen first"


def test_a_newly_force_added_undeclared_tag_goes_after_every_existing_undeclared_one() -> None:
    """A newly force-added undeclared tag goes after every existing undeclared one."""
    region = (
        f"{markers.open_marker(markers.view_tag('first_existing'))}\n\n"
        f"{markers.open_marker(markers.view_tag('second_existing'))}"
    )
    out = _place(region, None, force=("brand_new", False))
    assert out == (
        f"{markers.open_marker(markers.view_tag('first_existing'))}\n\n"
        f"{markers.open_marker(markers.view_tag('second_existing'))}\n\n"
        f"{markers.open_marker(markers.view_tag('brand_new'))}"
    ), "a newly placed undeclared tag must come last, after every existing undeclared tag"


def test_same_state_duplicates_of_one_view_collapse_to_a_single_tag() -> None:
    region = f"{_TAG['beta']}\n\n{_TAG['beta']}"
    out = _place(region, None, seeded=frozenset({"beta"}))
    assert out == _TAG["beta"]
    assert out.count(_TAG["beta"]) == 1


def test_a_conflicting_enabled_and_disabled_pair_refuses_naming_add_and_disable() -> None:
    """A conflicting enabled and disabled pair refuses, naming the item, add, and disable."""
    region = f"{_TAG['beta']}\n\n{_DISABLED['beta']}"
    add_cmd = view_placement_invocation("task", 5, "add", "beta")
    disable_cmd = view_placement_invocation("task", 5, "disable", "beta")

    with pytest.raises(ConflictingViewStateError) as exc:
        _place(region, None, seeded=frozenset({"beta"}))

    assert isinstance(exc.value, SquadsError)
    assert str(exc.value).startswith("task 5:")
    assert add_cmd in str(exc.value)
    assert disable_cmd in str(exc.value)


def test_force_settles_a_conflicting_pair_without_raising() -> None:
    """Naming the view's forced state collapses every copy into one, rather than raising."""
    region = f"{_TAG['beta']}\n\n{_DISABLED['beta']}"
    out = _place(region, None, seeded=frozenset({"beta"}), force=("beta", True))
    assert out == _DISABLED["beta"]


def test_a_seeded_view_absent_from_the_region_is_inserted_enabled() -> None:
    region = "Just prose, no tag at all."
    out = _place(region, None, seeded=frozenset({"beta"}))
    assert out == f"Just prose, no tag at all.\n\n{_TAG['beta']}"


def test_a_non_seeded_but_already_present_tag_is_kept_at_its_own_position() -> None:
    """A non-seeded but already-present tag is kept at its own position, never dropped."""
    region = f"{_TAG['alpha']}\n\nProse."
    out = _place(region, None, seeded=frozenset())
    assert out == region


# ------------------------------------------------------------------------------- after(): shape


def test_after_a_pattern_matching_several_times_anchors_on_the_first_match() -> None:
    """After a pattern matching several times, the tag anchors on the first match."""
    out = _place("", "## Marker\nfirst\n\n## Marker\nsecond", seeded=frozenset({"gamma"}))
    assert out == f"## Marker\n{_TAG['gamma']}\nfirst\n\n## Marker\nsecond"


def test_after_a_pattern_with_no_match_falls_back_to_bottom_silently() -> None:
    region = "No marker heading here at all."
    out = _place(region, None, seeded=frozenset({"gamma"}))
    assert out == f"No marker heading here at all.\n\n{_TAG['gamma']}"


# ------------------------------------------------------------------- position across two writes


def test_an_after_view_falling_out_of_match_leaves_no_stray_blank_line_behind() -> None:
    """An after-view falling out of match relocates to the bottom, leaving no stray blank line
    behind at its prior spot."""
    matching = bundled_spec().model_copy(
        update={
            "views": {
                "gamma": ViewSpec(source=ViewSource(kind="self"), position="after(^## Marker\\n)")
            }
        }
    )
    no_longer_matching = bundled_spec().model_copy(
        update={
            "views": {
                "gamma": ViewSpec(source=ViewSource(kind="self"), position="after(^## Renamed\\n)")
            }
        }
    )
    once = place_view_tags(
        "",
        "Before.\n\n## Marker\nline\n\nAfter.",
        seeded=frozenset({"gamma"}),
        spec=matching,
        item_type="task",
        addr=5,
    )
    assert once == f"Before.\n\n## Marker\n{_TAG['gamma']}\nline\n\nAfter."

    twice = place_view_tags(
        once,
        "New line.",
        append=True,
        seeded=frozenset({"gamma"}),
        spec=no_longer_matching,
        item_type="task",
        addr=5,
    )
    assert twice == f"Before.\n\n## Marker\nline\n\nAfter.\n\nNew line.\n\n{_TAG['gamma']}"

    thrice = place_view_tags(
        twice, None, seeded=frozenset({"gamma"}), spec=no_longer_matching, item_type="task", addr=5
    )
    assert thrice == twice


# --------------------------------------------------------------------------------- idempotence


@pytest.mark.parametrize(
    "region_builder",
    [
        lambda: ("", frozenset({"alpha", "beta"})),
        lambda: ("Some prose.", frozenset({"beta"})),
        lambda: (f"Prose.\n\n{_TAG['alpha']}", frozenset({"alpha", "beta"})),
        lambda: ("## Marker\nBefore.", frozenset({"gamma"})),
        lambda: (f"{_TAG['beta']}\n\n{_TAG['beta']}", frozenset({"beta"})),
    ],
    ids=["empty", "prose-only", "mixed-declared", "after-match", "duplicate-collapse"],
)
def test_a_second_identical_write_produces_identical_bytes(region_builder) -> None:
    region, seeded = region_builder()
    once = _place(region, None, seeded=seeded)
    twice = _place(once, None, seeded=seeded)
    assert twice == once
