"""Shared, loader-agnostic override-merge engine over raw parsed-TOML mappings.

Turns a bundled base document and a project override document into an effective merged
document, entirely on ``dict[str, Any]`` in, ``dict[str, Any]`` out — before any pydantic
model validation, since the strictly-typed spec models set ``extra="forbid"`` and would
reject an unresolved splat token or a stray ``[selected]`` table as a type error before
this engine ever got a chance to resolve it.

Four mechanisms, the first three applied in one fixed order by :func:`merge_override`:

1. **The override document's own top level** (:func:`_top_level_key_violations`) — a closed
   key space when the caller supplies one: an unrecognised top-level key is a collected
   violation naming it. Checked first, and only here, because after the merge every base key
   is present and the override's own top level is no longer distinguishable from it.
2. **Splat-refs** (:func:`resolve_splat_refs`) — resolve ``$(path)`` / ``$(*path)`` tokens
   against the base mapping only, never the override, so the merge stays order-independent.
   A path segment is exactly a TOML bare key (``A-Za-z0-9_-``, one or more characters, joined
   by ``.``) — the grammar addresses everything a bundled document could name without quoting,
   no narrower. A key that TOML itself would require quoting (non-ASCII, most concretely) is
   not addressable: by rule, not by accident of a character class, since a bare key is ASCII
   by TOML's own definition and ``.`` is the path delimiter, so a quoted key containing a dot
   would be irreducibly ambiguous to split back apart. That restriction binds this project's
   own bundled documents, never an adopter's — resolution is base-only, so a path only ever
   addresses a bundled key, and every bundled key today is already bare (see the standing
   guard in ``tests/meta``).
3. **Deep merge** (:func:`deep_merge`) — recurse tables per key; a leaf value (including a
   plain array — arrays are leaves, never element-merged) replaces its counterpart.
4. **``selected`` deselect** (:func:`apply_selected`) — shrink each named section to its
   surviving key set, then strip the ``[selected]`` table itself.

A string — value or key alike — is in **token territory** iff it *begins* with an unescaped
``$(``; a string that merely contains the sigil after its first character is data, in both
positions, left verbatim. In a value, territory means resolve, or refuse as malformed. In a
key, territory means **refuse**, always — never resolved, never passed through, because there
is no splice-into-a-key operation to define (a path addresses a value, and a value is not a
key) and a section's keys are the open vocabulary itself, so the models cannot backstop a key
the way they can a value's shape. ``$$(`` at the start unescapes to a literal ``$(`` in both
positions, which is what makes the key refusal a spelling requirement rather than a
restriction on what a key may be named.

The engine is loader-agnostic: it knows nothing about which document produced its inputs, or
what any of its caller-supplied key sets mean, and owns no floor check of its own — no
roster-locked rule, no lifecycle floor, no category catalog, no drift stamping, no live-index
cross-check. Those stay in each loader; this module supplies only the top-level check, the
merge, the deselect, and the splat resolution.

Two calling modes share one code path: every mechanism below always *collects* its
violations — including a nesting bound exceeded on either walk (see ``_MAX_NESTING_DEPTH``),
which is a hard structural limit rather than a data-shape violation but still lands on the
same collected channel, so a lint pass reports it beside every other finding instead of dying
on the first one it hits. Only the top-level :func:`merge_override` decides, from its
``collect_all`` flag, whether to raise on the first violation (fail-fast, the load path) or
return every violation it found (collect-all, a lint-style report) — never raising directly
itself.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from re import DOTALL
from re import compile as re_compile
from typing import Any, cast

from squads._errors import SquadsError

type RawMapping = dict[str, Any]

_SELECTED_KEY = "selected"

#: A splat token is recognised only when it is the *entire* string value: `$(path)` or
#: `$(*path)`, where `path` is one or more dot-joined TOML bare keys (`A-Za-z0-9_-`, one or
#: more characters each — no restriction on the leading character, so a hyphenated segment
#: like `user-story` and a digit-leading one both address) or the literal `self`. ASCII-only
#: in every position, deliberately and for the same reason throughout: a TOML bare key is
#: ASCII by the format's own definition, so a non-ASCII key is necessarily a *quoted* key and
#: is unaddressable by that rule rather than by an accident of this class rejecting it in one
#: position and not another.
_TOKEN_RE = re_compile(r"^\$\((\*)?([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*)\)$")

#: Broader than ``_TOKEN_RE``: anything shaped like a whole-string splat token — starts with
#: an unescaped `$(`, ends with a matching `)` — whether or not its interior is grammar-valid.
#: Used only to extract a nicer "path" substring for a malformed-token message; the decision
#: that a value is malformed is made by territory + a failed ``_parse_token``, not by whether
#: this pattern happens to match (an unclosed token, e.g. `$(items.task`, is malformed too,
#: and this pattern simply falls back to quoting the whole value for that case).
_TOKEN_SHAPE_RE = re_compile(r"^\$\((\*)?(.*)\)$", DOTALL)

#: A ceiling on override/base nesting depth, picked to satisfy two properties rather than any
#: particular number: **far above** anything a hand-authored document reaches (the deepest key
#: path in any bundled document is four levels), and **far below** the interpreter's own
#: recursion headroom, leaving room for the copy the merge performs at each level. 300 clears
#: both comfortably. Binds both walks — the override's own resolution, and the merge's
#: traversal of the untouched base — because a deep untouched-base subtree overflows the stack
#: inside the *copy*, not inside either walk's own recursive frame, so a guard on only one
#: side would miss the other.
_MAX_NESTING_DEPTH = 300


@dataclass(frozen=True, slots=True)
class MergeViolation:
    """One fail-closed violation, addressed at *path* within *origin* — the override's own
    path/label, as supplied by the caller. The engine never reads a file itself."""

    origin: str
    path: str
    reason: str
    hint: str

    def __str__(self) -> str:
        return f"{self.origin}: {self.path}: {self.reason} — {self.hint}"


@dataclass(frozen=True, slots=True)
class Deselection:
    """One key dropped from *section* by that section's own ``selected`` list — the
    provenance a caller needs to trace a floor violation back to an adopter's own line."""

    section: str
    key: str


