"""Each check that a type selects (rather than always runs) identifies its findings by one
fixed fragment of its message. No fragment is empty, equal to another or contained in another,
so a test that filters a report by a fragment never picks up a second check's finding.
"""

import itertools

from _selection_table import ALL_FRAGMENTS


def test_no_fragment_is_empty() -> None:
    assert all(ALL_FRAGMENTS.values())


def test_no_fragment_contains_another() -> None:
    for (a, frag_a), (b, frag_b) in itertools.permutations(ALL_FRAGMENTS.items(), 2):
        assert frag_a not in frag_b, (a, b)
