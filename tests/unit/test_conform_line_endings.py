"""A rewritten file keeps the endings of the lines it did not touch, and what it adds or changes
takes the file's dominant ending."""

import random
import time
from itertools import pairwise

import pytest

from squads import _sections
from squads._sections import conform_line_endings, dominant_eol, split_lines

_CASES = [
    pytest.param("a\nb\nc\n", "a\nX\nc\n", "a\nX\nc\n", id="lf-only-is-returned-as-given"),
    pytest.param("a\r\nb\r\nc\r\n", "a\nb\nc\n", "a\r\nb\r\nc\r\n", id="crlf-unchanged"),
    pytest.param("a\r\nb\r\nc\r\n", "a\nX\nc\n", "a\r\nX\r\nc\r\n", id="crlf-changed-line"),
    pytest.param(
        "a\r\nb\r\n", "a\r\nb\r\nnew\nmore\n", "a\r\nb\r\nnew\r\nmore\r\n", id="crlf-append"
    ),
    pytest.param("a\r\nc\r\n", "a\nb\nc\n", "a\r\nb\r\nc\r\n", id="crlf-insert-middle"),
    pytest.param("a\r\nb\r\nc\r\n", "a\nc\n", "a\r\nc\r\n", id="crlf-delete-middle"),
    pytest.param(
        "a\r\nb\nc\r\nd\r\n",
        "a\nb\nc\nd\nnew\n",
        "a\r\nb\nc\r\nd\r\nnew\r\n",
        id="mixed-keeps-each-line",
    ),
    pytest.param(
        "a\nb\nc\r\n", "a\nb\nc\nnew\n", "a\nb\nc\r\nnew\n", id="mixed-lf-majority-adds-lf"
    ),
    pytest.param("a\r\nb", "a\nb\nc\n", "a\r\nb\r\nc\r\n", id="last-line-gains-an-ending"),
    pytest.param("a\r\nb\r\n", "a\r\nb", "a\r\nb", id="last-line-loses-its-ending"),
    pytest.param(
        "a\nb\r\nc\n", "a\nB\nc\n", "a\nB\r\nc\n", id="an-edited-line-keeps-its-own-ending"
    ),
    pytest.param(
        "a\nb\r\nc\n", "a\nB\nB2\nc\n", "a\nB\nB2\nc\n", id="a-line-split-in-two-takes-the-dominant"
    ),
    pytest.param("", "x\n", "x\n", id="empty-old"),
]


@pytest.mark.parametrize("greedy", [False, True], ids=["full-diff", "greedy"])
@pytest.mark.parametrize(("old", "new", "expected"), _CASES)
def test_untouched_lines_keep_their_ending_and_added_lines_take_the_dominant(
    monkeypatch: pytest.MonkeyPatch, old: str, new: str, expected: str, greedy: bool
) -> None:
    if greedy:
        monkeypatch.setattr(_sections, "_FULL_DIFF_CELLS", -1)
    assert conform_line_endings(old, new) == expected


def test_a_large_file_with_scattered_edits_conforms_in_linear_time() -> None:
    old = "".join(f"line {i % 50}\r\n" if i % 7 else "\r\n" for i in range(40_000))
    new = "".join(
        f"edited {i}\n" if i % 997 == 0 else ln.replace("\r\n", "\n")
        for i, ln in enumerate(old.splitlines(keepends=True))
    )

    started = time.perf_counter()
    out = conform_line_endings(old, new)

    assert time.perf_counter() - started < 3
    assert "\n" not in out.replace("\r\n", "")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("a\r\nb\r\n", "\r\n"),
        ("a\nb\n", "\n"),
        ("a\r\nb\n", "\n"),
        ("a\r\nb\r\nc\n", "\r\n"),
        ("", "\n"),
    ],
)
def test_the_dominant_ending_is_crlf_only_when_strictly_most_lines_use_it(
    text: str, expected: str
) -> None:
    assert dominant_eol(text) == expected


def _endings(text: str) -> list[str]:
    return [ln[len(ln.rstrip("\r\n")) :] for ln in split_lines(text, keepends=True)]