@dataclass(frozen=True, slots=True)
class MergeResult:
    """The result of :func:`merge_override`. ``merged`` is ``None`` whenever ``violations``
    is non-empty — a merge that failed closed has nothing usable to hand back."""

    merged: RawMapping | None
    deselections: tuple[Deselection, ...]
    violations: tuple[MergeViolation, ...]


def _dotted(parent: str, key: str) -> str:
    return f"{parent}.{key}" if parent else key


def _lookup_base_path(base: RawMapping, path: str) -> tuple[bool, Any]:
    """Navigate dot-separated *path* into *base*. Returns ``(found, value)``."""
    node: Any = base
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return False, None
        node = cast(RawMapping, node)[part]
    return True, node


def _in_token_territory(value: str) -> bool:
    """A string — value or key alike — is in token territory iff it *begins* with an
    unescaped ``$(``. The sigil is POSIX command substitution and one of the three documents
    this engine serves carries command lines, so a value merely *containing* it after the
    first character (or a value/key beginning with the ``$$(`` escape, which this correctly
    excludes — its first two characters are ``$$``, not ``$(``) is plain data, never scanned,
    never touched."""
    return value.startswith("$(")


def _unescape_leading_token(value: str) -> str:
    """Outside token territory, the only transformation ever applied, in either string
    position: a leading ``$$(`` unescapes to a literal ``$(``. Nothing else in the string is
    ever touched — only a leading sigil needs escaping, so a value or key that merely
    contains ``$(`` after its first character needs no escape and gets none applied."""
    if value.startswith("$$("):
        return "$(" + value[3:]
    return value


def _parse_token(value: str) -> tuple[bool, str] | None:
    """``(star, path)`` when *value* is, in its entirety, a grammar-valid splat token;
    ``None`` otherwise. Only meaningful once *value* is already known to be in token
    territory — see :func:`_in_token_territory` — but harmless to call otherwise, since
    anything not starting with an unescaped ``$(`` can never fullmatch ``_TOKEN_RE`` either.
    ``fullmatch`` (not ``match``) so a single trailing newline — which Python's ``$`` anchor
    alone would let through — is not silently inside the grammar; the token must be the
    *entire* string value."""
    match = _TOKEN_RE.fullmatch(value)
    if match is None:
        return None
    return match.group(1) == "*", match.group(2)


