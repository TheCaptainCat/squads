"""Load-time validity checks over a workflow spec's declarations: lifecycle reachability, parent
and ref rules, validator selections, category consistency, field and attribute declarations,
views and ref kinds.

Each check appends human-readable problems to the caller's ``errors`` list;
``WorkflowSpec._validate`` runs them and raises the combined result.
"""

import keyword
import re
import uuid
import warnings
from collections.abc import Callable, Iterator
from re import compile as re_compile

from squads._models._attributes import ROW_ADDED_KEYS, AttributeKey
from squads._workflow._models import (
    COLOR_INTENTS,
    FALLBACK_ROLE_NAME,
    RESERVED_CLI_VERBS,
    RESERVED_VIEW_NAME,
    ROSTER_OPERATOR,
    ROSTER_ROLE,
    ROSTER_SKILL,
    Collection,
    Field,
    ItemSpec,
    Lifecycle,
    RefKindSpec,
    RoleSpec,
    SquadSpec,
    StatusSpec,
    SubentityKindSpec,
    ViewSource,
    ViewSpec,
    ViewTransform,
    parse_view_position,
    reserved_alias_owner,
)
from squads._workflow._validator_names import (
    ACTIVE_ITEM_SQUAD_GLOBAL_NAMES,
    ALWAYS_ON_SQUAD_GLOBAL_NAMES,
    CATEGORY_BUNDLES,
    COMMON_CORE,
    LEVEL_RANK,
    PARAMETERIZED_VALIDATOR_NAMES,
    REQUIRED_PARAM_SHAPE,
    SELECTABLE_SQUAD_GLOBAL_NAMES,
    SQUAD_GLOBAL_PARAM_MINIMUM,
    SQUAD_GLOBAL_VALIDATOR_NAMES,
    SUBENTITY_VALIDATOR_NAMES,
    VALIDATOR_LEVEL_FLOOR,
    VALIDATOR_LEVELS,
    VALIDATOR_NAMES,
    WORK_POLICY_VALIDATOR_NAMES,
    effective_bare_validators,
    parse_non_negative_int,
    parse_positive_int,
    parse_validator_entry,
    validator_selection_key,
)

#: One consistency clause: given a type, its spec, its effective (bare) validator names, the
#: sub-entity kind table and the declared ref-kind table, return the refusals its declarations
#: earn. Clauses are pure and independent — a type that trips two reports both.
type ConsistencyClause = Callable[
    [str, ItemSpec, frozenset[str], dict[str, SubentityKindSpec], dict[str, RefKindSpec]],
    list[str],
]


def check_lifecycle_statuses(
    lifecycles: dict[str, Lifecycle],
    all_statuses: set[str],
    errors: list[str],
) -> None:
    """Check initial and transition src/dst are declared statuses."""
    for name, m in lifecycles.items():
        tag = f"lifecycle {name!r}"
        if m.initial not in all_statuses:
            errors.append(f"{tag}: initial {m.initial!r} not in status set")
        for src, dsts in m.transitions.items():
            if src not in all_statuses:
                errors.append(f"{tag}: transition source {src!r} not in status set")
            errors.extend(
                f"{tag}: transition target {dst!r} not in status set"
                for dst in dsts
                if dst not in all_statuses
            )


def check_reachability(
    lifecycles: dict[str, Lifecycle],
    errors: list[str],
) -> None:
    """Every state in a lifecycle must be reachable from initial."""
    for name, m in lifecycles.items():
        reachable: set[str] = {m.initial}
        queue: list[str] = [m.initial]
        while queue:
            cur = queue.pop()
            for nxt in m.transitions.get(cur, []):
                if nxt not in reachable:
                    reachable.add(nxt)
                    queue.append(nxt)
        unreachable = m.states - reachable
        errors.extend(
            f"lifecycle {name!r}: state {s!r} unreachable from initial {m.initial!r}"
            for s in sorted(unreachable)
        )


def _status_role(
    status: str, statuses: dict[str, StatusSpec], roles: dict[str, RoleSpec]
) -> RoleSpec | None:
    """The role *status* resolves to: an absent ``role`` falls back to ``FALLBACK_ROLE_NAME``,
    and an unresolvable role name (already caught by ``check_role_references``) is ``None``
    rather than raising here."""
    spec = statuses.get(status)
    return roles.get((spec.role if spec else None) or FALLBACK_ROLE_NAME)


def _status_settled(
    status: str, statuses: dict[str, StatusSpec], roles: dict[str, RoleSpec]
) -> bool:
    """Whether *status* resolves to a settled role; an unresolvable role is not-settled."""
    role = _status_role(status, statuses, roles)
    return bool(role and role.settled)


def check_reachable_settled(
    lifecycles: dict[str, Lifecycle],
    statuses: dict[str, StatusSpec],
    roles: dict[str, RoleSpec],
    errors: list[str],
) -> None:
    """Every lifecycle must be able to reach at least one status whose role is settled.

    BFS from ``initial`` over the transition graph; if none of the reachable states resolves
    to a settled role, the machine can never close (breaking ``sq blocked``, the default
    closed-item filter, and inbox suppression for any item stuck on it).  Fails closed with the
    offending lifecycle name so ``sq workflow lint`` can point the author at the fix.
    """
    for name, m in lifecycles.items():
        reachable: set[str] = {m.initial}
        queue: list[str] = [m.initial]
        while queue:
            cur = queue.pop()
            for nxt in m.transitions.get(cur, []):
                if nxt not in reachable:
                    reachable.add(nxt)
                    queue.append(nxt)
        if not any(_status_settled(s, statuses, roles) for s in reachable):
            errors.append(
                f"lifecycle {name!r}: no status with a settled role reachable from initial "
                f"{m.initial!r} (reachable: {sorted(reachable)}) — items on this "
                f"lifecycle could never close; add a transition to a status with a settled role"
            )


def _status_live(status: str, statuses: dict[str, StatusSpec], roles: dict[str, RoleSpec]) -> bool:
    """Whether *status* resolves to a role declaring ``live``; an unresolvable role is not."""
    role = _status_role(status, statuses, roles)
    return bool(role and role.live)


def _status_blocked(
    status: str, statuses: dict[str, StatusSpec], roles: dict[str, RoleSpec]
) -> bool:
    """Whether *status* resolves to a role declaring ``blocked``; an unresolvable role is not."""
    role = _status_role(status, statuses, roles)
    return bool(role and role.blocked)


def _status_deferred(
    status: str, statuses: dict[str, StatusSpec], roles: dict[str, RoleSpec]
) -> bool:
    """Whether *status* resolves to a role declaring ``deferred``; an unresolvable role is not."""
    role = _status_role(status, statuses, roles)
    return bool(role and role.deferred)


def check_item_lifecycles_avoid_deferred(
    items: dict[str, ItemSpec],
    lifecycles: dict[str, Lifecycle],
    statuses: dict[str, StatusSpec],
    roles: dict[str, RoleSpec],
    errors: list[str],
) -> None:
    """An item lifecycle must not reach a status whose role declares ``deferred``: items name
    their carrier through refs, and the flag would silently do nothing on them."""
    for t, ts in items.items():
        lifecycle = lifecycles.get(ts.lifecycle)
        if lifecycle is None:
            continue
        reached = sorted(s for s in lifecycle.states if _status_deferred(s, statuses, roles))
        if reached:
            errors.append(
                f"item {t!r}: lifecycle {ts.lifecycle!r} reaches {reached} whose role declares "
                "deferred = true — only a sub-entity lifecycle may; use a ref to name a carrier "
                "or give the status another role"
            )


