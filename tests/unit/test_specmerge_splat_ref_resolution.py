"""Splat-ref resolution against a bundled base — before any merging, before any model
validation. Grammar: `$(path)` splices, `$(*path)` spreads, `$(self)`/`$(*self)` address the
key currently being written, `$$(` escapes a literal `$(`."""

import importlib.resources
import tomllib
from typing import Any

import pytest

from squads._specmerge import resolve_splat_refs


def _bundled_playbook() -> dict[str, Any]:
    pkg = importlib.resources.files("squads._specs")
    raw: dict[str, Any] = tomllib.loads((pkg / "playbook.toml").read_bytes().decode())
    return raw


def test_append_via_star_self_yields_base_elements_followed_by_the_new_one() -> None:
    base = {"widgets": {"colors": ["red", "green"]}}
    override = {"widgets": {"colors": ["$(*self)", "blue"]}}

    resolved, violations = resolve_splat_refs(base, override, "test-origin")

    assert violations == []
    assert resolved["widgets"]["colors"] == ["red", "green", "blue"]


def test_a_later_change_to_the_base_list_flows_through_with_the_override_untouched() -> None:
    override = {"widgets": {"colors": ["$(*self)", "blue"]}}

    base_v1 = {"widgets": {"colors": ["red"]}}
    resolved_v1, violations_v1 = resolve_splat_refs(base_v1, override, "o")
    assert violations_v1 == []
    assert resolved_v1["widgets"]["colors"] == ["red", "blue"]

    base_v2 = {"widgets": {"colors": ["red", "green"]}}
    resolved_v2, violations_v2 = resolve_splat_refs(base_v2, override, "o")
    assert violations_v2 == []
    assert resolved_v2["widgets"]["colors"] == ["red", "green", "blue"]


def test_dotted_path_addresses_a_keyed_table_elsewhere() -> None:
    base = {"items": {"task": {"validators": ["required-body"]}}}
    override = {"items": {"bug": {"validators": ["$(*items.task.validators)", "repro-steps"]}}}

    resolved, violations = resolve_splat_refs(base, override, "o")

    assert violations == []
    assert resolved["items"]["bug"]["validators"] == ["required-body", "repro-steps"]


def test_splice_without_star_splices_the_base_value_as_a_single_element() -> None:
    base = {"defaults": {"role": "python-dev"}, "widgets": {"owner": "nobody"}}
    override = {"widgets": {"owner": "$(defaults.role)"}}

    resolved, violations = resolve_splat_refs(base, override, "o")

    assert violations == []
    assert resolved["widgets"]["owner"] == "python-dev"


def test_dangling_splat_path_fails_closed() -> None:
    base = {"widgets": {"colors": ["red"]}}
    override = {"widgets": {"colors": ["$(*no.such.path)"]}}

    _resolved, violations = resolve_splat_refs(base, override, "override.toml")

    assert len(violations) == 1
    assert "dangling" in violations[0].reason
    assert violations[0].origin == "override.toml"


def test_star_self_on_a_key_with_no_base_counterpart_dangles() -> None:
    base = {"widgets": {}}
    override = {"widgets": {"brand_new": ["$(*self)", "x"]}}

    _resolved, violations = resolve_splat_refs(base, override, "o")

    assert len(violations) == 1
    assert "dangling" in violations[0].reason
    assert violations[0].path == "widgets.brand_new"


def test_spread_whose_base_value_is_not_a_list_fails_closed_with_a_type_mismatch() -> None:
    base = {"widgets": {"colors": "red"}}
    override = {"widgets": {"colors": ["$(*self)", "blue"]}}

    _resolved, violations = resolve_splat_refs(base, override, "o")

    assert len(violations) == 1
    assert "not a list" in violations[0].reason


def test_spread_token_used_outside_a_list_fails_closed() -> None:
    base = {"widgets": {"colors": ["red", "green"]}}
    override = {"widgets": {"colors": "$(*self)"}}

    _resolved, violations = resolve_splat_refs(base, override, "o")

    assert len(violations) == 1
    assert "nothing to spread into" in violations[0].reason


def test_a_dollar_paren_not_at_the_start_is_data_with_no_violation() -> None:
    """Token territory is `begins with`, not `contains` — a value with the sigil anywhere
    after its first character is data, always, with no violation and no escape needed. This
    is what keeps an interpolation attempt (and a real playbook command line, exercised
    below) merging through inert."""
    base = {"widgets": {}}
    override = {"widgets": {"note": "see $(docs) for details"}}

    resolved, violations = resolve_splat_refs(base, override, "o")

    assert violations == []
    assert resolved["widgets"]["note"] == "see $(docs) for details"