def _malformed_token_violation(value: str, path: str, origin: str) -> MergeViolation:
    """A string in token territory (see :func:`_in_token_territory`) that failed
    :func:`_parse_token` is a malformed *path*, not a surviving literal or plain data: the
    adopter already committed to the token form by opening it with an unescaped ``$(``, so
    the message names the grammar mistake rather than telling them to do the one thing they
    already did. Always constructs a violation — call only once territory is confirmed."""
    match = _TOKEN_SHAPE_RE.fullmatch(value)
    quoted = match.group(2) if match is not None else value
    return MergeViolation(
        origin,
        path,
        f"malformed splat-ref path {quoted!r} — not a valid dot-joined chain of TOML bare keys",
        "each path segment is one or more ASCII letters, digits, underscores or hyphens (a "
        "TOML bare key); segments join with '.'; 'self' is the only special one",
    )


def _depth_violation(origin: str, path: str, verb: str) -> MergeViolation:
    return MergeViolation(
        origin,
        path,
        f"nesting exceeds {_MAX_NESTING_DEPTH} levels while {verb} — refusing to recurse further",
        "this is a structural limit, not a data-shape rule; reduce the nesting depth of this "
        "subtree",
    )


def _bounded_deepcopy(
    value: Any, origin: str, path: str, depth: int = 0
) -> tuple[Any, list[MergeViolation]]:
    """A depth-guarded stand-in for ``copy.deepcopy``, scoped to what ``tomllib`` can actually
    produce: ``dict`` and ``list`` are the only mutable container types, so every other value
    (``str``, ``int``, ``float``, ``bool``, a ``datetime.date``/``time``/``datetime``, ``None``)
    is immutable and returning it unchanged is already a safe copy. Guards the one recursion
    stdlib ``deepcopy`` has none for — an untouched base subtree nested deep enough to overflow
    the stack on its own, independent of anything the override does.

    Collects rather than raises, matching every other mechanism in this module: past the
    bound, returns *value* uncopied alongside a violation naming the dotted path and stops
    descending that branch — never itself the point where a violation short-circuits the rest
    of the walk. The caller decides what to do about it (see :func:`_maybe_raise`).
    """
    if depth > _MAX_NESTING_DEPTH:
        return value, [_depth_violation(origin, path, "copying")]
    if isinstance(value, dict):
        result: RawMapping = {}
        violations: list[MergeViolation] = []
        for key, sub in cast(RawMapping, value).items():
            copied, sub_violations = _bounded_deepcopy(sub, origin, _dotted(path, key), depth + 1)
            result[key] = copied
            violations.extend(sub_violations)
        return result, violations
    if isinstance(value, list):
        result_list: list[Any] = []
        list_violations: list[MergeViolation] = []
        for element in cast(list[Any], value):
            copied, sub_violations = _bounded_deepcopy(element, origin, path, depth + 1)
            result_list.append(copied)
            list_violations.extend(sub_violations)
        return result_list, list_violations
    return value, []


def _resolve_key(key: str, current_path: str, origin: str, violations: list[MergeViolation]) -> str:
    """A dict key is never a splat target. Outside token territory a key is plain data, with
    only a leading ``$$(`` ever unescaped — exactly the value rule. *Inside* territory a key
    is always **refused**: there is no splice-into-a-key operation (a path addresses a value,
    and a value is not a key), and the refusal is a spelling requirement rather than a
    vocabulary restriction, since the escape still gets a project the literal key it wants.
    A grammar-valid token is reported distinctly from a malformed one, since resolving it is
    undefined rather than malformed."""
    if not _in_token_territory(key):
        return _unescape_leading_token(key)
    key_path = _dotted(current_path, key)
    if _parse_token(key) is not None:
        violations.append(
            MergeViolation(
                origin,
                key_path,
                f"splat-ref token {key!r} used as a key — keys are never a splat target",
                "escape it with '$$(' for a literal key, or move the token to a value",
            )
        )
    else:
        violations.append(_malformed_token_violation(key, key_path, origin))
    return key


