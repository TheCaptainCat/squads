"""The validator name registries: which per-item and squad-global checks exist, their default
levels and floors, the bundles each item category selects, and the grammar of a validator
selection entry (``name``, ``name:param``, ``name@level``, ``name:param@level``).

Names only, no check logic: the checks themselves live in ``squads._services._validators`` and the
load-time validity rules in :mod:`squads._workflow._validity`.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from squads._workflow._models import ItemSpec


#: The closed per-item validator NAME catalog — the vocabulary half of the pluggable-validator
#: decision. Behaviour (the actual check functions) lives high, in
#: ``_services/_validators.py::CATALOG``, which asserts ``set(CATALOG) == VALIDATOR_NAMES`` at
#: import time so impl can never drift from this declared contract. Living here (not in
#: ``_services``) lets ``WorkflowSpec._validate``'s Plane-1 catalog-membership check read the
#: valid names without ``_workflow`` importing up into ``_services`` (an inverted, cyclic edge).
VALIDATOR_NAMES: frozenset[str] = frozenset(
    {
        "parent_in",
        "no_parent",
        "parent_present",
        "parent_acyclic",
        "item_status_valid",
        "dangling_ref",
        "ref_kind_valid",
        "agent_registered",
        "subtask_story_mapping",
        "subentity_status_valid",
        "subentity_container_marker",
        "subentity_body_written",
        "subentity_title_max",
        "subentity_deferral_resolved",
        "subentities_settled_with_parent",
        "no_status_banner",
        "supersedes_incoming",
        "ref_rule_target_present",
        "item_skill_shadowed",
        "item_title_max",
        "ref_rule_target_typed",
        "body_written",
        "description_present",
        "assignee_present",
        "blocked_has_blocker",
        "settled_requires_discussion",
        "external_id_not_in_title",
        "attribute_valid",
        "frontmatter_key_undeclared",
        "pronouns_valid",
    }
)


#: The closed squad-global validator NAME catalog (``_services/_validators.py::
#: SQUAD_GLOBAL_CATALOG``) — whole-squad checks that run once per ``sq check``/gate
#: invocation, independent of any type's ``category``.
SQUAD_GLOBAL_VALIDATOR_NAMES: frozenset[str] = frozenset(
    {
        "index_reconciled",
        "backend_reconciled",
        "roster_config_integrity",
        "default_designation_duplicated",
        "roster_slug_valid",
        "playbook_guide_role_live",
        "display_config_valid",
        "working_language_valid",
        "view_transform_resolves",
        "type_has_live_author",
        "children_settled_with_parent",
        "dependency_acyclic",
        "wip_limit",
        "unassigned_active",
        "stale_active",
    }
)


#: The squad-global members that run in every squad and cannot be named in ``[squad]
#: validators``: a defect in any squad, not a policy a squad chooses.
ALWAYS_ON_SQUAD_GLOBAL_NAMES: frozenset[str] = frozenset(
    {
        "index_reconciled",
        "backend_reconciled",
        "roster_config_integrity",
        "default_designation_duplicated",
        "roster_slug_valid",
        "playbook_guide_role_live",
        "display_config_valid",
        "working_language_valid",
        "view_transform_resolves",
    }
)


#: The squad-global members a squad selects in ``[squad] validators``.
SELECTABLE_SQUAD_GLOBAL_NAMES: frozenset[str] = frozenset(
    {
        "type_has_live_author",
        "children_settled_with_parent",
        "dependency_acyclic",
        "wip_limit",
        "unassigned_active",
        "stale_active",
    }
)


#: Each squad-global member's default level, read by ``_services/_validators.py`` through one
#: resolver; a selection's ``@<level>`` overrides it. At this scope a level changes only
#: ``sq check``'s exit code, since squad-global members never run at the create/update gate.
DEFAULT_SQUAD_GLOBAL_LEVEL: dict[str, str] = {
    "index_reconciled": "error",
    "backend_reconciled": "error",
    "roster_config_integrity": "error",
    "default_designation_duplicated": "error",
    "roster_slug_valid": "error",
    "playbook_guide_role_live": "warn",
    "display_config_valid": "warn",
    "working_language_valid": "warn",
    "view_transform_resolves": "error",
    "type_has_live_author": "warn",
    "children_settled_with_parent": "warn",
    "dependency_acyclic": "warn",
    "wip_limit": "warn",
    "unassigned_active": "warn",
    "stale_active": "warn",
}


#: The selectable members that take a required ``:<n>`` parameter, and the least value each
#: accepts: ``wip_limit`` and ``stale_active`` need a positive number, while
#: ``unassigned_active:0`` ("any unassigned active item") is meaningful.
SQUAD_GLOBAL_PARAM_MINIMUM: dict[str, int] = {
    "wip_limit": 1,
    "unassigned_active": 0,
    "stale_active": 1,
}


#: The selectable members that only make sense where an item can be active: a work-category
#: type whose lifecycle holds a status of a live role.
ACTIVE_ITEM_SQUAD_GLOBAL_NAMES: frozenset[str] = frozenset(
    {"wip_limit", "unassigned_active", "stale_active"}
)


#: Validator names that legitimately carry a ``:<param>`` suffix, each read back by the
#: validator itself from the type's own ``validators`` entries — the dispatch engine strips the
#: suffix before the catalog lookup (``ValidatorEngine._run_per_item``), same as every other
#: name. ``subentity_title_max``'s param is its title-length threshold
#: (``WorkflowSpec.item_subentity_title_max``); ``ref_rule_target_present``'s is the item type
#: it selects an obligation for (``_services/_validators.py::_ref_rule_target_present``);
#: ``item_title_max``'s is its title-length threshold and ``external_id_not_in_title``'s a
#: regular expression (``WorkflowSpec.item_title_max``/``item_external_id_pattern``).
PARAMETERIZED_VALIDATOR_NAMES: frozenset[str] = frozenset(
    {"subentity_title_max", "ref_rule_target_present", "item_title_max", "external_id_not_in_title"}
)


#: The subset of :data:`PARAMETERIZED_VALIDATOR_NAMES` whose own runtime resolver **unions**
#: every matching entry it finds in a type's own ``validators`` list — so two entries naming
#: *different* params are independent, additive selections (one obligation per param), not a
#: repeat. ``ref_rule_target_present`` is the only member with this property today: its
#: ``targets`` set (``_services/_validators.py::_ref_rule_target_present``) is built from a
#: comprehension over every matching entry.
#:
#: "Is parameterized" and "accepts multiple selections" are two different properties — a name
#: can take a ``:<param>`` and still resolve to exactly one effective value (see
#: :data:`SINGLE_SELECTION_VALIDATOR_NAMES`). Keying the duplicate-selection identity
#: (:func:`validator_selection_key`) on parameterization alone conflates the two; this set is
#: the declared answer to the question that conflation skipped.
MULTI_SELECTION_VALIDATOR_NAMES: frozenset[str] = frozenset({"ref_rule_target_present"})


#: The complement within :data:`PARAMETERIZED_VALIDATOR_NAMES`: a member whose own resolver
#: returns on the **first** matching entry it finds rather than unioning every one —
#: ``subentity_title_max``'s is ``WorkflowSpec.item_subentity_title_max``, first match, single
#: value. A second, differently-parameterised entry of one of these names is therefore not an
#: independent selection: nothing decides which value the resolver would have picked instead,
#: so it is refused at Plane-1 the same as a same-param repeat — the alternative is a second
#: entry that loads clean and does nothing, forever, which is exactly what
#: :func:`_check_ref_rule_targets` refuses on principle for its own member ("refused here rather
#: than silently doing nothing forever").
SINGLE_SELECTION_VALIDATOR_NAMES: frozenset[str] = frozenset(
    {"subentity_title_max", "item_title_max", "external_id_not_in_title"}
)


#: The opt-in per-item policy checks about the work an item tracks. A type of the ``roster``
#: category (a role, a skill, an operator) is configuration, not tracked work, so naming one of
#: these on it is refused at load by :func:`_check_selections_that_cannot_fire` instead of
#: loading and reporting every roster entry.
WORK_POLICY_VALIDATOR_NAMES: frozenset[str] = frozenset(
    {
        "item_title_max",
        "ref_rule_target_typed",
        "body_written",
        "description_present",
        "assignee_present",
        "blocked_has_blocker",
        "settled_requires_discussion",
        "external_id_not_in_title",
    }
)


#: Members whose ``:<param>`` is required: a bare entry loads nothing to check, so it is refused
#: at load (:func:`_check_validator_param`) rather than selecting a check that never fires.
REQUIRED_PARAM_VALIDATOR_NAMES: frozenset[str] = frozenset(
    {"item_title_max", "external_id_not_in_title"}
)


#: The two levels a validator finding may carry — matches :class:`~squads._services._results.
#: CheckIssue`'s own closed ``level`` contract (``"error"`` aborts create/update at the gate;
#: ``"warn"`` is advisory everywhere, mirroring ``sq check``'s error-only exit code). A
#: selection's ``@<level>`` suffix (see :func:`parse_validator_entry`) is Plane-1-checked
#: against this set, so an adopter cannot invent a third severity the rest of the engine has no
#: meaning for.
VALIDATOR_LEVELS: frozenset[str] = frozenset({"error", "warn"})


#: Total order over :data:`VALIDATOR_LEVELS`, low to high — the comparison
#: :data:`VALIDATOR_LEVEL_FLOOR` needs to tell "raise" from "lower". Not exposed beyond this
#: module: every external caller asks a yes/no question (does this selection clear the floor),
#: never a rank.
LEVEL_RANK: dict[str, int] = {"warn": 0, "error": 1}


#: The separator between a validator name (with its optional ``:<param>``) and an optional
#: declared level. ``@`` rather than a second ``:`` — ``:`` is already the param separator, and
#: reusing it would make ``name:param:level`` ambiguous about which half is which. ``@`` cannot
#: appear in a validator name (plain identifiers) or in a title-length threshold (an integer,
#: enforced by :func:`_check_validator_param`), is refused in an ``external_id_not_in_title``
#: pattern (a literal ``@`` is written ``\x40``), and it is a different namespace from
#: the unrelated place a bare ``@`` already means something in this codebase (an ``@mention``
#: inside discussion prose — comment text, never spec vocabulary).
#:
#: It is **not** ruled out of ``ref_rule_target_present``'s own param, an item-type name:
#: unlike a ``[ref_kinds]`` key (:data:`_BARE_TOML_KEY_RE`), nothing restricts an
#: ``[items.<type>]`` TOML key's character set. A type declared with ``@`` in its own name
#: would mis-split when selected as a target — :func:`parse_validator_entry` cuts on the first
#: ``@`` regardless of which half it came from, so the piece after it is read as the level and
#: refused at Plane-1 as an unknown level rather than as the intended (but wrong) target type.
#: Fails closed, with a message naming the wrong half of the entry.
_LEVEL_SEP = "@"


_PARAM_SEP = ":"


def parse_validator_entry(entry: str) -> tuple[str, str | None, str | None]:
    """Split one ``validators``-list *entry* into ``(bare name, param, level)`` — the single
    parser every consumer of the assignment grammar (Plane-1 validation, the effective-set
    composition, the dispatch engine's catalog lookup, and a parameterised validator reading
    its own argument back) uses, so the grammar is defined once rather than re-partitioned at
    each call site with room for the definitions to disagree.

    Grammar, in the one order this parses: ``name``, ``name:param``, ``name@level``, or
    ``name:param@level`` — a param, when present, always precedes a level. The level is split
    off first (rightmost-meaningful cut, via the first ``@``), then a param is split off the
    remainder. A reversed composition (``name@level:param``) does not parse as intended: the
    ``:`` lands inside what this function treats as the level string, which is not a member of
    :data:`VALIDATOR_LEVELS`, so it fails the Plane-1 level check with a clear message rather
    than silently accepting an unintended parameter.
    """
    head, has_level, level_part = entry.partition(_LEVEL_SEP)
    level = level_part if has_level else None
    bare, has_param, param_part = head.partition(_PARAM_SEP)
    param = param_part if has_param else None
    return bare, param, level


def validator_selection_key(entry: str) -> tuple[str, str | None]:
    """The de-duplication identity of one ``validators``-list *entry* — what makes two entries
    "the same selection" rather than two different ones. Used identically by
    :func:`_check_validators_assignment`'s repeat-selection refusal and by
    :func:`effective_validator_names`'s composition, so both agree on what counts as a
    duplicate.

    A member in :data:`MULTI_SELECTION_VALIDATOR_NAMES` is keyed on its bare name *and* its
    param: its runtime (e.g. ``_ref_rule_target_present``) unions every matching entry it
    finds in a type's own list, so two entries naming different params are independent,
    additive selections — one target type each — not a repeat. Two entries naming the *same*
    param are a genuine duplicate (nothing decides which one "wins").

    Any other member — a non-parameterized name, a parameterized one selected with no param,
    or a :data:`SINGLE_SELECTION_VALIDATOR_NAMES` member (param or not) — is keyed on its bare
    name alone: nothing besides the name distinguishes two entries of it, so a repeat is always
    a duplicate regardless of a differing param or ``@<level>`` suffix. This is the property
    that keeps ``subentity_title_max:50`` and ``subentity_title_max:80`` on one type a refused
    duplicate rather than two selections whose second silently never resolves — see
    :data:`SINGLE_SELECTION_VALIDATOR_NAMES`.
    """
    bare, param, _level = parse_validator_entry(entry)
    if bare in MULTI_SELECTION_VALIDATOR_NAMES and param is not None:
        return bare, param
    return bare, None


#: Each catalog member's bundled default level, read by ``_services/_validators.py`` instead of
#: a level literal inline in the member's own ``CheckIssue(...)`` calls — the single place that
#: number lives, so a member's default cannot say one thing here and do another at runtime.
#: Lives in the spec layer for the same reason :data:`VALIDATOR_NAMES` does: a selection's
#: ``@<level>`` override is Plane-1-validated against it (and against
#: :data:`VALIDATOR_LEVEL_FLOOR` below) without ``_workflow`` importing up into ``_services``.
DEFAULT_VALIDATOR_LEVEL: dict[str, str] = {
    "parent_in": "error",
    "no_parent": "error",
    "parent_present": "error",
    "parent_acyclic": "error",
    "item_status_valid": "error",
    "dangling_ref": "warn",
    "ref_kind_valid": "warn",
    "agent_registered": "warn",
    "subtask_story_mapping": "error",
    "subentity_status_valid": "error",
    "subentity_container_marker": "error",
    "subentity_body_written": "warn",
    "subentity_title_max": "warn",
    "subentity_deferral_resolved": "warn",
    "subentities_settled_with_parent": "warn",
    "no_status_banner": "warn",
    "supersedes_incoming": "warn",
    "ref_rule_target_present": "warn",
    "item_skill_shadowed": "warn",
    "item_title_max": "warn",
    "ref_rule_target_typed": "warn",
    "body_written": "warn",
    "description_present": "warn",
    "assignee_present": "warn",
    "blocked_has_blocker": "warn",
    "settled_requires_discussion": "warn",
    "external_id_not_in_title": "warn",
    "attribute_valid": "error",
    "frontmatter_key_undeclared": "warn",
    "pronouns_valid": "error",
}


#: The declared floor: a selection may raise a member's level but never lower it below this,
#: for the members whose level is load-bearing for the *engine's own correctness* rather than a
#: policy preference a project may reasonably decline. Applied with the same placement test that
#: decides catalog placement, one level down: can a competent squad sit in this state on
#: purpose, indefinitely, with nothing else in the engine misbehaving because of it? A "yes"
#: means the member is not floor, however undesirable the state is.
#:
#: Applying that test to every error-level member, only two hold a floor:
#:
#: - ``parent_acyclic``: a parent cycle makes every ancestor/descendant walk in the engine
#:   non-terminating — a live hang reproduced and fixed on its own, not a house convention a
#:   project could decline. Demoted to warn, a project's own choice would let a whole-squad hang
#:   slip past ``sq check``'s exit code, which stays 0 on a warn-only finding.
#: - ``subentity_container_marker``: the corpus/spec desync it reports leaves no witness the
#:   loader, ``sq workflow lint``, or the index can see — its own docstring: ``sq check`` is the
#:   only plane that can. Demoted to warn, ``add-<kind>`` keeps failing on every item of the
#:   type while sub-entity body writes keep succeeding, and the one report able to say why is
#:   silenced by the project's own choice.
#:
#: The rest are NOT load-bearing, each for a reason specific to it rather than a blanket
#: "everything else is fine to dial down":
#:
#: - ``parent_in``/``no_parent``: nothing downstream assumes the constraint already holds in
#:   order to function — no walk or transition depends on parent-type eligibility, only on the
#:   parent existing and the chain terminating (:data:`parent_acyclic`'s own job). A team mid
#:   reorganisation, or one that wants a looser hierarchy than the bundled default, can hold
#:   this state on purpose without anything else in the engine misbehaving.
#: - ``item_status_valid``: flags a status absent from the *type's own* lifecycle graph, not an
#:   undeclared status altogether — badge/role resolution reads the global status catalog, not
#:   the per-type graph, so rendering is unaffected. The engine already ships a designed
#:   recovery for exactly this state: an ordinary status update's ``--force`` short-circuits the
#:   transition-table lookup and only re-checks target-vocabulary membership, so an item outside
#:   its lifecycle graph is one recognised, documented escape away rather than genuinely stuck —
#:   unlike a parent cycle, which has no equivalent designed recovery short of clearing the
#:   parent.
#: - ``subtask_story_mapping``: an unresolved mapping affects grouping/rollup display only;
#:   nothing gates or walks on it resolving, and it is visible wherever the mapping is rendered
#:   rather than invisible the way the container-marker desync is.
#: - ``subentity_status_valid``: the same shape and the same reasoning as
#:   ``item_status_valid``, one level down — the sub-entity status-update path documents the
#:   identical designed-recovery property in its own code: the vocabulary gate runs first and
#:   unconditionally, so a sub-entity already carrying a non-member status stays recoverable
#:   regardless of ``--force``.
#:
#: ``parent_present`` is deliberately absent and must stay absent: it sits in no
#: :data:`CATEGORY_BUNDLES` entry at all, so the only way it is ever effective is a type naming
#: it — its level, not its rule, is what a project dials, and a floor here would defeat the
#: entire point of making it selectable at warn.
VALIDATOR_LEVEL_FLOOR: dict[str, str] = {
    "parent_acyclic": "error",
    "subentity_container_marker": "error",
}


#: Per-item validators every type runs regardless of category — cross-cutting item hygiene.
#: Lives here rather than in ``_services`` for the same reason :data:`VALIDATOR_NAMES` does:
#: the Plane-1 spec-validity pass below has to resolve a type's *effective* validator set to
#: check that its declared capability fields are reachable at all, and ``_workflow`` must not
#: import up into ``_services``. ``_services/_validators.py`` reads these names from here,
#: so there is one definition of what a category turns on.
COMMON_CORE: tuple[str, ...] = (
    "item_status_valid",
    "dangling_ref",
    "ref_kind_valid",
    "agent_registered",
    "parent_acyclic",
    "attribute_valid",
)


#: Per-category default per-item validator-name bundle — the category's *behaviour*, since
#: nothing else in the engine branches on ``work`` vs ``records`` (every other category
#: consumer asks only "roster or not"). A type's own ``validators`` list extends this floor and
#: may never subtract from it.
CATEGORY_BUNDLES: dict[str, tuple[str, ...]] = {
    "roster": ("pronouns_valid",),
    "work": (
        "parent_in",
        "subentity_status_valid",
        "subentity_container_marker",
        "subentity_body_written",
        "subentity_deferral_resolved",
        "subtask_story_mapping",
    ),
    "records": ("no_parent", "supersedes_incoming"),
}


#: The validators whose subject is a type's declared ``subentity_kind``. A type that declares a
#: kind but whose effective set holds none of these has declared sub-entities nothing can check
#: — see :func:`_check_category_consistency`. ``subentity_title_max`` is a member although no
#: bundle supplies it: a hosting type may satisfy the clause by naming it alone.
#: ``subtask_story_mapping`` is deliberately absent: it is specific to one kind's
#: ``maps_parent_story`` capability, not to hosting a kind at all, so it is guarded by its own
#: clause (:func:`_clause_story_mapping_reachable`) instead.
SUBENTITY_VALIDATOR_NAMES: frozenset[str] = frozenset(
    {
        "subentity_status_valid",
        "subentity_container_marker",
        "subentity_body_written",
        "subentity_title_max",
        "subentity_deferral_resolved",
    }
)


def effective_validator_names(
    category: str,
    *,
    common_core: tuple[str, ...] = COMMON_CORE,
    category_bundles: dict[str, tuple[str, ...]] | None = None,
    extra: tuple[str, ...] = (),
) -> tuple[str, ...]:
    """A type's effective per-item validator-name set: common core + its category's default
    bundle + its own additions (the "extend-only floor" — a type may add to a bundle, never
    subtract from it).

    *extra* is the per-type ``ItemSpec.validators`` field (the assignment surface) —
    ``_run_per_item`` passes the item's own list; every other caller defaults to none.

    De-duplicated by :func:`validator_selection_key`, last occurrence of a given key winning —
    the same "same selection, not same bare name" identity :func:`_check_validators_assignment`
    refuses a repeat of. *common_core* and *category_bundles* entries are always bare (module
    constants, never carrying a ``:<param>``/``@<level>`` suffix, so their key is always
    ``(bare, None)``); the ordinary way a key recurs is a type naming an already-bundled member
    in its own *extra* with a suffix and no param — e.g. ``subentity_body_written@error`` overriding
    the level of a category's bare ``subentity_body_written`` — and keeping only the last occurrence
    makes that override the member's one authoritative entry instead of running it twice under
    two spellings of the same name. A type's own *extra* naming a
    :data:`MULTI_SELECTION_VALIDATOR_NAMES` member with two *different* params (e.g.
    ``ref_rule_target_present:contract`` and ``ref_rule_target_present:milestone``) keys
    differently for each and both survive as independent selections; the dispatch engine
    (``ValidatorEngine._run_per_item``) still calls the member's catalog function only once per
    bare name regardless, since this member's own resolver unions every one of its own entries
    back off the spec itself rather than off what survived here. A
    :data:`SINGLE_SELECTION_VALIDATOR_NAMES` member (``subentity_title_max``) keys on its bare
    name alone no matter the param, so it never reaches this function with two surviving
    entries in the first place — :func:`_check_validators_assignment` refuses a second,
    differently-parameterised entry outright, because that member's own resolver reads only its
    first matching entry rather than unioning. Keeping the *first*-seen key's position is what
    "extend-only" still means positionally — a type's own addition cannot reorder what the
    bundle already turned on.

    Parameterised on *common_core*/*category_bundles* — not hardcoded to the module
    constants — so a caller (or a test) can exercise the composition against a stub bundle.
    *category_bundles* defaults to ``None`` (resolved to the module-level
    :data:`CATEGORY_BUNDLES` below) rather than binding the mutable dict itself as a parameter
    default.
    """
    bundles = category_bundles if category_bundles is not None else CATEGORY_BUNDLES
    combined = common_core + bundles.get(category, ()) + extra
    resolved = {validator_selection_key(name): name for name in combined}
    key_order = dict.fromkeys(validator_selection_key(name) for name in combined)
    return tuple(resolved[key] for key in key_order)


def parse_positive_int(text: str) -> int | None:
    """*text* as a positive integer, or ``None``. ASCII decimal digits only: ``str.isdigit`` is
    also true for characters such as a superscript digit that ``int`` refuses."""
    if not (text.isascii() and text.isdigit()):
        return None
    value = int(text)
    return value if value > 0 else None


def parse_non_negative_int(text: str) -> int | None:
    """*text* as an integer of at least zero, or ``None``; ASCII decimal digits only."""
    return int(text) if text.isascii() and text.isdigit() else None


def effective_bare_validators(ts: ItemSpec) -> frozenset[str]:
    """A type's effective validator names, bare (a ``:<param>``/``@<level>`` suffix stripped)."""
    names = effective_validator_names(ts.category, extra=tuple(ts.validators))
    return frozenset(parse_validator_entry(name)[0] for name in names)


assert ALWAYS_ON_SQUAD_GLOBAL_NAMES.isdisjoint(SELECTABLE_SQUAD_GLOBAL_NAMES), (
    "a squad-global member is either always-on or selectable, never both"
)
assert (
    ALWAYS_ON_SQUAD_GLOBAL_NAMES | SELECTABLE_SQUAD_GLOBAL_NAMES == SQUAD_GLOBAL_VALIDATOR_NAMES
), "every squad-global member must be placed in exactly one of always on or opt-in"
assert SQUAD_GLOBAL_VALIDATOR_NAMES.isdisjoint(VALIDATOR_NAMES), (
    "a name cannot be both a per-item and a squad-global validator"
)
assert set(DEFAULT_SQUAD_GLOBAL_LEVEL) == SQUAD_GLOBAL_VALIDATOR_NAMES, (
    "DEFAULT_SQUAD_GLOBAL_LEVEL must declare exactly one default per squad-global member"
)
assert (
    MULTI_SELECTION_VALIDATOR_NAMES | SINGLE_SELECTION_VALIDATOR_NAMES
) == PARAMETERIZED_VALIDATOR_NAMES, (
    "every PARAMETERIZED_VALIDATOR_NAMES member must be classified into exactly one of "
    "MULTI_SELECTION_VALIDATOR_NAMES or SINGLE_SELECTION_VALIDATOR_NAMES — a new parameterized "
    "member added to one catalog without a place in the other fails this assert instead of "
    "silently inheriting either behaviour"
)
assert MULTI_SELECTION_VALIDATOR_NAMES.isdisjoint(SINGLE_SELECTION_VALIDATOR_NAMES), (
    "MULTI_SELECTION_VALIDATOR_NAMES and SINGLE_SELECTION_VALIDATOR_NAMES must not overlap — "
    "a member cannot be both first-match and unioning"
)
assert set(DEFAULT_VALIDATOR_LEVEL) == VALIDATOR_NAMES, (
    "DEFAULT_VALIDATOR_LEVEL must declare exactly one bundled default per VALIDATOR_NAMES member"
)
assert set(DEFAULT_VALIDATOR_LEVEL.values()) <= VALIDATOR_LEVELS, (
    "DEFAULT_VALIDATOR_LEVEL values must each be a declared level"
)
assert VALIDATOR_LEVEL_FLOOR.keys() <= VALIDATOR_NAMES, (
    "VALIDATOR_LEVEL_FLOOR must only name declared VALIDATOR_NAMES members"
)
assert set(VALIDATOR_LEVEL_FLOOR.values()) <= VALIDATOR_LEVELS, (
    "VALIDATOR_LEVEL_FLOOR values must each be a declared level"
)
assert "parent_present" not in VALIDATOR_LEVEL_FLOOR, (
    "parent_present must carry no floor — its level, not its rule, is what makes it "
    "selectable at warn"
)
