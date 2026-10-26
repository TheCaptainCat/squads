"""Shared, loader-agnostic override-merge engine over raw parsed-TOML mappings: a bundled base and a
project override in, an effective merged ``dict[str, Any]`` out, before any pydantic validation,
since the spec models set ``extra="forbid"`` and would reject an unresolved splat token or a stray
``[selected]`` table as a type error first. :func:`merge_override` applies four mechanisms in this
fixed order:

1. The override's own top level (:func:`_top_level_key_violations`): an unrecognised key is a
   collected violation, checked first and only here because after the merge every base key is
   present and the override's top level is indistinguishable.
2. Splat-refs (:func:`resolve_splat_refs`): ``$(path)`` / ``$(*path)`` resolve against the base
   only, never the override, keeping the merge order-independent. A path segment is a TOML bare key
   (``A-Za-z0-9_-``) joined by ``.``; a key TOML would quote is not addressable, by rule, since a
   quoted key containing a dot would be ambiguous. That binds this project's bundled documents (all
   bare, guarded in ``tests/meta``), never an adopter's.
3. Deep merge (:func:`deep_merge`): tables recurse per key and a leaf, including a plain array,
   replaces its counterpart.
4. ``selected`` deselect (:func:`apply_selected`): shrink each named section to its surviving keys,
   then strip the table.

A string, value or key, is in token territory iff it begins with an unescaped ``$(``; one that only
contains the sigil later is data. A value in territory is resolved or refused as malformed. A key in
territory is always refused, since no splice-into-a-key operation exists and a section's keys are
the open vocabulary, so the models cannot backstop one. ``$$(`` at the start unescapes to a literal
``$(`` in both positions, so the refusal is a spelling requirement, not a naming restriction.

The engine knows nothing of which document produced its inputs or what its caller-supplied key sets
mean, and owns no floor check, roster lock, lifecycle floor, category catalog, drift stamping or
live-index cross-check; those stay in each loader. It does own the wording of an unknown-key refusal
at both depths (the top-level check and, via :func:`describe_spec_error`, the models' own
``extra="forbid"`` one level down), sharing one version-qualified menu sentence
(:func:`_accepted_menu`) so the two cannot diverge.

Every mechanism collects its violations, including a nesting bound exceeded on either walk
(``_MAX_NESTING_DEPTH``, a hard structural limit that still lands on the collected channel), so a
lint pass reports it beside the rest. Only :func:`merge_override` decides, from ``collect_all``,
whether to raise on the first violation (the load path) or return them all.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from re import DOTALL
from re import compile as re_compile
from types import UnionType
from typing import Any, Union, cast, get_args, get_origin

from pydantic import BaseModel, ValidationError

from squads import __version__
from squads._errors import SquadsError

type RawMapping = dict[str, Any]

_SELECTED_KEY = "selected"

#: A splat token is recognised only as the entire string value: `$(path)` or `$(*path)`, `path`
#: being dot-joined TOML bare keys (`A-Za-z0-9_-`, any leading character, so `user-story` and digit-
#: leading keys address) or the literal `self`. It is ASCII-only in every position because a TOML
#: bare key is ASCII by definition, so a non-ASCII key is a quoted key and unaddressable by rule.
_TOKEN_RE = re_compile(r"^\$\((\*)?([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*)\)$")

#: Broader than ``_TOKEN_RE``: anything shaped like a whole-string splat token (starts with an
#: unescaped `$(`, ends with `)`), used only to extract a "path" for a malformed-token message.
#: Malformedness is decided by token territory plus a failed ``_parse_token``, not by this pattern,
#: which falls back to quoting the whole value (e.g. an unclosed `$(items.task`).
_TOKEN_SHAPE_RE = re_compile(r"^\$\((\*)?(.*)\)$", DOTALL)

#: A ceiling on override/base nesting depth, far above any hand-authored document (the deepest
#: bundled key path is four levels) and far below the interpreter's recursion headroom, which the
#: merge's per-level copy also uses. It binds both walks, as a deep untouched-base subtree overflows
#: inside the copy, not inside either walk's own frame.
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
    """A string, value or key, is in token territory iff it begins with an unescaped ``$(``. The
    sigil is POSIX command substitution and one bundled document carries command lines, so a string
    that merely contains it after its first character, or begins with the ``$$(`` escape, is plain
    data, never scanned or touched.
    """
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
    """``(star, path)`` when *value* is, in its entirety, a grammar-valid splat token, else
    ``None``; meaningful once :func:`_in_token_territory` holds but harmless otherwise. It uses
    ``fullmatch`` so a single trailing newline, which ``$`` alone would let through, is not inside
    the grammar.
    """
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
    """A depth-guarded stand-in for ``copy.deepcopy`` scoped to what ``tomllib`` produces: ``dict``
    and ``list`` are the only mutable containers, so every other value is immutable and returning it
    is a safe copy. It guards the one recursion ``deepcopy`` has no bound for, an untouched base
    subtree deep enough to overflow the stack. It collects rather than raises: past the bound it
    returns *value* uncopied with a violation naming the dotted path and stops descending that
    branch (see :func:`_maybe_raise`).
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
    """A dict key is never a splat target. Outside token territory a key is plain data (only a
    leading ``$$(`` is unescaped, as for values); inside it a key is always refused, since a path
    addresses a value and a value is not a key, and the escape still lets a project spell the
    literal key. A grammar-valid token is reported distinctly from a malformed one, as resolving it
    is undefined rather than malformed.
    """
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
    malformed. There is no third case: anything containing the sigil after its first
    character is outside token territory, so it is data, never a violation."""
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
    """Walk *override* and replace every splat token with a value read from *base*, in a single pass
    (a spliced value is never re-scanned) and against *base* only, which keeps the merge cycle-free
    and order-independent. It returns the resolved mapping, best-effort (a dangling, mismatched,
    malformed or too-deep token is left as a marker string or uncopied), plus every violation; it
    never raises.

    ``self``/``*self`` address the nearest enclosing keyed path at any list depth, since a list
    index contributes no dotted name: two ``self`` tokens at different list depths under one key
    resolve to the same base value, and ``$(*self)`` in a sub-list spreads the enclosing key's list
    into it, the destination's shape being the models' concern.
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
    """Recursively merge *override* over *base* at leaf granularity: tables recurse per key and any
    other value, a plain array included, replaces its counterpart wholesale. *override* should
    already have its splats resolved. The result shares no ``dict`` or ``list`` with either input at
    any depth, which lets a caller reuse *base* unmodified across every merge. Key order is base
    order with override-only keys appended in override order, so an override touching one field
    never relocates an entry. A nesting bound exceeded on either side (via
    :func:`_bounded_deepcopy`) is collected with the dotted path and that branch skipped; it never
    raises.
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
    """Every key in *keys* not in *accepted*, one collected violation each naming the key, the
    running squads version and the accepted set. It is shared by two checks over different key
    spaces, ``[selected]`` section names (*path_prefix* ``selected``, *what* ``"[selected]
    section"``) and the override's closed top-level keys (*path_prefix* empty, *what* ``"top-level
    key"``). The version tells an adopter a typo from a key a newer squads accepts or an older one
    dropped.

    *empty_accepted_hint* replaces the useless "one of the accepted ...s: []" fix hint when a
    document has no valid entries for this key space by design; it omits the version, being true at
    every version, and is ignored when *accepted* is non-empty.
    """
    fix_hint = (
        empty_accepted_hint
        if not accepted and empty_accepted_hint is not None
        else _accepted_menu(what, accepted)
    )
    return [
        MergeViolation(origin, _dotted(path_prefix, key), f"unknown {what} {key!r}", fix_hint)
        for key in keys
        if key not in accepted
    ]


def _accepted_menu(what: str, accepted: frozenset[str]) -> str:
    """The version-qualified menu sentence, written once because an unknown top-level key
    (:func:`_unknown_key_violations`) and an unknown nested key (:func:`describe_spec_error`) are
    the same promise at two depths, and sharing it stops the nested half drifting into another
    dialect. The version lets an adopter tell a typo from a key a newer squads accepts or an older
    one dropped.
    """
    return f"use one of the accepted {what}s in v{__version__}: {sorted(accepted)}"


def _model_in(annotation: Any) -> tuple[type[BaseModel] | None, bool]:
    """The pydantic model reachable through *annotation*, plus whether reaching it passes through a
    container. The flag keeps a location path aligned with the model graph: ``list[M]`` contributes
    two path segments (name, then index) and ``M`` one, and walking both alike would resolve the
    wrong model and print another section's menu. ``M | None`` unwraps to ``M``, as only a present
    section can carry an unknown key.
    """
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation, False
    origin = get_origin(annotation)
    if origin is Union or origin is UnionType:
        for arg in get_args(annotation):
            model, container = _model_in(arg)
            if model is not None:
                return model, container
        return None, False
    args = get_args(annotation)
    if origin in (list, tuple, set, frozenset) and args:
        model, _ = _model_in(args[0])
        return model, model is not None
    if origin is dict and len(args) == 2:
        model, _ = _model_in(args[1])
        return model, model is not None
    return None, False


def _accepted_keys_at(model: type[BaseModel], loc: tuple[int | str, ...]) -> frozenset[str] | None:
    """The declared field names of the section *loc* addresses inside *model*, read off the model so
    the menu grows with it; *loc* is a pydantic error location whose last segment is the offending
    key. ``None`` when the route cannot be resolved, which the caller treats as "no menu", since a
    menu naming another section's keys is worse than none.
    """
    current: type[BaseModel] = model
    parts = loc[:-1]
    i = 0
    while i < len(parts):
        segment = parts[i]
        if not isinstance(segment, str):
            return None
        field = current.model_fields.get(segment)
        if field is None:
            return None
        nested, container = _model_in(field.annotation)
        if nested is None:
            return None
        i += 1
        if container:
            if i >= len(parts):  # a container addressed without an index: unresolvable
                return None
            i += 1  # consume the list index / mapping key
        current = nested
    return frozenset(current.model_fields)


def describe_spec_error(exc: Exception, model: type[BaseModel]) -> str:
    """Render *exc*, raised validating a document against *model*, as the message body a spec loader
    gives an adopter. An unknown key is folded into the shape a top-level unknown key produces (key,
    location, the section's accepted keys, running version), replacing pydantic's internal header,
    input dump and docs link. Everything else is returned verbatim, since the fold covers only a
    failure whose whole cause is unknown keys: a wrong type, a missing required field, or a mix
    keeps its existing handling.
    """
    if not isinstance(exc, ValidationError):
        return str(exc)
    errors = exc.errors(include_url=False)
    if not errors or any(entry["type"] != "extra_forbidden" for entry in errors):
        return str(exc)
    sentences: list[str] = []
    for entry in errors:
        loc = entry["loc"]
        if not loc:  # pragma: no cover - pydantic always locates an extra key
            return str(exc)
        where = ".".join(str(segment) for segment in loc[:-1])
        reason = f"unknown key {str(loc[-1])!r}" + (f" in {where!r}" if where else "")
        accepted = _accepted_keys_at(model, loc)
        sentences.append(
            reason if accepted is None else f"{reason} — {_accepted_menu('key', accepted)}"
        )
    return "; ".join(sentences)


def spec_error_sentences(exc: Exception, model: type[BaseModel]) -> list[str]:
    """One written sentence per bad field of a validation failure against *model*, with no
    pydantic rendering in it. An unknown key keeps the accepted-keys menu
    :func:`describe_spec_error` gives; any other failure names the key and states what
    pydantic found wrong with it. A non-validation error is its own single sentence."""
    if not isinstance(exc, ValidationError):
        return [str(exc)]
    sentences: list[str] = []
    for entry in exc.errors(include_url=False):
        loc = entry["loc"]
        where = ".".join(str(segment) for segment in loc)
        if entry["type"] == "extra_forbidden" and loc:
            parent = ".".join(str(segment) for segment in loc[:-1])
            reason = f"unknown key {str(loc[-1])!r}" + (f" in {parent!r}" if parent else "")
            accepted = _accepted_keys_at(model, loc)
            sentences.append(
                reason if accepted is None else f"{reason} — {_accepted_menu('key', accepted)}"
            )
        elif entry["type"] == "missing" and loc:
            sentences.append(f"missing required key {where!r}")
        else:
            subject = f"key {where!r}" if where else "the entry"
            sentences.append(f"{subject} is invalid — {entry['msg']}")
    return sentences or [str(exc)]


def _top_level_key_violations(
    override: RawMapping, top_level_keys: frozenset[str], origin: str
) -> list[MergeViolation]:
    """The override's own top level, checked before the merge, when every base key is present. The
    accepted set is always caller-supplied and closed, derived from where that document's vocabulary
    is declared (a role document's from ``RoleSpec.model_fields``), because an open mode turned a
    typo into a silent no-op. ``selected`` is accepted unconditionally as this engine's own reserved
    key, defined and stripped by :func:`apply_selected`, so a caller need not add it and a
    legitimate override is not refused.
    """
    top_level_keys = top_level_keys | {_SELECTED_KEY}
    return _unknown_key_violations(override.keys(), top_level_keys, origin, "", "top-level key")


def _validate_selected_shape(
    selected: RawMapping,
    section_names: frozenset[str],
    origin: str,
    empty_selected_hint: str | None = None,
) -> list[MergeViolation]:
    """Every ``[selected]`` shape violation, collected: an unknown section key, a ``keep`` that is
    not a list, or a non-string element. A mismatch must never reach ``set(keep)``, as ``keep =
    "task"`` would become the characters ``{"t", "a", "s", "k"}`` and drop every key, so it fails
    closed naming the problem. *empty_selected_hint* (see :func:`_unknown_key_violations`) explains
    a document with no deselectable sections.
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
    """A section named by ``[selected]`` but absent from the merged mapping is an inert no-op, but
    one that is present and not a table fails closed: silently doing nothing would mean the
    adopter's deselect never happened while the resulting spec stays valid, the one deselect failure
    no downstream floor, referential or live-index check can see.
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
    """Every ``[selected]`` keep-list entry that names no key of its section, the counterpart of
    :func:`_validate_selected_shape` for contents: a well-shaped list with a misspelled entry
    (``"guied"``) silently drops the key it meant to keep and leaves a valid spec no downstream
    check can flag, so it fails closed naming the section's real keys. A keep list may name any key
    the merged mapping holds, including one the override adds.
    """
    violations: list[MergeViolation] = []
    for section, keep in selected.items():
        raw_section_map = result.get(section)
        if not isinstance(raw_section_map, dict):
            continue  # absent (inert no-op) or non-table (already collected)
        violations.extend(
            _unknown_key_violations(
                list(dict.fromkeys(cast(list[str], keep))),
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
    """Apply the top-level ``[selected]`` deselect, then strip it. *section_names* is the closed
    caller-supplied set of sections it may name (any other fails closed); each named list is the
    surviving set, replaced wholesale, and every entry must name a key the section holds
    (:func:`_selected_entry_violations`). On success it returns the merged mapping with ``selected``
    removed and deselected keys dropped, in base order, plus each drop's provenance. On violations
    it returns *merged* unmodified with ``selected`` still present and no deselections, which must
    not be read as an attempted deselect (:func:`merge_override` sets ``MergeResult.merged`` to
    ``None``). It never raises.
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

    violations = _validate_selected_shape(selected, section_names, origin, empty_selected_hint)

    result = {key: value for key, value in merged.items() if key != _SELECTED_KEY}

    # The deeper checks read only a section whose name and keep list are well formed, so a
    # shape violation above neither repeats nor misleads them.
    well_formed: RawMapping = {
        section: keep
        for section, keep in selected.items()
        if section in section_names
        and isinstance(keep, list)
        and all(isinstance(entry, str) for entry in cast(list[Any], keep))
    }
    violations.extend(_selected_section_shape_violations(well_formed, result, origin))
    violations.extend(_selected_entry_violations(well_formed, result, origin))
    if violations:
        return merged, (), violations

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
    top_level_keys: frozenset[str],
    collect_all: bool = False,
    empty_selected_hint: str | None = None,
) -> MergeResult:
    """The public entry point: check the override's top level, resolve splats, deep-merge, apply
    ``selected`` and strip it, in that fixed order, since the typed models would reject an
    unresolved token before it could resolve and only the first step still sees the override's own
    top level. ``top_level_keys`` has no default, so forgetting it is a type error, and no ``None``
    opt-out exists because every overridable document (workflow, playbook, role catalog, per-slug
    role) has a closed top level.

    With ``collect_all=False`` (the load path) it raises a clean ``SquadsError`` on the first
    violation; with ``True`` (a lint report) it never raises and returns every violation, a nesting
    bound included. ``empty_selected_hint`` (see :func:`_unknown_key_violations`) is for a document
    with no deselectable sections (the playbook) and is ignored when *section_names* is non-empty.
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
