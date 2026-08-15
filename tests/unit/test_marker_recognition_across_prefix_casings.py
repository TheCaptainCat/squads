"""``find_markers`` must recognise *every* well-formed sq marker tag, whatever the casing of
the sub-entity ``local_prefix`` embedded in it — while still refusing the documentation
placeholders that appear in agent-facing prose.

This is the primitive behind CLAUDE.md invariant #3: the marker-injection guard and the
``sq check`` marker linter both answer "is there a marker here?" through it and nothing else,
so a tag shape it cannot see is a tag shape neither of them can see either. The blind spot this
module pins existed because the tag class was lowercase-only while every declared
``local_prefix`` is uppercase, and because the only coverage was a single lowercase top-level
tag: the cases below are therefore a *family* — every declared kind, every prefix casing shape,
and one pipeline-level count over a real generated multi-sub-entity file — not one example per
branch.

Marker tags are built at runtime throughout, so this source file contains no literal marker
comment of its own (the same convention as the injection-guard suite).
"""

import re

import pytest

from squads import _discussion as discussion
from squads import _sections as sections
from squads._models import _markers as markers
from squads._workflow import bundled_spec

#: Every ``<!-- sq:... -->``-shaped comment, however malformed its tag — the denominator
#: ``find_markers`` is measured against. Deliberately permissive where ``MARKER_RE`` is strict.
_ANY_SQ_COMMENT = re.compile(r"<!--\s*sq:[^>]*-->")


def _wrap(tag: str) -> str:
    return markers.open_marker(tag)


# --------------------------------------------------------------------------- casing family


#: (label, local_prefix) — the shapes a declared ``local_prefix`` can take. ``local_prefix`` is
#: validated only for non-emptiness and uniqueness, so an adopter is free to use any of these.
_PREFIX_SHAPES = [
    ("all-lowercase", "us"),
    ("all-uppercase", "US"),
    ("mixed-case", "Us"),
    ("single-uppercase-letter", "F"),
    ("digits-only", "7"),
    ("underscored", "U_S"),
    ("hyphenated", "U-S"),
    ("non-ascii-letter", "Ünï"),
]


@pytest.mark.parametrize(("label", "prefix"), _PREFIX_SHAPES, ids=[s[0] for s in _PREFIX_SHAPES])
def test_every_local_prefix_casing_is_recognised_open_and_close(label: str, prefix: str) -> None:
    tag = f"story:{prefix}12"
    text = f"{markers.open_marker(tag)}\nprose\n{markers.close_marker(tag)}\n"
    assert sections.find_markers(text) == [f"sq:{tag}", f"sq:{tag}:end"]


@pytest.mark.parametrize(("label", "prefix"), _PREFIX_SHAPES, ids=[s[0] for s in _PREFIX_SHAPES])
def test_every_nested_sub_region_of_a_sub_entity_block_is_recognised(
    label: str, prefix: str
) -> None:
    """A sub-entity block nests ``:head``/``:body``/``:discussion`` under its own tag — those
    are where the prose actually lives, so a blind spot on them is the damaging one."""
    base = f"finding:{prefix}3"
    tags = [base, f"{base}:head", f"{base}:body", markers.discussion_tag(base)]
    text = "".join(f"{markers.open_marker(t)}{markers.close_marker(t)}" for t in tags)
    expected = [x for t in tags for x in (f"sq:{t}", f"sq:{t}:end")]
    assert sections.find_markers(text) == expected


def test_every_declared_sub_entity_kind_of_the_bundled_spec_is_recognised() -> None:
    """Driven off the spec's own declared kinds rather than a hardcoded three, so a kind added
    to ``workflow.toml`` later is covered the day it lands."""
    spec = bundled_spec()
    assert spec.subentity_kinds, "the bundled spec must declare at least one sub-entity kind"
    for kind, ks in spec.subentity_kinds.items():
        tag = f"{kind}:{ks.local_prefix}1"
        text = f"{markers.open_marker(tag)}{markers.close_marker(tag)}"
        assert sections.find_markers(text) == [f"sq:{tag}", f"sq:{tag}:end"], (
            f"kind {kind!r} (local_prefix {ks.local_prefix!r}) is invisible to find_markers"
        )


# --------------------------------------------------------------------------- strictness family


#: Shapes that are NOT well-formed tags and must stay unrecognised. The first two are live
#: prose in this product's own agent-facing text — the role template's "never alter the
#: ``sq:*`` marker lines" line, and the marker-rejection error message's ellipsis form — so a
#: regression here would make sq lint its own documentation as corruption.
_NON_MARKERS = [
    ("star-placeholder", "<!-- sq:* -->"),
    ("ellipsis-placeholder", "<!-- sq:… -->"),
    ("angle-placeholder", "<!-- sq:<tag> -->"),
    ("empty-tag", "<!-- sq: -->"),
    ("space-in-tag", "<!-- sq:story US1 -->"),
    ("uppercase-sq-namespace", "<!-- SQ:body -->"),
    ("no-sq-namespace", "<!-- body -->"),
    ("not-a-comment", "sq:story:US1"),
]


@pytest.mark.parametrize(("label", "text"), _NON_MARKERS, ids=[s[0] for s in _NON_MARKERS])
def test_prose_that_is_not_a_well_formed_tag_is_never_a_marker(label: str, text: str) -> None:
    assert sections.find_markers(f"prose {text} more prose") == []


def test_the_widened_class_did_not_swallow_the_placeholder_next_to_a_real_marker() -> None:
    """The two must coexist in one file: a role body legitimately documents ``sq:*`` inside a
    region delimited by real markers."""
    text = f"{_wrap(markers.BODY)}\nnever alter the <!-- sq:* --> lines\n"
    assert sections.find_markers(text) == [f"sq:{markers.BODY}"]


# --------------------------------------------------------------------------- pipeline level


def test_every_marker_of_a_production_rendered_sub_entity_block_is_recognised() -> None:
    """The block scaffold as production actually emits it (``_discussion.build_block``, the one
    renderer of a sub-entity region), measured as a whole-text property: the number of tags
    ``find_markers`` reports equals the number of ``<!-- sq:... -->`` comments physically
    present. A synthetic one-tag fixture cannot express that, which is why the original blind
    spot survived a passing suite. The same property over a full, service-written item file is
    pinned at the service layer (tests/service/test_marker_injection_guard.py).
    """
    text = "".join(
        discussion.build_block("finding", f"F{n}", f"finding {n}", body="prose") for n in (1, 2, 3)
    )
    present = _ANY_SQ_COMMENT.findall(text)
    assert len(present) >= 24, "the block scaffold must carry its nested sub-regions"
    assert len(sections.find_markers(text)) == len(present)