def _resolve_scalar_token(
    base: RawMapping,
    current_path: str,
    star: bool,
    path: str,
    origin: str,
    violations: list[MergeViolation],
) -> Any:
    """Resolve a splat token found at a non-list (dict-value or top-level) position."""
    if star:
        violations.append(
            MergeViolation(
                origin,
                current_path,
                f"spread token '$(*{path})' used outside a list — nothing to spread into",
                "use a plain '$(path)' splice, or move this into a list",
            )
        )
        return f"$(*{path})"
    target_path = current_path if path == "self" else path
    found, base_value = _lookup_base_path(base, target_path)
    if not found:
        violations.append(
            MergeViolation(
                origin,
                current_path,
                f"dangling splat path {path!r} has no counterpart in the bundled base",
                "fix the path, or drop the token",
            )
        )
        return f"$({path})"
    copied, copy_violations = _bounded_deepcopy(base_value, origin, current_path)
    violations.extend(copy_violations)
    return copied


def _resolve_string(
    value: str,
    base: RawMapping,
    current_path: str,
    origin: str,
    violations: list[MergeViolation],
) -> Any:
    """Resolve a value-position string: outside token territory it is plain data (only a
    leading ``$$(`` ever unescaped); inside it, resolve a well-formed token or report it as
    malformed. There is no third case — the old "surviving literal" category is gone:
    anything containing the sigil after its first character was never in territory to begin
    with, so it was always data, never a violation."""
    if not _in_token_territory(value):
        return _unescape_leading_token(value)
    token = _parse_token(value)
    if token is not None:
        star, path = token
        return _resolve_scalar_token(base, current_path, star, path, origin, violations)
    violations.append(_malformed_token_violation(value, current_path, origin))
    return value


def _resolve_value(
    value: Any,
    base: RawMapping,
    current_path: str,
    origin: str,
    violations: list[MergeViolation],
    depth: int = 0,
) -> Any:
    if depth > _MAX_NESTING_DEPTH:
        violations.append(_depth_violation(origin, current_path, "resolving"))
        return value
    if isinstance(value, dict):
        mapping = cast(RawMapping, value)
        return {
            _resolve_key(key, current_path, origin, violations): _resolve_value(
                sub, base, _dotted(current_path, key), origin, violations, depth + 1
            )
            for key, sub in mapping.items()
        }
    if isinstance(value, list):
        return _resolve_list(
            cast(list[Any], value), base, current_path, origin, violations, depth + 1
        )
    if isinstance(value, str):
        return _resolve_string(value, base, current_path, origin, violations)
    return value


def _resolve_list_element_token(
    base: RawMapping,
    current_path: str,
    star: bool,
    path: str,
    origin: str,
    violations: list[MergeViolation],
) -> list[Any] | None:
    """Resolve a splat token found as one element of a list. Returns the list of elements it
    expands to (one for a splice, zero-or-more for a spread), or ``None`` on a dangling path
    (the token is dropped from the output — the violation already flags the whole merge)."""
    target_path = current_path if path == "self" else path
    found, base_value = _lookup_base_path(base, target_path)
    if not found:
        violations.append(
            MergeViolation(
                origin,
                current_path,
                f"dangling splat path {path!r} has no counterpart in the bundled base",
                "fix the path, or drop the token"
                if path != "self"
                else "a brand-new key has no bundled list to append to",
            )
        )
        return None
    if star:
        if not isinstance(base_value, list):
            violations.append(
                MergeViolation(
                    origin,
                    current_path,
                    f"spread token '$(*{path})' targets a {type(base_value).__name__}, not a list",
                    "use a plain '$(path)' splice instead of a spread",
                )
            )
            return None
        copied, copy_violations = _bounded_deepcopy(
            cast(list[Any], base_value), origin, current_path
        )
        violations.extend(copy_violations)
        return cast(list[Any], copied)
    copied, copy_violations = _bounded_deepcopy(base_value, origin, current_path)
    violations.extend(copy_violations)
    return [copied]


def _resolve_list(
    items: list[Any],
    base: RawMapping,
    current_path: str,
    origin: str,
    violations: list[MergeViolation],
    depth: int = 0,
) -> list[Any]:
    result: list[Any] = []
    for element in items:
        token = _parse_token(element) if isinstance(element, str) else None
        if token is not None:
            star, path = token
            expanded = _resolve_list_element_token(
                base, current_path, star, path, origin, violations
            )
            if expanded is not None:
                result.extend(expanded)
            continue
        result.append(_resolve_value(element, base, current_path, origin, violations, depth))
    return result


