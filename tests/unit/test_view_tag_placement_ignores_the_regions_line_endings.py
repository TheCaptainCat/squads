"""Placing view tags in a region gives the same result whether the region's lines end in LF or
CRLF, and converging a settled CRLF body is a no-op."""

import pytest

from squads._models import _markers as markers
from squads._sections import get_section
from squads._services._maintenance import _converge_body_tag
from squads._view_tags import place_view_tags
from squads._workflow import bundled_spec

_SPEC = bundled_spec()
_TAG = markers.open_marker(markers.view_tag("item_skill"))
_REGIONS = ["", f"\n{_TAG}\n", f"\nSome prose.\n\n{_TAG}\n", f"\n{_TAG}\n\nSome prose.\n"]


@pytest.mark.parametrize("region", _REGIONS)
@pytest.mark.parametrize("edit", [None, "edited\nprose"])
def test_a_crlf_region_places_like_the_same_region_in_lf(region: str, edit: str | None) -> None:
    def place(text: str) -> str:
        return place_view_tags(
            text, edit, seeded=frozenset({"item_skill"}), spec=_SPEC, item_type="skill", addr="x"
        )

    assert place(region.replace("\n", "\r\n")) == place(region)


def test_converging_a_settled_crlf_body_changes_no_line() -> None:
    text = (
        f"{markers.open_marker(markers.BODY)}\r\n{_TAG}\r\n{markers.close_marker(markers.BODY)}\r\n"
    )

    out = _converge_body_tag(text, "item_skill", _SPEC, "skill", "x")

    assert get_section(out, markers.BODY) is not None
    assert [ln.strip() for ln in out.splitlines() if ln.strip()] == [
        ln.strip() for ln in text.splitlines() if ln.strip()
    ]
