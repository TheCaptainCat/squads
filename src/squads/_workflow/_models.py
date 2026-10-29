"""WorkflowSpec pydantic v2 value objects. The loaded spec is the sole vocabulary authority on both
axes: TOML type keys and status keys stay plain ``str`` (no enum, no closed set). The reserved
surface is exactly the three roster types (``ROSTER_TYPES``) with their fixed ``category =
"roster"``; no status name is reserved. Behaviour needing lifecycle semantics resolves through a
declared status role, never a literal name: ``WorkflowSpec.live_statuses``/``live_initial`` are the
accessors, and a lifecycle bound to a roster type must meet the floor in ``_validate`` (R1 at least
one live status; R1' exactly one live status if ``initial`` is not live; R2 a settled, non-live
status reachable from a live one).

The capability flags (``category``, ``subentity_kind``, ``parent_required``, ``ref_rules``) are
additive, and ``SubentityKindSpec.completion`` names the status a mark-done action
targets. ``StatusSpec.role`` is the sole status axis, a reference into the
``RoleSpec`` catalog (``WorkflowSpec.roles``) carrying ``settled``/``hidden``/``color``;
``is_open``/``terminal_set``/``hidden_by_default`` are derived from it, never stored.
``Badge``/``Collection``/``Field`` are the badge schema:
``ItemSpec.fields``/``SubentityKindSpec.fields`` bind a type or kind to a ``Collection`` of
``Badge``s, so "does X carry field Y" is a ``fields_for(X)`` lookup.
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

#: The three roster types the engine binds by literal name, the irreducible structural minimum (the
#: roster, the backends that write role/skill files, and the agent lifecycle reference them by
#: name). It is not a closed type vocabulary: every other type is ordinary, droppable, renamable
#: spec vocabulary.
ROSTER_ROLE = "role"
ROSTER_SKILL = "skill"
ROSTER_OPERATOR = "operator"
ROSTER_TYPES: frozenset[str] = frozenset({ROSTER_ROLE, ROSTER_SKILL, ROSTER_OPERATOR})

#: Top-level CLI verbs a declared type's name or alias must never collide with: each is a Click
#: command at ``sq``'s root not derived from an item type, so a type claiming one would lose its
#: ``sq <type> <n> <verb>`` surface to the built-in, with no traceback.
#: ``role``/``skill``/``operator`` are excluded, as they are item types whose command group
#: legitimately shares the name (the roster floor already makes that key un-droppable).
#:
#: It is hand-maintained, not imported from ``_cli/``, since ``_workflow`` sits below ``_cli``
#: (``_cli -> _services -> _models``/``_workflow``) and cannot import the Typer app without a
#: cycle; a ``tests/meta`` guard pins it against the live registered command set.
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

#: The fallback role name a status with no declared ``role`` resolves to — neutral/non-settled/
#: shown, so a custom status is fail-safe-visible until its author assigns one.
FALLBACK_ROLE_NAME = "pending"

#: The closed semantic colour-intent palette a role's ``color`` must belong to (Plane-1, in
#: ``WorkflowSpec._validate``). Roles are an open vocabulary, but colour intent is closed so every
#: client (CLI/TUI/VS Code) can map any role to a concrete colour, with a neutral fallback for an
#: unrecognised one.
COLOR_INTENTS: frozenset[str] = frozenset(
    {"positive", "danger", "warning", "muted", "neutral", "info"}
)


#: What a bare ``subentity_title_max`` selection resolves to; a type's ``subentity_title_max:<n>``
#: names another number. Callers wanting the bundled number without validator machinery read this,
#: but nothing reads it as a live threshold: :meth:`WorkflowSpec.item_subentity_title_max` is the
#: only resolver (``None`` for a type not selecting the check).
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
    """A declared ref-kind rule for a type, e.g. ``task`` -> ``fixes``/``addresses`` (drives the
    parent hint) or ``decision`` -> ``supersedes`` (gates the superseded-record warning). It is a
    rule about a kind, never a permission: :meth:`WorkflowSpec.parent_hint` appends the declared
    ``hint``, and ``sq check``'s ``supersedes_incoming`` runs only for a type declaring a
    ``supersedes`` rule, so dropping ``decision`` takes the check with it. It is not an allowlist of
    the kinds a type may carry (the navigational kinds are carried by every type and declared by
    none), and the accepted ``--kind`` vocabulary is declared spec vocabulary
    (``WorkflowSpec.ref_kinds``). What is enforced is that it can apply: the loader refuses a
    ``kind`` not in ``[ref_kinds]``, as the rule could never fire.

    ``target`` (optional) types the rule: an edge of this kind from this type is expected to point
    at the named type (``feature``'s ``implements`` targets ``contract``, disambiguating a reused
    kind). It restricts nothing by itself (``ref_rule_target_typed`` reports a mismatch if selected;
    requiredness is ``ref_rule_target_present``), and Plane-1 ``check_ref_rule_targets`` checks it
    names a declared item type, which ``_parse_ref_rules`` cannot since types are known only after
    every ``[items.*]`` block parses.
    """

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
    """One declared entry of ``[ref_kinds]``, a navigational or semantically-bound ref kind;
    identity is the dict key, never restated on the value, as for
    ``ItemSpec``/``StatusSpec``/``Lifecycle``/``Collection``. ``role`` binds engine behaviour to a
    declared semantic, not a spelling, so a project may rename or drop a kind without silently
    losing it; no ``role`` means purely navigational. ``dependency``, ``preload`` and
    ``supersession`` are read by engine sites elsewhere. ``default`` is consumed by the ref
    primitives (``split_ref``/``make_ref``): exactly one kind must carry it, since a bare ``"ID"``
    decodes to it and none would turn existing data into a load failure (the bundled spec puts it on
    ``related``), and renaming it is safe as the bare form binds to the semantic. As ``role`` is one
    field, the ``default`` kind can never also carry another role. ``direction``
    (``"blocker"``/``"dependent"``) accompanies only ``role = "dependency"``.
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
    back to the generic kind-derived placeholder (``_discussion.body_placeholder``)."""

    heading: str | None = None
    """The ``## <heading>`` line above this kind's container block; ``None`` falls back to the
    title-cased ``plural``."""

    maps_to_parent: bool = False
    """Capability flag: a sub-entity of this kind maps to a sub-entity of its host's parent, of
    the kind that parent's type hosts (:meth:`WorkflowSpec.mapping_target_kind`)."""

    completion: str
    """The status a mark-done action should target inside this kind's own ``lifecycle``:
    ``Done``/``Fixed`` for the bundled kinds. Must name a reachable, non-initial state of that
    lifecycle (enforced at load by ``check_completion_status``)."""

    fields: list[Field] = []