def resolve_splat_refs(
    base: RawMapping, override: RawMapping, origin: str
) -> tuple[RawMapping, list[MergeViolation]]:
    """Walk *override* and replace every splat token with a value read from *base*.

    Single pass: a value spliced or spread in from the base is never itself re-scanned for
    tokens. Resolution targets *base* only — no override value is ever a splat target — which
    is what keeps the merge free of cycles and order-independent. Returns the resolved
    mapping (best-effort — a dangling/mismatched/malformed/too-deep token is left as a marker
    string or uncopied, not substituted) plus every violation found; never raises.

    ``self``/``*self`` address **the nearest enclosing keyed path, at any list depth** — this
    is definitional, not a special case: a list position contributes nothing to the path,
    because a list index has no dotted name to contribute, so "the key currently being
    written" is unchanged by however many list levels sit between the token and that key.
    Two ``self`` tokens at different list depths under one key therefore resolve to the same
    base value, and a ``$(*self)`` nested inside a sub-list spreads the enclosing key's list
    into that sub-list — permitted, because the destination's shape is the models' plane, not
    this engine's.
    """
    violations: list[MergeViolation] = []
    resolved = _resolve_value(override, base, "", origin, violations)
    return resolved, violations


def deep_merge(
    base: RawMapping,
    override: RawMapping,
    origin: str,
    *,
    _current_path: str = "",
    _depth: int = 0,
) -> tuple[RawMapping, list[MergeViolation]]:
    """Recursively merge *override* over *base* at leaf granularity.

    Tables recurse per key; any other value — including a plain array, which is always a
    leaf — replaces its counterpart wholesale. *override* should already have its splat
    tokens resolved (see :func:`resolve_splat_refs`); this function has no opinion on tokens.

    The result shares no ``dict`` or ``list`` object with either input, at any depth — the
    two mutable container types a parsed TOML document can hold; every other value type
    (``str``, ``int``, ``float``, ``bool``, a date/time value, ``None``) is immutable, so
    sharing it is already safe. This is the guarantee a caller relies on to reuse *base*
    unmodified across every subsequent merge, whatever *base* itself turns out to be — the
    engine makes no assumption about that beyond its declared ``dict[str, Any]`` shape.

    Key order is base order, with override-only keys appended in override order — an override
    touching one field of one entry must never relocate that entry (or any other key) in the
    merged mapping's iteration order, at this level or any nested one.

    Collects rather than raises, matching every other mechanism: a nesting bound exceeded on
    either side — the override's own structure, or a deep untouched base subtree copied via
    :func:`_bounded_deepcopy` — appends a violation naming the dotted path and stops
    descending that one branch, so the rest of the document is still walked and a lint pass
    sees every finding together. Never raises.
    """
    if _depth > _MAX_NESTING_DEPTH:
        return {}, [_depth_violation(origin, _current_path, "merging")]
    merged: RawMapping = {}
    violations: list[MergeViolation] = []
    for key, base_value in base.items():
        key_path = _dotted(_current_path, key)
        if key not in override:
            copied, copy_violations = _bounded_deepcopy(base_value, origin, key_path)
            merged[key] = copied
            violations.extend(copy_violations)
            continue
        value = override[key]
        if isinstance(base_value, dict) and isinstance(value, dict):
            sub_merged, sub_violations = deep_merge(
                cast(RawMapping, base_value),
                cast(RawMapping, value),
                origin,
                _current_path=key_path,
                _depth=_depth + 1,
            )
            merged[key] = sub_merged
            violations.extend(sub_violations)
        elif isinstance(value, dict | list):
            copied, copy_violations = _bounded_deepcopy(
                cast(dict[str, Any] | list[Any], value), origin, key_path
            )
            merged[key] = copied
            violations.extend(copy_violations)
        else:
            merged[key] = value
    for key, value in override.items():
        if key in base:
            continue
        key_path = _dotted(_current_path, key)
        if isinstance(value, dict | list):
            copied, copy_violations = _bounded_deepcopy(
                cast(dict[str, Any] | list[Any], value), origin, key_path
            )
            merged[key] = copied
            violations.extend(copy_violations)
        else:
            merged[key] = value
    return merged, violations


