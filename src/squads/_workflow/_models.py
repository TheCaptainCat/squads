"""WorkflowSpec pydantic v2 value objects.

The loaded spec is the sole vocabulary authority for both axes: TOML type keys AND status
keys stay plain ``str`` (no enum coercion, no closed set). The reserved surface is exactly
the three roster types (``ROSTER_TYPES``) plus their fixed ``category = "roster"`` — no
status name is reserved. Instead, engine behaviour that needs lifecycle semantics resolves
through a declared status *role*, never a literal status name: ``WorkflowSpec.live_statuses``/
``live_initial`` are the read/create-target accessors, and a lifecycle bound to a
``category = "roster"`` type must satisfy the additional floor enforced in ``_validate``
(R1 — at least one live status; R1' — if the lifecycle's ``initial`` is not itself live,
exactly one status is live; R2 — at least one settled, non-live status reachable from a
live one).

The capability flags declared here (``category``, ``subentity_kind``, ``parent_required``,
``ref_rules``) are additive; ``SubentityKindSpec.completion`` is consumed by the sub-entity/
finding done-toggle (``_services/_subentities.py``). ``StatusSpec.role`` is the sole explicit
status axis — a reference into the ``RoleSpec`` catalog (``WorkflowSpec.roles``) that carries
``settled``/``hidden``/``color``; ``is_open``/``terminal_set``/``hidden_by_default`` are all
derived from the referenced role, never stored directly. They are encoded in
``workflow.toml``.

``Badge``/``Collection``/``Field`` are the badge-vocabulary schema: ``ItemSpec.fields`` /
``SubentityKindSpec.fields`` bind a type or sub-entity kind to a reusable ``Collection`` of
``Badge``s — "does type/kind X carry field Y" is a ``fields_for(X)`` lookup, replacing the old
closed-set ``Priority``/``Severity`` enums.
"""

import math
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from re import compile as re_compile
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, model_validator

#: The three roster types the engine binds by literal name — the irreducible
#: structural minimum: the roster, the backends (which write role/skill files), and the
#: agent lifecycle genuinely reference these by name. NOT a closed type vocabulary — every
#: other type (built-in or custom) is ordinary, droppable/renamable spec vocabulary.
ROSTER_ROLE = "role"
ROSTER_SKILL = "skill"
ROSTER_OPERATOR = "operator"
ROSTER_TYPES: frozenset[str] = frozenset({ROSTER_ROLE, ROSTER_SKILL, ROSTER_OPERATOR})

#: Top-level CLI verbs a declared item type's name or alias must never collide with — every
#: name here is a Click command registered at ``sq``'s root (``sq <this>``) that is NOT itself
#: derived from an item type, so a type claiming one permanently loses its own `sq <type> <n>
#: <verb>` surface to the built-in (Click dispatches the shorter/first-registered match; the
#: type's item-level verbs — status/update/body/comment/ref/retype/remove — become unreachable,
#: with no traceback, just a clean-looking `sq <type>` running the wrong command).
#:
#: ``role``/``skill``/``operator`` are deliberately NOT in this set: those ARE item types (the
#: fixed roster, ``ROSTER_TYPES``) whose own dedicated command group is expected to share the
#: name — that is not a collision, it's the same identity, and the roster floor check above
#: already makes that key un-droppable/un-reassignable.
#:
#: This list is intentionally maintained by hand, NOT imported live from `_cli/` — `_workflow`
#: sits below `_cli` in the module layering (`_cli → _services → _models`/`_workflow`), so it
#: cannot import the Typer app without an import cycle. `tests/meta` pins this list against the
#: live registered command set so it cannot silently drift (a new built-in top-level command
#: added to `_cli/` without a matching entry here would fail that guard, not this one).
RESERVED_CLI_VERBS: frozenset[str] = frozenset(
    {
        "adopt",
        "blocked",
        "board",
        "check",
        "create",
        "dev",
        "docs",
        "graph",
        "import",
        "inbox",
        "init",
        "list",
        "memory",
        "migrate",
        "mine",
        "override",
        "reflog",
        "renumber",
        "repair",
        "search",
        "show",
        "sync",
        "tree",
        "ui",
        "workflow",
        "workload",
    }
)

#: Every alias string the CLI's import-time registration loop binds into the root Click table,
#: paired with the bundled type whose command group it routes to (``sq feat …`` -> the bundled
#: ``feature`` group). Registration is unconditional and reads the BUNDLED spec, so these ten
#: names are live root commands in every squad no matter what the active spec declares — which
#: makes them exactly as collision-prone as the fixed verbs above, and for the same reason:
#: Click answers from its own table, so a declared type or alias wearing one of these names is
#: silently served by the bundled type's command tree instead of its own.
#:
#: Owning the alias is not a collision — the bundled ``feature`` type declaring ``feat`` IS the
#: static table's entry, not a conflict with it — so the check below refuses a name only when
#: the *declaring* type differs from the owner recorded here (see :func:`reserved_alias_owner`).
#:
#: Hand-maintained for the same layering reason as ``RESERVED_CLI_VERBS`` (``_workflow`` sits
#: below ``_cli``, and this table is consulted while the bundled spec is still being built, so
#: it cannot read that spec either). ``tests/meta`` pins it against both the bundled spec's own
#: alias declarations and the live registered command table, in both directions.
RESERVED_CLI_ALIASES: tuple[tuple[str, str], ...] = (
    ("b", "bug"),
    ("c", "contract"),
    ("d", "decision"),
    ("dec", "decision"),
    ("e", "epic"),
    ("f", "feature"),
    ("feat", "feature"),
    ("g", "guide"),
    ("m", "milestone"),
    ("mile", "milestone"),
    ("prd", "contract"),
    ("r", "review"),
    ("rev", "review"),
    ("t", "task"),
)


def reserved_alias_owner(name: str) -> str | None:
    """The bundled type *name* is statically registered as an alias of, or ``None``.

    ``reserved_alias_owner("feat") == "feature"``; ``reserved_alias_owner("feature") is None``
    (a type *name* is not an alias). The linear scan over ten entries is deliberate — a
    module-level dict would be mutable shared state for a lookup this small.
    """
    return next((owner for alias, owner in RESERVED_CLI_ALIASES if alias == name), None)


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
        "no_status_banner",
        "supersedes_incoming",
        "ref_rule_target_present",
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
        "playbook_guide_role_live",
    }
)

#: The fallback role name a status with no declared ``role`` resolves to — neutral/non-settled/
#: shown, so a custom status is fail-safe-visible until its author assigns one.
FALLBACK_ROLE_NAME = "pending"

#: The closed semantic colour-intent palette a role's ``color`` must be a member of (Plane-1,
#: enforced in ``WorkflowSpec._validate``). Roles themselves are an OPEN vocabulary — an adopter
#: may declare custom roles — but colour intent is closed so every client (CLI/TUI/VS Code) can
#: map any role to a concrete colour with a neutral fallback for one it doesn't recognise.
COLOR_INTENTS: frozenset[str] = frozenset(
    {"positive", "danger", "warning", "muted", "neutral", "info"}
)

#: Validator names that legitimately carry a ``:<param>`` suffix. ``subentity_title_max``'s is
#: documentary/seed-catalog shorthand only — the threshold isn't a structured spec field
#: (``TITLE_ADVISORY_MAX`` is a module constant) and the suffix is never read back at
#: runtime. ``ref_rule_target_present``'s is a genuine parameter: the item type it selects an
#: obligation for, read from the type's own ``validators`` entries by the validator itself
#: (``_services/_validators.py::_ref_rule_target_present``) — the dispatch engine still strips
#: it before the catalog lookup (``ValidatorEngine._run_per_item``), same as every other name.
PARAMETERIZED_VALIDATOR_NAMES: frozenset[str] = frozenset(
    {"subentity_title_max", "ref_rule_target_present"}
)

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
    "no_status_banner",
    "agent_registered",
    "parent_acyclic",
)

#: Per-category default per-item validator-name bundle — the category's *behaviour*, since
#: nothing else in the engine branches on ``work`` vs ``records`` (every other category
#: consumer asks only "roster or not"). A type's own ``validators`` list extends this floor and
#: may never subtract from it.
CATEGORY_BUNDLES: dict[str, tuple[str, ...]] = {
    "roster": (),
    "work": (
        "parent_in",
        "subentity_status_valid",
        "subentity_container_marker",
        "subentity_body_written",
        "subentity_title_max",
        "subtask_story_mapping",
    ),
    "records": ("no_parent", "supersedes_incoming"),
}