def check_roster_lifecycle_floor(
    items: dict[str, ItemSpec],
    lifecycles: dict[str, Lifecycle],
    statuses: dict[str, StatusSpec],
    roles: dict[str, RoleSpec],
    errors: list[str],
) -> None:
    """The extra floor for a lifecycle bound to a ``category = "roster"`` type, restated against the
    ``live`` flag, never a role name. R1: at least one live status, or no entry could be
    materialised and generated config could present no agent. R1': if ``initial`` is not live,
    exactly one status is live, keeping ``live_initial`` total for scaffolding that must create an
    entry already on offer. R2: a settled, non-live status reachable from a live one (from the whole
    live set), since the universal reachable-settled floor only guarantees reachability from
    ``initial`` and a live entry might never retire. A lifecycle referencing an undeclared status is
    skipped, being reported by ``check_item_refs``/``check_lifecycle_statuses``.
    """
    for t, ts in items.items():
        if ts.category != "roster":
            continue
        machine = lifecycles.get(ts.lifecycle)
        if machine is None:
            continue
        live = sorted(s for s in machine.states if _status_live(s, statuses, roles))
        if not live:
            errors.append(
                f"roster type {t!r}: lifecycle {ts.lifecycle!r} has no live status — no "
                f"entry of this type could ever be materialised (R1)"
            )
            continue
        live_set = set(live)
        if machine.initial not in live_set and len(live) != 1:
            errors.append(
                f"roster type {t!r}: lifecycle {ts.lifecycle!r}'s initial {machine.initial!r} "
                f"is not live, so exactly one status must be live to give the create "
                f"path an unambiguous target (R1'; found {len(live)} live: {live})"
            )
        reachable: set[str] = set()
        queue: list[str] = list(live_set)
        seen: set[str] = set(live_set)
        while queue:
            cur = queue.pop()
            for nxt in machine.transitions.get(cur, []):
                if nxt not in seen:
                    seen.add(nxt)
                    reachable.add(nxt)
                    queue.append(nxt)
        if not any(s not in live_set and _status_settled(s, statuses, roles) for s in reachable):
            errors.append(
                f"roster type {t!r}: lifecycle {ts.lifecycle!r} has no settled, non-live "
                f"status reachable from a live status (reachable: {sorted(reachable)}) — "
                f"an entry could never retire (R2)"
            )


def check_role_references(
    statuses: dict[str, StatusSpec],
    roles: dict[str, RoleSpec],
    errors: list[str],
) -> None:
    """Plane-1 role-catalog checks: every explicit ``status.role`` must name a declared role,
    every declared role's ``color`` must be a member of the closed intent palette, and the
    fallback role (``FALLBACK_ROLE_NAME``) a role-less status resolves to must itself be
    declared — ``role_for``'s fallback lookup otherwise ``KeyError``s instead of failing
    closed at load."""
    if FALLBACK_ROLE_NAME not in roles:
        errors.append(f"role catalog: the fallback role {FALLBACK_ROLE_NAME!r} must be declared")
    for name, spec in statuses.items():
        if spec.role is not None and spec.role not in roles:
            errors.append(f"status {name!r}: role {spec.role!r} not declared in roles")
    for name, role in roles.items():
        if role.color not in COLOR_INTENTS:
            errors.append(
                f"role {name!r}: color {role.color!r} not in the closed intent palette "
                f"{sorted(COLOR_INTENTS)}"
            )


def check_completion_status(
    subentity_kinds: dict[str, SubentityKindSpec],
    lifecycles: dict[str, Lifecycle],
    errors: list[str],
) -> None:
    """Each declared sub-entity kind's ``completion`` must name a reachable, non-initial
    state of its own ``lifecycle`` — the done-toggle target ``subentity_completion(kind)``
    resolves to. An undeclared ``lifecycle`` is caught separately by
    ``check_subentity_kinds``; skipped here to avoid a duplicate error.
    """
    for kind, ks in subentity_kinds.items():
        machine = lifecycles.get(ks.lifecycle)
        if machine is None:
            continue
        if ks.completion == machine.initial:
            errors.append(
                f"subentity kind {kind!r}: completion {ks.completion!r} is the initial "
                f"status of lifecycle {ks.lifecycle!r} — nothing is done at creation"
            )
        elif ks.completion not in machine.states:
            errors.append(
                f"subentity kind {kind!r}: completion {ks.completion!r} not a reachable "
                f"status of lifecycle {ks.lifecycle!r} (states: {sorted(machine.states)})"
            )


def check_subentity_kinds(
    items: dict[str, ItemSpec],
    subentity_kinds: dict[str, SubentityKindSpec],
    all_lifecycle_names: set[str],
    errors: list[str],
) -> None:
    """ItemSpec.subentity_kind references a declared kind; SubentityKindSpec.lifecycle
    reference + plural/local_prefix non-empty & uniqueness."""
    errors.extend(
        f"item {t!r}: references undeclared subentity kind {ts.subentity_kind!r} "
        f"(not in subentity_kinds)"
        for t, ts in sorted(items.items())
        if ts.subentity_kind and ts.subentity_kind not in subentity_kinds
    )

    seen_plurals: dict[str, str] = {}
    seen_prefixes: dict[str, str] = {}
    for kind, ks in subentity_kinds.items():
        if ks.lifecycle not in all_lifecycle_names:
            errors.append(
                f"subentity kind {kind!r}: lifecycle {ks.lifecycle!r} not declared in lifecycles"
            )

        if not ks.plural:
            errors.append(f"subentity kind {kind!r}: plural must be non-empty")
        elif ks.plural in seen_plurals:
            errors.append(
                f"duplicate subentity plural {ks.plural!r}: used by kinds "
                f"{seen_plurals[ks.plural]!r} and {kind!r}"
            )
        else:
            seen_plurals[ks.plural] = kind

        if not ks.local_prefix:
            errors.append(f"subentity kind {kind!r}: local_prefix must be non-empty")
        elif ks.local_prefix in seen_prefixes:
            errors.append(
                f"duplicate subentity local_prefix {ks.local_prefix!r}: used by kinds "
                f"{seen_prefixes[ks.local_prefix]!r} and {kind!r}"
            )
        else:
            seen_prefixes[ks.local_prefix] = kind


def check_parent_cycles(
    items: dict[str, ItemSpec],
    errors: list[str],
) -> None:
    """Detect cycles in the type-parent graph.

    Walks ``items[t].parents`` using DFS with a colour-marking scheme:
    - WHITE (unvisited), GREY (on the current path), BLACK (fully explored).
    A back-edge (GREY → GREY) indicates a cycle.

    Reports each cycle once in a deterministic order (sorted entry points).
    """
    WHITE, GREY, BLACK = 0, 1, 2
    colour: dict[str, int] = {t: WHITE for t in items}
    path: list[str] = []
    reported: set[frozenset[str]] = set()

    def dfs(node: str) -> None:
        colour[node] = GREY
        path.append(node)
        for parent in items[node].parents:
            if parent not in colour:
                # Parent declared but not a known type — caught by check_item_refs.
                continue
            if colour[parent] == GREY:
                # Back-edge: reconstruct cycle from path.
                cycle_start = path.index(parent)
                cycle_nodes = path[cycle_start:]
                key = frozenset(cycle_nodes)
                if key not in reported:
                    reported.add(key)
                    cycle_str = " → ".join([*cycle_nodes, parent])
                    errors.append(f"type-parent graph has a cycle: {cycle_str}")
            elif colour[parent] == WHITE:
                dfs(parent)
        path.pop()
        colour[node] = BLACK

    for t in sorted(items):
        if colour[t] == WHITE:
            dfs(t)


