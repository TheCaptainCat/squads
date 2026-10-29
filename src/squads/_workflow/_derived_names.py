"""Load-time check that the names the spec derives onto a command or an import op collide with
nothing: a field code gives a flag, a target kind gives a flag, and a field code or a kind gives an
import key. Each is refused when it equals a fixed name of its surface or another derived name on
it, naming the surface and the name.

The fixed names are the options and keys the code declares; a guard under ``tests/meta`` holds each
table to the live command and the live event model.
"""

from squads._workflow._models import WorkflowSpec
from squads._workflow._validity import (
    GENERIC_SUBENTITY_VERB,
    reserved_item_keys,
    reserved_subentity_keys,
)

#: The fixed options (without ``--``) of each command that derives flags from the spec.
FIXED_OPTIONS: dict[str, frozenset[str]] = {
    "create": frozenset(
        {"help", "author", "parent", "desc", "label", "ref", "assignee", "message", "file", "json"}
    ),
    "update": frozenset(
        {
            "help",
            "title",
            "desc",
            "author",
            "status",
            "force",
            "parent",
            "no-parent",
            "assignee",
            "clear-assignee",
            "add-label",
            "rm-label",
            "set",
            "unset",
            "as",
            "json",
        }
    ),
    "list": frozenset(
        {
            "help",
            "type",
            "status",
            "parent",
            "label",
            "assignee",
            "category",
            "badge",
            "min-badge",
            "sort",
            "all",
            "json",
            "compact",
        }
    ),
    "tree": frozenset(
        {
            "help",
            "type",
            "status",
            "assignee",
            "category",
            "label",
            "badge",
            "min-badge",
            "sort",
            "depth",
            "all",
            "json",
        }
    ),
    "add-<kind>": frozenset(
        {"help", "assignee", "status", "deferred-to", "message", "file", "json", "as"}
    ),
    "<kind> update": frozenset(
        {
            "help",
            "title",
            "assignee",
            "clear-assignee",
            "status",
            "deferred-to",
            "force",
            "as",
            "json",
        }
    ),
}

#: The fixed keys of each import op that derives keys from the spec.
FIXED_IMPORT_KEYS: dict[str, frozenset[str]] = {
    "add-<kind>": frozenset(
        {
            "op",
            "at",
            "as",
            "target",
            "kind",
            "title",
            "maps_to",
            "fields",
            "assignee",
            "status",
            "deferred_to",
            "body",
            "handle",
        }
    ),
    "comment": frozenset({"op", "at", "as", "target", "messages", "message", "sub"}),
}


def flag_name(code: str) -> str:
    """The option name of a field code or kind: its name with dashes."""
    return code.replace("_", "-")


def _collisions(
    surface: str, fixed: frozenset[str], derived: list[tuple[str, str]], prefix: str
) -> list[str]:
    """The refusals for *derived* ``(name, origin)`` pairs on *surface*: a name in *fixed*, or
    given by two origins. *prefix* is what spells the name on the surface (``--`` or nothing)."""
    errors: list[str] = []
    seen: dict[str, str] = {}
    for name, origin in derived:
        if name in fixed:
            errors.append(
                f"{surface}: {origin} gives {prefix}{name}, which {surface} already takes — "
                "rename it in the workflow override"
            )
        elif name in seen and seen[name] != origin:
            errors.append(
                f"{surface}: {origin} and {seen[name]} both give {prefix}{name} — "
                "rename one in the workflow override"
            )
        seen.setdefault(name, origin)
    return errors


def _field_flags(spec: WorkflowSpec, owner: str, *, clearing: bool) -> list[tuple[str, str]]:
    """The flags *owner*'s fields give, but for a code already refused as a reserved key."""
    reserved = reserved_item_keys() if owner in spec.items else reserved_subentity_keys()
    flags: list[tuple[str, str]] = []
    for f in spec.fields_for(owner):
        if f.code in reserved:
            continue
        origin = f"field {f.code!r}"
        flags.append((flag_name(f.code), origin))
        if clearing and not f.required:
            flags.append((f"no-{flag_name(f.code)}", origin))
    return flags


def _filter_flags(spec: WorkflowSpec) -> list[tuple[str, str]]:
    """The flags `list` and `tree` derive: one per field code some non-roster type declares, and a
    threshold for one on an ordered collection."""
    reserved = reserved_item_keys()
    flags: list[tuple[str, str]] = []
    seen: set[str] = set()
    for item_type in sorted(spec.non_roster_types()):
        for f in spec.fields_for(item_type):
            if f.code in seen or f.code in reserved:
                continue
            seen.add(f.code)
            origin = f"field {f.code!r}"
            flags.append((flag_name(f.code), origin))
            coll = spec.collections.get(f.collection)
            if coll is not None and coll.ordered:
                flags.append((f"min-{flag_name(f.code)}", origin))
    return flags


def check_derived_names(spec: WorkflowSpec, errors: list[str]) -> None:
    """Refuse a derived flag or import key that equals a fixed name on its surface or another
    derived name on it."""
    for item_type in sorted(spec.non_roster_types()):
        errors.extend(
            _collisions(
                f"create {item_type}",
                FIXED_OPTIONS["create"],
                _field_flags(spec, item_type, clearing=False),
                "--",
            )
        )
        errors.extend(
            _collisions(
                f"{item_type} update",
                FIXED_OPTIONS["update"],
                _field_flags(spec, item_type, clearing=True),
                "--",
            )
        )
    filters = _filter_flags(spec)
    errors.extend(_collisions("list", FIXED_OPTIONS["list"], filters, "--"))
    errors.extend(_collisions("tree", FIXED_OPTIONS["tree"], filters, "--"))
    for kind in spec.subentity_kinds:
        target = spec.mapping_target_kind(kind)
        origin = f"target kind {target!r}"
        adds = _field_flags(spec, kind, clearing=False)
        updates = _field_flags(spec, kind, clearing=True)
        if target is not None:
            adds.append((flag_name(target), origin))
            updates += [(flag_name(target), origin), (f"no-{flag_name(target)}", origin)]
        errors.extend(_collisions(f"add-{kind}", FIXED_OPTIONS["add-<kind>"], adds, "--"))
        errors.extend(_collisions(f"{kind} update", FIXED_OPTIONS["<kind> update"], updates, "--"))
        reserved = reserved_subentity_keys()
        keys = [
            (f.code, f"field {f.code!r}") for f in spec.fields_for(kind) if f.code not in reserved
        ]
        if target is not None:
            keys.append((target, origin))
        errors.extend(
            _collisions(f"import op add-{kind}", FIXED_IMPORT_KEYS["add-<kind>"], keys, "")
        )
    selectors = [
        (kind, f"kind {kind!r}") for kind in spec.subentity_kinds if kind != GENERIC_SUBENTITY_VERB
    ]
    errors.extend(_collisions("import op comment", FIXED_IMPORT_KEYS["comment"], selectors, ""))