#: The validators whose subject is a type's declared ``subentity_kind``. A type that declares a
#: kind but whose effective set holds none of these has declared sub-entities nothing can check
#: — see :func:`_check_category_consistency`. ``subtask_story_mapping`` is deliberately absent:
#: it is specific to one kind's ``maps_parent_story`` capability, not to hosting a kind at all,
#: so it is guarded by its own clause (:func:`_clause_story_mapping_reachable`) instead.
SUBENTITY_VALIDATOR_NAMES: frozenset[str] = frozenset(
    {
        "subentity_status_valid",
        "subentity_container_marker",
        "subentity_body_written",
        "subentity_title_max",
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

    Parameterised on *common_core*/*category_bundles* — not hardcoded to the module
    constants — so a caller (or a test) can exercise the composition against a stub bundle.
    *category_bundles* defaults to ``None`` (resolved to the module-level
    :data:`CATEGORY_BUNDLES` below) rather than binding the mutable dict itself as a parameter
    default.
    """
    bundles = category_bundles if category_bundles is not None else CATEGORY_BUNDLES
    return common_core + bundles.get(category, ()) + extra


# ---------------------------------------------------------------------------
# Workflow dataclass — the thin shim over Lifecycle
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Workflow:
    """Thin shim: exposes the ``Workflow`` interface backed by ``Lifecycle``.

    Status fields are plain ``str`` — there is no enum backing them.
    """

    initial: str
    transitions: dict[str, tuple[str, ...]]

    @property
    def states(self) -> set[str]:
        seen: set[str] = {self.initial}
        for src, dsts in self.transitions.items():
            seen.add(src)
            seen.update(dsts)
        return seen

    def can_transition(self, src: str, dst: str) -> bool:
        return dst in self.transitions.get(src, ())

    @staticmethod
    def from_machine(m: Lifecycle) -> Workflow:
        """Build a ``Workflow`` shim from a ``Lifecycle`` (public factory)."""
        return Workflow(
            initial=m.initial,
            transitions={s: tuple(dsts) for s, dsts in m.transitions.items()},
        )


class Lifecycle(BaseModel):
    """A named lifecycle state machine: initial state + transition map.

    ``.states`` is derived (initial union all sources union all targets),
    mirroring ``Workflow.states``.

    Status fields are plain ``str`` — there is no enum backing them; the spec is the sole
    vocabulary authority (module docstring above).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    initial: str
    transitions: dict[str, list[str]]

    @property
    def states(self) -> frozenset[str]:
        seen: set[str] = {self.initial}
        for src, dsts in self.transitions.items():
            seen.add(src)
            seen.update(dsts)
        return frozenset(seen)

    def can_transition(self, src: str, dst: str) -> bool:
        return dst in self.transitions.get(src, [])


class RefRule(BaseModel):
    """A declared ref-kind rule for a type.

    Examples:
    - task → fixes / addresses (drives the parent_hint suffix)
    - decision → supersedes (gates the sq check superseded-record warning)

    **What a rule does and does not do.** It is a *rule about* a kind, never a permission for
    one. Two consumers read it today, both keyed on the declaring type:
    :meth:`WorkflowSpec.parent_hint` appends the declared ``hint`` text, and ``sq check``'s
    ``supersedes_incoming`` validator only runs for a type that declares a ``supersedes``
    rule — so a project that renames or drops ``decision`` takes that check with it.

    It is **not** an allowlist of the kinds a type may carry, and reading it as one would be a
    change of meaning rather than an enforcement of the existing one: the bundled document
    declares rules on two types only, while the navigational kinds (``related``,
    ``depends-on``, ``blocks``, ``implements``, ``duplicates``, ``scopes``) are carried by
    every type and declared by none. The accepted ``--kind`` vocabulary is declared spec
    vocabulary (``WorkflowSpec.ref_kinds``), not a fixed set in code, so an adopter-declared
    kind is an ordinary ``ref_rules`` target too, on the same terms as any bundled kind;
    scoping ``ref add`` per type would still need a rule of its own, this one just validates
    against the merged spec instead of a frozenset.

    What *is* enforced about a declaration is that it can actually apply: the loader refuses a
    rule whose ``kind`` isn't a declared entry of ``[ref_kinds]``, because every ref surface
    would reject that kind and the rule could never fire.

    ``target`` (optional) **types** the rule: an edge of this kind, declared by this type, is
    expected to point at an item of the named type — e.g. ``feature``'s ``implements`` rule
    targets ``contract``, disambiguating a kind reused for more than one relationship. It is
    **not** an allowlist and restricts nothing on its own (a ``feature`` carrying
    ``implements`` to a ``decision`` is unaffected); requiredness stays with whatever
    validator selects it (``ref_rule_target_present``). Referential validation (Plane-1,
    ``_check_ref_rule_targets``) checks ``target`` names a declared item type —
    ``_parse_ref_rules`` cannot: item types are known only after every ``[items.*]`` block has
    parsed, while it sees the declared ref *kinds* alone. Carried on the same declared-
    vocabulary, nothing-published terms as ``kind``/``hint``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: str
    """The ref kind this rule applies to (e.g. ``"fixes"``, ``"supersedes"``). Must name a
    declared entry of ``WorkflowSpec.ref_kinds`` — validated at load."""
    hint: str = ""
    """Human-readable hint injected into ``parent_hint`` / error messages (optional)."""
    target: str | None = None
    """The declared item type this kind is expected to point at when declared by this type
    (optional) — see the class docstring for what it means and does not mean."""


class RefKindSpec(BaseModel):
    """One declared entry of ``[ref_kinds]`` — a navigational or semantically-bound ref kind.

    Identity is the dict key on ``WorkflowSpec.ref_kinds``, never restated on the value — the
    convention ``ItemSpec``/``StatusSpec``/``Lifecycle``/``Collection`` already follow.

    ``role`` binds engine behaviour to a declared semantic instead of a spelling, so a project
    may rename or drop any kind without silently losing the behaviour bound to it. A kind
    declaring no ``role`` is purely navigational (display + graph traversal only) — the
    default, and what an adopter-declared kind gets unless it says otherwise. Three of the four
    values (``dependency``, ``preload``, ``supersession``) are read by engine sites elsewhere,
    not by anything here; nothing in this module branches on them.

    The fourth, ``default``, is the one the ref primitives (``split_ref``/``make_ref``) already
    consume: exactly one declared kind must carry it (mandatory — a bare ``"ID"`` ref decodes
    to whichever kind does, so a spec declaring none would turn existing on-disk data into a
    load failure), and the bundled spec declares it on ``related``. Renaming the kind that
    carries it is permitted and safe: the bare wire form binds to the semantic, never a
    spelling, so a rename relabels the same edges instead of re-pointing them. Because ``role``
    is one field, the kind carrying ``default`` can never simultaneously carry ``dependency``,
    ``preload`` or ``supersession`` — that reassignment is unrepresentable, not merely checked.

    ``direction`` only ever accompanies ``role = "dependency"`` (``"blocker"`` or
    ``"dependent"``) — carried here, alongside ``role``, so the catalog command can emit it
    without a second per-kind table.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str
    hint: str = ""
    role: Literal["dependency", "preload", "supersession", "default"] | None = None
    direction: Literal["blocker", "dependent"] | None = None


class Badge(BaseModel):
    """One atomic value in a collection: stored ``code`` + display ``label`` + presentation
    ``emoji``. Rendered verbatim — a field may relabel the collection, never a badge itself."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    label: str
    emoji: str | None = None


class Collection(BaseModel):
    """A reusable, named library of badges.

    Identified by its key in ``WorkflowSpec.collections`` — no self-stored code, mirroring
    ``ItemSpec``/``StatusSpec``/``Lifecycle`` (identity lives in the dict key, never
    duplicated onto the value). ``ordered`` drives sort + threshold filtering; ``default``
    is the collection's own fallback badge code, overridable per-field.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str
    ordered: bool = False
    default: str | None = None
    badges: list[Badge] = []

    @property
    def badge_codes(self) -> frozenset[str]:
        return frozenset(b.code for b in self.badges)


class Field(BaseModel):
    """A type's or sub-entity-kind's binding to a collection.

    ``code`` is the frontmatter key + CLI flag identity (list-item identity, like
    ``Badge.code``/``RefRule.kind``); ``label`` relabels the bound collection for this
    field's display only. ``required``/``default`` are per-field, not per-collection.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    label: str
    collection: str
    required: bool = False
    default: str | None = None


class SubentityKindSpec(BaseModel):
    """Per-sub-entity-kind declarations: machine binding + CLI/storage vocabulary + fields.

    Mirrors ``ItemSpec`` on the sub-entity axis — ``lifecycle`` is the explicit machine
    reference (retiring the former kind-name==lifecycle-name convention), ``plural``/
    ``local_prefix``/``placeholder`` are the CLI-facing vocabulary a custom kind needs to
    behave like a built-in one, and ``fields`` reuses the item-axis field mechanism, unforked.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    lifecycle: str
    """Explicit lifecycle-machine reference (mirrors ``ItemSpec.lifecycle``); the machine
    a sub-entity of this kind is driven by, looked up in ``WorkflowSpec.lifecycles``."""

    plural: str
    """CLI list verb and container-marker name (e.g. ``"stories"``, ``"subtasks"``)."""

    local_prefix: str
    """Local-id prefix for this kind (e.g. ``"US"``, ``"ST"``, ``"F"``)."""

    placeholder: str | None = None
    """Scaffold prose shown for a freshly-created block with no body yet. ``None`` falls
    back to a generic kind-derived placeholder (derivation not yet wired — a later task)."""

    maps_parent_story: bool = False
    """Capability flag: a sub-entity of this kind maps to one of its parent's stories
    (drives the ``--story`` option and the ``Story`` column). ``True`` only for the
    built-in ``subtask`` kind."""

    completion: str
    """The done-toggle target status inside this kind's own ``lifecycle`` — what
    ``subentity_completion(kind)`` resolves to instead of a hardcoded ``Done``/``Fixed``
    literal. Must name a reachable, non-initial state of that lifecycle (enforced at load
    by ``_check_completion_status``)."""

    fields: list[Field] = []


class LabelSpec(BaseModel):
    """Optional per-type display-label overrides: four independently-optional,
    named forms — ``singular``/``plural``/``singular_lower``/``plural_lower``. Each omitted
    form falls back to a value computed from the type-name string (``label_for`` in
    ``_models/_vocab.py`` — the sole fallback authority); a regular type needs no ``labels``
    table at all, an acronym/irregular type pins only the forms derivation gets wrong (e.g. an
    acronym's ``*_lower`` forms must stay capitalized, never a lowercased ``singular``)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    singular: str | None = None
    plural: str | None = None
    singular_lower: str | None = None
    plural_lower: str | None = None


class ItemSpec(BaseModel):
    """Vocabulary for one item type: prefix, folder, lifecycle, parents, aliases.

    Capability flags are additive and default to the ``False``/``None`` values
    that represent the common case (a non-roster work item with no special spine).
    They are consumed by the engine: ``category`` selects the type's validator bundle
    (:data:`CATEGORY_BUNDLES`), ``subentity_kind``/``parent_required``/``ref_rules`` are each
    read by a named validator, and :func:`_check_category_consistency` refuses a declaration
    whose enforcing validator the type's own category does not turn on.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    prefix: str
    folder: str
    lifecycle: str
    parents: list[str] = []
    aliases: list[str] = []

    labels: LabelSpec | None = None
    """Optional display-label overrides; resolved via ``label_for`` in
    ``_models/_vocab.py``, never read directly by consumers."""

    order: float = math.inf
    """Explicit ascending registration/display order; the type-name string breaks ties.
    Drives the CLI's per-type command registration order (deterministic, not alphabetical
    and not on-disk TOML order). A ``float`` (not ``int``) so a type can be inserted between
    two adjacent explicitly-ordered types (e.g. ``25.5`` between ``20`` and ``30``) without
    renumbering anything. Omitted ⇒ ``+inf``, so an un-ordered type (e.g. a project-declared
    custom type that doesn't set this) sorts after every explicitly-ordered type, then
    alphabetically among themselves."""

    # ------------------------------------------------------------------
    # Capability flags (additive; each consumed by a named validator — see the class docstring)
    # ------------------------------------------------------------------

    category: Literal["roster", "work", "records"] = "work"
    """The type's behavioural bundle, per the accepted category/validator decision: ``roster``
    (role/skill/operator — not a work type, no work lifecycle, slug-keyed identity,
    retype-ineligible, self-author bypass for bootstrap; locked off the override surface),
    ``work`` (burn-down items), or ``records`` (durable references). The ``Literal`` itself
    rejects any value outside the closed catalog at construction — the Plane-1
    category-catalog-membership check."""

    subentity_kind: str | None = None
    """The kind of sub-entity this type hosts: ``"story"`` | ``"subtask"`` | ``"finding"``
    or ``None`` for types that have no sub-entities (epic/bug/decision/guide/roster types)."""

    parent_required: str | None = None
    """The single parent type this type is defined *against* (e.g. ``"feature"`` for task);
    ``None`` for a type that is defined against no particular parent.

    Read for three things, and the name promises more than two of them deliver — so read this
    before declaring it. **Sub-entity story mapping**: it is what resolves the host whose
    sub-entities this type's own may map onto (``maps_parent_story``), and there it *is*
    enforced, hard — ``add-<kind> --story`` refuses an item whose parent is missing or is not
    this type, and ``subtask_story_mapping`` reports the same as a ``sq check`` error. That
    resolution is why this is a single type name and not derivable from ``parents``, which is a
    multi-valued allowlist with no way to say which member owns the stories. **Generated agent
    prose**: the ``--parent`` example in the per-type skills, and the anchor-type score behind
    the "Common commands" block, both read it. **Requiredness**: declaring it does *not* on its
    own make a parent mandatory at create — ``parents`` says which types are eligible,
    ``no_parent`` forbids one outright, and neither expresses "there must be one". A type that
    wants that names ``parent_present`` in its own ``validators``; without it,
    ``sq create <type>`` with no parent is accepted, as it always has been.

    Must name a type its own ``parents`` allowlist admits (an empty allowlist admits any) —
    otherwise ``parent_in`` refuses the one parent the story mapping insists on, and the Plane-1
    consistency clause refuses the spec."""

    ref_rules: list[RefRule] = []
    """Declared ref-kind rules that drive parent_hint text and gate the per-kind ``sq check``
    validators (e.g. task → fixes/addresses; decision → supersedes). Not an allowlist of the
    kinds this type may carry — see :class:`RefRule` for what a declaration means, and for
    what the loader validates about it."""

    fields: list[Field] = []
    """Badge-collection bindings this type carries (e.g. priority/severity) — "does this type
    carry field X" is ``X in {f.code for f in fields}``, exposed via ``fields_for()``."""

    extra_fields: list[str] = []
    """Generic (non-badge) ``extra`` metadata keys (``ExtraKey`` values) this type exposes via
    ``sq update --set`` — spec-declared identity so a renamed work type (e.g. guide->doc)
    keeps its settable fields instead of losing them to a hardcoded literal type name. The
    value kind (str/list/bool) per key is fixed in ``_models/_metadata.py``, not declared here."""

    validators: list[str] = []
    """Per-type additions to the category's default validator bundle (the pluggable-validator
    decision's assignment surface) — bare catalog names, **extend-only** over the bundle: a
    type may add a validator, never deselect a category default. Resolved at call time via
    ``_services._validators.effective_validator_names(category, extra=validators)``; every
    entry must name a member of ``VALIDATOR_NAMES`` (Plane-1, enforced below)."""

    views: list[str] = []
    """Declared ``[views]`` entries rendered as part of this type's own ``show``/``--json``
    surface — the reverse binding a view needs to reach a reader, since a ``ViewSpec`` never
    names the type(s) it is shown on (:class:`ViewSource` names a ref kind, a sub-entity kind
    or a subtree type, never "the item this is attached to"). Referentially checked at
    spec-build time by :func:`_check_item_views`, on the same ``WorkflowSpec._validate`` pass
    every sibling attached-by-name list is checked on: every name here must resolve against
    ``[views]``, and a ``subentity``-source view's kind must match this type's own
    ``subentity_kind``. This means every hand-built partial spec across the test suite that
    spreads ``bundled.items`` must also carry the matching ``bundled.views`` entries, or the
    attachment is (correctly) refused as dangling — the fixture cost the earlier "check at
    first use instead" design avoided, judged not worth the risk of bricking a whole type's
    read path on a spec that lints clean.

    A bundled type's own attachment travels with the type through ``[selected]``: dropping
    ``items.<type>`` from ``selected.items`` removes this list along with everything else the
    type declared, and the loader (``_prune_orphaned_type_owned_views`` in ``_loader.py``)
    prunes a bundled view left with no surviving owner from ``[views]`` too — so deselecting a
    type takes its bundled view with it rather than stranding a declaration over vocabulary
    nothing shows any more. A view still attached by another type, or never attached by any
    type at all (a freestanding view reached only via ``sq workflow view``), is untouched."""


#: The fixed, closed three-member category catalog — read off ``ItemSpec.category``'s own
#: ``Literal`` annotation (single-sourced) rather than a hand-duplicated tuple, so a caller
#: validating a ``--category`` value (or enumerating the axis for a filter/help text) never
#: drifts from the type actually declared above. Not spec vocabulary: an adopter cannot add,
#: rename, or remove a category — the catalog is closed, only its per-type assignment is open.
CATEGORIES: tuple[str, ...] = get_args(ItemSpec.model_fields["category"].annotation)


class ViewSource(BaseModel):
    """The relation a derived view projects — exactly one of three shapes, named by *kind*:

    - ``"ref"`` — refs of the declared kind named by ``name`` pointing at the item the view is
      resolved against, recovered by inverting stored forward edges. ``name`` must be a
      declared entry of ``[ref_kinds]``.
    - ``"subentity"`` — the projecting item's own sub-entity collection of the kind named by
      ``name``. ``name`` must be a declared entry of ``[subentity_kinds]``, and the item the
      view resolves against must itself host that kind.
    - ``"subtree"`` — the projecting item's descendants whose type is the one named by
      ``name``. ``name`` must be a declared entry of ``[items]``.

    ``name`` is checked against the merged spec by the same referential pass every other
    workflow-spec cross-reference goes through (see ``_check_views``); it is never a Python
    literal at the resolving end (``squads._views``), which reads it off the declared source
    instead.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["ref", "subentity", "subtree"]
    name: str


class ViewField(BaseModel):
    """One projected column of a derived view: ``code`` names either a base record attribute
    (``VIEW_BASE_FIELDS``, resolved generically — id/type/status/status_role/assignee/title/
    story) or a badge field the source's own type/kind declares; ``label`` is its display
    header. ``code`` is list-item identity (mirrors ``Field.code``/``Badge.code``), not a dict
    key, since a view's fields are ordered."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    label: str


class ViewSpec(BaseModel):
    """One declared entry of ``[views]`` — a computed projection with no fourth part.

    Identity is the dict key on ``WorkflowSpec.views``, never restated on the value (the
    convention ``ItemSpec``/``StatusSpec``/``Lifecycle``/``Collection``/``RefKindSpec`` already
    follow); a view's presentation template resolves from that same key
    (``templates/views/<name>.md.j2``), so no ``presentation`` field is declared either — the
    template path *is* the declared identity, the same way the dict key already is.

    ``group_by``/``order_by`` name a declared ``fields`` entry's ``code`` — never a raw status
    or ref-kind literal — so grouping and ordering stay spec-driven the way every other
    engine binding in this project is applied to the projection axis.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: ViewSource
    fields: list[ViewField] = []
    group_by: str | None = None
    order_by: list[str] = []


#: Base record attributes a view's ``fields`` may project without naming a declared badge
#: field — resolved generically by ``squads._views`` off the record itself (id/status/
#: assignee/title) or the active spec (``status_role``), never off a stored/spec value. Split
#: per source ``kind`` because ``"story"`` only exists on a sub-entity record (a subtask's
#: mapped parent story) and ``"type"`` only exists on an item record (a ref/subtree source).
#: ``"settled"``/``"delivered"`` carry the role axis a presentation needs to tell "still
#: outstanding" from "reached its own kind's happy-path terminal" from "settled some other
#: way" — booleans resolved off the declared role/lifecycle, never a literal status name; see
#: :func:`squads._views._is_delivered`. Projecting any of these from the wrong source kind is
#: refused at load, not resolved as blank.
VIEW_BASE_FIELDS_BY_SOURCE: dict[str, frozenset[str]] = {
    "ref": frozenset(
        {"id", "type", "status", "status_role", "settled", "delivered", "assignee", "title"}
    ),
    "subentity": frozenset(
        {"id", "status", "status_role", "settled", "delivered", "assignee", "title", "story"}
    ),
    "subtree": frozenset(
        {"id", "type", "status", "status_role", "settled", "delivered", "assignee", "title"}
    ),
}


class RoleSpec(BaseModel):
    """A first-class status ROLE object — the sole explicit status axis.

    A status references one role by name (``StatusSpec.role``); the role object carries the
    behaviour that governs how a status is treated:

    - ``settled`` — is this a resting/end state?
    - ``hidden`` — hidden from the default (non-``--all``) view?
    - ``color`` — a semantic colour intent (one client-agnostic vocabulary word, not a
      concrete colour); must be a member of ``COLOR_INTENTS`` (Plane-1, enforced at load).
    - ``live`` — is an entity resting in a status with this role the current, in-force instance
      of itself, and therefore available to be spawned, loaded, cited, and assigned? This is a
      **declared** property of the role, stated per status role rather than derived from
      ``settled`` — it is deliberately *narrower* than not-settled. Three bundled roles
      (``pending``, ``attention``, ``blocked``) are themselves non-settled without being live:
      "not at rest" and "on offer" are different questions, and a suspended or provisional entry
      should not be treated as live merely because it isn't settled. Defaults ``False``,
      deliberately the opposite direction from ``hidden``'s default: wrongly hiding an item is
      recoverable, wrongly treating one as live writes an agent into a host's config, which is
      the worse mistake. Materialisation into a backend's generated files is the downstream
      *consequence* of this flag for the roster, not what it names — the flag lives in
      vocabulary every item type shares, so it has to read sensibly on an ordinary work status
      too, not only a roster one.

    Roles are an OPEN vocabulary (an adopter may declare custom roles); colour intent is a
    CLOSED palette so every client can render any role safely with a neutral fallback.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    settled: bool
    hidden: bool = False
    color: str
    live: bool = False


class StatusSpec(BaseModel):
    """A role reference + optional sub-entity badge for one status name.

    ``role`` names an entry in ``WorkflowSpec.roles`` — the single source for this status's
    settled/hidden/colour behaviour (``terminal``/``is_open`` are derived, never stored here).
    An absent role resolves to the bundled ``FALLBACK_ROLE_NAME`` ("pending") role, so a custom
    status is fail-safe-visible until its author assigns one. ``badge`` stays independent — the
    sub-entity glyph is orthogonal to the role's colour/settled/hidden behaviour.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    badge: str | None = None
    role: str | None = None


# ---------------------------------------------------------------------------
# Validation helpers (extracted to keep _validate under complexity limits)
# ---------------------------------------------------------------------------


def _check_lifecycle_statuses(
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


def _check_reachability(
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
            for s in unreachable
        )


def _status_settled(
    status: str, statuses: dict[str, StatusSpec], roles: dict[str, RoleSpec]
) -> bool:
    """Whether *status* resolves to a settled role — an absent ``role`` falls back to
    ``FALLBACK_ROLE_NAME``; an unresolvable role name (should already be caught by
    ``_check_role_references``) is treated as not-settled rather than raising here."""
    spec = statuses.get(status)
    role_name = (spec.role if spec else None) or FALLBACK_ROLE_NAME
    role = roles.get(role_name)
    return bool(role and role.settled)


def _check_reachable_settled(
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
    """Whether *status* resolves to a live role — mirrors ``_status_settled``'s lookup: an
    absent ``role`` falls back to ``FALLBACK_ROLE_NAME``; an unresolvable role name (should
    already be caught by ``_check_role_references``) is treated as not-live rather than
    raising here."""
    spec = statuses.get(status)
    role_name = (spec.role if spec else None) or FALLBACK_ROLE_NAME
    role = roles.get(role_name)
    return bool(role and role.live)


def _check_roster_lifecycle_floor(
    items: dict[str, ItemSpec],
    lifecycles: dict[str, Lifecycle],
    statuses: dict[str, StatusSpec],
    roles: dict[str, RoleSpec],
    errors: list[str],
) -> None:
    """The additional floor a lifecycle bound to a ``category = "roster"`` type must satisfy
    on top of the universal floor above, restated against the ``live`` flag — never a role
    *name* (the same name-locking the engine forbids one layer down, on the status axis).

    R1 — at least one status whose role is live: zero means no entry of this type could
    ever be materialised, so the squad's generated config could never present an agent.

    R1' — if the lifecycle's ``initial`` status is not itself live, exactly one status is
    live: the narrow uniqueness the engine genuinely needs, so ``live_initial`` stays
    total for the scaffolding path that must create an entry already on offer. When ``initial``
    IS live there is no ambiguity to resolve and any number of further live statuses is
    fine.

    R2 — at least one settled, non-live status reachable from a live one: retirement must
    be reachable, not merely from ``initial`` — the universal reachable-settled floor
    (``_check_reachable_settled``) only guarantees the latter, which a machine could satisfy
    while never letting a live entry retire. Reachability is computed from the whole
    live *set* (R1 no longer guarantees a single status), the same way the previous shape
    excluded its sole live status from its own "reachable" set.

    All three are derived from the role assignment and the ``initial`` the spec already
    carries; a lifecycle whose ``initial``/transitions reference an undeclared status is
    skipped here (already reported by ``_check_item_refs``/``_check_lifecycle_statuses``).
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


def _check_role_references(
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


def _check_completion_status(
    subentity_kinds: dict[str, SubentityKindSpec],
    lifecycles: dict[str, Lifecycle],
    errors: list[str],
) -> None:
    """Each declared sub-entity kind's ``completion`` must name a reachable, non-initial
    state of its own ``lifecycle`` — the done-toggle target ``subentity_completion(kind)``
    resolves to. An undeclared ``lifecycle`` is caught separately by
    ``_check_subentity_kinds``; skipped here to avoid a duplicate error.
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


def _check_subentity_kinds(
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


def _check_parent_cycles(
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
                # Parent declared but not a known type — caught by _check_item_refs.
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


def _check_item_refs(
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


def _check_validators_assignment(items: dict[str, ItemSpec], errors: list[str]) -> None:
    """Plane-1 catalog-membership check for each type's ``validators`` list: an unknown name
    fails closed. Param-aware — split on ``:``, the bare name must be a declared catalog
    member, and a ``:<param>`` suffix is only well-formed on a name in
    ``PARAMETERIZED_VALIDATOR_NAMES`` (``subentity_title_max``, ``ref_rule_target_present``;
    every other name on the assignment surface, ``parent_in`` among them, is bare). A
    ``ref_rule_target_present:<T>`` entry's own coherence — ``<T>`` naming a
    declared item type, and this type declaring a rule targeting it — is a further check, run
    once every ``[items.*]`` block is known: see :func:`_check_ref_rule_targets`.
    """
    for t, ts in items.items():
        for entry in ts.validators:
            bare, sep, _param = entry.partition(":")
            if bare not in VALIDATOR_NAMES:
                errors.append(f"item {t!r}: validators entry {entry!r} names an unknown validator")
            elif sep and bare not in PARAMETERIZED_VALIDATOR_NAMES:
                errors.append(f"item {t!r}: validator {bare!r} takes no param (got {entry!r})")


def _check_ref_rule_targets(items: dict[str, ItemSpec], errors: list[str]) -> None:
    """Plane-1 referential validation for :attr:`RefRule.target` — run here, never inside
    ``_parse_ref_rules``, because item types are known only once every ``[items.*]`` block has
    parsed, while the ref-rule parser sees the declared ref *kinds* alone.

    Three independent checks:

    1. Every declared ``target`` must name an item type the merged spec declares — otherwise
       the rule types an edge against a type that does not exist.
    2. A ``ref_rule_target_present`` validator entry must carry a ``:<T>`` parameter at all.
       The bare name is accepted by :func:`_check_validators_assignment` (it *is* a declared
       catalog member) and then builds an empty target set at runtime
       (``_services/_validators.py``'s own ``and sep`` guard), so it is permanently inert —
       nothing ever fires, and nothing tells the adopter why. Refused here rather than
       silently doing nothing forever, the same reasoning as check 3.
    3. A type selecting ``ref_rule_target_present:<T>`` must itself declare at least one
       ``ref_rules`` entry whose ``target`` is ``<T>``. Without this, ``<T>`` could be an
       item type nothing points the check at (an accepted set empty by construction — every
       settled item warns and no edge can ever clear it) or not a declared item type at all;
       both are refused here rather than warning forever at runtime.
    """
    for t, ts in items.items():
        errors.extend(
            f"item {t!r}: ref_rules target {rr.target!r} does not name a declared item type"
            for rr in ts.ref_rules
            if rr.target is not None and rr.target not in items
        )

    for t, ts in items.items():
        for entry in ts.validators:
            bare, sep, param = entry.partition(":")
            if bare != "ref_rule_target_present":
                continue
            if not sep:
                errors.append(
                    f"item {t!r}: validators entry {entry!r} is missing its required target "
                    "type parameter — name it as 'ref_rule_target_present:<type>', or drop "
                    "the validator; without a parameter it never fires"
                )
                continue
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


def _effective_bare_validators(ts: ItemSpec) -> frozenset[str]:
    """A type's effective validator names, bare (a documentary ``:<param>`` suffix stripped)."""
    names = effective_validator_names(ts.category, extra=tuple(ts.validators))
    return frozenset(name.partition(":")[0] for name in names)


#: One consistency clause: given a type, its spec, its effective (bare) validator names, the
#: sub-entity kind table and the declared ref-kind table, return the refusals its declarations
#: earn. Clauses are pure and independent — a type that trips two reports both.
type ConsistencyClause = Callable[
    [str, ItemSpec, frozenset[str], dict[str, SubentityKindSpec], dict[str, RefKindSpec]],
    list[str],
]


def _clause_parent_reachable(
    t: str,
    ts: ItemSpec,
    effective: frozenset[str],
    _kinds: dict[str, SubentityKindSpec],
    _ref_kinds: dict[str, RefKindSpec],
) -> list[str]:
    """Guards ``parent_in``, and owns every arm about the parent declarations as a set.

    Two ways a declared parent constraint cannot be acted on. **Contradicted**: the effective
    set includes ``no_parent``, which forbids any parent at all, so neither ``parents`` nor
    ``parent_required`` can ever be satisfied — the records contract's own named example, and
    reachable without any reassignment by a ``work`` type that adds ``no_parent`` to its own
    ``validators``. **Unenforced**: neither ``no_parent`` nor ``parent_in`` is effective (today
    only the ``roster`` bundle, which is empty), so the ``parents`` allowlist is declared and
    nothing ever reads it.

    Two further contradictions, both between declarations rather than between a declaration and
    a bundle, and both silent before they were checked here:

    - ``parent_present`` and ``no_parent`` in one effective set. One demands a parent, the other
      forbids one, so *every* item of the type is refused whichever way it is created. Reachable
      only by naming ``parent_present`` on a type whose category carries ``no_parent`` (or the
      reverse), which is why it is the clause rather than the bundle that has to catch it.
    - ``parent_required`` naming a type the ``parents`` allowlist excludes. ``parent_in`` refuses
      the one parent type ``subtask_story_mapping`` then insists on, so the mapping capability is
      dead in both directions while the loaded spec reports both fields — the same shape as a
      contradictory category reassignment, arrived at without one. An empty ``parents`` is the
      lenient "any parent", so it excludes nothing and is not a contradiction.

    ``parent_required`` is deliberately absent from the *reachability* audit (only from it): it
    has a live consumer under every category — the ``--parent`` example in generated agent prose
    and the anchor-type score both read it — so there is no configuration in which declaring it
    reaches nothing, and a reachability arm over it would fire on a correct spec. Its
    enforcement half is opt-in (``parent_present``), which is why the two arms above are the
    whole of what this clause can say about it.
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
    """Guards the four :data:`SUBENTITY_VALIDATOR_NAMES`. A type declaring a ``subentity_kind``
    must keep at least one validator whose subject is that kind. The ``records`` bundle carries
    none, so a hosting type moved there keeps its sub-entities while every check on them stops
    running.

    "At least one" rather than "all four" deliberately: the ``validators`` list is extend-only
    from the closed catalog, so an adopter who genuinely wants a record that hosts sub-entities
    can say so by naming the checks they want back — the refusal is reachable, which is what
    keeps this validation rather than prohibition.
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
    """Guards ``supersedes_incoming``, whose gate is a ref rule naming a declared
    ``supersession``-role kind: the validator returns immediately for a type that declares
    none, and it sits in the ``records`` bundle and nowhere else. So a type keeping its
    ``supersession`` rule under any other category keeps the declaration and loses the only
    check it drives — a record left in a superseded state with no incoming edge stops being
    reported, on every gate.

    Resolved through *ref_kinds* (mirrors the validator's own gate,
    ``rr.kind in spec.supersession_ref_kinds()`` in ``_services/_validators.py``), never a
    fixed ``"supersedes"`` spelling; the rest of a type's ``ref_rules`` drive hint text only,
    which stays live under every category, so they need nothing here.
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


#: Each clause paired with the validator names whose *reachability* it guards. Declarative so
#: the coverage assert below can hold, not decoration: the rule is defined over the validator
#: set, so the audit that matters is per-validator, and every member of the closed catalog must
#: be accounted for exactly once.
CONSISTENCY_CLAUSES: tuple[tuple[frozenset[str], ConsistencyClause], ...] = (
    (frozenset({"parent_in"}), _clause_parent_reachable),
    (SUBENTITY_VALIDATOR_NAMES, _clause_subentity_checked),
    (frozenset({"supersedes_incoming"}), _clause_supersedes_checked),
    (frozenset({"subtask_story_mapping"}), _clause_story_mapping_reachable),
)

#: The audit's third bucket, and the one that has to be argued rather than derived: a catalog
#: member no clause guards, because no *declaration* selects it.
#:
#: - :data:`COMMON_CORE`'s members are effective for every type under every category, so nothing
#:   a type declares can put one out of reach — there is no silent-loss shape to catch. That is
#:   also why ``parent_acyclic`` lives there rather than in a bundle: an acyclic parent relation
#:   is not a house convention a category could decline, and common-core placement means no
#:   reachability clause is owed for it.
#: - ``no_parent`` is the inverse of a declaration: it enforces the *absence* of a parent, so an
#:   adopter declares nothing that it could stop enforcing. Its failure mode is the opposite one
#:   — being on while a parent field is declared — which is
#:   :func:`_clause_parent_reachable`'s first arm.
#: - ``parent_present`` sits in no :data:`CATEGORY_BUNDLES` entry at all, so the only way it is
#:   ever effective is a type naming it in its own ``validators``. A name you wrote yourself
#:   cannot be silently lost to a category, which is what a reachability clause exists to catch;
#:   its failure mode is again the opposite one, contradiction with ``no_parent``, and again
#:   :func:`_clause_parent_reachable` owns it.
#: - ``ref_rule_target_present`` is the same shape as ``parent_present``: it sits in no
#:   category bundle, so it is only ever effective when a type names it (with its param) in its
#:   own ``validators`` — nothing a category reassignment can silently take away. Its own
#:   coherence — the param must name a declared item type, and the declaring type's own
#:   ``ref_rules`` must carry a rule targeting it — is a *referential*, not reachability, check
#:   (:func:`_check_ref_rule_targets`), because it is about what the declaration *means*, not
#:   about which category turns it on.
UNGUARDED_VALIDATOR_NAMES: frozenset[str] = frozenset(
    {"no_parent", "parent_present", "ref_rule_target_present"}
)

_CLAUSE_GUARDED: frozenset[str] = frozenset(
    name for names, _ in CONSISTENCY_CLAUSES for name in names
)
assert _CLAUSE_GUARDED | frozenset(COMMON_CORE) | UNGUARDED_VALIDATOR_NAMES == VALIDATOR_NAMES, (
    "every validator must be guarded by a consistency clause, common-core, or named unguarded"
)


def _check_category_consistency(
    items: dict[str, ItemSpec],
    kinds: dict[str, SubentityKindSpec],
    ref_kinds: dict[str, RefKindSpec],
    errors: list[str],
) -> None:
    """Plane-1: every capability a type declares must be *reachable* under the validator set
    its own category turns on.

    An override may move a built-in between ``work`` and ``records`` — that is settled, and the
    guardrail is validation, not prohibition. What was never checked is whether the result is
    internally consistent, and the failure was silent on every gate: ``sq list`` exit 0,
    ``sq workflow lint`` "no errors or warnings", ``sq check`` exit 0. Moving ``task`` to
    ``records`` while it still declared ``parents = ["feature"]`` and
    ``parent_required = "feature"`` made that constraint unreachable *in both directions* —
    creating with no parent succeeded where a parent had been required, and creating with the
    declared parent was refused by the records rule — while the loaded spec went on reporting
    both fields.

    The check is written against the **validator set**, not against the category name, because
    the validator set is what a category actually *is*: nothing else in the engine branches on
    ``work`` versus ``records``. That makes the rule category-agnostic — it catches a ``work``
    type that adds ``no_parent`` to its own ``validators`` while declaring ``parents`` just as
    it catches a reassignment — and it needs no second table to keep in step with the bundles.

    Being defined over the validator set has a second consequence, which is why the clauses are
    a registry rather than a run of ``if``s: the *complete* rule is one clause per validator
    whose subject is a declared capability, and a clause set written against the fields that
    came to mind instead leaves the rest silently unenforced. :data:`CONSISTENCY_CLAUSES` pairs
    each clause with the names it guards and the assert above closes it against
    :data:`VALIDATOR_NAMES`, so a validator added to a bundle later cannot skip the decision:
    guard it, or name it in :data:`UNGUARDED_VALIDATOR_NAMES` with the reason.
    """
    for t, ts in sorted(items.items()):
        effective = _effective_bare_validators(ts)
        for _guards, clause in CONSISTENCY_CLAUSES:
            errors.extend(clause(t, ts, effective, kinds, ref_kinds))


#: Field codes exempt from the reserved-key check below because this exact schema models
#: them by field code on purpose — the bundled ``priority``/``severity`` fields keep the
#: literal key their axis has always used (``Item.priority``/``Item.severity``/
#: ``SubEntity.severity`` are themselves the badge-code storage, not a shadow of it), so
#: frontmatter keeps round-tripping unchanged.
_FIELD_ELIGIBLE_ITEM_KEYS: frozenset[str] = frozenset({"priority", "severity"})
_FIELD_ELIGIBLE_SUBENTITY_KEYS: frozenset[str] = frozenset({"severity"})


def _reserved_item_keys() -> frozenset[str]:
    """Item frontmatter keys a field code may not shadow.

    Derived from ``Item``'s own model/computed fields (never hand-copied) minus ``path``
    (model-only, never written to frontmatter) and the field-eligible exemptions.

    ``prefix`` stays reserved even though it, too, is model-only/never written: it is a
    *tolerated* legacy frontmatter key on read (``Item.id`` always wins over it), so a live
    field coded ``prefix`` would silently shadow — be read and discarded — exactly the hazard
    this check exists to catch. Excluding it here, as ``path`` is, would defeat that.
    """
    from squads._models._item import Item

    keys = set(Item.model_fields) | set(Item.model_computed_fields)
    return frozenset(keys - {"path"} - _FIELD_ELIGIBLE_ITEM_KEYS)


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


def _check_field_codes(
    items: dict[str, ItemSpec],
    subentity_kinds: dict[str, SubentityKindSpec],
    errors: list[str],
) -> None:
    """Field-code uniqueness per owner + reserved-frontmatter-key collision."""
    reserved_item = _reserved_item_keys()
    reserved_subentity = _reserved_subentity_keys()
    for owner, is_item, fields in _iter_field_owners(items, subentity_kinds):
        seen: set[str] = set()
        reserved = reserved_item if is_item else reserved_subentity
        for f in fields:
            if f.code in seen:
                errors.append(f"{owner!r}: duplicate field code {f.code!r}")
            seen.add(f.code)
            if f.code in reserved:
                errors.append(
                    f"{owner!r}: field code {f.code!r} shadows a reserved frontmatter key"
                )


def _check_field_collections(
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
            # Ordered-only for now. The flag stays in the schema (reserved for a future
            # unordered kind), but nothing downstream (sort/--min-<field>) reads it —
            # accepting ordered=false here would rank badges by declaration order
            # silently, a meaningless-but-quiet result. Fail closed instead.
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


def _resolve_view_source(
    tag: str,
    src: ViewSource,
    items: dict[str, ItemSpec],
    subentity_kinds: dict[str, SubentityKindSpec],
    ref_kinds: dict[str, RefKindSpec],
    errors: list[str],
) -> frozenset[str]:
    """Refuse *src* when its ``name`` doesn't resolve against the vocabulary its ``kind``
    points at, and return the badge-field codes declared for it (empty for an unresolved
    source; see :func:`_check_views`).

    A ``"ref"`` source's records can be items of any declared type — no single type's
    ``fields`` applies to all of them — so the declared set for it is the *union* across every
    declared item type's own ``fields`` (never a
    sub-entity-kind's, since a ``ref`` source's records are always items), roster types
    included — never narrowed to ``non_roster_types()``, since a ``ref`` source may
    legitimately project a roster record, e.g. a skill's edge to the role that preloads it. A
    code no declared type carries is absent from that union and stays refused as inert-by-
    construction; a code some type carries resolves for every record of that type and renders
    ``null`` for the rest, the same ``null`` an
    unset declared field already renders anywhere. ``subtree``/``subentity`` are unaffected:
    each already yields records of exactly one type/kind, so their declared-field set was
    already exactly right."""
    if src.kind == "ref":
        if src.name not in ref_kinds:
            errors.append(f"{tag}: source names ref kind {src.name!r}, not declared in [ref_kinds]")
        return frozenset(f.code for ts in items.values() for f in ts.fields)
    if src.kind == "subentity":
        ks = subentity_kinds.get(src.name)
        if ks is None:
            errors.append(
                f"{tag}: source names sub-entity kind {src.name!r}, not declared in "
                "[subentity_kinds]"
            )
            return frozenset()
        return frozenset(f.code for f in ks.fields)
    # "subtree"
    ts = items.get(src.name)
    if ts is None:
        errors.append(f"{tag}: source names item type {src.name!r}, not declared in [items]")
        return frozenset()
    return frozenset(f.code for f in ts.fields)


def _check_view_fields(
    tag: str,
    v: ViewSpec,
    base_allowed: frozenset[str],
    declared_fields: frozenset[str],
    errors: list[str],
) -> frozenset[str]:
    """Field-code uniqueness + resolvability, returning the view's own declared code set for
    :func:`_check_views` to validate ``group_by``/``order_by`` against.

    The unresolvable-field message has two shapes. For ``subtree``/``subentity`` it names the
    type/kind that could genuinely declare the field — that clause is unchanged. For ``ref`` it
    cannot: ``source.name`` is a ref *kind*, and no spec grammar lets a ref kind declare a
    field, so telling the author to add one there is an unperformable, actively false remedy.
    The ``ref`` branch instead says no declared item type carries the code, and names the two
    remedies that actually exist."""
    if not v.fields:
        errors.append(f"{tag}: must declare at least one field")

    seen_codes: set[str] = set()
    for f in v.fields:
        if f.code in seen_codes:
            errors.append(f"{tag}: duplicate field code {f.code!r}")
        seen_codes.add(f.code)
        if f.code in base_allowed or f.code in declared_fields:
            continue
        if v.source.kind == "ref":
            errors.append(
                f"{tag}: field {f.code!r} is not declared by any item type — a 'ref' source "
                "can only project a code at least one declared item type carries. Declare "
                f"{f.code!r} as a field on an item type, or name one of the base attributes "
                f"for a 'ref' source ({sorted(base_allowed)})"
            )
        else:
            errors.append(
                f"{tag}: field {f.code!r} is neither a base attribute for a "
                f"{v.source.kind!r} source ({sorted(base_allowed)}) nor a field "
                f"{v.source.name!r} declares"
            )
    return frozenset(seen_codes)


def _check_views(
    views: dict[str, ViewSpec],
    items: dict[str, ItemSpec],
    subentity_kinds: dict[str, SubentityKindSpec],
    ref_kinds: dict[str, RefKindSpec],
    errors: list[str],
) -> None:
    """Referential + structural floor over ``[views]``, run on the **merged** mapping so it
    lands on the exact same collect-all pass every other cross-reference here does (``sq
    workflow lint`` reports a broken view alongside every other violation in one run, never
    only the first).

    A view's ``source.name`` must name a declared entry of the vocabulary its ``source.kind``
    points at (``[ref_kinds]``/``[subentity_kinds]``/``[items]``) — the same shape
    ``_parse_ref_rules`` already refuses a rule naming an undeclared kind for, applied to the
    view axis: a source that can never resolve is refused here rather than carried as an inert
    declaration. Every declared field's ``code`` must be a base attribute
    :data:`VIEW_BASE_FIELDS_BY_SOURCE` allows for that source kind, or a badge field the
    resolved vocabulary actually declares — for ``subtree``/``subentity`` that vocabulary is
    the one resolved type/kind; for ``ref`` (whose records can be items of any declared type)
    it is the union of every declared item type's own fields — a code no declared type carries
    anywhere is still refused as inert-by-construction. ``group_by``/``order_by`` must each
    name one of the view's own declared field codes.
    """
    for name, v in sorted(views.items()):
        tag = f"view {name!r}"
        base_allowed = VIEW_BASE_FIELDS_BY_SOURCE[v.source.kind]
        declared_fields = _resolve_view_source(
            tag, v.source, items, subentity_kinds, ref_kinds, errors
        )
        seen_codes = _check_view_fields(tag, v, base_allowed, declared_fields, errors)

        if v.group_by is not None and v.group_by not in seen_codes:
            errors.append(f"{tag}: group_by {v.group_by!r} must name one of its own fields")
        errors.extend(
            f"{tag}: order_by {ob!r} must name one of its own fields"
            for ob in v.order_by
            if ob not in seen_codes
        )


def _check_item_views(
    items: dict[str, ItemSpec],
    views: dict[str, ViewSpec],
    errors: list[str],
) -> None:
    """Reciprocal check for :attr:`ItemSpec.views`, the attached-by-name list on ``ItemSpec``
    — the same shape every sibling in this module guards from the attaching side
    (:func:`_check_item_refs` for ``parents``/``lifecycle``, :func:`_check_validators_assignment`
    for ``validators``, :func:`_check_ref_rule_targets` for ``RefRule.target``,
    :func:`_check_field_collections` for a field's ``collection``,
    :func:`_check_subentity_kinds` for a kind's ``lifecycle``). :func:`_check_views` above
    validates the ``[views]`` mapping itself (a view's own
    ``source``/``fields``/``group_by``/``order_by``); this one validates the reverse binding —
    the name an ``items.<type>.views`` list attaches.

    Two axes, both fully determinable from the spec alone with no filesystem access (the one
    axis that needs the filesystem — a declared view with no presentation template on disk —
    is refused at the render boundary instead; see ``squads._views.render_view``):

    1. Every name in ``ts.views`` must resolve against ``views`` — whether it was dropped
       through ``[selected].views``, mistyped, or never declared at all. Left unchecked, this
       turns ``show``/``show --json``/``show --raw`` into a hard failure for every item of the
       attaching type, on a spec ``sq workflow lint`` calls clean.
    2. A view whose ``source.kind`` is ``"subentity"`` may attach only to a type whose own
       ``subentity_kind`` is that same kind — a type that hosts no sub-entities, or a
       different kind, can never satisfy it, the same way :func:`resolve_records` in
       ``squads._views`` refuses it at first use today.
    """
    for t, ts in items.items():
        for name in ts.views:
            v = views.get(name)
            if v is None:
                errors.append(
                    f"item {t!r}: views entry {name!r} does not name a declared [views] entry"
                )
                continue
            if v.source.kind == "subentity":
                kind = v.source.name
                hosted = ts.subentity_kind
                if hosted != kind:
                    hosted_desc = repr(hosted) if hosted else "none"
                    errors.append(
                        f"item {t!r}: view {name!r} projects {kind!r} sub-entities, but "
                        f"{t!r} hosts {hosted_desc}"
                    )


#: A TOML bare key (``[A-Za-z0-9_-]+``) — what every ``[ref_kinds]`` entry's own key must
#: satisfy so it stays splat-ref addressable; also rules out the wire ref
#: separator ``:`` (``split_ref`` partitions on it, ``_models/_item.py``) without a second check.
_BARE_TOML_KEY_RE = re_compile(r"^[A-Za-z0-9_-]+$")


def _check_ref_kinds_floor(ref_kinds: dict[str, RefKindSpec], errors: list[str]) -> None:
    """The per-capability floor over ``[ref_kinds]`` (plus the ``default`` role folded in by
    the amendment that ruled it onto this floor) — checked here, on the merged mapping, so a
    violation surfaces as an ordinary ``_build_spec`` finding: visible to ``sq workflow lint``
    on the exact path every other structural failure already takes, not only at first use
    inside an accessor like :meth:`WorkflowSpec.default_ref_kind`/
    :meth:`WorkflowSpec.preload_ref_kind`. This is
    what keeps lint and a mutating command in agreement on a spec neither should bless.

    - Every key must be a bare TOML key (see :data:`_BARE_TOML_KEY_RE`).
    - Exactly one kind carries ``role = "default"`` — mandatory; a bare ``"ID"`` ref is
      undecodable without exactly one.
    - Exactly one kind carries ``role = "preload"`` — mandatory; zero strands every custom
      skill from the role that scopes it, two make the resolver's inversion ambiguous.
    - At most one kind per ``dependency`` direction (``"blocker"``/``"dependent"``) — zero is
      legal per direction; two spelling the same direction would make the normalisation the
      graph traversal relies on ambiguous. A kind declaring ``role = "dependency"`` with no
      direction at all is refused outright — it would silently resolve through neither bucket.
    - ``supersession`` has no upper bound and no floor: zero is a stated choice (an empty
      incoming-supersedes check), any number above zero is fine — the validator sites this
      task converts read the full declared set, not a single kind.
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


# Canonical priority order for well-known exception/side states: states appearing together
# in the side-state list sort by this (lower = earlier), regardless of BFS discovery order
# (e.g. Blocked before Cancelled). States absent here keep BFS order via the fallback rank
# (len(_SIDE_PRIORITY)).
_SIDE_PRIORITY: dict[str, int] = {
    "WontFix": 0,
    "Blocked": 1,
    "Cancelled": 2,
    "Rejected": 3,
    "Deprecated": 4,
}

# Bundled sub-entity container headings, keyed by kind and paired with the PLURAL that
# heading belongs to — see WorkflowSpec.subentity_container_heading. The plural is what makes
# the entry conditional rather than absolute: keyed by kind code alone, this table outranked an
# adopter's declared plural for the three bundled kind names, rendering "## User Stories" above
# a container marked `sq:outcomes`.
_BUNDLED_CONTAINER_HEADINGS: dict[str, tuple[str, str]] = {
    "story": ("stories", "User Stories"),
    "subtask": ("subtasks", "Subtasks"),
    "finding": ("findings", "Findings"),
}


def lifecycle_spine(machine: Lifecycle) -> list[str]:
    """The "happy-path" chain through *machine*: greedy forward walk from ``initial``,
    following the first unvisited outgoing transition at each step, stopping when no new
    state is reachable. E.g. ``["Draft", "Ready", "InProgress", "InReview", "Done"]`` for
    the bundled ``work`` lifecycle — exception/side branches (``Blocked``, ``Cancelled``)
    never appear, by construction (they're only reached as a non-first transition target).

    Shared by :func:`linearize_lifecycle` (renders it as ``"A → B → C"`` plus side states)
    and the "first happy-path status matching some predicate" family
    (:meth:`WorkflowSpec.first_active_status`/:meth:`WorkflowSpec.first_settled_status`) —
    those need the spine specifically, not full BFS reachability order, since a side branch
    like ``Cancelled`` can resolve to a settled role at a shallower BFS depth than the actual
    happy-path terminal and would otherwise be picked first.
    """
    initial = machine.initial
    transitions = machine.transitions
    spine: list[str] = [initial]
    visited: set[str] = {initial}
    current = initial
    while True:
        next_state: str | None = None
        for candidate in transitions.get(current, []):
            if candidate not in visited:
                next_state = candidate
                break
        if next_state is None:
            break
        spine.append(next_state)
        visited.add(next_state)
        current = next_state
    return spine


def linearize_lifecycle(machine: Lifecycle) -> str:
    """Derive a readable lifecycle string from an arbitrary transition graph.

    Algorithm:
    1. Build the **spine** (:func:`lifecycle_spine`) — the "happy-path" chain ``A → B → C``.
    2. Collect **side states** — all states reachable from ``machine.initial`` that
       are not on the spine — in BFS discovery order.
    3. Sort side states into canonical order using :data:`_SIDE_PRIORITY`, so the
       output is independent of TOML transition-list ordering.  States not in the
       priority table retain their relative BFS order (sorted after the known states).
    4. Return ``"A → B → C"`` when there are no side states, or
       ``"A → B → C (+ D, E)"`` otherwise.

    Deterministic: given the same machine the output is always identical.

    Examples::

        linearize_lifecycle(guide_machine)   # "Draft → Published → Deprecated"
        linearize_lifecycle(adr_machine)     # "Proposed → Accepted → Superseded (+ ...)"
    """
    initial = machine.initial
    transitions = machine.transitions
    spine = lifecycle_spine(machine)

    # BFS from initial to collect all reachable states in discovery order.
    bfs_order: list[str] = [initial]
    bfs_visited: set[str] = {initial}
    queue: list[str] = [initial]
    while queue:
        node = queue.pop(0)
        for nxt in transitions.get(node, []):
            if nxt not in bfs_visited:
                bfs_visited.add(nxt)
                bfs_order.append(nxt)
                queue.append(nxt)

    # Side states = reachable but not on the spine, sorted into canonical order.
    # Known states sort by their explicit priority; unknown states sort after them
    # in BFS-discovery order (secondary key = bfs position).
    spine_set: set[str] = set(spine)
    _unknown_rank = len(_SIDE_PRIORITY)
    side: list[str] = sorted(
        (s for s in bfs_order if s not in spine_set),
        key=lambda s: (_SIDE_PRIORITY.get(s, _unknown_rank), bfs_order.index(s)),
    )

    chain = " → ".join(spine)
    if side:
        return f"{chain} (+ {', '.join(side)})"
    return chain


def lifecycle_states_in_order(machine: Lifecycle) -> list[str]:
    """A deterministic listing of every state in ``machine``: BFS discovery order from
    ``initial`` (mirroring :func:`linearize_lifecycle`'s traversal), then any state left
    unreached (shouldn't normally happen) appended in sorted order.

    ``Lifecycle.states`` is a ``frozenset`` — its iteration order is hash-seed-dependent, so
    any caller whose output has to be byte-stable across process runs walks this instead.
    Today that is :meth:`WorkflowSpec.first_dropped_status`, which picks a status out of a
    machine for generated text; a hash-ordered pick would rewrite generated files at random.
    """
    order = [machine.initial]
    seen = {machine.initial}
    queue = [machine.initial]
    while queue:
        node = queue.pop(0)
        for nxt in machine.transitions.get(node, []):
            if nxt not in seen:
                seen.add(nxt)
                order.append(nxt)
                queue.append(nxt)
    order.extend(sorted(s for s in machine.states if s not in seen))
    return order


def lifecycle_edges_in_order(machine: Lifecycle) -> list[tuple[str, str]]:
    """Every transition edge in *machine*, as ``(source, target)`` pairs in a deterministic,
    byte-stable order: sources in :func:`lifecycle_states_in_order` order, targets in each
    source's declared ``Lifecycle.transitions`` list order (the TOML declaration order the
    ``list`` values preserve — never ``Lifecycle.states``, a ``frozenset`` with a
    hash-seed-dependent iteration order). A source with no outgoing edges contributes nothing.

    This re-derives what the now-deleted ``lifecycle_edges()`` helper used to return (dropped
    as dead code once the cheatsheet's state-diagram render was removed); the ordering it fixed
    is preserved here for the ``sq workflow lifecycles --json`` catalog, which publishes each
    pair as a ``{from, to}`` object.
    """
    return [
        (src, dst)
        for src in lifecycle_states_in_order(machine)
        for dst in machine.transitions.get(src, [])
    ]


class WorkflowSpec(BaseModel):
    """The full loaded workflow specification.

    Built by ``load_workflow_spec()``. A module-level singleton is used via
    the free-function shims; equivalent methods are provided for callers that
    hold an explicit spec.

    ``extra="forbid"``: unknown TOML keys are rejected at construction time,
    matching the roles/playbook loaders.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    items: dict[str, ItemSpec]
    statuses: dict[str, StatusSpec]
    lifecycles: dict[str, Lifecycle]
    # Derived reverse indexes — built by the loader, not stored in TOML.
    prefix_to_type: dict[str, str]
    alias_to_type: dict[str, str]
    #: Reusable badge libraries, keyed by collection code — the vocabulary
    #: ``ItemSpec.fields``/``SubentityKindSpec.fields`` bind to (priority/severity are two
    #: bundled defaults, no longer special-cased enums).
    collections: dict[str, Collection] = {}
    #: Per-sub-entity-kind declarations (machine binding, CLI/storage vocabulary, and
    #: field bindings), keyed by kind name.
    subentity_kinds: dict[str, SubentityKindSpec] = {}
    #: The role catalog, keyed by role name — the sole explicit status axis (settled/hidden/
    #: color live here; a status merely references one by name via ``StatusSpec.role``).
    roles: dict[str, RoleSpec] = {}
    #: The declared ref-kind vocabulary, keyed by kind name — the accepted ``--kind`` set,
    #: replacing the former ``VALID_REF_KINDS`` frozenset. A kind's ``role`` binds engine
    #: behaviour to a semantic instead of a spelling; see :class:`RefKindSpec`.
    ref_kinds: dict[str, RefKindSpec] = {}
    #: Declared derived views, keyed by view name — source + projection, no fourth part (no
    #: presentation field either: the key IS the presentation template's identity, resolved by
    #: ``squads._views`` at ``templates/views/<name>.md.j2``). See :class:`ViewSpec`.
    views: dict[str, ViewSpec] = {}

    # ------------------------------------------------------------------ convenience accessors

    def machine_for(self, item_type: str) -> Lifecycle:
        """The lifecycle machine bound to *item_type*.

        Raises ``KeyError`` when *item_type* isn't declared (or, on a corrupt spec, when its
        declared lifecycle name doesn't resolve) — there is no sensible empty ``Lifecycle`` to
        degrade to, the same shape as :meth:`collection`. Callers that must survive a
        dropped/renamed type gate first (``item_type in spec.items``) or go through a
        degrading wrapper like :meth:`live_statuses` instead of calling this directly.
        """
        return self.lifecycles[self.items[item_type].lifecycle]

    def initial_status(self, item_type: str) -> str:
        return self.machine_for(item_type).initial

    def can_transition(self, item_type: str, src: str, dst: str) -> bool:
        return self.machine_for(item_type).can_transition(src, dst)

    def role_for(self, status: str) -> RoleSpec:
        """The resolved role object for *status* — never raises, on a validated spec or not.

        An absent ``StatusSpec.role`` falls back to ``FALLBACK_ROLE_NAME`` ("pending"); an
        undeclared *status* itself (a dropped/renamed status) degrades the same way, treated
        exactly like a declared status with no role assigned — mirrors the validation-time
        ``_status_settled``/``_status_live`` helpers' ``.get()`` idiom. The single derivation
        site every settled/hidden/colour/live read routes through; ``_validate`` guarantees the
        fallback role itself is declared, so the final ``roles[...]`` lookup is total."""
        spec = self.statuses.get(status)
        role_name = (spec.role if spec else None) or FALLBACK_ROLE_NAME
        return self.roles[role_name]

    def is_open(self, status: str) -> bool:
        return not self.role_for(status).settled

    def hidden_by_default(self, item_type: str, status: str) -> bool:
        """True when an item of *item_type* carrying *status* is hidden from the default
        (non-``--all``) ``sq list``/``sq tree`` view.

        Purely role-derived — ``role_for(status).hidden`` — no category branch: the role
        object alone encodes whether an item at this status stays visible. A ``done`` role
        (e.g. ``Done``, ``Verified``) hides; an ``in_force`` role (e.g. ``Accepted``,
        ``Published``) is settled but stays visible — that split is what a single role object
        expresses that a bare ``terminal`` flag could not.

        Never raises — inherits ``role_for``'s total degrade for an undeclared *status*; a
        dropped/renamed status defaults to not-hidden (the ``pending`` fallback role's own
        setting), same as any other roleless status.
        """
        return self.role_for(status).hidden

    def parent_allowed(self, child: str, parent: str) -> bool:
        """Whether *parent*'s type may be *child*'s parent (no constraint declared == True).

        Degrades to ``False`` (fail closed) when *child* isn't declared at all — an
        undeclared/dropped child type has no known parent rule to satisfy, so a caller
        deciding whether to accept an edge must not be told "anything goes"."""
        ts = self.items.get(child)
        if ts is None:
            return False
        return len(ts.parents) == 0 or parent in ts.parents

    def terminal_set(self) -> frozenset[str]:
        return frozenset(s for s in self.statuses if self.role_for(s).settled)

    def status_badge(self, status: str) -> str | None:
        spec = self.statuses.get(status)
        return spec.badge if spec else None

    def collection(self, code: str) -> Collection:
        """The reusable badge library named *code* (raises ``KeyError`` if undeclared)."""
        return self.collections[code]

    def fields_for(self, type_or_kind: str) -> list[Field]:
        """Declared fields for an item type OR a sub-entity kind (same lookup, either
        namespace — the two never collide in a valid spec)."""
        item = self.items.get(type_or_kind)
        if item is not None:
            return list(item.fields)
        kind_spec = self.subentity_kinds.get(type_or_kind)
        return list(kind_spec.fields) if kind_spec else []

    # ------------------------------------------------------------------ capability-flag accessors

    def non_roster_types(self) -> frozenset[str]:
        """Creatable/trackable types: work + records — every type whose category isn't
        roster. For sites that need one category exactly, use ``item_is_roster``/the
        type's own ``category`` field instead of this lump."""
        return frozenset(t for t, ts in self.items.items() if ts.category != "roster")

    def item_is_roster(self, item_type: str) -> bool:
        """True when *item_type*'s category is roster (role, skill, operator).

        Also returns False (rather than raising) when *item_type* isn't declared in this
        spec at all — role/skill/operator are locked by key identity and can never be
        dropped, so an undeclared type is never roster; a dropped/renamed work or records
        type must cleanly read as "not roster", not crash the caller."""
        ts = self.items.get(item_type)
        return ts is not None and ts.category == "roster"

    def item_subentity_kind(self, item_type: str) -> str | None:
        """The sub-entity kind this type hosts, or None.

        Also returns None (rather than raising) when *item_type* isn't declared in this
        spec at all — a dropped/renamed type must cleanly lose its sub-entity check, not
        crash the caller.
        """
        ts = self.items.get(item_type)
        return ts.subentity_kind if ts else None

    def item_parent_required(self, item_type: str) -> str | None:
        """The required parent type slug, or None (no constraint).

        Also None when *item_type* isn't declared — a dropped/renamed type has no
        constraint to report, same shape as :meth:`item_subentity_kind`."""
        ts = self.items.get(item_type)
        return ts.parent_required if ts else None

    def item_extra_fields(self, item_type: str) -> list[str]:
        """Declared generic ``extra``-metadata keys for this type (drives ``sq update --set``
        identity for a renamed/custom type, e.g. guide's ``tags``, review's ``target_ref``)."""
        ts = self.items.get(item_type)
        return list(ts.extra_fields) if ts else []

    def item_ref_rules(self, item_type: str) -> list[RefRule]:
        """Declared ref-kind rules for the type (e.g. fixes/addresses/supersedes).

        Also ``[]`` when *item_type* isn't declared — no rules to report for a
        dropped/renamed type, same shape as :meth:`item_extra_fields`/:meth:`fields_for`."""
        ts = self.items.get(item_type)
        return list(ts.ref_rules) if ts else []

    def default_ref_kind(self) -> str:
        """The one declared ``[ref_kinds]`` entry carrying ``role = "default"`` — what a bare
        ``"ID"`` ref (:func:`~squads._models._item.split_ref`'s unspelled ``""``) actually
        means.

        Raises ``SquadsError`` when the merged spec declares zero or more than one — a
        per-capability floor clause elsewhere is meant to keep this total at merge time,
        landing alongside the rest of that floor; this accessor still fails closed rather than
        guessing, since a bare ref is undecodable without exactly one.
        """
        defaults = [k for k, ks in self.ref_kinds.items() if ks.role == "default"]
        if len(defaults) != 1:
            from squads._errors import SquadsError

            raise SquadsError(
                "the workflow spec must declare exactly one ref kind with role = 'default' "
                f"(a bare ref decodes to it); found {len(defaults)}: {sorted(defaults)}"
            )
        return defaults[0]

    def ref_kinds_with_role(self, role: str) -> dict[str, RefKindSpec]:
        """Declared ``[ref_kinds]`` entries carrying *role* — the generic semantic lookup
        every engine binding resolves through instead of a kind's spelling."""
        return {k: ks for k, ks in self.ref_kinds.items() if ks.role == role}

    def preload_ref_kind(self) -> str:
        """The one declared ``[ref_kinds]`` entry carrying ``role = "preload"`` — a skill's
        forward edge to the role that preloads it, inverted by the roster resolver.

        Raises ``SquadsError`` when the merged spec declares zero or more than one — the
        per-capability floor (:func:`_check_ref_kinds_floor`) keeps this total at merge time;
        this accessor still fails closed rather than guessing, the same shape as
        :meth:`default_ref_kind`.
        """
        preloads = sorted(self.ref_kinds_with_role("preload"))
        if len(preloads) != 1:
            from squads._errors import SquadsError

            raise SquadsError(
                "the workflow spec must declare exactly one ref kind with role = 'preload' "
                f"(a skill's forward edge to the role that preloads it); found "
                f"{len(preloads)}: {preloads}"
            )
        return preloads[0]

    def dependency_ref_kind(self, direction: Literal["blocker", "dependent"]) -> str | None:
        """The declared ``[ref_kinds]`` entry carrying ``role = "dependency"`` in *direction*,
        or ``None`` — zero is legal per direction (a squad may decline that half, or all, of
        the dependency capability). Raises ``SquadsError`` if more than one claims the same
        direction — the floor's job to prevent; this accessor stays defensive rather than
        picking one."""
        by_direction = self.ref_kinds_with_role("dependency")
        claimants = sorted(k for k, ks in by_direction.items() if ks.direction == direction)
        if len(claimants) > 1:
            from squads._errors import SquadsError

            raise SquadsError(
                f"the workflow spec declares {len(claimants)} ref kinds with role = "
                f"'dependency' and direction = {direction!r}; at most one is allowed: "
                f"{claimants}"
            )
        return claimants[0] if claimants else None

    def dependency_ref_kinds(self) -> frozenset[str]:
        """Every declared kind carrying ``role = "dependency"``, either direction — the
        traversal filter over the dependency pair, resolved from the spec instead of a
        literal ``{"blocks", "depends-on"}`` pair."""
        return frozenset(self.ref_kinds_with_role("dependency"))

    def canonical_dependency_ref_kind(self) -> str | None:
        """The declared kind every collapsed dependency edge's ``edge_kind`` emits: the kind
        carrying ``role = "dependency"`` in the DEPENDENT direction,
        or the BLOCKER-direction kind when a project declares only that half. ``None`` when
        neither direction is declared — the dependency capability is legal to decline
        entirely, and the graph then carries no dependency edges to label."""
        return self.dependency_ref_kind("dependent") or self.dependency_ref_kind("blocker")

    def supersession_ref_kinds(self) -> frozenset[str]:
        """Every declared kind carrying ``role = "supersession"`` — zero or more; zero is
        legal (a squad may decline the capability entirely), and no upper bound is floored,
        so every consumer reads the full declared set rather than a single kind."""
        return frozenset(self.ref_kinds_with_role("supersession"))

    def status_role(self, status: str) -> str | None:
        """Semantic role marker for this status (e.g. ``'superseded'``), or None."""
        spec = self.statuses.get(status)
        return spec.role if spec else None

    def live_statuses(self, item_type: str) -> frozenset[str]:
        """States of *item_type*'s own lifecycle whose resolved role carries the ``live``
        flag — the read predicate every "is this entry on offer" caller uses instead of naming
        a status literal or a role name: ``item.status in spec.live_statuses(item.type)``.
        Fallback resolution (an undeclared ``StatusSpec.role`` resolves to
        ``FALLBACK_ROLE_NAME``, itself not live) applies, via ``role_for``.

        Also ``frozenset()`` when *item_type* isn't declared — a dropped/renamed type has no
        lifecycle to report live states for, so this gates before calling :meth:`machine_for`
        (which would otherwise raise) rather than crash the caller."""
        if item_type not in self.items:
            return frozenset()
        machine = self.machine_for(item_type)
        return frozenset(s for s in machine.states if self.role_for(s).live)

    def _machine_for_type_or_kind(self, type_or_kind: str) -> Lifecycle | None:
        """The lifecycle machine bound to *type_or_kind* — an item type or a sub-entity kind,
        the same dual-namespace resolution :meth:`fields_for` already uses (the two never
        collide in a valid spec). ``None`` when neither namespace declares it."""
        ts = self.items.get(type_or_kind)
        if ts is not None:
            return self.lifecycles[ts.lifecycle]
        ks = self.subentity_kinds.get(type_or_kind)
        return self.lifecycles[ks.lifecycle] if ks is not None else None

    def _first_status_matching(
        self, item_type: str, predicate: Callable[[RoleSpec], bool]
    ) -> str | None:
        """Shared walk for :meth:`first_active_status`/:meth:`first_settled_status`: the
        first status on *item_type*'s own lifecycle **spine** — :func:`lifecycle_spine`'s
        happy-path chain, not full BFS reachability order — whose resolved role satisfies
        *predicate*. The spine specifically (not BFS order) matters: an exception branch
        like ``Cancelled`` can resolve to a settled role at a shallower BFS depth than the
        actual happy-path terminal and would otherwise be matched first. *item_type* may also
        be a sub-entity kind (:meth:`_machine_for_type_or_kind`'s dual namespace) — the derived
        views engine walks a sub-entity record's own kind through the same accessor. ``None``
        when *item_type* names neither, or no status on its spine matches."""
        machine = self._machine_for_type_or_kind(item_type)
        if machine is None:
            return None
        for state in lifecycle_spine(machine):
            if predicate(self.role_for(state)):
                return state
        return None

    def first_active_status(self, item_type: str) -> str | None:
        """The first status in *item_type*'s own lifecycle whose resolved role carries the
        ``live`` flag — "the state you move an item to once you actually start working it",
        as a concrete example status derived from the spec rather than a literal like
        ``"InProgress"`` that only happens to be right for the bundled ``work`` lifecycle.

        Returns ``None`` when *item_type* isn't declared, or its lifecycle has no live
        status at all (a fully static lifecycle) — a caller building a "move it forward"
        example should fall back to describing the concept rather than naming a status.
        """
        return self._first_status_matching(item_type, lambda r: r.live)

    def first_settled_status(self, item_type: str) -> str | None:
        """The first status in *item_type*'s own lifecycle whose resolved role is
        ``settled`` — "the happy-path terminal state", generalizing a literal like
        ``"Done"`` (right only for the bundled ``work``/``bug`` lifecycles) to any
        lifecycle's own closing state, whatever it's named (e.g. ``"Accepted"`` for a
        decision, ``"Published"`` for a guide). *item_type* may also be a sub-entity kind,
        resolved against its own declared ``lifecycle`` the same way — the axis the derived
        views engine reads to tell a genuinely delivered record from one that merely settled.

        Returns ``None`` when *item_type* isn't declared, or its lifecycle reaches no
        settled status at all (shouldn't happen on a valid spec, but this is a read
        helper for generated prose, not a validator — it degrades rather than raises).
        """
        return self._first_status_matching(item_type, lambda r: r.settled)

    def first_dropped_status(self, item_type: str) -> str | None:
        """The first settled status of *item_type*'s lifecycle that is **off the spine** —
        the "considered, then dropped" exit, generalizing the bundled ``"Cancelled"`` literal
        to whatever a lifecycle names that state.

        The spine (:func:`lifecycle_spine`) is the happy path, so its own settled terminal
        (``Done``/``Accepted``/``Published``) is excluded by construction: what is left is the
        abandonment branch. Walked in :func:`lifecycle_states_in_order` (deterministic BFS)
        so generated text is byte-stable across process runs.

        ``None`` when *item_type* isn't declared, or its lifecycle has no off-spine settled
        state at all — a caller writing generated prose falls back to describing the concept
        rather than naming a status.
        """
        if item_type not in self.items:
            return None
        machine = self.machine_for(item_type)
        spine = set(lifecycle_spine(machine))
        return next(
            (
                s
                for s in lifecycle_states_in_order(machine)
                if s not in spine and self.role_for(s).settled
            ),
            None,
        )

    def statuses_with_role(self, role_name: str) -> list[str]:
        """Every declared status whose resolved role is *role_name*, in declaration order.

        The read counterpart to :meth:`status_role` for callers that need to go the other
        way — "which status means *superseded* here" — instead of naming the bundled status
        literal. Empty when no declared status resolves to that role (roles are an open
        vocabulary, so a custom spec need not declare one at all).
        """
        return [
            s for s, ss in self.statuses.items() if (ss.role or FALLBACK_ROLE_NAME) == role_name
        ]

    def live_initial(self, item_type: str) -> str:
        """The status an entry of *item_type* squads *itself* scaffolds is created at: the
        lifecycle's ``initial`` when that status is itself live, otherwise the sole live
        status. R1' (enforced in ``_validate``) is what makes this total for every roster type;
        raises a clean ``SquadsError`` naming the type when the spec handed to it does not
        satisfy the floor, never an ``IndexError``/bare ``StopIteration``, so a caller cannot
        get a silent wrong answer."""
        initial = self.initial_status(item_type)
        live = self.live_statuses(item_type)
        if initial in live:
            return initial
        if len(live) == 1:
            return next(iter(live))

        from squads._errors import SquadsError

        raise SquadsError(
            f"type {item_type!r} has a non-live initial status {initial!r} and "
            f"{len(live)} live status(es) (expected exactly one when the initial isn't "
            f"live): {sorted(live)}"
        )

    def workflow_for(self, item_type: str) -> Workflow:
        """Return the ``Workflow`` shim for the given item type.

        Raises ``KeyError`` for an undeclared *item_type* — inherits :meth:`machine_for`'s
        raise; same "no sensible empty object" shape as :meth:`collection`."""
        return Workflow.from_machine(self.machine_for(item_type))

    def _subentity_machine(self, kind: str) -> Lifecycle:
        """The lifecycle machine bound to *kind* via ``SubentityKindSpec.lifecycle``.

        Raises ``KeyError`` for an undeclared *kind* — same shape as :meth:`machine_for`."""
        return self.lifecycles[self.subentity_kinds[kind].lifecycle]

    def subentity_workflow(self, kind: str) -> Workflow:
        """Return the ``Workflow`` shim for the given sub-entity kind.

        Raises ``KeyError`` for an undeclared *kind* — inherits :meth:`_subentity_machine`'s
        raise."""
        return Workflow.from_machine(self._subentity_machine(kind))

    def subentity_initial(self, kind: str) -> str:
        """Return the initial status for the given sub-entity kind.

        Raises ``KeyError`` for an undeclared *kind* — inherits :meth:`_subentity_machine`'s
        raise."""
        return self._subentity_machine(kind).initial

    def subentity_can_transition(self, kind: str, src: str, dst: str) -> bool:
        """Return True if the given transition is valid for the given sub-entity kind.

        Raises ``KeyError`` for an undeclared *kind* — inherits :meth:`_subentity_machine`'s
        raise."""
        return self._subentity_machine(kind).can_transition(src, dst)

    def subentity_completion(self, kind: str) -> str:
        """The sub-entity/finding kind's designated completion status.

        This is what the done-toggle resolves to instead of a hardcoded ``Done``/``Fixed``
        literal. An O(1) lookup — ``_check_completion_status`` guarantees at load time that
        a validated spec's ``completion`` names a reachable, non-initial status.

        Raises ``KeyError`` for an undeclared *kind* — same shape as :meth:`collection`: a
        vocabulary lookup by a caller-supplied code with no sensible universal default.
        Every reachable call site resolves *kind* from ``item_subentity_kind`` first, which
        only ever hands back a declared kind or ``None``.
        """
        return self.subentity_kinds[kind].completion

    def subentity_plural(self, kind: str) -> str:
        """The kind's declared plural — the CLI list-verb name and container marker tag.

        Retires the static ``_SUBENTITY_PLURAL`` CLI table (kind -> plural was the last
        piece of hand-maintained sub-entity vocabulary).

        Raises ``KeyError`` for an undeclared *kind* — same shape as :meth:`collection` and
        :meth:`subentity_completion`.
        """
        return self.subentity_kinds[kind].plural

    def subentity_container_heading(self, kind: str) -> str:
        """The ``## <heading>`` line above *kind*'s container block.

        The three bundled kinds keep their exact historical wording (``_BUNDLED_CONTAINER_
        HEADINGS`` — "User Stories" isn't derivable from ``plural``: ``"stories".title()`` is
        ``"Stories"``, not ``"User Stories"``) **only while they still carry their bundled
        plural**; every other case — a renamed bundled kind, or a wholly custom one — falls
        back to the declared ``plural`` title-cased (e.g. ``"actions"`` -> ``"Actions"``).

        That condition is the whole point of the pairing. The bundled wording is an
        irregularity of one specific plural, not a property of the kind *name*: a project that
        renames story's plural to ``"outcomes"`` has said what the container is called, and
        keying the heading off the kind code alone answered "User Stories" above a container
        marked ``sq:outcomes`` — the declared value losing to a bundled default, which is what
        this docstring already promised would not happen.

        Used by every item template that hosts a container (instead of a hardcoded heading) and
        by :func:`squads._services._base.ensure_subentity_container_text`, so a rename can never
        make the two disagree.

        Raises ``KeyError`` for an undeclared *kind* — same shape as
        :meth:`subentity_plural`/:meth:`collection`.
        """
        plural = self.subentity_kinds[kind].plural
        bundled = _BUNDLED_CONTAINER_HEADINGS.get(kind)
        if bundled is not None and bundled[0] == plural:
            return bundled[1]
        return plural.title()

    def parent_hint(self, child: str) -> str:
        """Human guidance for an invalid parent (used in error messages).

        Appends the spec-declared ``RefRule.hint`` text(s) instead of re-detecting a
        literal ``fixes``/``addresses`` ref kind and emitting bundled "bug or review"
        prose — a renamed type or a custom ref rule gets its own declared hint verbatim.

        Never raises: this only ever runs to explain a refusal already in flight, so an
        undeclared *child* (``parents`` empty, no ref rules) still returns a message rather
        than crashing while building one — degrades the same way
        :meth:`item_parent_required`/:meth:`item_ref_rules` do.
        """
        ts = self.items.get(child)
        names = (" or ".join(sorted(ts.parents)) if ts else "") or "none"
        msg = f"a {child}'s parent must be of type {names}"
        hints = {r.hint for r in self.item_ref_rules(child) if r.hint}
        if hints:
            msg += "; " + "; ".join(sorted(hints))
        return msg

    # ------------------------------------------------------------------ validation

    @model_validator(mode="after")
    def _validate(self) -> WorkflowSpec:
        """Fail-closed validation."""
        all_statuses = set(self.statuses)
        all_lifecycle_names = set(self.lifecycles)
        all_types = set(self.items)
        errors: list[str] = []

        # Lifecycle initial/transition statuses exist.
        _check_lifecycle_statuses(self.lifecycles, all_statuses, errors)

        # Role-catalog checks: every status.role names a declared role; every role.color is
        # in the closed intent palette.
        _check_role_references(self.statuses, self.roles, errors)

        # Reachability.
        _check_reachability(self.lifecycles, errors)

        # Every lifecycle must be able to reach a status with a settled role.
        _check_reachable_settled(self.lifecycles, self.statuses, self.roles, errors)

        # Additional floor for a lifecycle bound to a category="roster" type: R1 (at least one
        # live status), R1' (exactly one live status when the initial isn't live),
        # and R2 (a settled, non-live status reachable from a live one) — the create-at
        # target and the retirement path the engine needs.
        _check_roster_lifecycle_floor(
            self.items, self.lifecycles, self.statuses, self.roles, errors
        )

        # ItemSpec cross-refs + uniqueness.
        _check_item_refs(self.items, all_lifecycle_names, all_types, errors)

        # Validator-catalog-membership check for each type's `validators` assignment list.
        _check_validators_assignment(self.items, errors)

        # RefRule.target referential validation: names a declared item type, and a type
        # selecting ref_rule_target_present:<T> declares a rule targeting <T>.
        _check_ref_rule_targets(self.items, errors)

        # Every capability a type declares must be reachable under the validators its own
        # category turns on — a category reassignment that contradicts itself fails here.
        _check_category_consistency(self.items, self.subentity_kinds, self.ref_kinds, errors)

        # Parent-cycle detection in the type-parent graph.
        _check_parent_cycles(self.items, errors)

        # Field-code uniqueness + reserved-key collision (per item type / sub-entity kind).
        _check_field_codes(self.items, self.subentity_kinds, errors)

        # Field->collection referential integrity + default-badge resolution.
        _check_field_collections(self.items, self.subentity_kinds, self.collections, errors)

        # SubentityKindSpec.lifecycle reference + plural/local_prefix uniqueness.
        _check_subentity_kinds(self.items, self.subentity_kinds, all_lifecycle_names, errors)

        # Each declared sub-entity kind's completion names a reachable, non-initial status.
        _check_completion_status(self.subentity_kinds, self.lifecycles, errors)

        # The per-capability floor over [ref_kinds]: bare-key shape, exactly one default,
        # exactly one preload, at most one kind per dependency direction.
        _check_ref_kinds_floor(self.ref_kinds, errors)

        # [views] referential + structural floor: source vocabulary declared, field codes
        # resolvable, group_by/order_by name a declared field.
        _check_views(self.views, self.items, self.subentity_kinds, self.ref_kinds, errors)

        # ItemSpec.views reciprocal check: every attached name resolves in [views], and a
        # subentity-source view's kind matches the attaching type's own subentity_kind.
        _check_item_views(self.items, self.views, errors)

        # Reserved-vocab floor — the spec must declare the three roster types, each with
        # category = "roster". This is the ONLY type-axis floor: every other type
        # (built-in or custom) is ordinary spec vocabulary that may be omitted, renamed, or
        # re-prefixed. A missing roster type OR one declared without category = "roster" fails
        # closed.
        spec_types = set(self.items)
        missing_roster = ROSTER_TYPES - spec_types
        if missing_roster:
            errors.append(f"spec missing required roster types: {sorted(missing_roster)}")
        errors.extend(
            f"roster type {t!r} must declare category = 'roster'"
            for t in sorted(ROSTER_TYPES & spec_types)
            if self.items[t].category != "roster"
        )

        if errors:
            from squads._errors import SquadsError

            raise SquadsError("Invalid workflow spec:\n" + "\n".join(f"  - {e}" for e in errors))

        return self