def test_a_playbook_command_line_survives_the_merge_byte_for_byte() -> None:
    """The sigil is POSIX command substitution and the playbook's `commands` entries are
    shell command lines — this is the case an adopter meets first, and it must never be
    refused as a splat-ref grammar error for a grammar its author never used."""
    base = {"types": {}}
    override = {"types": {"epic": {"commands": ['git commit -m "$(cat msg)"']}}}

    resolved, violations = resolve_splat_refs(base, override, "o")

    assert violations == []
    assert resolved["types"]["epic"]["commands"] == ['git commit -m "$(cat msg)"']


def test_a_value_beginning_with_the_sigil_but_not_a_well_formed_token_is_malformed() -> None:
    """Unlike the playbook command line above, this value's *first* character is the sigil,
    so it is in token territory by the stated rule ("begins with"), and "date +%s) --flag" is
    not a whole-value dotted-path token — trailing content after the token, like leading
    content before it, is not a partial match. In territory and not well-formed means
    malformed, with no third reading."""
    base = {"widgets": {}}
    override = {"widgets": {"note": "$(date +%s) --flag"}}

    _resolved, violations = resolve_splat_refs(base, override, "o")

    assert len(violations) == 1
    assert "malformed splat-ref path" in violations[0].reason


def test_a_leading_double_dollar_paren_escapes_to_a_literal() -> None:
    base = {"widgets": {}}
    override = {"widgets": {"note": "$$(foo) is now a literal"}}

    resolved, violations = resolve_splat_refs(base, override, "o")

    assert violations == []
    assert resolved["widgets"]["note"] == "$(foo) is now a literal"


def test_a_double_dollar_paren_not_at_the_start_is_never_unescaped() -> None:
    """Only a *leading* sigil is ever escaped — a `$$(` occurring later in the string is
    outside token territory in the first place, so it is data like everything else there,
    left exactly as written rather than being unescaped too."""
    base = {"widgets": {}}
    override = {"widgets": {"note": "literally $$(foo) stays as text"}}

    resolved, violations = resolve_splat_refs(base, override, "o")

    assert violations == []
    assert resolved["widgets"]["note"] == "literally $$(foo) stays as text"


def test_a_resolved_spliced_value_is_not_itself_re_scanned_for_tokens() -> None:
    base = {"literal": {"value": "$(never.resolved)"}, "widgets": {}}
    override = {"widgets": {"copy": "$(literal.value)"}}

    resolved, violations = resolve_splat_refs(base, override, "o")

    assert violations == []
    assert resolved["widgets"]["copy"] == "$(never.resolved)"


def test_array_of_tables_splat_append_against_a_real_parsed_toml_inline_array_override() -> None:
    """The override must use TOML's inline-array form for a splatted array of tables,
    because the header form (`[[...]]`) has no slot for a token."""
    base = _bundled_playbook()
    override_source = """
    [types.feature]
    roles = ["$(*self)", { slug = "custom-role", enter = ["do the custom thing"] }]
    """
    override = tomllib.loads(override_source)

    resolved, violations = resolve_splat_refs(base, override, "playbook-override.toml")

    assert violations == []
    feature_roles = resolved["types"]["feature"]["roles"]
    assert feature_roles[:-1] == base["types"]["feature"]["roles"]
    assert feature_roles[-1] == {"slug": "custom-role", "enter": ["do the custom thing"]}


# --------------------------------------------------------------------- out-of-grammar paths
# A path shaped like a whole-string token (starts `$(`, ends `)`) but outside the grammar is a
# *malformed path*, distinct from a `$(` occurring inside otherwise-ordinary text (which stays
# the generic "surviving token" case, exercised above). Table-driven: every one of these must
# name the real problem instead of contradicting what the adopter actually wrote. A path
# segment is exactly a TOML bare key (`A-Za-z0-9_-`, one or more characters) — a hyphen and a
# leading digit are *not* malformed (see the grammar-widens tests below); only a shape TOML
# itself could never key without quotes, or a structurally broken token, lands here.
_MALFORMED_PATHS = [
    "$(élan)",  # non-ASCII first character — necessarily a quoted TOML key
    "$(itéms)",  # non-ASCII after the first character: the exact asymmetry that was open
    "$(items..task)",  # empty path segment
    "$()",  # empty path
    "$(*)",  # empty path, spread form
    "$(**items)",  # double star
]