class LabelSpec(BaseModel):
    """Optional per-type display-label overrides, four independently optional forms
    (``singular``/``plural``/``singular_lower``/``plural_lower``). An omitted form falls back to a
    value computed from the type name (``label_for`` in ``_models/_vocab.py``, the sole fallback
    authority); a regular type needs no table, and an acronym or irregular type pins only the forms
    derivation gets wrong (an acronym's ``*_lower`` forms must stay capitalized).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    singular: str | None = None
    plural: str | None = None
    singular_lower: str | None = None
    plural_lower: str | None = None


class ItemSpec(BaseModel):
    """Vocabulary for one item type: prefix, folder, lifecycle, parents, aliases. The capability
    flags are additive and default to the common case (a non-roster work item): ``category`` selects
    the validator bundle (:data:`CATEGORY_BUNDLES`),
    ``subentity_kind``/``parent_required``/``ref_rules`` are each read by a named validator, and
    :func:`check_category_consistency` refuses a declaration whose enforcing validator the type's
    category does not turn on.
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
    sub-entities this type's own may map onto (``maps_to_parent``), and there it *is*
    enforced, hard — ``add-<kind> --story`` refuses an item whose parent is missing or is not
    this type, and ``subentity_mapping`` reports the same as a ``sq check`` error. That
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