def _unknown_key_violations(
    keys: Iterable[str],
    accepted: frozenset[str],
    origin: str,
    path_prefix: str,
    what: str,
    *,
    empty_accepted_hint: str | None = None,
) -> list[MergeViolation]:
    """Every key in *keys* not present in *accepted* — one collected violation each, naming
    the key and the accepted set. Shared, verbatim, by two callers that are the same check
    over two different key spaces: ``[selected]``'s section names (*path_prefix* the
    ``selected`` table, *what* ``"[selected] section"``) and the override document's own
    closed top-level key space (*path_prefix* empty, *what* ``"top-level key"``) — the
    engine's ignorance of what either name space *means* is exactly what makes one helper
    correct for both.

    *empty_accepted_hint* is the escape hatch for that ignorance: when *accepted* is empty,
    ``"use one of the accepted ...s: []"`` offers a menu with nothing on it — technically
    correct, useless to read. A caller whose document has NO valid entries for this key space
    at all (rather than merely none the adopter happened to name) may pass a one-line reason
    here instead; it replaces the empty-menu fix hint verbatim. Ignored (and harmless) when
    *accepted* is non-empty — the normal menu is the useful one there.
    """
    fix_hint = (
        empty_accepted_hint
        if not accepted and empty_accepted_hint is not None
        else f"use one of the accepted {what}s: {sorted(accepted)}"
    )
    return [
        MergeViolation(origin, _dotted(path_prefix, key), f"unknown {what} {key!r}", fix_hint)
        for key in keys
        if key not in accepted
    ]


def _top_level_key_violations(
    override: RawMapping, top_level_keys: frozenset[str] | None, origin: str
) -> list[MergeViolation]:
    """The override document's own top level, checked before the merge — after merging,
    every base key is present and the override's own top level is no longer distinguishable
    from it. A caller that supplies no accepted set (``top_level_keys=None``) gets no check
    at all and every top-level key passes through: the roles loader is that caller, since a
    role override's top-level keys are the fields of a role, a set that grows release to
    release, so leniency there is forward compatibility rather than a gap.

    ``selected`` is accepted unconditionally, whether or not the caller's own set names it.
    It is not the document's vocabulary — it is *this engine's* own reserved key (defined,
    consumed, and stripped by :func:`apply_selected`), the same status the sigil holds in
    every string position. A caller should never have to know to add it, and a caller who
    forgot to would otherwise see a legitimate override refused on the load path for a
    document the adopter got right.
    """
    if top_level_keys is None:
        return []
    top_level_keys = top_level_keys | {_SELECTED_KEY}
    return _unknown_key_violations(override.keys(), top_level_keys, origin, "", "top-level key")


def _validate_selected_shape(
    selected: RawMapping,
    section_names: frozenset[str],
    origin: str,
    empty_selected_hint: str | None = None,
) -> list[MergeViolation]:
    """Every ``[selected]`` shape violation, collected together: an unknown section key, a
    ``keep`` value that is not a list, or a list containing a non-string element.

    A shape mismatch must never reach ``set(keep)`` unchecked — ``keep = "task"`` (the typo
    for ``["task"]``) would silently become the character set ``{"t", "a", "s", "k"}``,
    matching no real key and dropping every one of them, the most damaging way this could
    fail. Fail closed instead, with a message that names what is actually wrong.

    *empty_selected_hint* — see :func:`_unknown_key_violations` — lets a document with no
    deselectable sections at all (an empty *section_names*) explain why, rather than pointing
    at an empty menu.
    """
    violations = _unknown_key_violations(
        selected.keys(),
        section_names,
        origin,
        _SELECTED_KEY,
        "[selected] section",
        empty_accepted_hint=empty_selected_hint,
    )
    for section, keep in selected.items():
        if section not in section_names:
            continue  # already collected above
        path = f"{_SELECTED_KEY}.{section}"
        if not isinstance(keep, list):
            violations.append(
                MergeViolation(
                    origin,
                    path,
                    f"selected.{section} must be a list of key names, got {type(keep).__name__}",
                    f'wrap it in a list, e.g. {section} = ["{keep}"]'
                    if isinstance(keep, str)
                    else "declare the surviving keys as a list of strings",
                )
            )
            continue
        if not all(isinstance(item, str) for item in cast(list[Any], keep)):
            violations.append(
                MergeViolation(
                    origin,
                    path,
                    f"selected.{section} must be a list of strings; found a non-string entry",
                    "every surviving key name must be a plain string",
                )
            )
    return violations