@pytest.mark.parametrize("value", _MALFORMED_PATHS)
def test_an_out_of_grammar_splat_path_is_reported_as_malformed_not_as_surviving(
    value: str,
) -> None:
    base = {"items": {}}
    override = {"items": {"x": value}}

    _resolved, violations = resolve_splat_refs(base, override, "o")

    assert len(violations) == 1
    assert "malformed splat-ref path" in violations[0].reason
    assert "the entire string" not in violations[0].hint  # the surviving-token hint, wrong here


def test_a_dollar_paren_inside_ordinary_text_is_never_diagnosed_as_malformed() -> None:
    """The malformed-path diagnosis applies only inside token territory — a string that does
    not begin with the sigil is never in territory, however many `$(` occurrences (malformed
    or otherwise) it holds later on, so it is data with no violation of any kind."""
    base = {"items": {}}
    override = {"items": {"x": "see $(docs) for more, or $(items.élan) maybe"}}

    resolved, violations = resolve_splat_refs(base, override, "o")

    assert violations == []
    assert resolved["items"]["x"] == "see $(docs) for more, or $(items.élan) maybe"


# ------------------------------------------------------------- the grammar widens, not narrows
# A path segment addresses exactly what TOML can key without quotes — the abbreviation rule
# means a value the adopter may write literally (a hyphenated type, a digit-leading one) has
# to stay expressible as a reference.


def test_a_hyphenated_path_segment_resolves_a_bundled_key() -> None:
    base = {"items": {"user-story": {"validators": ["a", "b"]}}}
    override = {"items": {"bug": {"validators": ["$(*items.user-story.validators)", "v"]}}}

    resolved, violations = resolve_splat_refs(base, override, "o")

    assert violations == []
    assert resolved["items"]["bug"]["validators"] == ["a", "b", "v"]


def test_a_digit_leading_path_segment_resolves_a_bundled_key() -> None:
    base = {"items": {"2fa": {"prefix": "2FA"}}}
    override = {"items": {"x": "$(items.2fa.prefix)"}}

    resolved, violations = resolve_splat_refs(base, override, "o")

    assert violations == []
    assert resolved["items"]["x"] == "2FA"


def test_a_hyphenated_path_with_no_bundled_counterpart_still_dangles() -> None:
    """Widening the grammar does not widen what exists in the base — a hyphenated path is
    addressable, not automatically present."""
    base = {"items": {}}
    override = {"items": {"x": "$(items.no-such-type)"}}

    _resolved, violations = resolve_splat_refs(base, override, "o")

    assert len(violations) == 1
    assert "dangling" in violations[0].reason


# ------------------------------------------------------------------------------- key positions


def test_a_grammar_valid_token_used_as_a_key_fails_closed_naming_the_key() -> None:
    base = {"items": {"task": {"a": 1}}}
    override = {"items": {"$(items.task)": {"a": 2}}}

    _resolved, violations = resolve_splat_refs(base, override, "o")

    assert len(violations) == 1
    assert "used as a key" in violations[0].reason


def test_an_unclosed_token_key_fails_closed_as_malformed_not_as_vocabulary() -> None:
    """A key beginning with the sigil is in token territory and gets refused — an unclosed
    token is malformed, not passed through, so the typo never becomes a real key. Since
    section keys are the vocabulary itself (a type name, a status name, …), that refusal is
    the only thing standing between a typo and a minted vocabulary entry."""
    base = {"items": {"task": {"a": 1}}}
    override = {"items": {"$(oops": {"a": 2}}}

    _resolved, violations = resolve_splat_refs(base, override, "o")

    assert len(violations) == 1
    assert "malformed splat-ref path" in violations[0].reason


def test_a_key_with_the_sigil_not_at_the_start_passes_through_untouched() -> None:
    """A key is only ever refused when it is *in* token territory (begins with the sigil) —
    one occurring later is data, exactly like a value."""
    base = {"items": {}}
    override = {"items": {"weird-$(x)-key": {"a": 1}}}

    resolved, violations = resolve_splat_refs(base, override, "o")

    assert violations == []
    assert list(resolved["items"]) == ["weird-$(x)-key"]


def test_a_malformed_path_shaped_key_is_reported_as_malformed_too() -> None:
    base = {"items": {}}
    override = {"items": {"$(élan)": {}}}

    _resolved, violations = resolve_splat_refs(base, override, "o")

    assert len(violations) == 1
    assert "malformed splat-ref path" in violations[0].reason