def check_item_refs(
    items: dict[str, ItemSpec],
    all_lifecycle_names: set[str],
    all_types: set[str],
    errors: list[str],
) -> None:
    """ItemSpec lifecycle/parent references + prefix/folder/alias uniqueness."""
    seen_prefixes: dict[str, str] = {}
    seen_folders: dict[str, str] = {}
    seen_aliases: dict[str, str] = {}

    for t, ts in items.items():
        if ts.lifecycle not in all_lifecycle_names:
            errors.append(f"item {t!r}: lifecycle {ts.lifecycle!r} not declared in lifecycles")
        errors.extend(
            f"item {t!r}: parent type {p!r} not declared" for p in ts.parents if p not in all_types
        )
        if t in RESERVED_CLI_VERBS:
            errors.append(
                f"item {t!r}: shadows the built-in `sq {t}` command — rename the type "
                "(its whole per-type verb surface, `sq <type> <n> <verb>`, becomes unreachable "
                "behind the built-in)"
            )
        name_alias_owner = reserved_alias_owner(t)
        if name_alias_owner is not None:
            errors.append(
                f"item {t!r}: shadows the built-in `sq {t}` alias of the {name_alias_owner!r} "
                f"command — rename the type (`sq {t} <n> <verb>` and `sq create {t}` both "
                f"dispatch into {name_alias_owner!r}'s command tree, not this type's)"
            )
        errors.extend(
            f"item {t!r}: alias {alias!r} shadows the built-in `sq {alias}` command — rename "
            "or drop the alias"
            for alias in ts.aliases
            if alias in RESERVED_CLI_VERBS
        )
        errors.extend(
            f"item {t!r}: alias {alias!r} shadows the built-in `sq {alias}` alias of the "
            f"{owner!r} command — rename or drop the alias"
            for alias in ts.aliases
            if (owner := reserved_alias_owner(alias)) is not None and owner != t
        )
        if ts.prefix in seen_prefixes:
            errors.append(
                f"duplicate prefix {ts.prefix!r}: used by {seen_prefixes[ts.prefix]!r} and {t!r}"
            )
        seen_prefixes[ts.prefix] = t

        if ts.folder in seen_folders:
            errors.append(
                f"duplicate folder {ts.folder!r}: used by {seen_folders[ts.folder]!r} and {t!r}"
            )
        seen_folders[ts.folder] = t

        for alias in ts.aliases:
            if alias in seen_aliases:
                errors.append(
                    f"duplicate alias {alias!r}: used by {seen_aliases[alias]!r} and {t!r}"
                )
            seen_aliases[alias] = t