def _selected_section_shape_violations(
    selected: RawMapping, result: RawMapping, origin: str
) -> list[MergeViolation]:
    """A section named by ``[selected]`` but *absent* from the merged mapping is a deliberate,
    inert no-op — there is nothing to shrink. A section that is *present* but not a table is
    not: silently doing nothing there means the adopter's deselect never happened, and the
    resulting spec is still perfectly valid — the one deselect failure mode no downstream
    floor/referential/live-index check can ever see, because there is nothing wrong with the
    spec that resulted, only with the one that was asked for. Fail closed instead.
    """
    violations: list[MergeViolation] = []
    for section in selected:
        if section not in result:
            continue
        section_value = result[section]
        if not isinstance(section_value, dict):
            violations.append(
                MergeViolation(
                    origin,
                    f"{_SELECTED_KEY}.{section}",
                    f"selected names section {section!r}, but it is a "
                    f"{type(section_value).__name__}, not a table",
                    "a deselect needs a keyed table to drop keys from — this section cannot "
                    "be shrunk as it stands",
                )
            )
    return violations


def _selected_entry_violations(
    selected: RawMapping, result: RawMapping, origin: str
) -> list[MergeViolation]:
    """Every ``[selected]`` keep-list *entry* that names no key of the section it is keeping.

    The counterpart of :func:`_validate_selected_shape` one level down: that function refuses a
    keep list whose *shape* is wrong, on the argument that a mismatch must never reach
    ``set(keep)`` unchecked — and the same argument applies to the list's contents. A
    well-shaped list holding a misspelled entry (``selected.items = [… "guied"]``) passes every
    shape check, silently drops the key it meant to keep, and leaves a spec that is *valid* —
    so nothing downstream can report it. It is the deselect failure mode with no backstop: the
    floor, the referential checks and the live-index cross-check all inspect the spec that
    resulted, never the one that was asked for. Fail closed instead, naming the section's real
    keys.

    A keep list may name only keys the *merged* mapping actually holds — a key the override
    itself adds is present by then, so adding and keeping in one document works; only a name
    that matches nothing is refused.
    """
    violations: list[MergeViolation] = []
    for section, keep in selected.items():
        raw_section_map = result.get(section)
        if not isinstance(raw_section_map, dict):
            continue  # absent (inert no-op) or non-table (already collected)
        violations.extend(
            _unknown_key_violations(
                cast(list[str], keep),
                frozenset(cast(RawMapping, raw_section_map)),
                origin,
                f"{_SELECTED_KEY}.{section}",
                f"{section} key",
            )
        )
    return violations


