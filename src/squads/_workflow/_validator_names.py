"""The validator name registries: which per-item and squad-global checks exist, their default
levels and floors, the bundles each item category selects, and the grammar of a validator
selection entry (``name``, ``name:param``, ``name@level``, ``name:param@level``).

Names only, no check logic: the checks themselves live in ``squads._services._validators`` and the
load-time validity rules in :mod:`squads._workflow._validity`.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from squads._workflow._models import ItemSpec


#: The closed per-item validator NAME catalog, the vocabulary half of the pluggable-validator
#: design. The check functions live in ``_services/_validators.py::CATALOG``, which asserts
#: ``set(CATALOG) == VALIDATOR_NAMES`` at import so they cannot drift. It lives here so
#: ``WorkflowSpec._validate``'s Plane-1 membership check reads the names without ``_workflow``
#: importing up into ``_services``.
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
        "subentity_mapping",
        "subentity_status_valid",
        "subentity_container_marker",
        "subentity_body_written",
        "subentity_title_present",
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
        "subentity_kind_mismatch",
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
        "role_base_resolves",
        "role_definition_shadowed",
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
        "role_base_resolves",
        "role_definition_shadowed",
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
    "role_base_resolves": "error",
    "role_definition_shadowed": "warn",
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


#: Validator names that carry a ``:<param>`` suffix, each read back by the validator itself from the
#: type's ``validators`` entries (dispatch strips the suffix before the catalog lookup, as for every
#: name): a title-length threshold for ``subentity_title_max`` and ``item_title_max``, the item type
#: for ``ref_rule_target_present``, a regular expression for ``external_id_not_in_title``.
PARAMETERIZED_VALIDATOR_NAMES: frozenset[str] = frozenset(
    {"subentity_title_max", "ref_rule_target_present", "item_title_max", "external_id_not_in_title"}
)


#: The subset of :data:`PARAMETERIZED_VALIDATOR_NAMES` whose resolver unions every matching entry in
#: a type's ``validators`` list, so entries with different params are independent additive
#: selections, not a repeat; today only ``ref_rule_target_present``. "Parameterized" and "accepts
#: multiple selections" differ (see :data:`SINGLE_SELECTION_VALIDATOR_NAMES`), which keying
#: :func:`validator_selection_key` on parameterization alone would conflate.
MULTI_SELECTION_VALIDATOR_NAMES: frozenset[str] = frozenset({"ref_rule_target_present"})


#: The complement within :data:`PARAMETERIZED_VALIDATOR_NAMES`: a member whose resolver returns the
#: first matching entry (``subentity_title_max``, via ``WorkflowSpec.item_subentity_title_max``). A
#: second, differently-parameterised entry is not an independent selection, as nothing picks which
#: value applies, so Plane-1 refuses it like a same-param repeat rather than load an entry that does
#: nothing forever (as :func:`check_ref_rule_targets` does for its member).
SINGLE_SELECTION_VALIDATOR_NAMES: frozenset[str] = frozenset(
    {"subentity_title_max", "item_title_max", "external_id_not_in_title"}
)


#: The opt-in per-item policy checks about tracked work. A ``roster``-category type (role, skill,
#: operator) is configuration, not tracked work, so :func:`check_selections_that_cannot_fire`
#: refuses naming one on it at load rather than reporting every roster entry.
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


#: Members whose ``:<param>`` is required, each with the shape its refusal names: a bare entry
#: loads nothing to check, so it is refused at load (:func:`_check_validator_param`) rather than
#: selecting a check that never fires.
REQUIRED_PARAM_SHAPE: dict[str, str] = {
    "item_title_max": "<n>",
    "external_id_not_in_title": "<regex>",
    "ref_rule_target_present": "<type>",
}


#: The names of :data:`REQUIRED_PARAM_SHAPE`.
REQUIRED_PARAM_VALIDATOR_NAMES: frozenset[str] = frozenset(REQUIRED_PARAM_SHAPE)


#: The two levels a finding may carry, matching :class:`~squads._services._results.CheckIssue`'s
#: ``level`` (``"error"`` aborts create/update at the gate, ``"warn"`` is advisory, as ``sq check``
#: exits non-zero on errors only). A selection's ``@<level>`` suffix (:func:`parse_validator_entry`)
#: is checked against this set so no third severity can be invented.
VALIDATOR_LEVELS: frozenset[str] = frozenset({"error", "warn"})


#: Total order over :data:`VALIDATOR_LEVELS`, low to high, which :data:`VALIDATOR_LEVEL_FLOOR` needs
#: to tell "raise" from "lower"; only the Plane-1 level check (``_check_validator_level``) reads
#: it, and other callers ask whether a selection clears the floor, never a rank.
LEVEL_RANK: dict[str, int] = {"warn": 0, "error": 1}


#: The separator between a validator name (with its optional ``:<param>``) and a declared level.
#: It is ``@`` because ``:`` is the param separator and reusing it would make
#: ``name:param:level`` ambiguous; ``@`` cannot appear in a validator name, in a title-length
#: threshold (an integer, :func:`_check_validator_param`) or in an ``external_id_not_in_title``
#: pattern (write ``\x40``).
#:
#: It is not ruled out of ``ref_rule_target_present``'s param, an item-type name, as nothing
#: restricts an ``[items.<type>]`` key's characters. A type named with ``@`` would mis-split,
#: since :func:`parse_validator_entry` cuts on the first ``@``, and fails closed at Plane-1 as an
#: unknown level, naming the wrong half of the entry.
_LEVEL_SEP = "@"


_PARAM_SEP = ":"


def parse_validator_entry(entry: str) -> tuple[str, str | None, str | None]:
    """Split one ``validators``-list *entry* into ``(bare name, param, level)``: the single parser
    every consumer of the grammar uses (Plane-1 validation, effective-set composition, dispatch
    lookup, a validator reading its own argument), so the definitions cannot disagree. The grammar
    is ``name``, ``name:param``, ``name@level`` or ``name:param@level``, the level split off first
    at the first ``@`` and then the param from the remainder. A reversed ``name@level:param`` leaves
    the ``:`` inside the level string, so it fails the Plane-1 level check rather than silently
    accepting a parameter.
    """
    head, has_level, level_part = entry.partition(_LEVEL_SEP)
    level = level_part if has_level else None
    bare, has_param, param_part = head.partition(_PARAM_SEP)
    param = param_part if has_param else None
    return bare, param, level


def validator_selection_key(entry: str) -> tuple[str, str | None]:
    """The de-duplication identity of one ``validators`` entry, used identically by
    :func:`check_validators_assignment`'s repeat refusal and :func:`effective_validator_names`. A
    :data:`MULTI_SELECTION_VALIDATOR_NAMES` member is keyed on bare name and param (different params
    are independent selections; the same param is a duplicate). Any other member, including a
    :data:`SINGLE_SELECTION_VALIDATOR_NAMES` one, is keyed on its bare name alone, so a repeat is a
    duplicate whatever its param or ``@<level>``; that is what makes ``subentity_title_max:50`` plus
    ``:80`` a refusal, not a second selection that never resolves.
    """
    bare, param, _level = parse_validator_entry(entry)
    if bare in MULTI_SELECTION_VALIDATOR_NAMES and param is not None:
        return bare, param
    return bare, None


#: Each catalog member's bundled default level, read by ``_services/_validators.py`` instead of an
#: inline literal in the member's ``CheckIssue(...)`` calls, so the number lives in one place. It
#: sits in the spec layer, like :data:`VALIDATOR_NAMES`, so a selection's ``@<level>`` is
#: Plane-1-validated against it and :data:`VALIDATOR_LEVEL_FLOOR` without ``_workflow`` importing up
#: into ``_services``.
DEFAULT_VALIDATOR_LEVEL: dict[str, str] = {
    "parent_in": "error",
    "no_parent": "error",
    "parent_present": "error",
    "parent_acyclic": "error",
    "item_status_valid": "error",
    "dangling_ref": "warn",
    "ref_kind_valid": "warn",
    "agent_registered": "warn",
    "subentity_mapping": "error",
    "subentity_status_valid": "error",
    "subentity_container_marker": "error",
    "subentity_body_written": "warn",
    "subentity_title_present": "warn",
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
    "subentity_kind_mismatch": "warn",
    "pronouns_valid": "error",
}


#: The declared floor: a selection may raise a member's level but never lower it below this, for
#: members whose level is load-bearing for the engine's own correctness rather than a policy a
#: project may decline. The test: can a competent squad sit in this state indefinitely with
#: nothing else in the engine misbehaving? If so the member is not floor, however undesirable the
#: state.
#:
#: Only two error-level members hold a floor. ``parent_acyclic``: a cycle makes every
#: ancestor/descendant walk non-terminating, and demoted to warn it would let a whole-squad hang
#: pass ``sq check``'s exit code. ``subentity_container_marker``: its corpus/spec desync leaves
#: no witness the loader, ``sq workflow lint`` or the index can see, and demoted, ``add-<kind>``
#: keeps failing on every item of the type while body writes succeed and the one report that
#: explains it is silenced.
#:
#: The rest are not load-bearing. ``parent_in``/``no_parent``: nothing downstream relies on
#: parent-type eligibility, only on the chain terminating. ``item_status_valid``: rendering reads
#: the global status catalog, not the per-type graph, and ``--force`` on a status update is a
#: designed recovery. ``subentity_mapping``: it affects grouping display only and stays
#: visible where rendered. ``subentity_status_valid``: the same as ``item_status_valid``, since
#: the sub-entity vocabulary gate runs first and unconditionally, so a non-member stays
#: recoverable.
#:
#: ``parent_present`` must stay absent: it is in no :data:`CATEGORY_BUNDLES` entry, so it is
#: effective only when a type names it, its level being what a project dials, and a floor would
#: defeat making it selectable at warn.
VALIDATOR_LEVEL_FLOOR: dict[str, str] = {
    "parent_acyclic": "error",
    "subentity_container_marker": "error",
}


#: Per-item validators every type runs regardless of category (cross-cutting hygiene). It lives
#: here, as :data:`VALIDATOR_NAMES` does, because the Plane-1 pass must resolve a type's effective
#: set to check its declared capability fields are reachable and ``_workflow`` must not import up
#: into ``_services``; ``_services/_validators.py`` reads the names from here.
COMMON_CORE: tuple[str, ...] = (
    "item_status_valid",
    "dangling_ref",
    "ref_kind_valid",
    "agent_registered",
    "parent_acyclic",
    "attribute_valid",
)


#: Per-category default validator-name bundle, the category's behaviour (nothing else branches on
#: ``work`` versus ``records``; other consumers ask only "roster or not"). A type's own
#: ``validators`` list extends this floor and never subtracts from it.
CATEGORY_BUNDLES: dict[str, tuple[str, ...]] = {
    "roster": ("pronouns_valid",),
    "work": (
        "parent_in",
        "subentity_status_valid",
        "subentity_container_marker",
        "subentity_body_written",
        "subentity_title_present",
        "subentity_deferral_resolved",
        "subentity_mapping",
        "subentity_kind_mismatch",
    ),
    "records": ("no_parent", "supersedes_incoming"),
}


#: The validators whose subject is a type's declared ``subentity_kind``: a type that declares a kind
#: but whose effective set holds none has sub-entities nothing can check
#: (:func:`check_category_consistency`). ``subentity_title_max`` is a member although no bundle
#: supplies it, so a type may satisfy the clause by naming it alone. ``subentity_mapping`` is
#: absent, as it belongs to one kind's ``maps_to_parent`` capability and has its own clause
#: (:func:`_clause_story_mapping_reachable`).
SUBENTITY_VALIDATOR_NAMES: frozenset[str] = frozenset(
    {
        "subentity_status_valid",
        "subentity_container_marker",
        "subentity_body_written",
        "subentity_title_present",
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
    """A type's effective per-item validator-name set: common core, its category's default bundle
    and its own additions (extend-only: a type may add to a bundle, never subtract). *extra* is the
    per-type ``ItemSpec.validators`` list; *common_core* and *category_bundles* are parameters
    (``None`` meaning :data:`CATEGORY_BUNDLES`) so a test can use a stub bundle.

    It de-duplicates by :func:`validator_selection_key`, the last occurrence of a key winning (so
    ``subentity_body_written@error`` in *extra* overrides a bundle's bare entry's level instead of
    running the member twice) while the first-seen key keeps its position, so an addition cannot
    reorder what the bundle turned on. Two different params on a multi-selection member
    (``ref_rule_target_present:contract`` and ``:milestone``) both survive, and dispatch still calls
    the member once per bare name since its resolver unions its own entries from the spec. A
    single-selection member never arrives with two entries, as :func:`check_validators_assignment`
    refuses a second.
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
