"""A frontmatter timestamp the file does not carry loads as an invented placeholder — and that
placeholder must never be mistaken for on-disk state that diverged from the index.

``created_at``/``updated_at`` are the one part of ``Item.from_frontmatter`` that is not a
function of the file's bytes: absent, they default to ``clock.now()`` so a legacy or
hand-authored ``.md`` loads at all. ``frontmatter_skew`` round-trips *both* sides through that
same loader, so including an invented value in the comparison meant the disk side re-invented a
later ``now`` on every read, could never equal the index, and refused every mutation of the
item for good — with a "run ``sq repair``" pointer repair structurally cannot honour, since it
rebuilds the index from markdown and never rewrites markdown.

The matrix below is per timestamp field x per value shape, because the two fields are read by
separate call sites and only the absent/null shapes are exempt: a value the file *does* carry
must still be compared, and one it carries unparseably must still fail the load boundary.
"""

from datetime import UTC, datetime
from typing import Any

import pytest

from squads import _clock as clock
from squads import _itemfile as itemfile
from squads._errors import SquadsError
from squads._models._item import Item
from squads._sections import join_frontmatter, split_frontmatter

_PATH = "reviews/REV-000002-a-review.md"
_CREATED = "2026-01-01T00:00:00Z"
_UPDATED = "2026-01-02T00:00:00Z"

_FILE = f"""---
id: REV-2
sequence_id: 2
type: review
title: a review
status: Requested
author: reviewer
created_at: '{_CREATED}'
updated_at: '{_UPDATED}'
---
<!-- sq:body -->
scope
<!-- sq:body:end -->
"""

_TIMESTAMP_FIELDS = ["created_at", "updated_at"]


def _base() -> tuple[Item, dict[str, Any], str]:
    data, body = split_frontmatter(_FILE)
    return Item.from_frontmatter(data, path=_PATH), data, body


def _skew(data: dict[str, Any], body: str, base: Item) -> list[str]:
    return itemfile.frontmatter_skew(join_frontmatter(data, body), base)


# --------------------------------------------------------------------------- absent / null


@pytest.mark.parametrize("field", _TIMESTAMP_FIELDS)
def test_an_absent_timestamp_is_not_reported_as_skew(field: str) -> None:
    base, data, body = _base()
    data.pop(field)
    assert _skew(data, body, base) == []


@pytest.mark.parametrize("field", _TIMESTAMP_FIELDS)
def test_an_explicitly_null_timestamp_is_not_reported_as_skew(field: str) -> None:
    """``created_at:`` with nothing after it parses to ``None``, the same absence."""
    base, data, body = _base()
    data[field] = None
    assert _skew(data, body, base) == []


def test_both_timestamps_absent_at_once_is_not_reported_as_skew() -> None:
    base, data, body = _base()
    for field in _TIMESTAMP_FIELDS:
        data.pop(field)
    assert _skew(data, body, base) == []


@pytest.mark.parametrize("field", _TIMESTAMP_FIELDS)
def test_the_verdict_is_stable_across_repeated_reads_of_the_same_file(field: str) -> None:
    """The wedge's defining symptom was that re-reading never converged: each read invented a
    later ``now``, so 'run repair and try again' could not terminate. Advancing the clock
    between reads is what a second attempt actually looks like."""
    base, data, body = _base()
    data.pop(field)
    text = join_frontmatter(data, body)
    verdicts: list[list[str]] = []
    for minute in (0, 5, 60):
        clock.set_now(datetime(2026, 6, 7, 10, minute % 60, 0, tzinfo=UTC))
        verdicts.append(itemfile.frontmatter_skew(text, base))
    assert verdicts == [[], [], []]


# --------------------------------------------------------------------------- values present


@pytest.mark.parametrize("field", _TIMESTAMP_FIELDS)
def test_a_timestamp_the_file_does_carry_is_still_compared(field: str) -> None:
    """The exemption is for absence only — a real divergence on a present value must still be
    refused, which is the whole point of the skew guard."""
    base, data, body = _base()
    data[field] = "2030-05-05T05:05:05Z"
    assert _skew(data, body, base) == [field]


@pytest.mark.parametrize("field", _TIMESTAMP_FIELDS)
@pytest.mark.parametrize("spelling", ["string", "datetime"], ids=["quoted", "unquoted"])
def test_a_matching_timestamp_in_either_yaml_spelling_is_not_skew(
    field: str, spelling: str
) -> None:
    """PyYAML resolves an unquoted timestamp to a ``datetime`` and a quoted one to a string;
    both must round-trip to the index's own value, absence handling notwithstanding."""
    iso = _CREATED if field == "created_at" else _UPDATED
    base, data, body = _base()
    data[field] = iso if spelling == "string" else datetime.fromisoformat(iso)
    assert _skew(data, body, base) == []


@pytest.mark.parametrize("field", _TIMESTAMP_FIELDS)
def test_an_unparseable_timestamp_still_fails_the_load_boundary(field: str) -> None:
    """Not silently exempted into "absent": a value the file *does* carry and that cannot be
    read is a broken file, and must surface as a clean error at the one load boundary."""
    base, data, body = _base()
    data[field] = "not-a-timestamp"
    with pytest.raises(SquadsError, match=field):
        _skew(data, body, base)


def test_an_absent_timestamp_never_masks_a_real_skew_on_another_field() -> None:
    base, data, body = _base()
    data.pop("created_at")
    data.pop("updated_at")
    data["title"] = "changed on disk"
    assert _skew(data, body, base) == ["title"]


# --------------------------------------------------------------------------- injectable clock


@pytest.mark.parametrize("field", _TIMESTAMP_FIELDS)
def test_the_invented_placeholder_comes_from_the_injectable_clock(field: str) -> None:
    """No module in the product reads wall-clock time directly. A forged ``--at`` run (or a
    frozen-time test) must see its own instant here, not ``datetime.now()``."""
    forged = datetime(2019, 3, 4, 5, 6, 7, tzinfo=UTC)
    clock.set_now(forged)
    _base_item, data, _body = _base()
    data.pop(field)
    loaded = Item.from_frontmatter(data, path=_PATH)
    assert getattr(loaded, field) == forged