def _check_external_id_pattern(t: str, entry: str, param: str, errors: list[str]) -> None:
    """*param* must compile without a warning and must not match the empty string, which would
    report every title (and, at ``@error``, refuse every write of the type).

    ``re`` warns only on the first compile of a pattern, so the warning check compiles a copy
    behind a unique comment group: its cache key is never seen before, the semantics are
    unchanged, and no other caller's cached pattern is touched."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            compiled = re_compile(param)
        except re.error as exc:
            errors.append(
                f"item {t!r}: validators entry {entry!r} names an invalid regular expression "
                f"{param!r}: {exc}"
            )
            return
        re_compile(f"(?#{uuid.uuid4().hex}){param}")
    if caught:
        detail = re.sub(r" at position \d+", "", str(caught[0].message))
        errors.append(
            f"item {t!r}: validators entry {entry!r} names a regular expression {param!r} that "
            f"compiles with a warning: {detail} — rewrite it"
        )
    elif compiled.search("") is not None:
        errors.append(
            f"item {t!r}: validators entry {entry!r} names a regular expression {param!r} that "
            "matches the empty string, so it would report every title — make it require a "
            "character"
        )


def _check_validator_param(
    t: str, entry: str, bare: str, param: str | None, errors: list[str]
) -> None:
    """The meaningful params: a title-length threshold (``subentity_title_max:<n>``,
    ``item_title_max:<n>``) must parse as a positive integer, ``external_id_not_in_title``'s
    must compile as a regular expression, and a member in
    :data:`REQUIRED_PARAM_SHAPE` must carry one at all. Resolvable without the whole
    ``[items.*]`` table (nothing here needs a cross-type lookup)."""
    if bare in REQUIRED_PARAM_SHAPE and not (param and param.strip()):
        shape = REQUIRED_PARAM_SHAPE[bare]
        errors.append(
            f"item {t!r}: validators entry {entry!r} is missing its required parameter — "
            f"name it as '{bare}:{shape}', or drop the validator; "
            "without a parameter it never fires"
        )
        return
    if param is None:
        return
    if bare == "external_id_not_in_title":
        _check_external_id_pattern(t, entry, param, errors)
        return
    if bare not in ("subentity_title_max", "item_title_max"):
        return
    if parse_positive_int(param) is None:
        errors.append(
            f"item {t!r}: validators entry {entry!r} names a non-positive-integer "
            f"{bare} threshold {param!r}"
        )


def _check_validator_level(t: str, entry: str, bare: str, level: str, errors: list[str]) -> None:
    """A declared ``@<level>`` must be a member of :data:`VALIDATOR_LEVELS`, and — for a member
    :data:`VALIDATOR_LEVEL_FLOOR` names — no lower ranked than its floor."""
    if level not in VALIDATOR_LEVELS:
        errors.append(
            f"item {t!r}: validators entry {entry!r} names an unknown level {level!r} "
            f"(must be one of {sorted(VALIDATOR_LEVELS)})"
        )
        return
    floor = VALIDATOR_LEVEL_FLOOR.get(bare)
    if floor is not None and LEVEL_RANK[level] < LEVEL_RANK[floor]:
        errors.append(
            f"item {t!r}: validator {bare!r} cannot be selected below its floor level "
            f"{floor!r} (got {level!r})"
        )


def _repeat_selection_message(item_type: str, bare: str, prior: str, entry: str) -> str:
    """The refusal message for two ``validators`` entries sharing one
    :func:`validator_selection_key`. They can differ in text (a differing param on a
    :data:`SINGLE_SELECTION_VALIDATOR_NAMES` member, or a differing ``@<level>``), so asserting "the
    same selection" would read as self-contradictory; it names the actual reason and the remedy.
    """
    if prior == entry:
        return (
            f"item {item_type!r}: validator {bare!r} is selected more than once "
            f"({entry!r} repeated) — keep one entry"
        )
    _, prior_param, _ = parse_validator_entry(prior)
    _, cur_param, _ = parse_validator_entry(entry)
    if prior_param != cur_param:
        # Only a SINGLE_SELECTION_VALIDATOR_NAMES member reaches this branch with differing
        # params — a MULTI_SELECTION_VALIDATOR_NAMES member keys on (bare, param), so two
        # differing params never collide for it in the first place.
        reason = (
            f"{bare!r} resolves only its first matching entry, so the second would be "
            "silently ignored rather than take effect — refused here instead"
        )
    else:
        reason = "an '@<level>' suffix alone does not make two entries independent selections"
    return (
        f"item {item_type!r}: validator {bare!r} is selected more than once "
        f"({prior!r} and {entry!r}) — {reason}; keep one entry"
    )


def check_validators_assignment(items: dict[str, ItemSpec], errors: list[str]) -> None:
    """Plane-1 checks for each type's ``validators`` list, entry by entry: the bare name must be a
    declared catalog member; a ``:<param>`` is well-formed only on a
    ``PARAMETERIZED_VALIDATOR_NAMES`` name and, for ``subentity_title_max``, a positive integer
    (:func:`_check_validator_param`); an ``@<level>`` must name a declared level at or above the
    member's floor (:func:`_check_validator_level`); and a type may not repeat a *selection*
    (:func:`validator_selection_key`). Outside ``MULTI_SELECTION_VALIDATOR_NAMES`` the key is the
    bare name alone, so a second entry is refused (which value wins is not the loader's call, and a
    differently-parameterised second would load clean yet stay inert); on a multi-selection member
    different params are independent and only an identical param is refused. A
    ``ref_rule_target_present:<T>`` entry's coherence is checked once every ``[items.*]`` block is
    known (:func:`check_ref_rule_targets`).
    """
    for t, ts in items.items():
        seen: dict[tuple[str, str | None], str] = {}
        for entry in ts.validators:
            bare, param, level = parse_validator_entry(entry)
            if bare in SQUAD_GLOBAL_VALIDATOR_NAMES:
                errors.append(
                    f"item {t!r}: validators entry {entry!r}: {bare} is a squad-global "
                    "validator — select it in the `[squad]` table's `validators` list"
                )
                continue
            if bare not in VALIDATOR_NAMES:
                errors.append(f"item {t!r}: validators entry {entry!r} names an unknown validator")
                continue
            if param is not None and bare not in PARAMETERIZED_VALIDATOR_NAMES:
                errors.append(f"item {t!r}: validator {bare!r} takes no param (got {entry!r})")
            else:
                _check_validator_param(t, entry, bare, param, errors)
            if level is not None:
                if bare == "external_id_not_in_title" and level not in VALIDATOR_LEVELS:
                    errors.append(
                        f"item {t!r}: validators entry {entry!r} reads {level!r} as its level — "
                        "'@' separates the pattern from the level ('error' or 'warn') and cannot "
                        "appear in the pattern; write a literal '@' as \\x40"
                    )
                else:
                    _check_validator_level(t, entry, bare, level, errors)
            key = validator_selection_key(entry)
            if key in seen:
                errors.append(_repeat_selection_message(t, bare, seen[key], entry))
            else:
                seen[key] = entry


def check_ref_rule_targets(items: dict[str, ItemSpec], errors: list[str]) -> None:
    """Plane-1 referential validation for :attr:`RefRule.target`, run here and not in
    ``_parse_ref_rules`` because item types are known only after every ``[items.*]`` block parses.
    Two checks: every ``target`` names a declared item type; and a type selecting
    ``ref_rule_target_present:<T>`` declares a ``ref_rules`` entry targeting ``<T>``, or ``<T>``
    could be a type nothing points the check at or not a type at all. Each is refused rather than
    doing nothing forever.
    """
    for t, ts in items.items():
        errors.extend(
            f"item {t!r}: ref_rules target {rr.target!r} does not name a declared item type"
            for rr in ts.ref_rules
            if rr.target is not None and rr.target not in items
        )

    for t, ts in items.items():
        for entry in ts.validators:
            bare, param, _level = parse_validator_entry(entry)
            if bare != "ref_rule_target_present":
                continue
            if param is None or not param.strip():
                continue  # _check_validator_param refuses a missing target type
            if param not in items:
                errors.append(
                    f"item {t!r}: validators entry {entry!r} names target type {param!r}, "
                    "which is not a declared item type"
                )
            elif not any(rr.target == param for rr in ts.ref_rules):
                errors.append(
                    f"item {t!r}: validators entry {entry!r} selects target {param!r}, but "
                    f"{t!r} declares no ref_rules entry with that target — the validator "
                    "would refuse every settled item unconditionally. Add "
                    f"{{ kind = ..., target = {param!r} }} to its ref_rules, or drop the "
                    "validator"
                )


def check_selections_that_cannot_fire(
    items: dict[str, ItemSpec],
    lifecycles: dict[str, Lifecycle],
    statuses: dict[str, StatusSpec],
    roles: dict[str, RoleSpec],
    ref_kinds: dict[str, RefKindSpec],
    errors: list[str],
) -> None:
    """Plane-1: a selected check the spec's own declarations make unable to fire is refused, so it
    is never a silent no-op nor dependent on the corpus; each message names the type, the entry and
    the missing declaration. A :data:`WORK_POLICY_VALIDATOR_NAMES` member is refused on a ``roster``
    type; ``ref_rule_target_typed`` also needs a ref rule with a target, ``assignee_present`` a
    lifecycle with a live-role status, and ``blocked_has_blocker`` a blocked-role status plus a
    declared dependency ref kind.
    """
    for t, ts in items.items():
        for entry in ts.validators:
            bare, _param, _level = parse_validator_entry(entry)
            if bare in WORK_POLICY_VALIDATOR_NAMES and ts.category == "roster":
                errors.append(
                    f"item {t!r}: validators entry {entry!r} cannot apply to a roster type — "
                    f"{bare} is a policy about tracked work and applies to 'work' and "
                    "'records' types only; drop the entry"
                )
                continue
            if bare == "ref_rule_target_typed" and not any(
                rr.target is not None for rr in ts.ref_rules
            ):
                errors.append(
                    f"item {t!r}: validators entry {entry!r} needs a ref_rules entry with a "
                    f"target, and {t!r} declares none (a rule whose target type was dropped "
                    "through [selected] is removed with it) — declare "
                    "{ kind = ..., target = ... } in its ref_rules, or drop the entry"
                )
            lifecycle = lifecycles.get(ts.lifecycle)
            if (
                bare == "assignee_present"
                and lifecycle is not None
                and not any(_status_live(st, statuses, roles) for st in lifecycle.states)
            ):
                errors.append(
                    f"item {t!r}: validators entry {entry!r} needs a status of a role declaring "
                    f"live = true, and the lifecycle {ts.lifecycle!r} of {t!r} holds none — "
                    "without one it never fires; drop the entry or give the lifecycle a status "
                    "of a live role"
                )
            if bare == "blocked_has_blocker":
                errors += _blocked_has_blocker_refusals(
                    t, ts, entry, lifecycle, statuses, roles, ref_kinds
                )


def _blocked_has_blocker_refusals(
    t: str,
    ts: ItemSpec,
    entry: str,
    lifecycle: Lifecycle | None,
    statuses: dict[str, StatusSpec],
    roles: dict[str, RoleSpec],
    ref_kinds: dict[str, RefKindSpec],
) -> list[str]:
    """What keeps ``blocked_has_blocker`` from firing on *t*: no status of a blocked role in
    its lifecycle, or no declared dependency ref kind in the spec."""
    refusals: list[str] = []
    if lifecycle is not None and not any(
        _status_blocked(st, statuses, roles) for st in lifecycle.states
    ):
        refusals.append(
            f"item {t!r}: validators entry {entry!r} needs a status of a role declaring "
            f"blocked = true, and the lifecycle {ts.lifecycle!r} of {t!r} holds none — "
            "without one it never fires; drop the entry or give the lifecycle a status of a "
            "blocked role"
        )
    if not any(rk.role == "dependency" for rk in ref_kinds.values()):
        refusals.append(
            f"item {t!r}: validators entry {entry!r} needs a declared ref kind with "
            'role = "dependency", and the spec declares none — without one no edge can '
            "satisfy it; drop the entry or declare a dependency ref kind"
        )
    return refusals


def _check_squad_validator_entry(entry: str, errors: list[str]) -> None:
    """Refusals for one ``[squad] validators`` entry's name, parameter and level."""
    bare, param, level = parse_validator_entry(entry)
    where = f"squad validators entry {entry!r}"
    if bare in VALIDATOR_NAMES:
        errors.append(
            f"{where}: {bare} is a per-item validator — name it on a type's `validators` list"
        )
        return
    if bare in ALWAYS_ON_SQUAD_GLOBAL_NAMES:
        errors.append(f"{where}: {bare} always runs and cannot be selected — drop the entry")
        return
    if bare not in SELECTABLE_SQUAD_GLOBAL_NAMES:
        errors.append(f"{where} names an unknown validator")
        return
    minimum = SQUAD_GLOBAL_PARAM_MINIMUM.get(bare)
    if minimum is None:
        if param is not None:
            errors.append(f"{where}: {bare} takes no parameter")
    elif not (param and param.strip()):
        errors.append(f"{where}: {bare} needs its parameter — write '{bare}:<n>'")
    else:
        value = parse_non_negative_int(param)
        if value is None or value < minimum:
            kind = "positive" if minimum > 0 else "non-negative"
            errors.append(f"{where}: {bare} needs a {kind} integer parameter (got {param!r})")
    if level is not None and level not in VALIDATOR_LEVELS:
        errors.append(
            f"{where} names an unknown level {level!r} (must be one of {sorted(VALIDATOR_LEVELS)})"
        )