#: The fixed three-member category catalog, read off ``ItemSpec.category``'s ``Literal`` (single-
#: sourced) so a caller validating ``--category`` or enumerating the axis cannot drift. It is not
#: spec vocabulary: an adopter cannot add, rename or remove a category, only assign one per type.
CATEGORIES: tuple[str, ...] = get_args(ItemSpec.model_fields["category"].annotation)


class ViewSource(BaseModel):
    """What a derived view resolves against, six shapes by *kind*; the first three are relations,
    the rest resolve without one. ``"ref"``: refs of the declared kind ``name`` (in ``[ref_kinds]``)
    pointing at the host, recovered by inverting stored forward edges. ``"subentity"``: the host's
    own sub-entity collection of kind ``name`` (in ``[subentity_kinds]``, which the host must host).
    ``"subtree"``: the host's descendants of type ``name`` (in ``[items]``). ``"role"``: the host's
    own merged role definition (catalog, overrides, item fields), no ``name``. ``"playbook"``: the
    playbook lane of type ``name`` (in ``[items]``) or of the host's type when absent. ``"self"``:
    the host itself, no ``name``.

    ``name`` is checked against the merged spec by ``check_views`` and is never a Python literal at
    the resolving end (``squads._views``), which reads it off the declared source.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["ref", "subentity", "subtree", "role", "playbook", "self"]
    name: str | None = None
    """Required for ``ref``/``subentity``/``subtree`` (refused at load if absent — see
    ``_validity._check_view_source``); forbidden for ``role``/``self`` (refused at load if given);
    optional for ``playbook``, where its absence means "the host's own type", resolved at read
    time rather than at load — the one kind whose name is genuinely conditional rather than
    strictly required or strictly forbidden."""


#: A view name is a bare TOML key and nothing else, reusing :data:`_BARE_TOML_KEY_RE`; enforced in
#: :func:`check_views`, not ``ViewSpec``, since the dict key is constrained. A colon would make the
#: colon-delimited disabled suffix (``squads._models._markers._DISABLED_SUFFIX``) ambiguous, and a
#: character outside :data:`~squads._sections.MARKER_RE`'s class would hide the tag from
#: ``find_markers``/``reject_markers``. ``end`` is refused too, as ``sq:view:end`` spells a close
#: marker.
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
    """*raw* (a ``[views.<name>]`` ``position`` string) parsed into a :class:`ViewPosition`: the one
    place the grammar (``"top"``, ``"bottom"``, ``"after(<regex>)"``) is recognised, so
    :func:`check_views` and the placement routine (``squads._views``) cannot disagree, and a new
    value adds one branch. It raises :class:`ValueError` for an unrecognised value or an
    ``after(...)`` pattern that does not compile, so :func:`check_views` can defer it into its
    collect-all report.
    """
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
    """One declared entry of ``[views]``: a source and where its tag is placed. Identity is the dict
    key, not restated on the value, and the presentation template resolves from that key
    (``templates/views/<name>.md.j2``), so no ``presentation`` field exists. Grouping and ordering
    are not spec grammar: a template does its own with Jinja against the source's unflattened shape
    (``squads._views``).

    ``position`` says where the placement routine re-inserts the tag on every body write: ``"top"``,
    ``"bottom"`` (default) or ``"after(<regex>)"`` (its own line after the first match's line,
    falling back to ``"bottom"`` silently). It is kept as the raw string, as ``extra="forbid"``
    checks only that it is a string, so a bad value is reported by :func:`check_views`'s collect-all
    pass instead of aborting the load; :func:`parse_view_position` types it for both that check and
    the placement routine. Several views resolving to one place go in the declared order of the
    merged ``[views]``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: ViewSource
    position: str = "bottom"
    transform: ViewTransform | None = None


