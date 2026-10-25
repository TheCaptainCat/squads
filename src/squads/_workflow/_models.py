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
import re
from collections.abc import Callable
from dataclasses import dataclass
from re import compile as re_compile
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, StrictBool, model_validator

from squads._models._attributes import AttributeSpec
from squads._workflow._lifecycle_order import lifecycle_spine, lifecycle_states_in_order
from squads._workflow._validator_names import (
    effective_bare_validators,
    parse_positive_int,
    parse_validator_entry,
)

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


#: What a bare ``subentity_title_max`` selection resolves to; a type's own
#: ``subentity_title_max:<n>`` entry names a different number. Callers that want "the bundled
#: number" without touching validator machinery (e.g. a test fixture building an over-threshold
#: title) read this constant; nothing reads it as a live threshold --
#: :meth:`WorkflowSpec.item_subentity_title_max` is the only resolver ``sq check`` and the
#: create-time advisory use, and it answers ``None`` for a type that does not select the check.
DEFAULT_SUBENTITY_TITLE_MAX: int = 120


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
    ``implements`` to a ``decision`` is unaffected unless its type selects
    ``ref_rule_target_typed``, which reports such an edge); requiredness stays with
    ``ref_rule_target_present``. Referential validation (Plane-1,
    ``check_ref_rule_targets``) checks ``target`` names a declared item type —
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

    def declares(self, value: object) -> bool:
        """Whether *value* is one of this collection's codes; anything but a string is not."""
        return isinstance(value, str) and value in self.badge_codes


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
    by ``check_completion_status``)."""

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
    read by a named validator, and :func:`check_category_consistency` refuses a declaration
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

    attributes: dict[str, AttributeSpec] = {}
    """The non-badge frontmatter keys this type declares, by name: the value ``kind``, whether
    ``sq check`` requires it, and whether ``sq update --set`` may write it. A key the file carries
    that no declaration names is kept untouched. Badge fields stay in ``fields``."""

    validators: list[str] = []
    """Per-type additions to the category's default validator bundle (the pluggable-validator
    decision's assignment surface) — **extend-only** over the bundle: a type may add a
    validator, never deselect a category default. Resolved at call time via
    ``_services._validators.effective_validator_names(category, extra=validators)``; every
    entry's bare name must name a member of ``VALIDATOR_NAMES`` (Plane-1, enforced below).

    Each entry is ``name``, ``name:param``, ``name@level``, or ``name:param@level``
    (:func:`parse_validator_entry` is the one parser for this grammar). A ``:<param>`` suffix
    is only well-formed on a name in ``PARAMETERIZED_VALIDATOR_NAMES``. An ``@<level>`` suffix
    declares the member's level for this type — ``error`` or ``warn``
    (:data:`VALIDATOR_LEVELS`), no lower than the member's declared floor if it has one
    (:data:`VALIDATOR_LEVEL_FLOOR`) — and defaults to the bundled
    :data:`DEFAULT_VALIDATOR_LEVEL` when omitted. Naming an already-bundled member here with a
    suffix overrides its bundled entry rather than running it twice
    (:func:`effective_validator_names`'s de-duplication)."""


#: The fixed, closed three-member category catalog — read off ``ItemSpec.category``'s own
#: ``Literal`` annotation (single-sourced) rather than a hand-duplicated tuple, so a caller
#: validating a ``--category`` value (or enumerating the axis for a filter/help text) never
#: drifts from the type actually declared above. Not spec vocabulary: an adopter cannot add,
#: rename, or remove a category — the catalog is closed, only its per-type assignment is open.
CATEGORIES: tuple[str, ...] = get_args(ItemSpec.model_fields["category"].annotation)


class ViewSource(BaseModel):
    """What a derived view resolves against — six shapes, named by *kind*. The first three are
    relations (a join over other items); the last three resolve without one:

    - ``"ref"`` — refs of the declared kind named by ``name`` pointing at the item the view is
      resolved against, recovered by inverting stored forward edges. ``name`` must be a
      declared entry of ``[ref_kinds]``.
    - ``"subentity"`` — the projecting item's own sub-entity collection of the kind named by
      ``name``. ``name`` must be a declared entry of ``[subentity_kinds]``, and the item the
      view resolves against must itself host that kind.
    - ``"subtree"`` — the projecting item's descendants whose type is the one named by
      ``name``. ``name`` must be a declared entry of ``[items]``.
    - ``"role"`` — the projecting item's own merged role definition (catalog + overrides +
      item fields). Takes no ``name``: a role source always reads the host, never another
      declared role.
    - ``"playbook"`` — the playbook lane of the type named by ``name``, or the projecting
      item's own type when ``name`` is absent. ``name``, when given, must be a declared entry
      of ``[items]``.
    - ``"self"`` — the projecting item itself, with no join at all. Takes no ``name``.

    ``name`` is checked against the merged spec by the same referential pass every other
    workflow-spec cross-reference goes through (see ``check_views``); it is never a Python
    literal at the resolving end (``squads._views``), which reads it off the declared source
    instead.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["ref", "subentity", "subtree", "role", "playbook", "self"]
    name: str | None = None
    """Required for ``ref``/``subentity``/``subtree`` (refused at load if absent — see
    ``_validity._check_view_source``); forbidden for ``role``/``self`` (refused at load if given);
    optional for ``playbook``, where its absence means "the host's own type", resolved at read
    time rather than at load — the one kind whose name is genuinely conditional rather than
    strictly required or strictly forbidden."""


#: A view name is a bare TOML key and nothing else — reuses
#: :data:`_BARE_TOML_KEY_RE`'s own grammar (defined below, alongside ``[ref_kinds]``'s
#: identical floor) rather than a second copy of the same pattern; enforced at load in
#: :func:`check_views` rather than by ``ViewSpec`` itself, since the dict *key* is what is
#: being constrained, not any field on the value. Two reasons, both load-bearing: the
#: disabled-state suffix is colon-delimited (``squads._models._markers._DISABLED_SUFFIX``), so a
#: colon inside the name itself would make that suffix ambiguous; and a character outside
#: :data:`~squads._sections.MARKER_RE`'s class (word characters, ``:``, ``-``) would make the
#: tag invisible to ``find_markers``/``reject_markers``, the property this whole family depends
#: on. ``end`` is refused too: ``sq:view:end`` spells a close marker, and the marker-pairing
#: scan would count it as one.
RESERVED_VIEW_NAME = "end"


@dataclass(frozen=True)
class ViewPosition:
    """A view's parsed ``position`` — never a raw string carried past
    :func:`parse_view_position`. ``kind`` is one of ``"top"``/``"bottom"``/``"after"``;
    ``pattern`` is the compiled ``after(<regex>)`` pattern, ``None`` for the other two kinds."""

    kind: Literal["top", "bottom", "after"]
    pattern: re.Pattern[str] | None = None


#: ``position = "after(<regex>)"`` — captures the inner pattern text. Anchored so a trailing
#: typo (``"after(foo)x"``) is refused rather than silently accepted as if the extra text were
#: part of the pattern.
_AFTER_POSITION_RE = re_compile(r"^after\((?P<pattern>.*)\)$")


def parse_view_position(raw: str) -> ViewPosition:
    """*raw* (a ``[views.<name>]`` entry's ``position`` string) parsed into a
    :class:`ViewPosition` — the one place the grammar (``"top"``, ``"bottom"``,
    ``"after(<regex>)"``) is recognised, so :func:`check_views` (validating) and the
    placement routine (``squads._views``, consuming) can never disagree about what a position
    string means. Dispatches on shape rather than growing an ``if/elif`` chain callers repeat,
    so a later grammar value adds one branch here, never a second parser.

    Raises :class:`ValueError` — never a bare string return — for an unrecognised value or an
    ``after(...)`` pattern that fails to compile, so callers that must defer the failure into a
    collect-all report (:func:`check_views`) catch it, and a runtime caller that only ever
    sees an already-validated spec is free not to."""
    if raw == "top":
        return ViewPosition("top")
    if raw == "bottom":
        return ViewPosition("bottom")
    m = _AFTER_POSITION_RE.fullmatch(raw)
    if m is not None:
        try:
            pattern = re.compile(m.group("pattern"), re.MULTILINE)
        except re.error as exc:
            raise ValueError(f"position {raw!r}: pattern does not compile: {exc}") from exc
        return ViewPosition("after", pattern)
    raise ValueError(f"position {raw!r}: not one of 'top', 'bottom', 'after(<regex>)'")


class ViewTransform(BaseModel):
    """A view's declared transform: ``function`` in a bundled ``module`` (a dotted import under
    ``squads.``) or in an override ``path`` (relative to ``.overrides/``, confined to it).
    Exactly one of ``module``/``path``; shape is checked by :func:`check_views`, and nothing
    here touches the filesystem or imports."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    module: str | None = None
    path: str | None = None
    function: str


class ViewSpec(BaseModel):
    """One declared entry of ``[views]`` — a source, and where its tag is placed.

    Identity is the dict key on ``WorkflowSpec.views``, never restated on the value (the
    convention ``ItemSpec``/``StatusSpec``/``Lifecycle``/``Collection``/``RefKindSpec`` already
    follow); a view's presentation template resolves from that same key
    (``templates/views/<name>.md.j2``), so no ``presentation`` field is declared either — the
    template path *is* the declared identity, the same way the dict key already is.

    Grouping and ordering are not spec grammar — a presentation template does its own with
    Jinja's ``groupby``/``sort``/``selectattr`` under ``StrictUndefined``, against the source's
    own unflattened shape (see ``squads._views``).

    ``position`` says where the placement routine re-inserts
    this view's tag on every body write: ``"top"`` (the region's first line), ``"bottom"`` (the
    default — its last line), or ``"after(<regex>)"`` (its own line after the line where the
    pattern's first match against the region's prose ends; no match falls back to ``"bottom"``
    silently). Kept here as the **raw string** — ``extra="forbid"`` on this model only checks
    it is a string, never that it parses — so an unrecognised value or a pattern that fails to
    compile is reported through :func:`check_views`'s collect-all pass rather than aborting
    the whole load at the first bad view; :func:`parse_view_position` is where it turns into a
    typed :class:`ViewPosition`, called both by that check and by the placement routine, never
    hand-parsed a second way at either call site. ``position`` carries no order key: several
    views resolving to the same place go in the declared order of the merged ``[views]``
    mapping (``squads._views``'s placement routine)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: ViewSource
    position: str = "bottom"
    transform: ViewTransform | None = None


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
    - ``blocked`` — do the role's statuses mean the item is waiting on something else? Defaults
      ``False``; unlike the other booleans it accepts only a TOML boolean.
    - ``deferred`` — is the work of an entity resting in this role's statuses carried by another
      item that the entity names? Defaults ``False`` and accepts only a TOML boolean. Only a
      sub-entity lifecycle may reach such a status.

    Roles are an OPEN vocabulary (an adopter may declare custom roles); colour intent is a
    CLOSED palette so every client can render any role safely with a neutral fallback.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    settled: bool
    hidden: bool = False
    color: str
    live: bool = False
    blocked: StrictBool = False
    deferred: StrictBool = False


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


class SquadSpec(BaseModel):
    """The ``[squad]`` table: the squad-wide checks this squad selects.

    ``validators`` takes the entries a type's ``validators`` list takes (``name``,
    ``name:param``, ``name@level``, ``name:param@level``), naming selectable squad-global
    members only.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    validators: list[str] = []


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
    #: bundled defaults).
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
    #: Declared derived views, keyed by view name — a source and nothing else (no presentation
    #: field either: the key IS the presentation template's identity, resolved by
    #: ``squads._views`` at ``templates/views/<name>.md.j2``). See :class:`ViewSpec`.
    views: dict[str, ViewSpec] = {}
    #: The squad-wide validator selection. See :class:`SquadSpec`.
    squad: SquadSpec = SquadSpec()

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

    def item_subentity_title_max(self, item_type: str) -> int | None:
        """The ``subentity_title_max`` threshold *item_type* runs, or ``None`` when its
        effective validator set does not hold the member (or the type is not declared). A
        selection carrying ``:<n>`` gives ``n``; a bare selection gives
        :data:`DEFAULT_SUBENTITY_TITLE_MAX`. The one resolver both ``sq check``
        (``_services/_validators.py::_subentity_title_max``) and the create-time advisory
        (``_services/_subentities.py``) ask, so the two never disagree on whether the check
        runs or at what number."""
        ts = self.items.get(item_type)
        if ts is None or "subentity_title_max" not in effective_bare_validators(ts):
            return None
        for entry in ts.validators:
            bare, param, _level = parse_validator_entry(entry)
            if bare == "subentity_title_max" and param is not None:
                return int(param)
        return DEFAULT_SUBENTITY_TITLE_MAX

    def item_title_max(self, item_type: str) -> int | None:
        """The ``item_title_max`` threshold *item_type* runs, or ``None`` when its effective
        validator set does not hold the member (or the type is not declared). The number is the
        type's own ``item_title_max:<n>`` entry."""
        ts = self.items.get(item_type)
        if ts is None:
            return None
        for entry in ts.validators:
            bare, param, _level = parse_validator_entry(entry)
            if bare == "item_title_max" and param is not None:
                return parse_positive_int(param)
        return None

    def item_external_id_pattern(self, item_type: str) -> str | None:
        """The ``external_id_not_in_title`` pattern *item_type* selects, or ``None`` when it does
        not select the check (or the type is not declared). The whole text after the entry's
        first colon, further colons included."""
        ts = self.items.get(item_type)
        if ts is None:
            return None
        for entry in ts.validators:
            bare, param, _level = parse_validator_entry(entry)
            if bare == "external_id_not_in_title":
                return param
        return None

    def item_attributes(self, item_type: str) -> dict[str, AttributeSpec]:
        """The attributes *item_type* declares, by name (empty for an undeclared type)."""
        ts = self.items.get(item_type)
        return dict(ts.attributes) if ts else {}

    def item_ref_rules(self, item_type: str) -> list[RefRule]:
        """Declared ref-kind rules for the type (e.g. fixes/addresses/supersedes).

        Also ``[]`` when *item_type* isn't declared — no rules to report for a
        dropped/renamed type, same shape as :meth:`item_attributes`/:meth:`fields_for`."""
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
        per-capability floor (:func:`check_ref_kinds_floor`) keeps this total at merge time;
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

    def is_delivered(self, item_type: str, status: str) -> bool:
        """Whether *status* is *item_type*'s own delivery target — the happy-path settled
        terminal :meth:`first_settled_status` names, not merely a settled status. Tells a
        genuinely finished record (``Done``, ``Accepted``, ``Verified`` — whatever a
        lifecycle's own spine terminal is named) from one that settled some *other* way
        (``Cancelled``, ``Superseded`` — off the spine): both are settled, only one is
        delivered.

        Takes a bare ``(item_type, status)`` pair — no resolved record required — so a
        template can call it directly (``{{ spec.is_delivered(item.type, item.status) }}``,
        e.g. from ``templates/views/milestone_rollup.md.j2``) the same way
        :meth:`first_settled_status` itself needs nothing but the two strings.

        ``False`` (never a raise) when *item_type* isn't declared, or its lifecycle reaches no
        settled status at all — the same total-degrade contract :meth:`first_settled_status`
        already has, since neither case legitimately has a delivered record to report.
        """
        return status == self.first_settled_status(item_type)

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

    def subentity_deferred_statuses(self, kind: str) -> frozenset[str]:
        """The statuses of *kind*'s lifecycle whose role declares ``deferred``.

        Raises ``KeyError`` for an undeclared *kind* — inherits :meth:`_subentity_machine`'s
        raise."""
        machine = self._subentity_machine(kind)
        return frozenset(s for s in machine.states if self.role_for(s).deferred)

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
        literal. An O(1) lookup — ``check_completion_status`` guarantees at load time that
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

        The three bundled kinds keep their exact bundled wording (``_BUNDLED_CONTAINER_
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
        from squads._workflow._validity import (
            check_attributes,
            check_category_consistency,
            check_completion_status,
            check_field_codes,
            check_field_collections,
            check_item_lifecycles_avoid_deferred,
            check_item_refs,
            check_lifecycle_statuses,
            check_parent_cycles,
            check_reachability,
            check_reachable_settled,
            check_ref_kinds_floor,
            check_ref_rule_targets,
            check_role_references,
            check_roster_lifecycle_floor,
            check_selections_that_cannot_fire,
            check_squad_validators,
            check_subentity_kinds,
            check_validators_assignment,
            check_views,
        )

        all_statuses = set(self.statuses)
        all_lifecycle_names = set(self.lifecycles)
        all_types = set(self.items)
        errors: list[str] = []

        # Lifecycle initial/transition statuses exist.
        check_lifecycle_statuses(self.lifecycles, all_statuses, errors)

        # Role-catalog checks: every status.role names a declared role; every role.color is
        # in the closed intent palette.
        check_role_references(self.statuses, self.roles, errors)

        # Reachability.
        check_reachability(self.lifecycles, errors)

        # Every lifecycle must be able to reach a status with a settled role.
        check_reachable_settled(self.lifecycles, self.statuses, self.roles, errors)

        # Additional floor for a lifecycle bound to a category="roster" type: R1 (at least one
        # live status), R1' (exactly one live status when the initial isn't live),
        # and R2 (a settled, non-live status reachable from a live one) — the create-at
        # target and the retirement path the engine needs.
        check_roster_lifecycle_floor(self.items, self.lifecycles, self.statuses, self.roles, errors)

        check_item_lifecycles_avoid_deferred(
            self.items, self.lifecycles, self.statuses, self.roles, errors
        )

        # ItemSpec cross-refs + uniqueness.
        check_item_refs(self.items, all_lifecycle_names, all_types, errors)

        # Validator-catalog-membership check for each type's `validators` assignment list.
        check_validators_assignment(self.items, errors)

        # RefRule.target referential validation: names a declared item type, and a type
        # selecting ref_rule_target_present:<T> declares a rule targeting <T>.
        check_ref_rule_targets(self.items, errors)

        # A selected check the spec's own declarations make unable to fire is refused.
        check_selections_that_cannot_fire(
            self.items, self.lifecycles, self.statuses, self.roles, self.ref_kinds, errors
        )

        check_squad_validators(
            self.squad,
            self.items,
            self.lifecycles,
            self.statuses,
            self.roles,
            self.ref_kinds,
            errors,
        )

        # Every capability a type declares must be reachable under the validators its own
        # category turns on — a category reassignment that contradicts itself fails here.
        check_category_consistency(self.items, self.subentity_kinds, self.ref_kinds, errors)

        # Parent-cycle detection in the type-parent graph.
        check_parent_cycles(self.items, errors)

        # Field-code uniqueness + reserved-key collision (per item type / sub-entity kind).
        check_field_codes(self.items, self.subentity_kinds, errors)

        # Attribute names + the pinned roster attributes.
        check_attributes(self.items, errors)

        # Field->collection referential integrity + default-badge resolution.
        check_field_collections(self.items, self.subentity_kinds, self.collections, errors)

        # SubentityKindSpec.lifecycle reference + plural/local_prefix uniqueness.
        check_subentity_kinds(self.items, self.subentity_kinds, all_lifecycle_names, errors)

        # Each declared sub-entity kind's completion names a reachable, non-initial status.
        check_completion_status(self.subentity_kinds, self.lifecycles, errors)

        # The per-capability floor over [ref_kinds]: bare-key shape, exactly one default,
        # exactly one preload, at most one kind per dependency direction.
        check_ref_kinds_floor(self.ref_kinds, errors)

        # [views] referential floor: a declared source's name resolves against its kind's
        # vocabulary.
        check_views(self.views, self.items, self.subentity_kinds, self.ref_kinds, errors)

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