def test_a_hyphenated_grammar_valid_token_used_as_a_key_still_fails_as_a_key_not_as_malformed() -> (
    None
):
    """The grammar widening only changes what counts as malformed — a hyphenated path is now
    grammar-valid, so as a key it hits the "used as a key" case, not "malformed"."""
    base = {"items": {"user-story": {"a": 1}}}
    override = {"items": {"$(items.user-story)": {"a": 2}}}

    _resolved, violations = resolve_splat_refs(base, override, "o")

    assert len(violations) == 1
    assert "used as a key" in violations[0].reason


def test_an_escaped_dollar_paren_key_unescapes_to_a_literal_key_with_no_violation() -> None:
    base = {"items": {}}
    override = {"items": {"$$(literal)": {"a": 1}}}

    resolved, violations = resolve_splat_refs(base, override, "o")

    assert violations == []
    assert list(resolved["items"]) == ["$(literal)"]


def test_an_ordinary_key_is_left_completely_untouched() -> None:
    base = {"items": {}}
    override = {"items": {"ordinary-ish_key": {"a": 1}}}

    resolved, violations = resolve_splat_refs(base, override, "o")

    assert violations == []
    assert list(resolved["items"]) == ["ordinary-ish_key"]


# ------------------------------------------------------------------------- trailing whitespace


@pytest.mark.parametrize("value", ["$(items)\n", "$(items)\n\n", "$(items) "])
def test_a_token_with_trailing_whitespace_is_malformed_not_resolved(value: str) -> None:
    """The token must be the *entire* string value — Python's `$` regex anchor alone would
    let a single trailing newline through; every trailing-whitespace shape must fail the same
    way, with no special case for a trailing newline. These values begin with the sigil, so
    they are in territory and a failed `_parse_token` there is always malformed."""
    base = {"items": ["a", "b"]}
    override = {"x": value}

    _resolved, violations = resolve_splat_refs(base, override, "o")

    assert len(violations) == 1
    assert "malformed splat-ref path" in violations[0].reason


@pytest.mark.parametrize("value", [" $(items)", "\n$(items)"])
def test_a_token_with_leading_whitespace_is_data_not_a_violation(value: str) -> None:
    """A value that does *not* begin with the sigil is never in token territory in the first
    place, whatever follows — leading whitespace before the token makes it data, not a
    malformed token, the same rule that keeps an interpolation attempt literal."""
    base = {"items": ["a", "b"]}
    override = {"x": value}

    resolved, violations = resolve_splat_refs(base, override, "o")

    assert violations == []
    assert resolved["x"] == value


# ------------------------------------------------------------------------------ nested lists
# `self`/`*self` addresses the key currently being written; a list position has no dotted
# name of its own to extend the path with, so inside a nested list `self` necessarily still
# means the *enclosing* key — there is nothing else it could mean. Pinned here as the intended
# behaviour, not left to be accidental.


def test_star_self_inside_a_nested_list_resolves_against_the_enclosing_key() -> None:
    base = {"a": ["x", "y"]}
    override = {"a": [["$(*self)"], "z"]}

    resolved, violations = resolve_splat_refs(base, override, "o")

    assert violations == []
    assert resolved == {"a": [["x", "y"], "z"]}


def test_spread_of_an_empty_base_list_yields_just_the_new_elements_with_no_violation() -> None:
    """Distinct from the dangling case (a key with no base counterpart at all), which does
    fail — an empty base list is a real, present list, just with nothing in it."""
    base = {"a": []}
    override = {"a": ["$(*self)", "new"]}

    resolved, violations = resolve_splat_refs(base, override, "o")

    assert violations == []
    assert resolved == {"a": ["new"]}


def test_the_same_base_list_spread_twice_duplicates_it() -> None:
    """Compose-only permits this: two spreads of one base list both add, neither removes."""
    base = {"a": [1, 2]}
    override = {"a": ["$(*self)", "$(*a)"]}

    resolved, violations = resolve_splat_refs(base, override, "o")

    assert violations == []
    assert resolved == {"a": [1, 2, 1, 2]}


# --------------------------------------------------------------------------------- deep nesting


def test_a_pathologically_deep_dotted_key_chain_collects_a_violation_not_a_recursion_error() -> (
    None
):
    """A ~2000-segment dotted-key chain is legal TOML (`tomllib` accepts it happily) — the
    engine, not the parser, is the only place left to guard against an uncaught
    ``RecursionError``. The refusal collects on the same violation channel as every other
    mechanism — `resolve_splat_refs` never raises."""
    segments = ".".join(f"k{i}" for i in range(2000))
    override = tomllib.loads(f"{segments} = 1\n")

    _resolved, violations = resolve_splat_refs({}, override, "o")

    assert len(violations) == 1
    assert "nesting exceeds" in violations[0].reason