class RoleSpec(BaseModel):
    """A first-class status ROLE object, the sole explicit status axis: a status references one by
    name (``StatusSpec.role``) and the role carries the behaviour. ``settled`` is a resting/end
    state; ``hidden`` is hidden from the default (non-``--all``) view; ``color`` is a semantic
    colour intent from ``COLOR_INTENTS`` (Plane-1). ``live`` declares that an entity resting there
    is the current, in-force instance, available to be spawned, loaded, cited and assigned; it is
    narrower than not-settled (the bundled ``pending``, ``attention`` and ``blocked`` roles are
    neither), defaults ``False`` because wrongly treating an item as live writes an agent into a
    host's config, and, living in vocabulary every type shares, reads sensibly on a work status too.
    ``blocked`` (the statuses mean waiting on something else) and ``deferred`` (the work is carried
    by another item the entity names; only a sub-entity lifecycle may reach it) default ``False``
    and accept only a TOML boolean. Roles are an open vocabulary and colour intent a closed palette
    with a neutral fallback.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    settled: bool
    hidden: bool = False
    color: str
    live: bool = False
    blocked: StrictBool = False
    deferred: StrictBool = False


class StatusSpec(BaseModel):
    """A role reference plus an optional sub-entity badge for one status. ``role`` names an entry in
    ``WorkflowSpec.roles``, the single source of settled/hidden/colour behaviour
    (``terminal``/``is_open`` are derived); an absent role resolves to the bundled
    ``FALLBACK_ROLE_NAME`` ("pending"), so a custom status is fail-safe-visible until assigned one.
    ``badge`` is independent, the sub-entity glyph being orthogonal to the role.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    badge: str | None = None
    role: str | None = None


# ---------------------------------------------------------------------------
# Validation helpers (extracted to keep _validate under complexity limits)
# ---------------------------------------------------------------------------


