"""Deterministic, seeded fuzz over prose shapes x view positions x move sequences for
``place_view_tags``: stripping takes back exactly what placement inserted, never an author's
own prose, and any sequence of writes and moves converges to a stable no-op."""

import random

import pytest

from squads._models import _markers as markers
from squads._views import place_view_tags, strip_view_tags
from squads._workflow import bundled_spec
from squads._workflow._models import ViewSource, ViewSpec, WorkflowSpec

# A small vocabulary of non-empty lines, plus one heading-shaped line for `after(<regex>)`.
_LINES = ["alpha", "beta gamma", "## Heading", "text with words"]

# A single line break or one blank line — a run of more than one blank line is excluded, since
# the routine's own collapse-to-one-blank-line rule makes a byte-for-byte round trip lossy there.
_SEPARATORS = ["\n", "\n\n"]

# Every position shape the grammar recognises.
_POSITIONS = [
    "top",
    "bottom",
    "after(^alpha$)",
    "after(^## Heading$)",
    "after(^$)",
    "after(no_such_line)",
]


def _random_prose(rng: random.Random) -> str:
    """A short, random multi-line prose blob, 0 to 4 lines joined by a random separator."""
    n = rng.randint(0, 4)
    lines = [rng.choice(_LINES) for _ in range(n)]
    out = ""
    for i, line in enumerate(lines):
        if i:
            out += rng.choice(_SEPARATORS)
        out += line
    return out


def _random_spec(rng: random.Random, names: tuple[str, ...]) -> WorkflowSpec:
    """A synthetic spec declaring one view per *names*, each at an independently random position."""
    return bundled_spec().model_copy(
        update={
            "views": {
                name: ViewSpec(source=ViewSource(kind="self"), position=rng.choice(_POSITIONS))
                for name in names
            }
        }
    )


_VIEW_NAMES = ("v1", "v2")


@pytest.mark.parametrize("seed", range(400))
def test_a_single_write_round_trips_and_repeats_identically(seed: int) -> None:
    """Placing then stripping every tag restores the original prose byte-for-byte, and a
    second identical write reproduces the first exactly."""
    rng = random.Random(seed)
    prose = _random_prose(rng)
    spec = _random_spec(rng, _VIEW_NAMES)
    seeded = frozenset(_VIEW_NAMES)

    once = place_view_tags(prose, None, seeded=seeded, spec=spec, item_type="task", addr=1)
    assert strip_view_tags(once).strip("\n") == prose.strip("\n")

    twice = place_view_tags(once, None, seeded=seeded, spec=spec, item_type="task", addr=1)
    assert twice == once


@pytest.mark.parametrize("seed", range(400))
def test_a_move_sequence_converges_to_a_stable_no_op(seed: int) -> None:
    """Placing, then re-placing under a moved spec, then writing that spec again converges:
    the last two writes are byte-identical."""
    rng = random.Random(seed)
    prose = _random_prose(rng)
    spec1 = _random_spec(rng, _VIEW_NAMES)
    spec2 = _random_spec(rng, _VIEW_NAMES)
    seeded = frozenset(_VIEW_NAMES)

    once = place_view_tags(prose, None, seeded=seeded, spec=spec1, item_type="task", addr=1)
    moved = place_view_tags(once, None, seeded=seeded, spec=spec2, item_type="task", addr=1)
    moved_again = place_view_tags(moved, None, seeded=seeded, spec=spec2, item_type="task", addr=1)

    assert moved == moved_again
    assert strip_view_tags(moved).strip("\n") == prose.strip("\n")


# --------------------------------------------------------------------- whitespace-only line

#: A line holding only horizontal whitespace — Markdown (and `after(^\s*$)`) reads it as blank,
#: the same as a genuinely empty line.
_WS_FILLERS = [" ", "  ", "\t", " \t "]


@pytest.mark.parametrize("seed", range(200))
def test_a_whitespace_only_line_round_trips_like_any_other_blank_line(seed: int) -> None:
    """A whitespace-only line round trips like any other blank line, and a second identical
    write repeats byte-for-byte."""
    rng = random.Random(seed)
    line1, line2 = rng.choice(_LINES), rng.choice(_LINES)
    ws = rng.choice(_WS_FILLERS)
    prose = f"{line1}\n{ws}\n{line2}"
    spec = bundled_spec().model_copy(
        update={"views": {"v1": ViewSpec(source=ViewSource(kind="self"), position=r"after(^\s*$)")}}
    )
    seeded = frozenset({"v1"})

    once = place_view_tags(prose, None, seeded=seeded, spec=spec, item_type="task", addr=1)
    assert once == f"{line1}\n\n<!-- sq:view:v1 -->\n\n{line2}"

    twice = place_view_tags(once, None, seeded=seeded, spec=spec, item_type="task", addr=1)
    assert twice == once

    assert strip_view_tags(once) == f"{line1}\n\n{line2}"


def test_a_whitespace_only_line_between_two_hand_placed_tags_breaks_their_chain() -> None:
    """A whitespace-only line between two hand-placed tags breaks their chain, and stripping
    both restores it exactly."""
    tag1 = markers.open_marker(markers.view_tag("v1"))
    tag2 = markers.open_marker(markers.view_tag("v2"))
    text = f"alpha\n{tag1}\n  \n{tag2}\nbeta"

    assert strip_view_tags(text) == "alpha\n  \nbeta"