def check_squad_validators(
    squad: SquadSpec,
    items: dict[str, ItemSpec],
    lifecycles: dict[str, Lifecycle],
    statuses: dict[str, StatusSpec],
    roles: dict[str, RoleSpec],
    ref_kinds: dict[str, RefKindSpec],
    errors: list[str],
) -> None:
    """Plane-1 checks for ``[squad] validators``: each entry names a selectable squad-global
    member with a well-formed parameter and level, no member is named twice, and a selection the
    spec's own declarations make unable to fire is refused (the corpus is never consulted)."""
    seen: dict[str, str] = {}
    for entry in squad.validators:
        _check_squad_validator_entry(entry, errors)
        bare = parse_validator_entry(entry)[0]
        if bare not in SELECTABLE_SQUAD_GLOBAL_NAMES:
            continue
        if bare in seen:
            errors.append(
                f"squad validators entry {entry!r} repeats {bare}, already selected as "
                f"{seen[bare]!r} — name each member once"
            )
            continue
        seen[bare] = entry
        if bare in ACTIVE_ITEM_SQUAD_GLOBAL_NAMES and not any(
            ts.category == "work"
            and (lc := lifecycles.get(ts.lifecycle)) is not None
            and any(_status_live(st, statuses, roles) for st in lc.states)
            for ts in items.values()
        ):
            errors.append(
                f"squad validators entry {entry!r} needs a work type whose lifecycle holds a "
                "status of a role declaring live = true, and none does — without one no item is "
                "active and it never fires; drop the entry or give a work type's lifecycle a "
                "status of a live role"
            )
        if bare == "dependency_acyclic" and not any(
            rk.role == "dependency" for rk in ref_kinds.values()
        ):
            errors.append(
                f"squad validators entry {entry!r} needs a declared ref kind with "
                'role = "dependency", and the spec declares none — without one no cycle can '
                "exist; drop the entry or declare a dependency ref kind"
            )


def _clause_parent_reachable(
    t: str,
    ts: ItemSpec,
    effective: frozenset[str],
    _kinds: dict[str, SubentityKindSpec],
    _ref_kinds: dict[str, RefKindSpec],
) -> list[str]:
    """Guards ``parent_in`` and owns every arm about the parent declarations as a set. A declared
    parent constraint is **contradicted** when the effective set includes ``no_parent`` (so
    ``parents`` and ``parent_required`` cannot be satisfied, reachable by a ``work`` type adding
    ``no_parent``) and **unenforced** when neither ``no_parent`` nor ``parent_in`` is effective
    (only the empty ``roster`` bundle), leaving ``parents`` declared but unread. Two further
    contradictions: ``parent_present`` with ``no_parent`` in one set refuses every item whichever
    way it is created, and ``parent_required`` naming a type the ``parents`` allowlist excludes
    makes ``subtask_story_mapping`` dead in both directions (an empty ``parents`` is the lenient
    "any parent" and excludes nothing).

    ``parent_required`` is absent from the reachability audit because it has a live consumer under
    every category (the generated ``--parent`` example and the anchor-type score), so such an arm
    would fire on a correct spec; its enforcement is opt-in (``parent_present``).
    """
    declared = [
        f"{name}={value!r}"
        for name, value in (("parents", ts.parents), ("parent_required", ts.parent_required))
        if value
    ]
    if declared and "no_parent" in effective:
        return [
            f"item {t!r}: category {ts.category!r} forbids a parent (its validator set "
            f"includes 'no_parent'), but the type still declares {', '.join(declared)} "
            f"— that constraint can never apply. Drop the parent field(s), or leave "
            f"{t!r} in a category that allows a parent"
        ]
    if {"parent_present", "no_parent"} <= effective:
        return [
            f"item {t!r}: its validator set holds both 'parent_present' (a parent is "
            f"mandatory) and 'no_parent' (a parent is forbidden), so every {t} would be "
            f"refused however it is created. Drop one of the two"
        ]
    if ts.parents and "parent_in" not in effective:
        return [
            f"item {t!r}: declares parents={ts.parents!r}, but category {ts.category!r} turns "
            f"on no validator that reads it ('parent_in'), so the allowlist would never be "
            f"checked. Drop parents, leave {t!r} in a category that checks a parent, or name "
            f"'parent_in' in its own 'validators' list"
        ]
    if ts.parent_required and ts.parents and ts.parent_required not in ts.parents:
        return [
            f"item {t!r}: declares parent_required={ts.parent_required!r}, but its "
            f"parents={ts.parents!r} allowlist excludes that type, so the one parent it "
            f"requires is the one 'parent_in' refuses. Add {ts.parent_required!r} to parents, "
            f"point parent_required at a type parents allows, or clear parents to allow any"
        ]
    return []


def _clause_subentity_checked(
    t: str,
    ts: ItemSpec,
    effective: frozenset[str],
    _kinds: dict[str, SubentityKindSpec],
    _ref_kinds: dict[str, RefKindSpec],
) -> list[str]:
    """Guards the sub-entity validators a bundle supplies; any of :data:`SUBENTITY_VALIDATOR_NAMES`
    satisfies it. A type declaring a ``subentity_kind`` must keep at least one validator whose
    subject is that kind, as the ``records`` bundle carries none and a hosting type moved there
    would lose every check on its sub-entities. It is "at least one", not all four, because the list
    is extend-only, so an adopter can name the checks wanted back and the refusal stays reachable
    (validation, not prohibition).
    """
    if ts.subentity_kind is None or (effective & SUBENTITY_VALIDATOR_NAMES):
        return []
    return [
        f"item {t!r}: declares subentity_kind {ts.subentity_kind!r}, but category "
        f"{ts.category!r} turns on no validator for it, so nothing would check those "
        f"sub-entities. Drop subentity_kind, leave {t!r} in a category that validates "
        f"sub-entities, or name the checks you want in its own 'validators' list "
        f"({', '.join(sorted(SUBENTITY_VALIDATOR_NAMES))})"
    ]


