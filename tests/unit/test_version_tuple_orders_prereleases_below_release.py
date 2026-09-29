"""``version_tuple`` orders a prerelease below its own release, across every shape a
squads version stamp or a chlog bound can take."""

import pytest

from squads._util import version_tuple

# (lower, higher): each pair must satisfy version_tuple(lower) < version_tuple(higher).
_ORDERED = [
    pytest.param("0.14.0", "0.15.0", id="clean-minor"),
    pytest.param("0.9.0", "0.10.0", id="multi-digit-segment"),
    pytest.param("1.2.3", "1.2.4", id="clean-patch"),
    pytest.param("0.14.0rc1", "0.14.0", id="rc-below-own-release"),
    pytest.param("0.14.0a1", "0.14.0", id="alpha-below-own-release"),
    pytest.param("0.14.0b2", "0.14.0", id="beta-below-own-release"),
    pytest.param("0.14.0.dev3", "0.14.0", id="dev-below-own-release"),
    pytest.param("0.14.0-rc1", "0.14.0", id="dash-separated-rc"),
    pytest.param("0.13.1", "0.14.0rc1", id="rc-above-previous-release"),
    pytest.param("0.14.0rc1", "0.15.0", id="rc-below-next-release"),
    pytest.param("0.14.0rc1", "0.14.1", id="rc-below-next-patch"),
    pytest.param("0.14.0a1", "0.14.0b1", id="alpha-below-beta"),
    pytest.param("0.14.0b1", "0.14.0rc1", id="beta-below-rc"),
    pytest.param("0.14.0.dev9", "0.14.0a1", id="dev-below-alpha"),
    pytest.param("0.14.0rc9", "0.14.0rc10", id="rc-multi-digit"),
    pytest.param("v0.14.0rc1", "v0.14.0", id="leading-v-prerelease"),
    pytest.param("v0.13.0", "0.14.0", id="leading-v-mixed"),
    pytest.param("0", "0.1.0", id="sentinel-zero-below-real"),
    pytest.param("0.14.0", "0.14.0-post1", id="dash-post-above-release"),
    pytest.param("0.14.0", "0.14.0.post1", id="dot-post-above-release"),
    pytest.param("0.14.0-post1", "0.14.1", id="post-below-next-patch"),
    pytest.param("0.14.0.post1", "0.14.0.post2", id="post-numbers-order"),
    pytest.param("0.14.0rc1.dev2", "0.14.0rc1", id="dev-of-rc-below-rc"),
    pytest.param("0.13.1", "0.14.0rc1.dev2", id="dev-of-rc-above-previous-release"),
    pytest.param("0.14.0rc1.dev2", "0.14.0", id="dev-of-rc-below-release"),
    pytest.param("0.14.0.dev1", "0.14.0.dev2", id="dev-numbers-order"),
    pytest.param("1.2.3", "1.2.3.1rc1", id="four-segment-rc-above-three-segment-release"),
    pytest.param("1.2.3.1rc1", "1.2.3.1", id="four-segment-rc-below-its-release"),
    pytest.param("1.2.3.1", "1.2.4", id="four-segment-release-below-next-patch"),
    pytest.param("0.14.0", "0.14.0.1", id="fourth-segment-above"),
]

# Pairs that must compare equal.
_EQUAL = [
    pytest.param("0.14", "0.14.0", id="short-equals-padded"),
    pytest.param("v0.14.0", "0.14.0", id="leading-v-ignored"),
    pytest.param("0.14.0", "0.14.0.0", id="trailing-zero-ignored"),
    pytest.param("0.14.0rc1", "0.14.0-rc1", id="separator-ignored"),
]


@pytest.mark.parametrize(("lower", "higher"), _ORDERED)
def test_lower_sorts_below_higher(lower, higher):
    assert version_tuple(lower) < version_tuple(higher)
    assert not version_tuple(higher) < version_tuple(lower)
    assert sorted([higher, lower], key=version_tuple) == [lower, higher]
    assert min([higher, lower], key=version_tuple) == lower


@pytest.mark.parametrize(("a", "b"), _EQUAL)
def test_equivalent_spellings_compare_equal(a, b):
    assert version_tuple(a) == version_tuple(b)


@pytest.mark.parametrize(
    ("text", "as_release"),
    [
        pytest.param("0.14.0a1b2", "0.14.0", id="stacked-suffix"),
        pytest.param("0.14.0 rc1", "0.14.0", id="space-before-tag"),
        pytest.param("0.14.x9", "0.14.0", id="letter-before-digits"),
    ],
)
def test_unparseable_text_never_joins_digits_across_a_suffix(text, as_release):
    assert version_tuple(text) == version_tuple(as_release)


def test_segment_without_digits_falls_back_to_zero():
    assert version_tuple("0.x.1") == version_tuple("0.0.1")
    assert version_tuple("garbage") == version_tuple("0")


def test_full_release_history_sorts_in_release_order():
    shuffled = ["0.15.0", "0.14.0", "0.14.0rc1", "0.13.1", "0.14.0a1", "0.14.0rc10", "0.14.0rc2"]
    assert sorted(shuffled, key=version_tuple) == [
        "0.13.1",
        "0.14.0a1",
        "0.14.0rc1",
        "0.14.0rc2",
        "0.14.0rc10",
        "0.14.0",
        "0.15.0",
    ]