class SquadSpec(BaseModel):
    """The ``[squad]`` table: the squad-wide checks this squad selects.

    ``validators`` takes the entries a type's ``validators`` list takes (``name``,
    ``name:param``, ``name@level``, ``name:param@level``), naming selectable squad-global
    members only.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    validators: list[str] = []


class WorkflowSpec(BaseModel):
    """The full loaded workflow specification, built by ``load_workflow_spec()`` and carried by the
    caller (``Service.spec``); there is no process-global mutable or active spec (the bundled spec
    is loaded once and read-only). ``extra="forbid"`` rejects unknown TOML keys at construction, as
    the roles and playbook loaders do.
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
        """The lifecycle machine bound to *item_type*. It raises ``KeyError`` when *item_type* is
        undeclared (or a corrupt spec's lifecycle name does not resolve), as there is no sensible
        empty ``Lifecycle``, like :meth:`collection`; a caller that must survive a dropped type
        gates on ``item_type in spec.items`` first or uses a degrading wrapper such as
        :meth:`live_statuses`.
        """
        return self.lifecycles[self.items[item_type].lifecycle]

    def initial_status(self, item_type: str) -> str:
        return self.machine_for(item_type).initial

    def can_transition(self, item_type: str, src: str, dst: str) -> bool:
        return self.machine_for(item_type).can_transition(src, dst)

    def role_for(self, status: str) -> RoleSpec:
        """The resolved role object for *status*; it never raises, validated spec or not. An absent
        ``StatusSpec.role`` falls back to ``FALLBACK_ROLE_NAME`` ("pending"), and an undeclared
        status (dropped or renamed) is treated as one with no role, like the ``.get()`` idiom of
        ``_status_settled``/``_status_live``. Every settled/hidden/colour/live read routes through
        it, and ``_validate`` guarantees the fallback role is declared, so the final ``roles[...]``
        lookup is total.
        """
        spec = self.statuses.get(status)
        role_name = (spec.role if spec else None) or FALLBACK_ROLE_NAME
        return self.roles[role_name]

    def is_open(self, status: str) -> bool:
        return not self.role_for(status).settled

    def hidden_by_default(self, item_type: str, status: str) -> bool:
        """True when an item of *item_type* at *status* is hidden from the default (non-``--all``)
        ``sq list``/``sq tree``, purely role-derived (``role_for(status).hidden``) with no category
        branch: a ``done`` role (``Done``, ``Verified``) hides while an ``in_force`` role
        (``Accepted``, ``Published``) is settled yet visible, which a bare ``terminal`` flag could
        not express. It never raises: an undeclared status defaults to not-hidden via the
        ``pending`` fallback.
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
        """The ``subentity_title_max`` threshold *item_type* runs, or ``None`` when its effective
        validator set lacks the member (or the type is undeclared): a ``:<n>`` selection gives ``n``
        and a bare one :data:`DEFAULT_SUBENTITY_TITLE_MAX`. It is the one resolver for ``sq check``
        (``_services/_validators.py::_subentity_title_max``) and the create-time advisory
        (``_services/_subentities.py``), so they agree on whether the check runs and at what number.
        """
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
        """The one declared ``[ref_kinds]`` entry carrying ``role = "default"``, which a bare
        ``"ID"`` ref (:func:`~squads._models._item.split_ref`'s unspelled ``""``) means. It raises
        ``SquadsError`` when the merged spec declares zero or several: the per-capability floor
        keeps it total at merge time, but a bare ref is undecodable without exactly one, so the
        accessor fails closed rather than guessing.
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
        """The one declared ``[ref_kinds]`` entry carrying ``role = "preload"``, a skill's forward
        edge to the role that preloads it, inverted by the roster resolver. Like
        :meth:`default_ref_kind` it raises ``SquadsError`` for zero or several, which
        :func:`check_ref_kinds_floor` prevents at merge time, rather than guessing.
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
        """States of *item_type*'s own lifecycle whose resolved role carries the ``live`` flag: the
        predicate every "is this entry on offer" caller uses instead of a status or role literal
        (``item.status in spec.live_statuses(item.type)``), with fallback resolution via
        ``role_for`` (the fallback role is not live). It is ``frozenset()`` for an undeclared type,
        gating before :meth:`machine_for` so a dropped type does not crash the caller.
        """
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
        """Shared walk for :meth:`first_active_status`/:meth:`first_settled_status`: the first
        status on *item_type*'s lifecycle spine (:func:`lifecycle_spine`) whose role satisfies
        *predicate*. It uses the spine, not BFS order, since an exception branch like ``Cancelled``
        can resolve settled at a shallower depth than the happy-path terminal. *item_type* may also
        be a sub-entity kind (:meth:`_machine_for_type_or_kind`'s dual namespace), as the views
        engine walks a record's own kind; ``None`` when it names neither or nothing on the spine
        matches.
        """
        machine = self._machine_for_type_or_kind(item_type)
        if machine is None:
            return None
        for state in lifecycle_spine(machine):
            if predicate(self.role_for(state)):
                return state
        return None

    def first_active_status(self, item_type: str) -> str | None:
        """The first status in *item_type*'s lifecycle whose role carries ``live``: "the state you
        move an item to once you start working it", derived from the spec rather than a literal like
        ``"InProgress"`` that suits only the bundled ``work`` lifecycle. ``None`` when the type is
        undeclared or has no live status, and a caller building a "move it forward" example should
        then describe the concept rather than name a status.
        """
        return self._first_status_matching(item_type, lambda r: r.live)

    def first_settled_status(self, item_type: str) -> str | None:
        """The first status in *item_type*'s lifecycle whose role is ``settled``: "the happy-path
        terminal state", generalising ``"Done"`` to a lifecycle's own closing state (``"Accepted"``
        for a decision, ``"Published"`` for a guide). *item_type* may be a sub-entity kind, resolved
        against its declared ``lifecycle``, which the views engine uses to tell a delivered record
        from one that merely settled. ``None`` when undeclared or no settled status is reached; it
        degrades, as a read helper for generated prose rather than a validator.
        """
        return self._first_status_matching(item_type, lambda r: r.settled)

    def is_delivered(self, item_type: str, status: str) -> bool:
        """Whether *status* is *item_type*'s delivery target, the happy-path settled terminal
        :meth:`first_settled_status` names, telling a finished record (``Done``, ``Accepted``,
        ``Verified``) from one settled another way (``Cancelled``, ``Superseded``, off the spine).
        It takes a bare ``(item_type, status)`` pair so a template can call it (``{{
        spec.is_delivered(item.type, item.status) }}``, as
        ``templates/views/milestone_rollup.md.j2`` does), and returns ``False``, never raising, when
        the type is undeclared or no settled status is reached.
        """
        return status == self.first_settled_status(item_type)

    def first_dropped_status(self, item_type: str) -> str | None:
        """The first settled status of *item_type*'s lifecycle that is off the spine: the
        "considered, then dropped" exit, generalising ``"Cancelled"``. The spine's own settled
        terminal is excluded by construction, and the walk is :func:`lifecycle_states_in_order`
        (deterministic BFS) so generated text is byte-stable across runs. ``None`` when the type is
        undeclared or has no off-spine settled state, and a caller writing prose should then
        describe the concept.
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
        """The status an entry of *item_type* that squads itself scaffolds is created at: the
        lifecycle's ``initial`` when live, otherwise the sole live status, which R1' (in
        ``_validate``) makes total for every roster type. It raises a clean ``SquadsError`` naming
        the type when the spec does not satisfy the floor, never an
        ``IndexError``/``StopIteration``, so a caller cannot get a silent wrong answer.
        """
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

    def subentity_plural(self, kind: str) -> str:
        """The kind's declared plural — the CLI list-verb name and container marker tag.

        Retires the static ``_SUBENTITY_PLURAL`` CLI table (kind -> plural was the last
        piece of hand-maintained sub-entity vocabulary).

        Raises ``KeyError`` for an undeclared *kind* — same shape as :meth:`collection`.
        """
        return self.subentity_kinds[kind].plural

    def subentity_container_heading(self, kind: str) -> str:
        """The ``## <heading>`` line above *kind*'s container block: the declared ``heading``, else
        the ``plural`` title-cased (``"actions"`` -> ``"Actions"``). Item templates and
        :func:`squads._services._base.ensure_subentity_container_text` share it, and it raises
        ``KeyError`` for an undeclared *kind* like :meth:`subentity_plural`.
        """
        ks = self.subentity_kinds[kind]
        return ks.heading if ks.heading is not None else ks.plural.title()

    def mapping_target_kind(self, kind: str) -> str | None:
        """The kind *kind*'s sub-entities map onto: the kind hosted by the ``parent_required`` type
        of the type that hosts *kind*. ``None`` when *kind* does not map or no such kind resolves
        (spec load refuses the latter for a mapping kind).
        """
        ks = self.subentity_kinds.get(kind)
        if ks is None or not ks.maps_to_parent:
            return None
        for ts in self.items.values():
            if ts.subentity_kind == kind and ts.parent_required is not None:
                parent = self.items.get(ts.parent_required)
                return parent.subentity_kind if parent is not None else None
        return None

    def parent_hint(self, child: str) -> str:
        """Human guidance for an invalid parent, for error messages: it appends the spec-declared
        ``RefRule.hint`` text(s) rather than re-detecting a literal ``fixes``/``addresses`` kind
        with bundled prose, so a renamed type or custom rule gets its own hint. It never raises,
        since it only explains a refusal in flight: an undeclared *child* still yields a message,
        degrading like :meth:`item_parent_required`/:meth:`item_ref_rules`.
        """
        ts = self.items.get(child)
        names = (" or ".join(sorted(ts.parents)) if ts else "") or "none"
        msg = f"the parent of {child} items must be of type {names}"
        hints = {r.hint for r in self.item_ref_rules(child) if r.hint}
        if hints:
            msg += "; " + "; ".join(sorted(hints))
        return msg

    # ------------------------------------------------------------------ validation

    @model_validator(mode="after")
    def _validate(self) -> WorkflowSpec:
        """Fail-closed validation."""
        from squads._workflow._derived_names import check_derived_names
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

        # Additional roster floor: R1 (a live status), R1' (exactly one live status when initial is
        # not live) and R2 (a settled, non-live status reachable from a live one), the create-at
        # target and retirement path the engine needs.
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

        # Derived flags and import keys against the fixed names of their surface.
        check_derived_names(self, errors)

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

        # Reserved-vocab floor: the spec must declare the three roster types, each with category =
        # "roster". It is the only type-axis floor, every other type being ordinary vocabulary that
        # may be omitted, renamed or re-prefixed; a missing roster type or one without that category
        # fails closed.
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