def _clause_supersedes_checked(
    t: str,
    ts: ItemSpec,
    effective: frozenset[str],
    _kinds: dict[str, SubentityKindSpec],
    ref_kinds: dict[str, RefKindSpec],
) -> list[str]:
    """Guards ``supersedes_incoming``, gated by a ref rule naming a declared ``supersession``-role
    kind: it returns at once for a type declaring none and sits only in the ``records`` bundle, so a
    type keeping its ``supersession`` rule under another category loses the only check it drives and
    a record left superseded with no incoming edge stops being reported. It resolves through
    *ref_kinds* (mirroring the validator's ``rr.kind in spec.supersession_ref_kinds()`` gate), never
    a fixed ``"supersedes"``; the other ``ref_rules`` drive hint text only and stay live under every
    category.
    """
    supersession_kinds = frozenset(k for k, ks in ref_kinds.items() if ks.role == "supersession")
    if not any(rr.kind in supersession_kinds for rr in ts.ref_rules) or "supersedes_incoming" in (
        effective
    ):
        return []
    return [
        f"item {t!r}: declares a 'supersession'-role ref rule, but category {ts.category!r} "
        "turns on no validator for it ('supersedes_incoming'), so a superseded "
        f"{t} with no incoming supersession edge would go unreported. Drop the ref rule, "
        f"leave {t!r} in a category that checks it, or name 'supersedes_incoming' in its own "
        "'validators' list"
    ]


def _clause_story_mapping_reachable(
    t: str,
    ts: ItemSpec,
    effective: frozenset[str],
    kinds: dict[str, SubentityKindSpec],
    _ref_kinds: dict[str, RefKindSpec],
) -> list[str]:
    """Guards ``subtask_story_mapping``, whose gate is the hosted kind's ``maps_parent_story``
    capability rather than anything on the item type itself — which is why it is not one of
    :data:`SUBENTITY_VALIDATOR_NAMES` and needs its own clause. Reachable independently of
    :func:`_clause_subentity_checked`: an adopter who satisfies that one by naming a sub-entity
    check back would otherwise still lose the mapping check with no report.
    """
    ks = kinds.get(ts.subentity_kind) if ts.subentity_kind is not None else None
    if ks is None or not ks.maps_parent_story or "subtask_story_mapping" in effective:
        return []
    return [
        f"item {t!r}: hosts subentity_kind {ts.subentity_kind!r}, which declares "
        f"maps_parent_story, but category {ts.category!r} turns on no validator for it "
        f"('subtask_story_mapping'), so a {ts.subentity_kind} mapping to a story its parent "
        f"does not have would go unreported. Drop maps_parent_story on "
        f"{ts.subentity_kind!r}, leave {t!r} in a category that checks the mapping, or name "
        f"'subtask_story_mapping' in its own 'validators' list"
    ]


#: The :data:`SUBENTITY_VALIDATOR_NAMES` a category bundle supplies -- the ones a category
#: reassignment can take away, and so the ones :func:`_clause_subentity_checked` guards. The
#: rest of the set is only ever effective when a type names it.
_BUNDLED_SUBENTITY_VALIDATOR_NAMES: frozenset[str] = frozenset(
    name
    for name in SUBENTITY_VALIDATOR_NAMES
    if any(name in bundle for bundle in CATEGORY_BUNDLES.values())
)


#: Each clause paired with the validator names whose reachability it guards, declarative so the
#: coverage assert below holds: every member of the closed catalog must be accounted for exactly
#: once.
CONSISTENCY_CLAUSES: tuple[tuple[frozenset[str], ConsistencyClause], ...] = (
    (frozenset({"parent_in"}), _clause_parent_reachable),
    (_BUNDLED_SUBENTITY_VALIDATOR_NAMES, _clause_subentity_checked),
    (frozenset({"supersedes_incoming"}), _clause_supersedes_checked),
    (frozenset({"subtask_story_mapping"}), _clause_story_mapping_reachable),
)


#: The audit's third bucket, argued rather than derived: catalog members no clause guards because
#: no declaration selects them.
#:
#: - :data:`COMMON_CORE` members are effective for every type, so nothing a type declares can put
#:   one out of reach (hence ``parent_acyclic`` is there, as a parent cycle is no house
#:   convention a category could decline).
#: - ``no_parent`` enforces the absence of a parent, so an adopter declares nothing it could stop
#:   enforcing; its failure mode is being on while a parent field is declared, which is
#:   :func:`_clause_parent_reachable`'s first arm.
#: - ``parent_present``, ``ref_rule_target_present``, ``no_status_banner``,
#:   ``subentity_title_max``, ``subentities_settled_with_parent`` and the
#:   :data:`WORK_POLICY_VALIDATOR_NAMES` members sit in no bundle or floor, so a type names them
#:   itself and no category reassignment can take one away. ``parent_present`` fails by
#:   contradiction with ``no_parent`` (:func:`_clause_parent_reachable`);
#:   ``ref_rule_target_present``'s coherence is referential (:func:`check_ref_rule_targets`).
#:   ``subentity_title_max`` still satisfies :func:`_clause_subentity_checked`, while
#:   ``subentities_settled_with_parent`` judges a policy about settled parents and does not.
#: - ``item_skill_shadowed`` is selected only in ``[items.skill]``'s own ``validators`` (the
#:   ``roster`` bundle is empty), and ``skill`` is locked to ``category = "roster"`` by
#:   ``_workflow/_loader.py``, so no reassignment can lose it.
#: - ``pronouns_valid`` is the roster bundle and judges one attribute no capability depends on.
UNGUARDED_VALIDATOR_NAMES: frozenset[str] = frozenset(
    {
        "no_parent",
        "parent_present",
        "ref_rule_target_present",
        "item_skill_shadowed",
        "no_status_banner",
        "subentity_title_max",
        "subentities_settled_with_parent",
        "item_title_max",
        "ref_rule_target_typed",
        "body_written",
        "description_present",
        "assignee_present",
        "blocked_has_blocker",
        "settled_requires_discussion",
        "external_id_not_in_title",
        "frontmatter_key_undeclared",
        "pronouns_valid",
    }
)


CLAUSE_GUARDED: frozenset[str] = frozenset(
    name for names, _ in CONSISTENCY_CLAUSES for name in names
)


def check_category_consistency(
    items: dict[str, ItemSpec],
    kinds: dict[str, SubentityKindSpec],
    ref_kinds: dict[str, RefKindSpec],
    errors: list[str],
) -> None:
    """Plane-1: every capability a type declares must be reachable under the validator set its
    category turns on. An override may move a built-in between ``work`` and ``records`` (validation,
    not prohibition), but an inconsistency is silent on every other gate: moving ``task`` to
    ``records`` while it declares ``parents = ["feature"]`` and ``parent_required = "feature"``
    makes the constraint unreachable both ways, while the spec reports both fields.

    The check is written against the validator set, which is what a category is (nothing else
    branches on ``work`` versus ``records``), so it is category-agnostic and needs no second table.
    The complete rule is one clause per validator whose subject is a declared capability, hence a
    registry: :data:`CONSISTENCY_CLAUSES` pairs each clause with the names it guards and the assert
    above closes it against :data:`VALIDATOR_NAMES`, so a new validator must be guarded or named in
    :data:`UNGUARDED_VALIDATOR_NAMES` with the reason.
    """
    for t, ts in sorted(items.items()):
        effective = effective_bare_validators(ts)
        for _guards, clause in CONSISTENCY_CLAUSES:
            errors.extend(clause(t, ts, effective, kinds, ref_kinds))


#: Field codes exempt from the reserved-key check below because this schema models them by field
#: code on purpose: ``priority``/``severity`` keep their literal key (``Item.priority``,
#: ``Item.severity`` and ``SubEntity.severity`` are the badge-code storage itself), so frontmatter
#: round-trips unchanged.
_FIELD_ELIGIBLE_ITEM_KEYS: frozenset[str] = frozenset({"priority", "severity"})