@pytest.mark.parametrize("cells", [-1, 4_000_000], ids=["greedy", "full-diff"])
def test_a_far_duplicate_does_not_strip_the_lines_before_it(
    monkeypatch: pytest.MonkeyPatch, cells: int
) -> None:
    monkeypatch.setattr(_sections, "_FULL_DIFF_CELLS", cells)
    lines = [f"line {i}" + ("\r\n" if i % 2 else "\n") for i in range(3000)]
    old = "".join(lines)
    edited = list(lines)
    edited[2900] = "edited 2900\n"
    edited.insert(10, lines[2800])
    new = "".join(edited)

    out = conform_line_endings(old, new)

    want = [
        *_endings("".join(lines[:10])),
        *_endings(lines[2800]),
        *_endings("".join(lines[10:2900])),
        "\n",
        *_endings("".join(lines[2901:])),
    ]
    assert _endings(out) == want


@pytest.mark.parametrize("cells", [50, 4_000_000], ids=["anchored", "full-diff"])
@pytest.mark.parametrize("seed", range(20))
def test_every_untouched_line_keeps_its_ending_under_random_edits(
    monkeypatch: pytest.MonkeyPatch, cells: int, seed: int
) -> None:
    monkeypatch.setattr(_sections, "_FULL_DIFF_CELLS", cells)
    rng = random.Random(seed)

    def ending(content: str) -> str:  # duplicates share one ending, so any alignment of them agrees
        return "\r\n" if sum(map(ord, content)) % 2 else "\n"

    contents = [
        f"unique {i}" if rng.random() < 0.8 else rng.choice(["", "dup a", "dup b"])
        for i in range(300)
    ]
    old_lines = [(c, ending(c)) for c in contents]
    new_lines: list[tuple[str, str | None]] = [(c, e) for c, e in old_lines]
    loose: set[str] = set()
    for _ in range(15):
        at = rng.randrange(len(new_lines))
        match rng.choice(["edit", "insert", "delete", "duplicate"]):
            case "edit":
                new_lines[at] = (f"edit {rng.random()}", None)
            case "insert":
                new_lines.insert(at, (f"new {rng.random()}", None))
            case "delete":
                del new_lines[at]
            case _:  # which of the equal lines is the old one is a free choice: assert none
                loose.add(new_lines[at][0])
                new_lines.insert(rng.randrange(len(new_lines)), (new_lines[at][0], None))
    old = "".join(c + e for c, e in old_lines)
    new = "".join(c + "\n" for c, _ in new_lines)

    out = split_lines(conform_line_endings(old, new), keepends=True)

    assert [ln.rstrip("\r\n") for ln in out] == [c for c, _ in new_lines]
    for line, (content, kept) in zip(out, new_lines, strict=True):
        if kept is not None and content not in loose:
            assert line[len(content) :] == kept, content


@pytest.mark.parametrize("seed", range(60))
def test_swapping_two_lines_leaves_every_other_ending_alone(
    monkeypatch: pytest.MonkeyPatch, seed: int
) -> None:
    monkeypatch.setattr(_sections, "_FULL_DIFF_CELLS", 50)
    rng = random.Random(seed)
    lines = [(f"unique {i}", rng.choice(["\n", "\r\n"])) for i in range(200)]
    a, b = sorted(rng.sample(range(200), 2))
    if b - a == 2:  # one line between: it and either swapped line are equally good anchors
        b += 1
    swapped = list(lines)
    swapped[a], swapped[b] = swapped[b], swapped[a]
    old = "".join(c + e for c, e in lines)
    new = "".join(c + "\n" for c, _ in swapped)

    out = split_lines(conform_line_endings(old, new), keepends=True)

    assert [ln.rstrip("\r\n") for ln in out] == [c for c, _ in swapped]
    for k, (line, (content, _)) in enumerate(zip(out, swapped, strict=True)):
        if k not in (a, b):
            assert line[len(content) :] == lines[k][1], content


@pytest.mark.parametrize("seed", range(60))
def test_the_alignment_tiles_both_texts_in_order_when_lines_move(
    monkeypatch: pytest.MonkeyPatch, seed: int
) -> None:
    monkeypatch.setattr(_sections, "_FULL_DIFF_CELLS", 50)
    rng = random.Random(seed)
    old = [f"unique {i}" for i in range(200)]
    new = list(old)
    for _ in range(rng.randrange(1, 5)):
        a, b = rng.sample(range(200), 2)
        new[a], new[b] = new[b], new[a]

    runs = _sections._align(old, new)

    assert (runs[0][1], runs[0][3]) == (0, 0)
    for (_, _, i2, _, j2), (_, i1, _, j1, _) in pairwise(runs):
        assert (i2, j2) == (i1, j1)
    assert (runs[-1][2], runs[-1][4]) == (len(old), len(new))
    for same, i1, i2, j1, j2 in runs:
        assert i2 >= i1 and j2 >= j1
        assert not same or old[i1:i2] == new[j1:j2]