def apply_selected(
    merged: RawMapping,
    section_names: frozenset[str],
    origin: str,
    empty_selected_hint: str | None = None,
) -> tuple[RawMapping, tuple[Deselection, ...], list[MergeViolation]]:
    """Apply the top-level ``[selected]`` table's surviving-set deselect, then strip it.

    *section_names* is the closed, caller-supplied set of section keys ``[selected]`` may
    name; any other key fails closed. Each named list is the surviving set for that section —
    replace-wholesale, keys not listed are dropped. Every entry of that list must name a key
    the section actually holds (:func:`_selected_entry_violations`).

    On success (``violations`` empty): returns the merged mapping with ``selected`` removed
    and every deselected key dropped, in base order, plus the provenance of each drop.

    On the violation path (``violations`` non-empty): returns *merged* completely unmodified
    — the caller's own input object, ``selected`` still present, nothing dropped — and empty
    deselections. This return value must never be used as if a deselect had been attempted;
    :func:`merge_override` already enforces that by setting ``MergeResult.merged`` to ``None``
    whenever any violation exists. Never raises.
    """
    raw_selected = merged.get(_SELECTED_KEY)
    if raw_selected is None:
        return merged, (), []
    if not isinstance(raw_selected, dict):
        violation = MergeViolation(
            origin,
            _SELECTED_KEY,
            f"[selected] must be a table, got {type(raw_selected).__name__}",
            "declare it as [selected] with one surviving-key list per section",
        )
        return merged, (), [violation]
    selected = cast(RawMapping, raw_selected)

    shape_violations = _validate_selected_shape(
        selected, section_names, origin, empty_selected_hint
    )
    if shape_violations:
        return merged, (), shape_violations

    result = {key: value for key, value in merged.items() if key != _SELECTED_KEY}

    section_violations = _selected_section_shape_violations(selected, result, origin)
    if section_violations:
        return merged, (), section_violations

    entry_violations = _selected_entry_violations(selected, result, origin)
    if entry_violations:
        return merged, (), entry_violations

    deselections: list[Deselection] = []
    for section, keep in selected.items():
        raw_section_map = result.get(section)
        if not isinstance(raw_section_map, dict):
            continue
        section_map = cast(RawMapping, raw_section_map)
        keep_set = set(cast(list[str], keep))
        dropped = [key for key in section_map if key not in keep_set]
        if not dropped:
            continue
        result[section] = {key: value for key, value in section_map.items() if key in keep_set}
        deselections.extend(Deselection(section, key) for key in dropped)
    return result, tuple(deselections), []


def _maybe_raise(violations: list[MergeViolation], collect_all: bool) -> None:
    if violations and not collect_all:
        raise SquadsError(str(violations[0]))


def merge_override(
    base: RawMapping,
    override: RawMapping,
    section_names: frozenset[str],
    origin: str,
    *,
    top_level_keys: frozenset[str] | None,
    collect_all: bool = False,
    empty_selected_hint: str | None = None,
) -> MergeResult:
    """The public entry point: check the override's own top level, resolve splats,
    deep-merge, apply ``selected``, strip it.

    Runs the four mechanisms in their fixed order — nothing later may be reordered ahead of
    splat resolution, since the strictly-typed spec models would reject an unresolved token
    as a type error before it could ever be resolved, and nothing may be reordered ahead of
    the top-level check, which is the only point at which the override's own top level is
    still distinguishable from the base's.

    ``top_level_keys`` has no default — a caller must pass either its accepted set or an
    explicit ``None``, so "forgot to pass it" becomes a type error rather than a silent
    fail-open. ``None`` still means "deliberately open, no check at all": the roles loader is
    that caller, since a role override's top-level keys are the fields of a role, a
    forward-compatible field set that grows release to release. ``selected`` is accepted
    unconditionally whenever a set *is* given — see :func:`_top_level_key_violations`.

    Two calling modes over one code path:

    - **fail-fast** (``collect_all=False``, the default — the load path): raises a clean
      ``SquadsError`` on the first violation found.
    - **collect-all** (``collect_all=True`` — a lint-style report): never raises; returns
      every violation found across every step, together — including a nesting bound exceeded
      on either walk (see ``_MAX_NESTING_DEPTH``), which lands on the same collected channel
      as everything else rather than aborting the pass.

    ``empty_selected_hint`` — see :func:`_unknown_key_violations` — is for a document with NO
    deselectable ``[selected]`` sections at all (an empty *section_names*, e.g. the playbook):
    an override that writes ``[selected]`` there is still refused, but the fix hint states the
    caller-supplied reason instead of pointing at an empty accepted-sections list. Ignored
    whenever *section_names* is non-empty.
    """
    violations: list[MergeViolation] = []

    violations.extend(_top_level_key_violations(override, top_level_keys, origin))
    _maybe_raise(violations, collect_all)

    resolved_override, resolve_violations = resolve_splat_refs(base, override, origin)
    violations.extend(resolve_violations)
    _maybe_raise(violations, collect_all)

    merged, merge_violations = deep_merge(base, resolved_override, origin)
    violations.extend(merge_violations)
    _maybe_raise(violations, collect_all)

    merged, deselections, select_violations = apply_selected(
        merged, section_names, origin, empty_selected_hint
    )
    violations.extend(select_violations)
    _maybe_raise(violations, collect_all)

    if violations:
        return MergeResult(merged=None, deselections=(), violations=tuple(violations))
    return MergeResult(merged=merged, deselections=deselections, violations=())