_FIELD_ELIGIBLE_SUBENTITY_KEYS: frozenset[str] = frozenset({"severity"})


def _reserved_item_keys() -> frozenset[str]:
    """Names a field code or an attribute may not take: the model's own fields (derived from
    ``Item``, never hand-copied), the names a ``--json`` row adds, and ``extra``. ``path`` and
    ``prefix`` are model fields that are not frontmatter, and are refused for the same reason: a
    key of that name is never read back as the user's value."""
    from squads._models._item import Item

    keys = set(Item.model_fields) | set(Item.model_computed_fields)
    return frozenset(keys | set(ROW_ADDED_KEYS) | {"extra"})


def _reserved_subentity_keys() -> frozenset[str]:
    """Sub-entity frontmatter keys a field code may not shadow (mirrors ``_reserved_item_keys``)."""
    from squads._models._subentity import SubEntity

    keys = set(SubEntity.model_fields) | set(SubEntity.model_computed_fields)
    return frozenset(keys - _FIELD_ELIGIBLE_SUBENTITY_KEYS)


def _iter_field_owners(
    items: dict[str, ItemSpec],
    subentity_kinds: dict[str, SubentityKindSpec],
) -> Iterator[tuple[str, bool, list[Field]]]:
    """Yield ``(owner_name, is_item, fields)`` for every type/kind that declares fields."""
    for t, ts in items.items():
        if ts.fields:
            yield t, True, ts.fields
    for k, ks in subentity_kinds.items():
        if ks.fields:
            yield k, False, ks.fields


def check_field_codes(
    items: dict[str, ItemSpec],
    subentity_kinds: dict[str, SubentityKindSpec],
    errors: list[str],
) -> None:
    """Field-code uniqueness per owner + reserved-frontmatter-key collision."""
    reserved_item = _reserved_item_keys()
    reserved_subentity = _reserved_subentity_keys()
    for owner, is_item, fields in _iter_field_owners(items, subentity_kinds):
        seen: set[str] = set()
        reserved = (reserved_item - _FIELD_ELIGIBLE_ITEM_KEYS) if is_item else reserved_subentity
        for f in fields:
            if f.code in seen:
                errors.append(f"{owner!r}: duplicate field code {f.code!r}")
            seen.add(f.code)
            if f.code in reserved:
                errors.append(
                    f"{owner!r}: field code {f.code!r} shadows a reserved frontmatter key"
                )


#: The attributes the engine materialises into agent-host files, by roster type, with the kind each
#: is declared with. A resolved spec may add attributes to a roster type but not drop or re-kind
#: these; an override merges over the bundled spec, which declares them all, so only a spec built
#: whole by hand restates them.
PINNED_ROSTER_ATTRIBUTES: dict[str, dict[str, str]] = {
    ROSTER_ROLE: {
        AttributeKey.IS_DEFAULT: "bool",
        AttributeKey.MODEL: "str",
        AttributeKey.ORIGIN: "str",
        AttributeKey.PRONOUNS: "str",
        AttributeKey.TECH: "str",
    },
    ROSTER_OPERATOR: {
        AttributeKey.PRONOUNS: "str",
    },
    ROSTER_SKILL: {
        AttributeKey.ALLOWED_TOOLS: "str",
        AttributeKey.MODEL: "str",
        AttributeKey.OPERATOR_INVOCABLE: "bool",
        AttributeKey.ORIGIN: "str",
        AttributeKey.WHEN_TO_USE: "str",
    },
}


def check_attributes(items: dict[str, ItemSpec], errors: list[str]) -> None:
    """Attribute names are free of reserved keys and badge codes, and each roster type declares
    its pinned attributes with the pinned kind."""
    reserved = _reserved_item_keys()
    for owner, ts in items.items():
        codes = {f.code for f in ts.fields}
        for name in ts.attributes:
            if name in reserved:
                errors.append(
                    f"{owner!r}: attribute {name!r} is a reserved key — pick another name"
                )
            elif name in codes:
                errors.append(f"{owner!r}: attribute {name!r} is also a field code on this type")
    for owner, pinned in PINNED_ROSTER_ATTRIBUTES.items():
        ts = items.get(owner)
        if ts is None:
            continue
        for name, kind in pinned.items():
            declared = ts.attributes.get(name)
            if declared is None or declared.kind != kind:
                errors.append(
                    f"roster type {owner!r} must declare attribute {name!r} with kind {kind!r} "
                    f'— add `{name} = {{ kind = "{kind}" }}` under [items.{owner}.attributes]'
                )


def check_field_collections(
    items: dict[str, ItemSpec],
    subentity_kinds: dict[str, SubentityKindSpec],
    collections: dict[str, Collection],
    errors: list[str],
) -> None:
    """Every field's collection resolves; every default badge code (field- or
    collection-level) names a badge in that collection; a required field with no
    resolvable default is rejected."""
    for code, coll in collections.items():
        if not coll.ordered:
            # Ordered-only for now: the flag stays in the schema for a future unordered kind, but
            # nothing downstream (sort, --min-<field>) reads it, so accepting ordered=false would
            # rank badges by declaration order silently. Fail closed.
            errors.append(f"collection {code!r}: unordered collections are not supported yet")
        if coll.default is not None and coll.default not in coll.badge_codes:
            errors.append(f"collection {code!r}: default {coll.default!r} not a declared badge")

    for owner, _is_item, fields in _iter_field_owners(items, subentity_kinds):
        for f in fields:
            coll = collections.get(f.collection)
            if coll is None:
                errors.append(
                    f"{owner!r} field {f.code!r}: collection {f.collection!r} not declared"
                )
                continue
            if f.default is not None and f.default not in coll.badge_codes:
                errors.append(
                    f"{owner!r} field {f.code!r}: default {f.default!r} not a badge in "
                    f"collection {f.collection!r}"
                )
            if f.required:
                resolved = f.default or coll.default
                if resolved is None or resolved not in coll.badge_codes:
                    errors.append(
                        f"{owner!r} field {f.code!r}: required with no resolvable default "
                        f"badge in collection {f.collection!r}"
                    )


def _check_view_source(
    tag: str,
    src: ViewSource,
    items: dict[str, ItemSpec],
    subentity_kinds: dict[str, SubentityKindSpec],
    ref_kinds: dict[str, RefKindSpec],
    errors: list[str],
) -> None:
    """Refuse *src* when its ``name`` doesn't resolve against the vocabulary its ``kind``
    points at — a view declares only ``source``, and this is the one referential check that
    declaration needs (see :func:`check_views`)."""
    if src.kind == "ref":
        if src.name is None or src.name not in ref_kinds:
            errors.append(f"{tag}: source names ref kind {src.name!r}, not declared in [ref_kinds]")
        return
    if src.kind == "subentity":
        if src.name is None or src.name not in subentity_kinds:
            errors.append(
                f"{tag}: source names sub-entity kind {src.name!r}, not declared in "
                "[subentity_kinds]"
            )
        return
    if src.kind == "subtree":
        if src.name is None or src.name not in items:
            errors.append(f"{tag}: source names item type {src.name!r}, not declared in [items]")
        return
    if src.kind in ("role", "self"):
        if src.name is not None:
            errors.append(f"{tag}: a {src.kind!r} source takes no name (got {src.name!r})")
        return
    # "playbook" — name is optional; when given it must resolve like a subtree's does
    if src.name is not None and src.name not in items:
        errors.append(f"{tag}: source names item type {src.name!r}, not declared in [items]")


