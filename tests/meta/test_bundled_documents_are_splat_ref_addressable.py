"""Two load-bearing static properties of the three bundled TOML documents
(``workflow.toml``, ``roles.toml``, ``playbook.toml``), both required by ``_specmerge``'s
splat-ref grammar rather than merely convenient:

1. **Every key, at every nesting level, is a TOML bare key** (``A-Za-z0-9_-``, one or more
   characters). Splat-ref resolution addresses a bundled key by dotted path, and the dotted
   path grammar cannot express a key that requires TOML quoting — most concretely, a
   non-ASCII key. This is deliberately not a runtime check inside the engine: resolution is
   base-only, so a path can only ever address a key the *bundled* document itself declares,
   and this scan is what keeps that key set inside the addressable grammar in the first
   place. Without it, a future bundled key requiring TOML quotes would not be rejected loudly
   — it would be **unaddressable by any path**, and a splat-ref aimed at it would report a
   plain dangling-path violation with no hint that the real problem is the bundled key's own
   spelling. The guard is what turns "unaddressable" into "provably never attempted" instead
   of "silently unreachable".
2. **No bundled string value begins with an unescaped ``$(``.** A bundled document never
   itself uses the splat-ref grammar — only an override does — so no bundled string should
   ever need a leading ``$$(`` escape to survive a merge unchanged. This scan proves that
   holds today, so no tool that ever writes a bundled string verbatim into an override file
   (a scaffold command, a docs generator) owes an escaping duty it could easily forget.

Both are read straight off the real bundled documents via ``tomllib`` — the same way
``_specmerge``'s own tests exercise them — not re-derived from a private assumption about
their shape.
"""

import importlib.resources
import tomllib
from re import compile as re_compile
from typing import Any

#: Mirrors `squads._specmerge._TOKEN_RE`'s path-segment grammar exactly: a TOML bare key.
_BARE_KEY_RE = re_compile(r"^[A-Za-z0-9_-]+$")

#: The three bundled documents this scan covers, by their package-relative filename.
_BUNDLED_DOCUMENT_NAMES: tuple[str, ...] = ("workflow.toml", "roles.toml", "playbook.toml")


def _load_bundled_document(name: str) -> dict[str, Any]:
    pkg = importlib.resources.files("squads._specs")
    raw: dict[str, Any] = tomllib.loads((pkg / name).read_bytes().decode())
    return raw


def _non_bare_keys(node: Any, path: str = "") -> list[str]:
    """Every dotted path, at any depth, whose *own* key segment is not a TOML bare key —
    walks both dicts (table keys) and lists (their elements, which may be tables too;
    list *indices* are never keys, so they never enter the path or get checked)."""
    hits: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            key_path = f"{path}.{key}" if path else str(key)
            if not isinstance(key, str) or not _BARE_KEY_RE.fullmatch(key):
                hits.append(key_path)
            hits.extend(_non_bare_keys(value, key_path))
    elif isinstance(node, list):
        for element in node:
            hits.extend(_non_bare_keys(element, path))
    return hits


def _leading_dollar_paren_values(node: Any, path: str = "") -> list[str]:
    """Every dotted path, at any depth, holding a string value that begins with an unescaped
    ``$(`` — a value already escaped with a leading ``$$(`` does not begin with ``$(`` (its
    first two characters are ``$$``, not ``$(``), so it is correctly never flagged here."""
    hits: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            key_path = f"{path}.{key}" if path else str(key)
            hits.extend(_leading_dollar_paren_values(value, key_path))
    elif isinstance(node, list):
        for element in node:
            hits.extend(_leading_dollar_paren_values(element, path))
    elif isinstance(node, str) and node.startswith("$("):
        hits.append(path)
    return hits


def test_every_bundled_key_at_every_depth_is_a_toml_bare_key() -> None:
    for name in _BUNDLED_DOCUMENT_NAMES:
        document = _load_bundled_document(name)
        hits = _non_bare_keys(document)
        assert not hits, f"{name}: key(s) requiring TOML quoting, unaddressable by any path: {hits}"


def test_no_bundled_string_value_begins_with_an_unescaped_dollar_paren() -> None:
    for name in _BUNDLED_DOCUMENT_NAMES:
        document = _load_bundled_document(name)
        hits = _leading_dollar_paren_values(document)
        assert not hits, f"{name}: string value(s) beginning with an unescaped '$(': {hits}"


# --------------------------------------------------------------------------- guard self-tests
# The two scans above are the load-bearing assertion; these confirm the walkers themselves
# actually detect what they claim to, on a synthetic document, independent of whether the
# real bundled documents happen to be clean.


def test_the_bare_key_scan_catches_a_non_ascii_key_at_any_depth() -> None:
    document = {"items": {"task": {"élan": 1}}}

    assert _non_bare_keys(document) == ["items.task.élan"]


def test_the_bare_key_scan_catches_a_dotted_toml_key_written_with_quotes() -> None:
    # tomllib parses [items."a.b"] into a literal key "a.b" — not a bare key, since a bare
    # key may never itself contain the path delimiter.
    document = tomllib.loads('[items."a.b"]\nx = 1\n')

    assert _non_bare_keys(document) == ["items.a.b"]


def test_the_bare_key_scan_accepts_hyphenated_and_digit_leading_keys() -> None:
    document = {"items": {"user-story": {}, "2fa": {}}}

    assert _non_bare_keys(document) == []


def test_the_leading_dollar_paren_scan_catches_a_value_nested_inside_a_list_of_tables() -> None:
    document = {"types": {"epic": {"roles": [{"enter": ["$(oops)"]}]}}}

    assert _leading_dollar_paren_values(document) == ["types.epic.roles.enter"]


def test_the_leading_dollar_paren_scan_does_not_flag_a_dollar_paren_after_the_first_character() -> (
    None
):
    document = {"types": {"epic": {"commands": ['git commit -m "$(cat msg)"']}}}

    assert _leading_dollar_paren_values(document) == []


def test_the_leading_dollar_paren_scan_does_not_flag_an_escaped_leading_token() -> None:
    document = {"note": "$$(literal)"}

    assert _leading_dollar_paren_values(document) == []