def check_views(
    views: dict[str, ViewSpec],
    items: dict[str, ItemSpec],
    subentity_kinds: dict[str, SubentityKindSpec],
    ref_kinds: dict[str, RefKindSpec],
    errors: list[str],
) -> None:
    """Referential floor over ``[views]``, run on the merged mapping so ``sq workflow lint`` reports
    a broken view with every other violation in one pass. A view's ``source.name`` must name a
    declared entry of the vocabulary its ``source.kind`` points at
    (``[ref_kinds]``/``[subentity_kinds]``/``[items]``; ``role``/``self`` take none, ``playbook``'s
    is optional), as ``_parse_ref_rules`` does for kinds, so a source that can never resolve is
    refused. In the same pass (not via ``ViewSpec``'s pydantic validation, which would abort at the
    first) the view's key must be a bare TOML key (:data:`_BARE_TOML_KEY_RE`) other than
    :data:`RESERVED_VIEW_NAME`, and its ``position`` must parse (:func:`parse_view_position`).
    """
    for name, v in sorted(views.items()):
        tag = f"view {name!r}"
        if name == RESERVED_VIEW_NAME or not _BARE_TOML_KEY_RE.fullmatch(name):
            errors.append(
                f"{tag}: not a bare TOML key other than {RESERVED_VIEW_NAME!r} — a view name "
                "must match [A-Za-z0-9_-]+ and must not be 'end' (the disabled-state suffix is "
                "colon-delimited, and `sq:view:end` would spell a close marker)"
            )
        try:
            parse_view_position(v.position)
        except ValueError as exc:
            errors.append(f"{tag}: invalid position {v.position!r}: {exc}")
        _check_view_source(tag, v.source, items, subentity_kinds, ref_kinds, errors)
        if v.transform is not None:
            errors.extend(f"{tag}: {problem}" for problem in view_transform_problems(v.transform))


def view_transform_problems(transform: ViewTransform) -> list[str]:
    """Every shape defect of *transform*, none when it is well formed. Pure string checks: no
    file is opened and nothing is imported."""
    problems: list[str] = []
    if (transform.module is None) == (transform.path is None):
        problems.append("transform takes exactly one of `module` or `path`")
    if not transform.function.isidentifier() or keyword.iskeyword(transform.function):
        problems.append(f"transform function {transform.function!r} is not an identifier")
    if transform.module is not None and not _TRANSFORM_MODULE_RE.fullmatch(transform.module):
        problems.append(
            f"transform module {transform.module!r} is not a dotted identifier under `squads.`"
        )
    if transform.path is not None:
        problems.extend(_transform_path_problems(transform.path))
    return problems


#: ``squads.`` followed by one or more dotted identifier segments.
_TRANSFORM_MODULE_RE = re_compile(r"^squads(\.[A-Za-z_][A-Za-z0-9_]*)+$")


def _transform_path_problems(path: str) -> list[str]:
    problems: list[str] = []
    if any(ord(c) < 32 or ord(c) == 127 for c in path):
        problems.append(f"transform path {path!r} must not contain control characters")
    elif "\\" in path or path.startswith("/") or re.match(r"^[A-Za-z]:", path):
        problems.append(f"transform path {path!r} must be a relative POSIX path")
    elif ".." in path.split("/"):
        problems.append(f"transform path {path!r} must not contain a `..` segment")
    if not path.endswith(".py"):
        problems.append(f"transform path {path!r} must end in `.py`")
    return problems


def subentity_source_reason(
    view_name: str, item_type: str, kind: str | None, items: dict[str, ItemSpec]
) -> str | None:
    """``None`` when *item_type*'s own declared sub-entity kind is *kind* — the type genuinely
    hosts sub-entities of that kind — else the reason it doesn't. The one place this
    question is composed: ``squads._views._subentity_source_applies`` (the read-time predicate,
    imported from there — ``_views`` sits above this module in the layering, so the edge runs
    one way only) calls this rather than independently wording the same comparison."""
    ts = items.get(item_type)
    hosted = ts.subentity_kind if ts else None
    if hosted == kind:
        return None
    hosted_desc = repr(hosted) if hosted else "none"
    return (
        f"view {view_name!r} sources {kind!r} sub-entities, but a {item_type!r} item hosts "
        f"{hosted_desc}"
    )


#: A TOML bare key (``[A-Za-z0-9_-]+``) — what every ``[ref_kinds]`` entry's own key must
#: satisfy so it stays splat-ref addressable; also rules out the wire ref
#: separator ``:`` (``split_ref`` partitions on it, ``_models/_item.py``) without a second check.
_BARE_TOML_KEY_RE = re_compile(r"^[A-Za-z0-9_-]+$")


def check_ref_kinds_floor(ref_kinds: dict[str, RefKindSpec], errors: list[str]) -> None:
    """The per-capability floor over ``[ref_kinds]`` (with the ``default`` role), checked on the
    merged mapping so a violation is an ordinary ``_build_spec`` finding visible to ``sq workflow
    lint``, not only at first use in an accessor, which keeps lint and a mutating command in
    agreement. Every key must be a bare TOML key. Exactly one kind has ``role = "default"`` (a bare
    ``"ID"`` ref is undecodable otherwise) and exactly one ``role = "preload"`` (zero strands custom
    skills, two make the inversion ambiguous). At most one kind per ``dependency`` direction
    (``"blocker"``/``"dependent"``; zero is legal, two make normalisation ambiguous), and a
    ``dependency`` kind with no direction is refused as it would resolve through neither.
    ``supersession`` has no bound or floor, as the validators read the full declared set.
    """
    errors.extend(
        f"ref_kinds {code!r}: not a bare TOML key (must match [A-Za-z0-9_-]+) — this keeps "
        "every kind splat-ref addressable and rules out the wire ref separator ':'"
        for code in sorted(ref_kinds)
        if not _BARE_TOML_KEY_RE.fullmatch(code)
    )

    defaults = sorted(k for k, ks in ref_kinds.items() if ks.role == "default")
    if len(defaults) != 1:
        errors.append(
            "the workflow spec must declare exactly one ref kind with role = 'default' "
            f"(a bare ref decodes to it); found {len(defaults)}: {defaults}"
        )

    preloads = sorted(k for k, ks in ref_kinds.items() if ks.role == "preload")
    if len(preloads) != 1:
        errors.append(
            "the workflow spec must declare exactly one ref kind with role = 'preload' "
            f"(a skill's forward edge to the role that preloads it); found {len(preloads)}: "
            f"{preloads}"
        )

    stray = sorted(
        k for k, ks in ref_kinds.items() if ks.role == "dependency" and ks.direction is None
    )
    if stray:
        errors.append(
            f"ref_kinds {stray}: role = 'dependency' requires a 'direction' of 'blocker' or "
            "'dependent'"
        )
    for direction in ("blocker", "dependent"):
        claimants = sorted(
            k
            for k, ks in ref_kinds.items()
            if ks.role == "dependency" and ks.direction == direction
        )
        if len(claimants) > 1:
            errors.append(
                f"the workflow spec declares {len(claimants)} ref kinds with role = "
                f"'dependency' and direction = {direction!r}; at most one is allowed: {claimants}"
            )


assert CLAUSE_GUARDED | frozenset(COMMON_CORE) | UNGUARDED_VALIDATOR_NAMES == VALIDATOR_NAMES, (
    "every validator must be guarded by a consistency clause, common-core, or named unguarded"
)
