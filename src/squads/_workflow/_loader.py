"""Load and validate the workflow spec, merging a project override that may shadow (not only add to)
the bundled vocabulary. ``load_workflow_spec()`` is the single entry point: with no ``squad_dir`` it
reads the bundled ``workflow.toml`` via ``importlib.resources``, parses it with ``tomllib`` (type
and status keys stay plain ``str``), builds the derived indexes and runs
``WorkflowSpec.validate()``; an invalid bundled spec raises ``SquadsError`` (fail closed).

With a ``squad_dir``, ``<squad_dir>/.overrides/workflow.toml`` is merged over the bundled default by
the loader-agnostic engine (``squads._specmerge``) at the raw parsed-TOML layer, before any model is
built: splats resolve against the bundled mapping, the override deep-merges leaf by leaf (a
hand-written value replaces its counterpart, which is what makes it shadowing), and ``[selected]``
shrinks named sections and is stripped. The engine owns no floor, so these stay here:

1. The roster type-key lock (``_collect_floor_violations``), on the raw merged mapping before any
   model: the roster keys (``role``/``skill``/``operator``) must survive with
   ``category = "roster"`` and no other key may claim it. It rests on the key set and ``category``
   immobility only, never ``prefix``, which is ordinary customisation.
2. Structural and referential validation (``_build_spec`` -> ``WorkflowSpec._validate``): the
   universal lifecycle floor and the roster R1/R1'/R2 clauses apply to the merged mapping, and a
   violation tracing to a ``[selected]`` drop is annotated with that provenance
   (``_annotate_deselections``), since an adopter cannot fix a cause they cannot see.
3. The live-index cross-check (``validate_against_index`` and ``..._fail_closed``), last, so a drop
   stranding a live item fails closed listing the IDs. It also gates prefix/folder and
   badge-collection changes against a live corpus (declared ``prefix``/``folder`` must match what
   the items were written under, and each stored badge value must still name a code in its
   collection), on a walk that already exists, since such a spec is valid in the abstract and wrong
   only for this corpus.

``lint_workflow_spec(squad_dir)`` runs all of this in collect-all mode for ``sq workflow lint``,
returning ``(level, location, message, fix_hint)`` tuples and never raising.
``validate_against_index_fail_closed(spec, squad_dir, bundled=...)`` is the enforcement point
``compose_service`` calls: it reads the index synchronously and raises ``SquadsError`` listing every
offending ID when the spec drops a type or status live items use or misaligns a type's
prefix/folder; lint reports the same findings without aborting.
"""

import tomllib
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from re import DOTALL, MULTILINE
from re import compile as re_compile
from typing import Any, cast

from pydantic import BaseModel

from squads._errors import SquadsError

# Import-direction note: `_overrides/_service.py` imports this module, so `_workflow` and
# `_overrides` form a package-level cycle but no module-level one: `_overrides._manifest` (home of
# `artifact_changed_since`) imports only `squads._util`, so loading it as a leaf never observes a
# partially-initialised module. `_interactions/_loader.py` takes the same edge for the playbook's
# stamp obligation.
from squads._specload import (
    OverrideFiles,
    OverrideMessages,
    OverrideReadError,
    SpecDocument,
    bundled_bytes,
    bundled_raw,
    bundled_text,
    load_override,
    merge_collecting,
    override_mapping,
    override_present,
    override_text,
    read_override,
)
from squads._specmerge import (
    Deselection,
    MergeViolation,
    RawMapping,
    describe_spec_error,
    spec_error_sentences,
)
from squads._workflow._models import (
    ROSTER_TYPES,
    Badge,
    Collection,
    Field,
    ItemSpec,
    Lifecycle,
    RefKindSpec,
    RefRule,
    RoleSpec,
    SquadSpec,
    StatusSpec,
    SubentityKindSpec,
    ViewSource,
    ViewSpec,
    WorkflowSpec,
)
from squads._workflow._validator_names import parse_validator_entry

#: Canonical location for the project workflow override (relative to squad_dir).
WORKFLOW_OVERRIDE_FILENAME = ".overrides/workflow.toml"

#: The workflow document's closed top-level section-key space, enforced on the raw mapping by the
#: merge engine before any model is built. ``[selected]`` may name every one but ``squad``
#: (:data:`WORKFLOW_SELECTABLE_SECTIONS`), and ``selected`` itself is accepted by the engine and
#: needs no entry here.
WORKFLOW_TOP_LEVEL_SECTIONS: frozenset[str] = frozenset(
    {
        "items",
        "statuses",
        "lifecycles",
        "collections",
        "subentity_kinds",
        "roles",
        "ref_kinds",
        "views",
        "squad",
    }
)

#: The sections ``[selected]`` may name: every top-level section except ``squad``, whose table
#: holds one list and has no entries to drop (refused by :func:`_selected_squad_violations`).
WORKFLOW_SELECTABLE_SECTIONS: frozenset[str] = WORKFLOW_TOP_LEVEL_SECTIONS - {"squad"}

#: Generic fix hint attached to every roster-lock finding in collect mode — the lock has exactly
#: one remedy shape (revert the key/category change), unlike a structural violation where the
#: fix varies per clause.
_ROSTER_LOCK_FIX_HINT = (
    "role/skill/operator are locked by key identity and fixed category; revert "
    "the change in .overrides/workflow.toml."
)

#: The retired view-declaration keys, each with its own reason, since what each did is the
#: template's job but which job differs (one shared sentence would misdescribe ``fields``, a column
#: list, as sort/group). A ``[views.<name>]`` table declares only ``source``. They are scanned at
#: any depth under a view's table, since one written under ``source`` would otherwise fall through
#: to ``ViewSource``'s generic ``extra="forbid"``.
_RETIRED_VIEW_KEY_REASONS: dict[str, str] = {
    "fields": (
        "choosing and labelling which columns render is the presentation template's own job "
        "now — write the fields a resolved record actually has directly in Jinja"
    ),
    "group_by": "grouping is the presentation template's own job now (Jinja `groupby`)",
    "order_by": "ordering is the presentation template's own job now (Jinja `sort`)",
}

#: The retired item-type view-attachment key: a view is placed with a ``sq:view:<name>`` tag
#: in a document body, never attached to a type by declaring it under ``[items.<type>]``.
_RETIRED_ITEM_VIEWS_KEY = "views"


def _scan_retired_view_grammar_keys(table: RawMapping, path: str) -> list[str]:
    """Every dotted path under *path* (a ``[views.<name>]`` table) naming a key in
    :data:`_RETIRED_VIEW_KEY_REASONS`, at any nesting depth. Runs on the raw, unmerged table,
    so a plain value, an inline table, an array, an empty value and a splat token in value
    position are all caught the same way — only the *key* is retired, not any particular shape
    of its value."""
    hits: list[str] = []
    for key, value in table.items():
        dotted = f"{path}.{key}"
        if key in _RETIRED_VIEW_KEY_REASONS:
            hits.append(dotted)
        if isinstance(value, dict):
            hits.extend(_scan_retired_view_grammar_keys(cast(RawMapping, value), dotted))
    return hits


def _override_transform_violations(raw_override: RawMapping, origin: str) -> list[MergeViolation]:
    """Every ``views.<name>.transform`` table the override writes that names ``module`` or
    lacks ``path`` or ``function``: an override reaches code through a file under
    ``.overrides/``, never through an import. A splat-ref string is not a table and passes."""
    violations: list[MergeViolation] = []
    views_section = raw_override.get("views")
    if not isinstance(views_section, dict):
        return violations
    for name, table in cast(RawMapping, views_section).items():
        transform = cast(RawMapping, table).get("transform") if isinstance(table, dict) else None
        if not isinstance(transform, dict):
            continue
        keys = set(cast(RawMapping, transform))
        if "module" in keys or not {"path", "function"} <= keys:
            violations.append(
                MergeViolation(
                    origin,
                    f"views.{name}.transform",
                    "an override transform is `{ path, function }` and may not name `module`",
                    'write `transform = { path = "transforms/<file>.py", function = "<name>" }` '
                    "with the file under .overrides/.",
                )
            )
    return violations


def _drop_inherited_unreachable_transitions(merged: RawMapping, override: RawMapping) -> None:
    """Drop a bundled transition key the override never names when the override redeclared its
    lifecycle's transitions and nothing now leads to the key's state. The state then leaves that
    machine instead of lingering unreachable; an adopter's own unreachable state stays and is
    reported."""
    lifecycles = merged.get("lifecycles")
    own = override.get("lifecycles")
    bundled = _bundled_raw().get("lifecycles")
    if not (isinstance(lifecycles, dict) and isinstance(own, dict) and isinstance(bundled, dict)):
        return
    for name, table in cast(RawMapping, lifecycles).items():
        mine = cast(RawMapping, own).get(name)
        base = cast(RawMapping, bundled).get(name)
        if not (isinstance(table, dict) and isinstance(mine, dict) and isinstance(base, dict)):
            continue
        written = cast(RawMapping, mine).get("transitions")
        inherited = cast(RawMapping, base).get("transitions")
        merged_transitions = cast(RawMapping, table).get("transitions")
        if not (
            isinstance(written, dict)
            and isinstance(inherited, dict)
            and isinstance(merged_transitions, dict)
        ):
            continue
        graph = cast(dict[str, list[str]], merged_transitions)
        reached = {cast(str, cast(RawMapping, table).get("initial"))}
        queue = list(reached)
        while queue:
            for nxt in graph.get(queue.pop(), []):
                if nxt not in reached:
                    reached.add(nxt)
                    queue.append(nxt)
        for state in [s for s in graph if s in inherited and s not in written and s not in reached]:
            del graph[state]


def _drop_bundled_module_where_override_sets_path(merged: RawMapping) -> None:
    """Remove the bundled ``module`` leaf from a merged transform that also carries ``path``,
    so an override's ``path`` replaces the bundled transform instead of conflicting with it."""
    views_section = merged.get("views")
    if not isinstance(views_section, dict):
        return
    for table in cast(RawMapping, views_section).values():
        transform = cast(RawMapping, table).get("transform") if isinstance(table, dict) else None
        if isinstance(transform, dict) and "path" in cast(RawMapping, transform):
            cast(dict[str, Any], transform).pop("module", None)


def _retired_view_grammar_violations(raw_override: RawMapping, origin: str) -> list[MergeViolation]:
    """Every retired-grammar key still declared in *raw_override* (``fields``, ``group_by`` and
    ``order_by`` on a view, ``views`` on an item type), scanned on the raw, pre-merge, pre-splat
    document. It runs before :func:`~squads._specmerge.merge_override` because afterwards a retired
    key reaching ``ViewSpec``'s or ``ItemSpec``'s ``extra="forbid"`` is indistinguishable from an
    unknown one (and a self-splat makes it "brand-new"), whereas this says the key was retired and
    what replaces it.
    """
    violations: list[MergeViolation] = []
    views_section = raw_override.get("views")
    if isinstance(views_section, dict):
        for name, table in cast(RawMapping, views_section).items():
            if not isinstance(table, dict):
                continue
            for dotted in _scan_retired_view_grammar_keys(cast(RawMapping, table), f"views.{name}"):
                key = dotted.rsplit(".", 1)[-1]
                violations.append(
                    MergeViolation(
                        origin,
                        dotted,
                        f"{key!r} was retired — {_RETIRED_VIEW_KEY_REASONS[key]}, not a "
                        "declared key",
                        "remove it; a `[views.<name>]` table declares only `source` now.",
                    )
                )
    items_section = raw_override.get("items")
    if isinstance(items_section, dict):
        for type_name, table in cast(RawMapping, items_section).items():
            if isinstance(table, dict) and "extra_fields" in cast(RawMapping, table):
                violations.append(
                    MergeViolation(
                        origin,
                        f"items.{type_name}.extra_fields",
                        "'extra_fields' is not a declared key — a type's keys are declared in "
                        "an `attributes` table",
                        f"replace it with `[items.{type_name}.attributes]` and one "
                        '`<name> = { kind = "str" }` line per key (kind is str, list, bool '
                        "or date).",
                    )
                )
            if isinstance(table, dict) and _RETIRED_ITEM_VIEWS_KEY in cast(RawMapping, table):
                violations.append(
                    MergeViolation(
                        origin,
                        f"items.{type_name}.views",
                        "'views' was retired — a view is placed with a `sq:view:<name>` tag "
                        "in a document body now, not attached to a type",
                        "remove the key; place the view's tag with "
                        "`sq <type> <n> view add <name>` instead.",
                    )
                )
    return violations


#: The grammar names that became neutral, by the table they were spelled in.
_RENAMED_KIND_KEYS: tuple[tuple[str, str], ...] = (("maps_parent_story", "maps_to_parent"),)
_RENAMED_VALIDATORS: tuple[tuple[str, str], ...] = (("subtask_story_mapping", "subentity_mapping"),)
_RENAMED_TRANSFORM_FUNCTIONS: tuple[tuple[str, str], ...] = (("milestone_rollup", "status_rollup"),)
_BUNDLED_TRANSFORM_MODULE = "squads._view_transforms"


type _Renamed = tuple[str, str, str]


def _renamed_kind_keys(raw_override: RawMapping) -> list[_Renamed]:
    """``(path, old, new)`` for each renamed key a ``[subentity_kinds.<kind>]`` table spells."""
    return [
        (f"subentity_kinds.{kind}.{old}", old, new)
        for kind, table in _tables(raw_override.get("subentity_kinds"))
        for old, new in _RENAMED_KIND_KEYS
        if old in table
    ]


def _renamed_validators(raw_override: RawMapping) -> list[_Renamed]:
    """``(path, entry, new)`` for each ``validators`` entry, of a type or of ``[squad]``, that
    spells a renamed validator in any ``name``, ``name:param`` or ``name@level`` form."""
    tables = {f"items.{t}": v for t, v in _tables(raw_override.get("items"))}
    tables.update(dict(_tables({"squad": raw_override.get("squad")})))
    found: list[_Renamed] = []
    for path, table in tables.items():
        entries = table.get("validators")
        for entry in cast(list[object], entries) if isinstance(entries, list) else ():
            bare = entry.split("@", 1)[0].split(":", 1)[0] if isinstance(entry, str) else ""
            found.extend(
                (f"{path}.validators", str(entry), new)
                for old, new in _RENAMED_VALIDATORS
                if old == bare
            )
    return found


def _renamed_transform_functions(raw_override: RawMapping) -> list[_Renamed]:
    """``(path, old, new)`` for each view transform that names a renamed function of the bundled
    transform module."""
    found: list[_Renamed] = []
    for name, table in _tables(raw_override.get("views")):
        transform = table.get("transform")
        if not isinstance(transform, dict):
            continue
        written = cast(RawMapping, transform)
        if written.get("module") == _BUNDLED_TRANSFORM_MODULE:
            found.extend(
                (f"views.{name}.transform", old, new)
                for old, new in _RENAMED_TRANSFORM_FUNCTIONS
                if written.get("function") == old
            )
    return found


def _renamed_grammar_violations(raw_override: RawMapping, origin: str) -> list[MergeViolation]:
    """Every old spelling of a renamed grammar name in *raw_override*: a kind key, a validator
    entry or a bundled transform function. The message names the neutral name, since the old one
    would otherwise surface as an unknown key or validator."""
    return [
        MergeViolation(origin, path, f"{old!r} was renamed {new!r}", f"write {new!r} in its place.")
        for path, old, new in (
            *_renamed_kind_keys(raw_override),
            *_renamed_validators(raw_override),
            *_renamed_transform_functions(raw_override),
        )
    ]


def _tables(section: object) -> list[tuple[str, RawMapping]]:
    """The named sub-tables of a raw *section*; empty when it is not a table."""
    if not isinstance(section, dict):
        return []
    return [
        (k, cast(RawMapping, v))
        for k, v in cast(RawMapping, section).items()
        if isinstance(v, dict)
    ]


def _selected_squad_violations(raw_override: RawMapping, origin: str) -> list[MergeViolation]:
    """``[selected]`` naming ``squad``: that table holds one list, so it has no entries to drop."""
    selected = raw_override.get("selected")
    if not isinstance(selected, dict) or "squad" not in selected:
        return []
    return [
        MergeViolation(
            origin,
            "selected.squad",
            "the `[squad]` table has no entries to drop — its one key is a list",
            "replace the list in `[squad]` (`validators = [...]`) instead.",
        )
    ]


def _without_selected_squad(raw_override: RawMapping) -> RawMapping:
    """*raw_override* without ``selected.squad``, which :func:`_selected_squad_violations` reports
    in the merge's place."""
    selected = raw_override.get("selected")
    if not isinstance(selected, dict) or "squad" not in selected:
        return raw_override
    kept = {key: value for key, value in cast(RawMapping, selected).items() if key != "squad"}
    return {**raw_override, "selected": kept}


def spec_refusal(override_path: Path | str, cause: object) -> str:
    """The one refusal text every surface prints when the workflow override will not resolve,
    composed where the file and the loader's cause are both in hand, so ``compose_service``'s hard
    stop and the CLI's per-invocation binding agree. It carries which file (an adopter may not know
    an override exists, as it can be inherited with the repo), the loader's key-level cause, and
    what to do, because a hard stop that does not say what to fix is worse than the quiet wrong
    answer it replaces. It does not claim to be the one command that still runs: ``sq repair``
    (documented bypass) and ``sq check`` (bundled-spec fallback) run too.
    """
    return (
        f"this squad's workflow override could not be loaded, so no command can answer with "
        f"the vocabulary it declares.\n"
        f"  file:  {override_path}\n"
        f"  cause: {cause}\n"
        f"  Fix the file, then re-run. `sq workflow lint` reports every problem at once with "
        f"a fix hint."
    )


def refusal_cause(refusal: str) -> str:
    """The cause of a :func:`spec_refusal` text, with the file it names; the whole text when it
    has none. A cause that lists several problems is joined into one line."""
    found = re_compile(r"file:\s+(.+)\n\s+cause:\s+(.+?)\n\s+Fix the file", DOTALL).search(refusal)
    if found is None:
        return " ".join(refusal.split())
    file, cause = found.groups()
    lines = [line.strip().removeprefix("- ") for line in cause.splitlines() if line.strip()]
    cause = f"{lines[0]} {'; '.join(lines[1:])}" if len(lines) > 1 else lines[0]
    return cause if file in cause else f"{cause} ({file})"


def load_workflow_spec(
    squad_dir: Path | None = None, files: OverrideFiles | None = None
) -> WorkflowSpec:
    """Read, parse, merge (if a project override is present) and validate the workflow spec. With
    ``squad_dir`` ``None`` it returns the validated bundled-only ``WorkflowSpec`` with no filesystem
    access beyond ``importlib.resources``. With ``<squad_dir>/.overrides/workflow.toml`` present,
    the override is merged with shadowing semantics (a key replaces its counterpart, a new key is
    added, ``[selected]`` drops one by name), the only floor being the roster type-key lock plus the
    spec's own validation and the live-index cross-check; with no override the bundled spec is
    returned unchanged. It raises ``SquadsError`` naming the offending key or item, pointing to ``sq
    workflow lint`` where the caller (``compose_service``) adds that.
    """
    loaded = load_override(_DOCUMENT, squad_dir, _bundled_raw, files)
    if loaded is None:
        return _load_bundled_spec()
    merged = loaded.raw
    _raise_on_floor_violation(merged, loaded.origin)
    _strip_ref_rule_targets_of_dropped_types(merged, loaded.deselections)
    _drop_bundled_module_where_override_sets_path(merged)
    _drop_inherited_unreachable_transitions(merged, loaded.override)

    try:
        return _build_spec(merged)
    except SquadsError as exc:
        raise SquadsError(_annotate_deselections(str(exc), loaded.deselections)) from exc


# ---------------------------------------------------------------------------
# Bundled loader
# ---------------------------------------------------------------------------


def _check_override_refusals(raw_override: RawMapping, origin: str) -> None:
    retired_violations = [
        *_retired_view_grammar_violations(raw_override, origin),
        *_override_transform_violations(raw_override, origin),
        *_selected_squad_violations(raw_override, origin),
        *_renamed_grammar_violations(raw_override, origin),
    ]
    if retired_violations:
        raise SquadsError("; ".join(str(v) for v in retired_violations))


WORKFLOW_OVERRIDE_MESSAGES = OverrideMessages(
    malformed="Malformed workflow override {path}: {exc}",
    unreadable="Cannot read workflow override {path}: {exc}",
    not_utf8="Workflow override {path} is not valid UTF-8; save it as UTF-8 and re-run.",
    malformed_hint="Fix the TOML syntax and re-run `sq workflow lint`.",
    unreadable_hint="Check file permissions and re-run `sq workflow lint`.",
)


_DOCUMENT = SpecDocument(
    bundled_file="workflow.toml",
    override_file=WORKFLOW_OVERRIDE_FILENAME,
    override_name="workflow override",
    top_level_keys=WORKFLOW_TOP_LEVEL_SECTIONS,
    selected_sections=WORKFLOW_SELECTABLE_SECTIONS,
    messages=WORKFLOW_OVERRIDE_MESSAGES,
    check_override=_check_override_refusals,
)


def bundled_workflow_bytes() -> bytes:
    """The packaged ``workflow.toml``'s bytes, the read the bundled spec is parsed from."""
    return bundled_bytes(_DOCUMENT)


def _bundled_raw() -> RawMapping:
    """The bundled ``workflow.toml``, parsed but not yet built into a model."""
    return bundled_raw(_DOCUMENT)


def bundled_workflow_toml_text() -> str:
    """The bundled ``workflow.toml``'s raw text — the ``sq override diff workflow`` Δ-mine
    baseline: an override can shadow, so an empty reference would describe only "what
    the team added"; the meaningful diff is what changed relative to the real bundled document."""
    return bundled_text(_DOCUMENT)


def _load_bundled_spec() -> WorkflowSpec:
    """Read, parse, coerce, and validate the bundled ``workflow.toml``."""
    return _build_spec(_bundled_raw())


# Raw mapping -> model, shared by the bundled-only and merged loads: one parser family run once over
# whichever mapping the caller hands it.


def _pop_legacy_is_meta(name: str, data: dict[str, Any]) -> dict[str, Any]:
    """Compatibility shim that translates a deprecated ``is_meta`` key before ``model_validate``
    sees it, so ``ItemSpec``'s ``extra="forbid"`` stays intact; it is dropped at 1.0 (see
    CHANGELOG). ``is_meta`` absent or ``false`` is a no-op (``category`` defaults to ``"work"``),
    and ``is_meta = true`` on a type outside the locked roster set is refused, as roster membership
    is not adopter-declarable.
    """
    if "is_meta" not in data:
        return data
    data = dict(data)
    legacy = data.pop("is_meta")
    if legacy and name not in ROSTER_TYPES:
        raise SquadsError(
            f"item spec {name!r}: 'is_meta' is deprecated in favour of 'category' — "
            f"roster is locked to {sorted(ROSTER_TYPES)}, so a custom type cannot set "
            f"is_meta = true. Declare 'category' instead (defaults to 'work')."
        )
    return data


# Shape guards. The merged mapping is adopter-authored data: TOML happily yields `items = "oops"`,
# and every walk then calls `.items()`/`.get()` on a `str`, escaping as a raw
# AttributeError/TypeError carrying internal paths, even out of `sq workflow lint`, whose contract
# is to never raise and report every problem. Every section, entry and inline list is shape-checked
# here, and a mismatch becomes the clean `SquadsError` a type error inside an entry already
# produced.


def as_table(value: Any, what: str) -> dict[str, Any]:
    """*value* as a keyed table, or a clean refusal naming *what* and the shape found."""
    if not isinstance(value, dict):
        raise SquadsError(
            f"{what} must be a table (got {type(value).__name__}) — "
            f"declare it as [{what}] with one key per entry"
        )
    return cast(dict[str, Any], value)


def as_entry_list(value: Any, what: str) -> list[Any]:
    """*value* as an array of inline tables, or a clean refusal naming *what*.

    Also refuses a list holding a non-table element: without this, ``fields = "oops"`` would
    iterate the string character by character and report a per-character model error, and
    ``fields = ["oops"]`` a bare pydantic dump — both technically refusals, neither readable.
    """
    if not isinstance(value, list):
        raise SquadsError(
            f"{what} must be an array of tables (got {type(value).__name__}) — "
            f"declare it as {what.rpartition('.')[2]} = [{{ … }}, …]"
        )
    entries = cast(list[Any], value)
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise SquadsError(
                f"{what}[{i}] must be a table (got {type(entry).__name__}) — "
                f"every entry of this array is an inline table"
            )
    return entries


def _section(raw: dict[str, Any], name: str) -> dict[str, dict[str, Any]]:
    """One top-level section as ``{key: table}``, shape-checked at both levels."""
    section = as_table(raw.get(name, {}), name)
    return {key: as_table(data, f"{name}.{key}") for key, data in section.items()}


class SpecEntryError(SquadsError):
    """A malformed entry of one workflow section. ``findings`` is one sentence per bad field,
    each naming the entry."""

    def __init__(self, label: str, exc: Exception, model: type[BaseModel]) -> None:
        super().__init__(f"{label}: {describe_spec_error(exc, model)}")
        self.findings = [f"{label}: {sentence}" for sentence in spec_error_sentences(exc, model)]


class SpecShapeErrors(SquadsError):
    """Every malformed entry of a workflow document, collected in one pass."""

    def __init__(self, findings: list[str]) -> None:
        super().__init__("\n".join(findings))
        self.findings = findings


def _parse_lifecycle(name: str, data: dict[str, Any]) -> Lifecycle:
    """Parse one ``[lifecycles.<name>]`` table.

    Hands the raw table straight to ``model_validate``: ``Lifecycle`` declares exactly
    ``initial`` + ``transitions`` with ``extra="forbid"``, so the model reports a missing
    ``initial``, a mistyped ``transitions``, and an unknown key alike — reading ``initial``
    out first only turned an absent one into a bare ``KeyError``.
    """
    try:
        return Lifecycle.model_validate(dict(data))
    except Exception as exc:
        raise SpecEntryError(f"Invalid lifecycle {name!r}", exc, Lifecycle) from exc


def _parse_ref_rules(raw_rules: Any, ctx: str, declared_kinds: frozenset[str]) -> list[RefRule]:
    """Parse a list of ref-rule dicts into ``RefRule`` objects, passing each raw dict to
    ``model_validate`` so ``extra="forbid"`` rejects unknown keys. Each rule's ``kind`` must name an
    entry of *declared_kinds* (the document's own ``[ref_kinds]``, parsed first), since a rule for a
    kind no ref surface accepts can never fire; it validates against the declared set and never
    widens it.
    """
    rules: list[RefRule] = []
    for i, rule_data in enumerate(as_entry_list(raw_rules, f"{ctx}.ref_rules")):
        try:
            rule = RefRule.model_validate(rule_data)
        except Exception as exc:
            raise SpecEntryError(f"{ctx} ref_rule[{i}]", exc, RefRule) from exc
        if rule.kind not in declared_kinds:
            raise SquadsError(
                f"{ctx} ref_rule[{i}]: kind {rule.kind!r} is not one of the declared ref "
                f"kinds {sorted(declared_kinds)} — every ref surface would reject it, so a "
                f"rule for it can never apply"
            )
        rules.append(rule)
    return rules


#: The long options every ``sq create <type>`` command has besides its field options. A field
#: code spelled like one would be shadowed by it, so an item type may not declare one.
CREATE_OPTION_NAMES: frozenset[str] = frozenset(
    {"author", "parent", "desc", "label", "ref", "assignee", "message", "file", "json", "help"}
)


def _parse_fields(
    raw_fields: Any, ctx: str, *, reserved: frozenset[str] = frozenset()
) -> list[Field]:
    """Parse a list of field dicts into ``Field`` objects (``extra="forbid"`` per entry).

    A code in *reserved* is refused, naming the code and *ctx*."""
    fields: list[Field] = []
    for i, field_data in enumerate(as_entry_list(raw_fields, f"{ctx}.fields")):
        try:
            field = Field.model_validate(field_data)
        except Exception as exc:
            raise SpecEntryError(f"{ctx} field[{i}]", exc, Field) from exc
        if field.code in reserved:
            raise SquadsError(
                f"{ctx} field[{i}]: code {field.code!r} is also a built-in `sq create` option "
                f"(--{field.code}); declare the field under another code"
            )
        fields.append(field)
    return fields


def _parse_badges(raw_badges: Any, ctx: str) -> list[Badge]:
    """Parse a list of badge dicts into ``Badge`` objects (``extra="forbid"`` per entry)."""
    badges: list[Badge] = []
    for i, badge_data in enumerate(as_entry_list(raw_badges, f"{ctx}.badges")):
        try:
            badges.append(Badge.model_validate(badge_data))
        except Exception as exc:
            raise SpecEntryError(f"{ctx} badge[{i}]", exc, Badge) from exc
    return badges


def _parse_collection(code: str, data: dict[str, Any]) -> Collection:
    """Parse one ``[collections.<code>]`` table (its ``badges`` list is pre-coerced)."""
    badges = _parse_badges(data.get("badges", []), f"collections.{code}")
    payload: dict[str, Any] = {**data, "badges": badges}
    try:
        return Collection.model_validate(payload)
    except Exception as exc:
        raise SpecEntryError(f"Invalid collection {code!r}", exc, Collection) from exc


def _parse_role(code: str, data: dict[str, Any]) -> RoleSpec:
    """Parse one ``[roles.<code>]`` table into a ``RoleSpec`` (``extra="forbid"`` fires here).
    ``blocked`` and ``deferred`` accept only a TOML boolean, refused here in the loader's own
    words."""
    for flag in ("blocked", "deferred"):
        if flag in data and not isinstance(data[flag], bool):
            raise SquadsError(
                f"Invalid role {code!r}: {flag} must be true or false, got {data[flag]!r}"
            )
    try:
        return RoleSpec.model_validate(data)
    except Exception as exc:
        raise SpecEntryError(f"Invalid role {code!r}", exc, RoleSpec) from exc


def _parse_ref_kind(code: str, data: dict[str, Any]) -> RefKindSpec:
    """Parse one ``[ref_kinds.<code>]`` table into a ``RefKindSpec`` (``extra="forbid"`` fires
    here)."""
    try:
        return RefKindSpec.model_validate(data)
    except Exception as exc:
        raise SpecEntryError(f"Invalid ref_kinds entry {code!r}", exc, RefKindSpec) from exc


def _parse_view(name: str, data: dict[str, Any]) -> ViewSpec:
    """Parse one ``[views.<name>]`` table into a ``ViewSpec``. ``source`` is required and a table
    (``{kind, name}``); ``required`` is an optional bool defaulting false. Anything else, the
    retired ``fields``/``group_by``/``order_by`` included, reaches ``ViewSpec.model_validate``
    verbatim and is refused by its ``extra="forbid"``
    (:func:`~squads._specmerge.describe_spec_error`). ``source.name`` is cross-referenced later by
    ``check_views``; this only builds the typed value.
    """
    ctx = f"views.{name}"
    raw_source = as_table(data.get("source", {}), f"{ctx}.source")
    try:
        source = ViewSource.model_validate(raw_source)
    except Exception as exc:
        raise SpecEntryError(f"Invalid {ctx}.source", exc, ViewSource) from exc
    payload: dict[str, Any] = {**data, "source": source}
    try:
        return ViewSpec.model_validate(payload)
    except Exception as exc:
        raise SpecEntryError(f"Invalid view {name!r}", exc, ViewSpec) from exc


def _parse_subentity_kind(kind: str, data: dict[str, Any]) -> SubentityKindSpec:
    """Parse one ``[subentity_kinds.<kind>]`` table (its ``fields`` list is pre-coerced)."""
    fields = _parse_fields(data.get("fields", []), f"subentity_kinds.{kind}")
    payload: dict[str, Any] = {**data, "fields": fields}
    try:
        return SubentityKindSpec.model_validate(payload)
    except Exception as exc:
        raise SpecEntryError(
            f"Invalid subentity_kinds entry {kind!r}", exc, SubentityKindSpec
        ) from exc


def _parse_squad(value: Any) -> SquadSpec:
    """The ``[squad]`` table, with a hint that names its one key."""
    if not isinstance(value, dict):
        raise SquadsError(
            f"squad must be a table (got {type(value).__name__}) — declare it as [squad] "
            "with one key, validators = [...]"
        )
    try:
        return SquadSpec.model_validate(value)
    except Exception as exc:
        raise SpecEntryError("Invalid squad table", exc, SquadSpec) from exc


def _parse_item(name: str, data: dict[str, Any], declared_ref_kinds: frozenset[str]) -> ItemSpec:
    """Parse one ``[items.<name>]`` table into an ``ItemSpec``."""
    data = _pop_legacy_is_meta(name, data)
    # parents stays a list of plain strings; cross-refs are checked in WorkflowSpec._validate.
    # A non-list here would become a per-character list, so it is refused like every other
    # shape — ItemSpec's own list[str] typing cannot tell "P","e" apart from a real entry.
    raw_parents = data.get("parents", [])
    if not isinstance(raw_parents, list):
        raise SquadsError(
            f"items.{name}.parents must be an array of type names "
            f"(got {type(raw_parents).__name__})"
        )
    parents: list[str] = list(cast(list[Any], raw_parents))
    ref_rules = _parse_ref_rules(data.get("ref_rules", []), f"items.{name}", declared_ref_kinds)
    fields = _parse_fields(data.get("fields", []), f"items.{name}", reserved=CREATE_OPTION_NAMES)
    # Start with the raw data, then override the pre-coerced fields so model_validate sees the
    # right types AND any unknown keys trigger extra="forbid".
    payload: dict[str, Any] = {**data, "parents": parents, "ref_rules": ref_rules, "fields": fields}
    try:
        return ItemSpec.model_validate(payload)
    except Exception as exc:
        raise SpecEntryError(f"Invalid item spec {name!r}", exc, ItemSpec) from exc


def _build_spec(raw: dict[str, Any], *, collect: bool = False) -> WorkflowSpec:
    """Build and validate a ``WorkflowSpec`` from a raw parsed-TOML mapping (the bundled one or a
    merged one) through one parser family. Every section and entry is read through
    :func:`_section`/:func:`as_entry_list`, so a malformed shape is a clean ``SquadsError`` (see the
    shape-guards comment). The first malformed entry is refused unless *collect* is set, which
    parses past each and raises them together as one :class:`SpecShapeErrors`.
    """
    raw = as_table(raw, "workflow spec")
    problems: list[str] = []

    def parse[K, V](
        entries: dict[K, dict[str, Any]], one: Callable[[K, dict[str, Any]], V]
    ) -> dict[K, V]:
        parsed: dict[K, V] = {}
        for key, data in entries.items():
            try:
                parsed[key] = one(key, data)
            except SquadsError as exc:
                if not collect:
                    raise
                problems.extend(exc.findings if isinstance(exc, SpecEntryError) else [str(exc)])
        return parsed

    def status(name: str, data: dict[str, Any]) -> StatusSpec:
        # Pass the full status data dict through model_validate so extra="forbid" fires
        # on any unknown keys.
        try:
            return StatusSpec.model_validate(data)
        except Exception as exc:
            raise SpecEntryError(f"Invalid status {name!r}", exc, StatusSpec) from exc

    lifecycles = parse(_section(raw, "lifecycles"), _parse_lifecycle)
    statuses = parse(_section(raw, "statuses"), status)
    # ref_kinds are parsed before items: ref_rules validation refuses a rule naming an
    # undeclared kind.
    ref_kinds = parse(_section(raw, "ref_kinds"), _parse_ref_kind)
    declared_ref_kinds = frozenset(ref_kinds)
    items = parse(
        _section(raw, "items"), lambda name, data: _parse_item(name, data, declared_ref_kinds)
    )
    prefix_to_type: dict[str, str] = {ts.prefix: name for name, ts in items.items()}
    alias_to_type: dict[str, str] = {
        alias: name for name, ts in items.items() for alias in ts.aliases
    }
    collections = parse(_section(raw, "collections"), _parse_collection)
    subentity_kinds = parse(_section(raw, "subentity_kinds"), _parse_subentity_kind)
    roles = parse(_section(raw, "roles"), _parse_role)
    # views are cross-referenced against items/subentity_kinds/ref_kinds by
    # WorkflowSpec._validate, not here.
    views = parse(_section(raw, "views"), _parse_view)
    squad = SquadSpec()
    try:
        squad = _parse_squad(raw.get("squad", {}))
    except SquadsError as exc:
        if not collect:
            raise
        problems.extend(exc.findings if isinstance(exc, SpecEntryError) else [str(exc)])
    if problems:
        raise SpecShapeErrors(problems)

    # WorkflowSpec construction triggers the model_validator (pydantic v2).
    # Route through model_validate so extra="forbid" fires at construction.
    try:
        spec = WorkflowSpec.model_validate(
            {
                "items": items,
                "statuses": statuses,
                "lifecycles": lifecycles,
                "collections": collections,
                "subentity_kinds": subentity_kinds,
                "prefix_to_type": prefix_to_type,
                "alias_to_type": alias_to_type,
                "roles": roles,
                "ref_kinds": ref_kinds,
                "views": views,
                "squad": squad,
            }
        )
    except SquadsError:
        raise
    except Exception as exc:
        raise SquadsError(
            f"Invalid workflow spec: {describe_spec_error(exc, WorkflowSpec)}"
        ) from exc

    return spec


# The loader's own floor, the roster type-key lock. It must run before any model is built, since
# nothing in the typed models stops a non-roster type declaring category="roster" (a Literal check
# does not know the three names are reserved); every other floor clause lives in
# WorkflowSpec._validate and runs on the merged mapping.


def _collect_floor_violations(merged: RawMapping, origin: str) -> list[str]:
    """The roster type-key lock: the three roster type keys (``role``/``skill``/``operator``) must
    exist in *merged* with ``category = "roster"``, and no other key may claim it. It rests on the
    key set and ``category`` immobility only, never ``prefix``, which is ordinary customisation
    under the full floor (``WorkflowSpec._validate``). It collects every violation, the caller
    choosing to raise on the first or report all, as ``merge_override`` does, and returns an empty
    list when the lock holds.
    """

    raw_items = merged.get("items", {})
    if not isinstance(raw_items, dict):
        return []  # malformed `items` table — _build_spec refuses it with a shape message
    merged_items = cast(dict[str, Any], raw_items)

    violations: list[str] = [
        f"workflow override may not drop roster type {name!r} — role/skill/operator are "
        f"locked by key identity; revert the change — {origin}"
        for name in sorted(ROSTER_TYPES)
        if name not in merged_items
    ]
    for name, data in merged_items.items():
        if not isinstance(data, dict):
            continue  # malformed item entry — _build_spec refuses it with a shape message
        category = cast(dict[str, Any], data).get("category", "work")
        if name in ROSTER_TYPES:
            if category != "roster":
                violations.append(
                    f"workflow override may not move roster type {name!r} out of category "
                    f"'roster' (got {category!r}) — its category is locked — "
                    f"{origin}"
                )
        elif category == "roster":
            violations.append(
                f"workflow override may not add a new roster type {name!r} — category "
                f"'roster' is locked to role/skill/operator — {origin}"
            )
    return violations


def _raise_on_floor_violation(merged: RawMapping, origin: str) -> None:
    violations = _collect_floor_violations(merged, origin)
    if violations:
        raise SquadsError(violations[0])


def _strip_ref_rule_targets_of_dropped_types(
    merged: RawMapping, deselections: tuple[Deselection, ...]
) -> None:
    """Remove a surviving type's declarations that name a type ``[selected].items`` just dropped:
    ``RefRule.target`` and a ``ref_rule_target_present:<T>`` entry both name another type by string
    from the targeting type's own block, and both
    :func:`~squads._workflow._validity.check_ref_rule_targets` clauses would refuse the dangling
    name (dropping ``contract`` hits the bundled ``feature`` ``implements`` rule and any opted-in
    ``ref_rule_target_present:contract``). Without this, dropping a non-reserved type bricks the
    squad until the adopter finds the unrelated-looking block. It targets declarations only, never
    ``parents`` (the standing ``epic``/``feature`` coupling), and mutates *merged* in place at the
    raw-mapping layer.
    """
    dropped_types = {d.key for d in deselections if d.section == "items"}
    if not dropped_types:
        return
    items_table = cast(dict[str, Any], merged.get("items", {}))
    for raw_entry in items_table.values():
        entry = cast(dict[str, Any], raw_entry)
        ref_rules = entry.get("ref_rules")
        if isinstance(ref_rules, list):
            entry["ref_rules"] = [
                rr
                for rr in cast("list[Any]", ref_rules)
                if not (
                    isinstance(rr, dict) and cast(dict[str, Any], rr).get("target") in dropped_types
                )
            ]
        validators = entry.get("validators")
        if isinstance(validators, list):
            entry["validators"] = [
                v
                for v in cast("list[Any]", validators)
                if not (
                    isinstance(v, str)
                    and parse_validator_entry(v)[0] == "ref_rule_target_present"
                    and parse_validator_entry(v)[1] in dropped_types
                )
            ]


# Deselection provenance: annotate a structural-validation error that traces to a `[selected]` drop,
# so the message says "dropped from a selected list" rather than "never declared".

#: Matches a single-quoted identifier as every WorkflowSpec._validate message names one (``!r`` on a
#: str). It recovers the last such identifier in an error line, since by convention every check
#: names the missing key last (referrer first, dangling reference last), a uniform way to spot it
#: without re-deriving each wording.
_QUOTED_IDENTIFIER_RE = re_compile(r"'([^']*)'")

_BULLET_PREFIX = "  - "


def _last_quoted(line: str) -> str | None:
    matches = _QUOTED_IDENTIFIER_RE.findall(line)
    return matches[-1] if matches else None


def _annotate_line(line: str, deselections: tuple[Deselection, ...]) -> str:
    """Append a provenance note to *line* when its last quoted identifier names a key the
    ``[selected]`` deselect dropped — an adopter who cannot see their own line caused the
    violation cannot fix it. Leaves *line* untouched when nothing matches."""
    last = _last_quoted(line)
    if last is None:
        return line
    for d in deselections:
        if d.key == last:
            return (
                f"{line} — {last!r} was dropped from a [selected] list (selected.{d.section}), "
                "not left undeclared"
            )
    return line


def _annotate_deselections(message: str, deselections: tuple[Deselection, ...]) -> str:
    """Apply :func:`_annotate_line` to every line of a (possibly multi-bullet)
    ``WorkflowSpec._validate``/``_build_spec`` error message. A no-op when nothing was
    deselected."""
    if not deselections:
        return message
    return "\n".join(_annotate_line(line, deselections) for line in message.split("\n"))


def _split_spec_errors(message: str) -> list[str]:
    """Split a ``_build_spec`` failure into individual bullet messages for collect-all
    reporting. ``WorkflowSpec._validate``'s combined ``"Invalid workflow spec:\\n  - ...\\n  -
    ..."`` shape splits into one message per bullet; any other ``_build_spec`` failure (a
    single-entry parse error, e.g. ``"Invalid item spec ...: ..."``) has no bullets and is
    returned whole, as one finding."""
    bullets = [
        line.removeprefix(_BULLET_PREFIX)
        for line in message.split("\n")
        if line.startswith(_BULLET_PREFIX)
    ]
    return bullets if bullets else [message]


# ---------------------------------------------------------------------------
# Index cross-check
# ---------------------------------------------------------------------------


def _expected_folder(item: Any) -> str:
    """The folder an *item* is actually filed under, recovered from its own stored ``path`` —
    never stored itself — the corpus-alignment check stores nothing new."""
    return PurePosixPath(item.path).parent.as_posix()


def _normalized_folder(folder: str) -> str:
    """Normalise a declared ``ItemSpec.folder`` for comparison with :func:`_expected_folder`, which
    is ``PurePosixPath``-normalised: ``"guides/"``, ``"./guides"`` and ``"guides//sub"`` spell one
    directory differently, and folding through ``PurePosixPath`` makes the comparison a real
    alignment check. Case is deliberately not folded, because it is a filesystem property, and
    folding it would silently accept a mismatch on a case-sensitive filesystem (Linux, where CI
    runs).
    """
    return PurePosixPath(folder).as_posix()


def _collect_corpus_alignment_errors(spec: WorkflowSpec, db: Any) -> list[str]:
    """The corpus-alignment check: for every type in *spec* with a live item, the declared
    ``prefix``/``folder`` must equal what those items were written under, recovered from each item's
    own derived ``.prefix`` and stored ``.path`` so nothing new enters the index. A mismatch fails
    closed, grouped per type listing every item ID, and names only the two performable ways forward
    (revert the field, or change it only while the type has no items), since no shipped verb
    realigns a corpus (``repad`` renames for padding only; ``retype`` moves one item while changing
    its type). An item whose type is undeclared is skipped, being reported by the type-name check.
    """

    prefix_mismatch: dict[str, list[str]] = {}
    folder_mismatch: dict[str, list[str]] = {}
    for item in db.items.values():
        ts = spec.items.get(item.type)
        if ts is None:
            continue
        if item.prefix and item.prefix != ts.prefix:
            prefix_mismatch.setdefault(item.type, []).append(item.id)
        if _expected_folder(item) != _normalized_folder(ts.folder):
            folder_mismatch.setdefault(item.type, []).append(item.id)

    errors: list[str] = []
    for t, ids in sorted(prefix_mismatch.items()):
        errors.append(
            f"type {t!r} prefix changed to {spec.items[t].prefix!r} in the workflow spec, but "
            f"{len(ids)} live item(s) are still filed under the old prefix: {sorted(ids)} — "
            f"revert the prefix in the override, or change it only while {t!r} has no items "
            f"(no command realigns an existing corpus)"
        )
    for t, ids in sorted(folder_mismatch.items()):
        errors.append(
            f"type {t!r} folder changed to {spec.items[t].folder!r} in the workflow spec, but "
            f"{len(ids)} live item(s) are still filed under the old folder: {sorted(ids)} — "
            f"revert the folder in the override, or change it only while {t!r} has no items "
            f"(no command realigns an existing corpus)"
        )
    return errors


def _collect_ref_kind_alignment_errors(spec: WorkflowSpec, db: Any) -> list[str]:
    """The ref-kind counterpart of :func:`_collect_corpus_alignment_errors`: for every kind the
    merged spec drops or renames, the items whose ``refs`` still spell it literally, the expected
    set recovered from the corpus (each edge carries its kind inline). It is not part of
    :func:`validate_against_index`, so it never gates the load boundary, since an undeclared kind on
    a live edge is bounded (every item loads, ``sq graph`` reports a null semantic); it is called by
    ``sq workflow lint`` and by the write-boundary gates (``_services/_refs.py``,
    ``_services/_base.py::create``, the bulk importer) checking a new ref's kind. An empty corpus is
    unaffected, which is the adoption-time case.

    A bare ref carries no literal kind and decodes through the spec's declared ``default``
    (:meth:`WorkflowSpec.default_ref_kind`), so renaming that role relabels those edges instead of
    stranding them. ``spec`` is read duck-typed for ``ref_kinds`` (``getattr`` with an empty
    default) like :func:`_collect_badge_alignment_errors`, since a real spec always has the
    ``default`` kind and an empty mapping means "nothing to check against".
    """
    from squads._models._item import split_ref

    declared_kinds: dict[str, Any] = getattr(spec, "ref_kinds", {})
    if not declared_kinds:
        return []
    declared = frozenset(declared_kinds)
    dropped: dict[str, set[str]] = {}
    for item in db.items.values():
        for r in item.refs:
            _, kind = split_ref(r)
            if kind and kind not in declared:
                dropped.setdefault(kind, set()).add(item.id)

    errors: list[str] = []
    for kind, ids in sorted(dropped.items()):
        errors.append(
            f"ref kind {kind!r} is no longer declared in the workflow spec, but "
            f"{len(ids)} live item(s) still carry a ref of that kind: {sorted(ids)} — "
            "restore the entry in the override, or remove those refs with "
            "`sq <type> <n> ref rm <target>` (run `sq repair` first if the edge is a "
            "legacy-mapped encoding you'd rather canonicalise onto the current default "
            "than remove)"
        )
    return errors


def _badge_field_mismatches(
    obj: Any, fields: list[Any], collections: dict[str, Any]
) -> list[tuple[str, str, str]]:
    """``(field_code, collection_code, bad_value)`` for every *fields* entry whose value on *obj*
    (an ``Item`` or ``SubEntity``, via the shared ``badge_value`` accessor) is no longer a member of
    its bound collection. A field with no stored value is skipped, unset being valid; only a stale
    code is a mismatch.
    """
    mismatches: list[tuple[str, str, str]] = []
    for f in fields:
        value = obj.badge_value(f.code)
        if value is None:
            continue
        coll = collections.get(f.collection)
        if coll is None or not coll.declares(value):
            mismatches.append((f.code, f.collection, value))
    return mismatches


def _code_removed_by_override(
    coll_code: str, bad_value: str, collections: dict[str, Any], bundled_collections: dict[str, Any]
) -> bool:
    """Whether *bad_value*, on a live item's field bound to *coll_code*, can be attributed to the
    override, per value: the code must have been valid under the bundled collection and be missing
    from the merged one. A stale value never valid under either is a plain data problem, not what
    this plane (catching an override regressing a live corpus) should report; that is the
    load-boundary check's job (``_index/_store.py::_validate_badge_codes``), whose message stays
    cause-agnostic.
    """
    bundled_coll = bundled_collections.get(coll_code)
    if bundled_coll is None or not bundled_coll.declares(bad_value):
        return False  # never valid under bundled — not an override regression
    coll = collections.get(coll_code)
    if coll is None:
        return True  # the merged spec dropped the whole collection
    return not coll.declares(bad_value)


def _collect_badge_alignment_errors(
    spec: WorkflowSpec, db: Any, bundled: WorkflowSpec
) -> list[str]:
    """The badge-vocabulary counterpart of :func:`_collect_corpus_alignment_errors`, on the same
    live-index plane: every live item or sub-entity whose stored badge value no longer names a code
    in its collection and whose specific code the override removed fails closed here, at load,
    rather than later at the load-boundary vocab check. The per-value attribution
    (:func:`_code_removed_by_override`) is load-bearing: treating any mismatch against the current
    spec as override-caused would blame configuration for a corrupted or stale-index value and block
    ``sq repair``, the command that fixes it.

    It stores nothing new and groups per (owning type or sub-entity kind, field code, offending
    code) so one override change reports one finding. ``spec`` is read duck-typed for
    ``collections``/``item_subentity_kind``/``subentity_kinds`` (``getattr`` with an empty default),
    as ``validate_against_index`` accepts a minimal object in narrower call sites; a real spec
    populates all of them.
    """
    collections: dict[str, Any] = getattr(spec, "collections", {})
    subentity_kinds: dict[str, Any] = getattr(spec, "subentity_kinds", {})
    kind_for_type = getattr(spec, "item_subentity_kind", None)
    if not collections:
        return []  # nothing to check a field's code against

    bundled_collections: dict[str, Any] = bundled.collections

    mismatches: dict[tuple[str, str, str, str], list[str]] = {}
    for item in db.items.values():
        ts = spec.items.get(item.type)
        if ts is None:
            continue  # already reported by the type-name check above
        for code, coll_code, bad_value in _badge_field_mismatches(item, ts.fields, collections):
            if not _code_removed_by_override(
                coll_code, bad_value, collections, bundled_collections
            ):
                continue  # not attributable to the override — the load-boundary check's job
            mismatches.setdefault((item.type, code, coll_code, bad_value), []).append(item.id)

        kind = kind_for_type(item.type) if kind_for_type is not None else None
        if kind is None:
            continue
        kind_spec = subentity_kinds.get(kind)
        if kind_spec is None:
            continue
        for sub in item.subentities:
            for code, coll_code, bad_value in _badge_field_mismatches(
                sub, kind_spec.fields, collections
            ):
                if not _code_removed_by_override(
                    coll_code, bad_value, collections, bundled_collections
                ):
                    continue
                mismatches.setdefault((kind, code, coll_code, bad_value), []).append(
                    f"{item.id}:{sub.local_id}"
                )

    errors: list[str] = []
    for (owner, code, coll_code, bad_value), ids in sorted(mismatches.items()):
        errors.append(
            f"{owner!r} field {code!r} carries code {bad_value!r}, which the workflow spec's "
            f"{coll_code!r} collection no longer declares, but {len(ids)} live item(s) still "
            f"carry it: {sorted(ids)} — add {bad_value!r} back to the collection, revert the "
            f"override, or update the affected item(s) to a current code"
        )
    return errors


def _collect_type_status_errors(spec: WorkflowSpec, db: Any) -> list[str]:
    """Every live item's or sub-entity's ``type``/``status`` still named in the merged spec: the
    fail-closed family and the weaker status question, whether the spec can still read this corpus.
    A status declared nowhere leaves an item unreadable, so refusing to load is the only safe
    answer; one declared but unreachable in the entity's own machine is a different question with a
    different remedy (:func:`_collect_unreachable_status_errors`, which reports it).
    """
    errors: list[str] = []
    known_types: frozenset[str] = frozenset(spec.items)
    known_statuses: frozenset[str] = frozenset(spec.statuses)

    for item in db.items.values():
        if item.type not in known_types:
            errors.append(
                f"item {item.id} has type {item.type!r} which is not declared in the "
                f"workflow spec (add it to the override or fix the item frontmatter)"
            )
        if item.status not in known_statuses:
            errors.append(
                f"item {item.id} has status {item.status!r} which is not declared in "
                f"the workflow spec (add it to the override or fix the item frontmatter)"
            )
        errors.extend(
            f"item {item.id} sub-entity {sub.local_id} has status "
            f"{sub.status!r} which is not declared in the workflow spec"
            for sub in item.subentities
            if sub.status not in known_statuses
        )
    return errors


def _machine_states(spec: WorkflowSpec, lifecycle_name: str | None) -> frozenset[str] | None:
    """The state set of *lifecycle_name* on *spec*, or ``None`` when it cannot be resolved —
    the object handed in cannot express lifecycles at all (the minimal duck-typed spec
    :func:`validate_against_index` accepts, see :func:`_collect_badge_alignment_errors`), or
    the machine is missing, which the spec's own structural validation reports on its own
    terms. ``None`` means "no scope to judge against", never "judge against everything"."""
    lifecycles: dict[str, Any] | None = getattr(spec, "lifecycles", None)
    if not lifecycles or lifecycle_name is None:
        return None
    machine = lifecycles.get(lifecycle_name)
    return None if machine is None else frozenset(machine.states)


def _collect_unreachable_status_errors(spec: WorkflowSpec, db: Any) -> list[str]:
    """Every live item or sub-entity resting on a status its own machine cannot reach (declared in
    the spec but not a state of the lifecycle driving the entity). This is the reporting family, not
    a load refusal: it judges against the declaring lifecycle, not the flat spec-wide set, so
    ``sq workflow lint`` agrees with ``sq check``, which validates per lifecycle
    (``_item_status_valid``/``_subentity_status_valid``). It stays a report because the remedy is
    per item and needs the tool running (``sq <type> <n> status <s> --force``), unlike the
    fail-closed families, where a dropped type, re-prefixed folder or stranded badge code leaves
    the corpus unreadable.
    """
    errors: list[str] = []
    subentity_kinds: dict[str, Any] = getattr(spec, "subentity_kinds", {})
    kind_for_type = getattr(spec, "item_subentity_kind", None)

    for item in db.items.values():
        ts = spec.items.get(item.type)
        if ts is None:
            continue  # undeclared type — already reported, and no lifecycle to judge against
        states = _machine_states(spec, ts.lifecycle)
        if states is not None and item.status not in states:
            errors.append(
                f"item {item.id} rests on status {item.status!r}, which lifecycle "
                f"{ts.lifecycle!r} — the machine {item.type!r} is driven by — cannot reach; "
                f"move it with `sq {item.type} {item.sequence_id} status <declared> --force`"
            )
        kind = kind_for_type(item.type) if kind_for_type is not None else None
        kind_spec = subentity_kinds.get(kind) if kind is not None else None
        if kind_spec is None:
            continue
        sub_states = _machine_states(spec, kind_spec.lifecycle)
        if sub_states is None:
            continue
        errors.extend(
            f"item {item.id} sub-entity {sub.local_id} rests on status {sub.status!r}, which "
            f"lifecycle {kind_spec.lifecycle!r} — the machine {kind!r} is driven by — cannot "
            f"reach"
            for sub in item.subentities
            if sub.status not in sub_states
        )
    return errors


def validate_against_index(
    spec: WorkflowSpec, db: Any, *, bundled: WorkflowSpec, alignment: bool = True
) -> list[str]:
    """Cross-check live index items against the merged workflow spec, returning human-readable error
    strings (empty means clean). It checks that every item's ``type``, and every item's and
    sub-entity's ``status``, is declared; that each type with a live item still has its
    ``prefix``/``folder`` matching what the items were written under; and that stored badge values
    still name a code in their bound collection when the active collection differs from bundled.
    Each error lists the item IDs, and removing a still-used status or type, re-prefixing or
    re-foldering a type, or shrinking a collection against a non-empty corpus fails closed.

    A dropped or renamed ref kind still spelled on a live edge is deliberately not one of these: it
    is a ``sq check`` finding, never a load failure, since nothing vanishes from the scan and ``sq
    graph``/``refs`` report a null semantic; :func:`_collect_ref_kind_alignment_errors` still gates
    ``sq workflow lint`` and every write of such a ref. *alignment* ``False`` omits the
    prefix/folder half, which exists to blame an override, for a caller with none. ``db`` is typed
    ``Any`` because ``_workflow`` must not import ``_models._index`` at module level.

    This is the combined, cause-blind contract every outside call site uses; ``lint_workflow_spec``
    needs each family's own fix, so it calls the collectors (:func:`_collect_type_status_errors`,
    :func:`_collect_corpus_alignment_errors`, :func:`_collect_badge_alignment_errors`,
    :func:`_collect_ref_kind_alignment_errors`) directly.
    """
    return [
        *_collect_type_status_errors(spec, db),
        *(_collect_corpus_alignment_errors(spec, db) if alignment else []),
        *_collect_badge_alignment_errors(spec, db, bundled),
    ]


# Drift stamping: whether a workflow override shadows the bundled spec is a raw key-set intersection
# needing no merge, shared by `sq check` and `sq workflow lint` so they never disagree about one
# file.


def _raw_shadows_bundled(bundled_raw: RawMapping, override_raw: RawMapping) -> bool:
    def keys(raw: RawMapping, section: str) -> set[str]:
        value = raw.get(section, {})
        return set(cast("dict[str, Any]", value)) if isinstance(value, dict) else set()

    return any(
        keys(bundled_raw, section) & keys(override_raw, section)
        for section in WORKFLOW_TOP_LEVEL_SECTIONS
    )


def workflow_override_shadows_bundled(squad_dir: Path, files: OverrideFiles | None = None) -> bool:
    """Whether ``<squad_dir>/.overrides/workflow.toml`` redeclares (shadows) at least one
    bundled key in any section — a raw key-set intersection, no merge required.

    Returns ``False`` when the override is absent, unreadable, or malformed TOML: the drift-
    stamp obligation is moot for a file that cannot even be parsed — that failure surfaces at
    load time instead, with its own message.
    """
    override_path = squad_dir / WORKFLOW_OVERRIDE_FILENAME
    if not override_present(override_path):
        return False
    try:
        override_raw: RawMapping = override_mapping(override_path, files)
    except (tomllib.TOMLDecodeError, OSError, UnicodeDecodeError):  # fmt: skip
        return False
    return _raw_shadows_bundled(_bundled_raw(), override_raw)


def workflow_stamp_finding(
    squad_dir: Path, stamp: str | None, files: OverrideFiles | None = None
) -> tuple[str, str] | None:
    """The stamp obligation for the workflow override, evaluated once so ``sq check`` and ``sq
    workflow lint`` agree; it returns ``(level, message)`` or ``None`` when nothing is owed.
    Shadowing and unstamped is an ``"error"``, as it has stopped tracking the bundled spec and
    carries the provenance obligation of every shadowing kind. Stamped, older than running and with
    the bundled ``workflow.toml`` actually changed since is a ``"warn"``: drift is content-gated, so
    an old stamp alone never warns. Stamped at the running version, unchanged since the stamp, or
    add-only and unstamped is ``None``. Absent provenance is reported, never a load-time refusal.
    """

    if stamp is None:
        if workflow_override_shadows_bundled(squad_dir, files):
            return (
                "error",
                "shadowing workflow override has no squads:override-base stamp; run "
                "`sq override update workflow` to re-stamp",
            )
        return None
    from squads import __version__
    from squads._overrides._manifest import WORKFLOW_KEY, artifact_changed_since

    if stamp != __version__ and artifact_changed_since(WORKFLOW_KEY, stamp):
        return (
            "warn",
            f"workflow override may be stale: bundled workflow.toml changed since v{stamp}; "
            "run `sq override diff workflow` to review, then `sq override update workflow` "
            "to re-stamp",
        )
    return None


# ---------------------------------------------------------------------------
# Collect-all-errors mode for sq workflow lint
# ---------------------------------------------------------------------------

#: A lint finding: (level, location, message, fix_hint)
type LintFinding = tuple[str, str, str, str]

_SPEC_ERROR_FIX_HINT = (
    "Fix the referenced key in .overrides/workflow.toml, or add it back "
    "(directly or via `selected`), and re-run `sq workflow lint`."
)

_SPEC_SHAPE_FIX_HINT = (
    "Correct the entry in .overrides/workflow.toml as the finding states, and re-run "
    "`sq workflow lint`."
)

_STAMP_FIX_HINT = "Run `sq override update workflow` after reviewing `sq override diff workflow`."


def _spec_failure_findings(
    exc: SquadsError, deselections: tuple[Deselection, ...]
) -> list[LintFinding]:
    """The findings for a ``_build_spec`` failure: one per malformed entry field, or one per
    referential bullet."""
    if isinstance(exc, SpecShapeErrors):
        return [
            ("error", WORKFLOW_OVERRIDE_FILENAME, line, _SPEC_SHAPE_FIX_HINT)
            for line in exc.findings
        ]
    return [
        (
            "error",
            WORKFLOW_OVERRIDE_FILENAME,
            _annotate_line(line, deselections),
            _SPEC_ERROR_FIX_HINT,
        )
        for line in _split_spec_errors(str(exc))
    ]


def lint_workflow_spec(  # noqa: PLR0911 — one return per gate below
    squad_dir: Path,
    files: OverrideFiles | None = None,
    loaded: WorkflowSpec | None = None,
) -> list[LintFinding]:
    """Run all workflow spec checks in collect-all mode and return ``(level, location, message,
    fix_hint)`` tuples; it never raises, so a spec that would hard-stop ``compose_service`` is still
    fully diagnosed. *files* and *loaded* are what the caller already read and built (the override
    text and the merged spec if it loaded, not built twice). Phases: (1) the stamp obligation,
    always evaluated since a raw key-set intersection needs no valid merge; (2) retired view-grammar
    keys on the raw pre-merge document, before splat resolution can mistake one for brand-new; (3)
    engine failures (``squads._specmerge.merge_override`` in collect-all mode), one finding each;
    (4) the roster type-key lock on the merged mapping; (5) ``_build_spec``, each failure its own
    finding annotated with ``[selected]`` provenance; (6) the live-index cross-check
    (``validate_against_index``) via ``_load_index_sync``, skipped if the index is absent or
    unreadable. A failure in phases 2 to 5 blocks the later phases, as there is no valid mapping or
    spec to run them on.
    """
    findings: list[LintFinding] = []

    override_path = squad_dir / WORKFLOW_OVERRIDE_FILENAME
    if not override_present(override_path):
        # No override; bundled spec is always clean — nothing to report.
        return findings

    raw_override, parse_error = _read_raw_override(override_path, files)
    if parse_error is not None:
        findings.append(("error", WORKFLOW_OVERRIDE_FILENAME, parse_error[0], parse_error[1]))
        return findings

    stamp_finding = workflow_stamp_finding(squad_dir, _read_toml_stamp(override_path, files), files)
    if stamp_finding is not None:
        level, message = stamp_finding
        findings.append((level, WORKFLOW_OVERRIDE_FILENAME, message, _STAMP_FIX_HINT))

    # Phase 2 — retired view-grammar keys, checked before splat resolution gets a chance to
    # call one "brand-new" instead.
    retired_violations = [
        *_retired_view_grammar_violations(raw_override, str(override_path)),
        *_override_transform_violations(raw_override, str(override_path)),
        *_renamed_grammar_violations(raw_override, str(override_path)),
    ]
    squad_violations = _selected_squad_violations(raw_override, str(override_path))
    origin = str(override_path)
    # The `[selected]` table is checked in the same run as the retired keys: its errors do not
    # depend on them, and the other merge violations would only follow from the retired keys.
    result = merge_collecting(
        _DOCUMENT, _bundled_raw(), _without_selected_squad(raw_override), origin
    )
    if retired_violations:
        selected_violations = [
            v for v in result.violations if (v.path or "").split(".")[0] == "selected"
        ]
        findings.extend(
            ("error", v.path or WORKFLOW_OVERRIDE_FILENAME, v.reason, v.hint)
            for v in [*retired_violations, *squad_violations, *selected_violations]
        )
        return findings

    # Phase 3 — engine-level failures (collect-all): splat/merge/[selected] violations, with the
    # `[selected] squad` refusal listed beside them rather than ahead of them.
    phase_violations = [*squad_violations, *result.violations]
    if phase_violations:
        findings.extend(
            ("error", v.path or WORKFLOW_OVERRIDE_FILENAME, v.reason, v.hint)
            for v in phase_violations
        )
        return findings
    merged = result.merged
    if merged is None:  # pragma: no cover - contradicts merge_override's own contract
        findings.append(("error", WORKFLOW_OVERRIDE_FILENAME, "workflow override merge failed", ""))
        return findings

    # Phase 4 — the roster type-key lock.
    floor_violations = _collect_floor_violations(merged, origin)
    if floor_violations:
        findings.extend(
            ("error", WORKFLOW_OVERRIDE_FILENAME, msg, _ROSTER_LOCK_FIX_HINT)
            for msg in floor_violations
        )
        return findings

    _strip_ref_rule_targets_of_dropped_types(merged, result.deselections)
    _drop_bundled_module_where_override_sets_path(merged)
    _drop_inherited_unreachable_transitions(merged, raw_override)

    # Phase 5 — structural + referential validation.
    try:
        spec = loaded if loaded is not None else _build_spec(merged, collect=True)
    except SquadsError as exc:
        findings.extend(_spec_failure_findings(exc, result.deselections))
        return findings

    # Phase 6, the live-index cross-check: each family gets its own fix hint (the collectors are
    # called separately, not through the combined validate_against_index), since a dropped
    # type/status, a re-prefixed type, a stale badge code and a dropped ref kind need different
    # remedies and a status transition is nonsense for a badge mismatch.
    db_raw = _load_index_sync(squad_dir)
    if db_raw is not None:
        from squads._workflow import bundled_spec

        bundled = bundled_spec()
        type_status_fix = (
            "Add the missing type/status back to .overrides/workflow.toml (directly or via "
            "`selected`), or update the affected items to a currently declared type/status."
        )
        corpus_fix = (
            "Revert the prefix/folder change in .overrides/workflow.toml, or make it only "
            "while the type has no items — no command realigns an existing corpus."
        )
        badge_fix = (
            "Add the code back to the collection in .overrides/workflow.toml, revert the "
            "override, or update the affected item(s) with `sq <type> <n> update --<field> "
            "<code>`."
        )
        ref_kind_fix = (
            "Add the ref kind back to [ref_kinds] in .overrides/workflow.toml, or remove the "
            "affected item(s)' refs of that kind with `sq <type> <n> ref rm <target>` — run "
            "`sq repair` first if the edge is a legacy-mapped encoding you'd rather "
            "canonicalise onto the current default than remove."
        )
        findings.extend(
            ("error", "index cross-check", msg, type_status_fix)
            for msg in _collect_type_status_errors(spec, db_raw)
        )
        findings.extend(
            ("error", "index cross-check", msg, corpus_fix)
            for msg in _collect_corpus_alignment_errors(spec, db_raw)
        )
        findings.extend(
            ("error", "index cross-check", msg, badge_fix)
            for msg in _collect_badge_alignment_errors(spec, db_raw, bundled)
        )
        findings.extend(
            ("error", "index cross-check", msg, ref_kind_fix)
            for msg in _collect_ref_kind_alignment_errors(spec, db_raw)
        )
        # The one family here that is not fail-closed: an entity on a status its machine cannot
        # reach is reported, never refused (see the collector), so lint agrees with `sq check`; the
        # hint names the per-item verb, since no override edit moves an item.
        unreachable_fix = (
            "Move the affected item(s) onto a status the type's/kind's own lifecycle declares "
            "with `sq <type> <n> status <declared> --force`, or declare the status in that "
            "lifecycle's transitions in .overrides/workflow.toml."
        )
        findings.extend(
            ("error", "index cross-check", msg, unreachable_fix)
            for msg in _collect_unreachable_status_errors(spec, db_raw)
        )

    return findings


#: Mirrors ``_overrides._stamp``'s TOML stamp regex (a ``# squads:override-base:<version>``
#: comment), duplicated because ``_workflow`` has no dependency on ``_overrides`` (the reverse
#: holds) and a two-line read-side regex is not worth inverting the layering.
_TOML_STAMP_RE = re_compile(r"^#\s*squads:override-base:([A-Za-z0-9._-]+)\s*$", MULTILINE)


def _read_toml_stamp(override_path: Path, files: OverrideFiles | None) -> str | None:
    """Read the ``# squads:override-base:<version>`` stamp straight off disk, tolerating a
    read failure (returns ``None``) — the caller has already confirmed the file parses as TOML
    by this point, but the stamp itself is a plain-text comment, read independent of that."""
    try:
        text = override_text(override_path, files)
    except (OSError, UnicodeDecodeError):  # fmt: skip
        return None
    m = _TOML_STAMP_RE.search(text)
    return m.group(1) if m else None


def _read_raw_override(
    override_path: Path, files: OverrideFiles | None
) -> tuple[dict[str, Any], None] | tuple[dict[str, Any], tuple[str, str]]:
    """Read and parse the raw TOML override file.

    Returns ``(raw_dict, None)`` on success, or ``({}, (message, fix_hint))``
    on any read/parse error.  Used by ``lint_workflow_spec`` to separate the
    raw-TOML loading step from merge/floor-violation detection.
    """
    try:
        return read_override(_DOCUMENT, override_path, files), None
    except OverrideReadError as exc:
        return {}, (str(exc), exc.fix_hint or "")


def _load_index_sync(squad_dir: Path) -> Any:
    """Read and parse the squad index synchronously, returning a ``SquadsDB``-like object (with
    ``.items``) or ``None`` if absent or unreadable; it spares ``lint_workflow_spec`` the async
    ``store.load()``. It bypasses ``_validate_item_vocab`` on purpose, since lint must see items
    with unknown statuses or types to report them.
    """
    from squads._models._index import SquadsDB

    index_path = squad_dir / ".squads.json"
    if not index_path.is_file():
        return None
    try:
        raw = index_path.read_text(encoding="utf-8")
        try:
            return SquadsDB.model_validate_json(raw)
        except Exception:
            # Corrupt index — return None; lint can't cross-check.
            return None
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Fail-closed index cross-check for compose_service
# ---------------------------------------------------------------------------


def validate_against_index_fail_closed(
    spec: WorkflowSpec, squad_dir: Path, *, bundled: WorkflowSpec
) -> None:
    """Raise ``SquadsError`` if the merged spec drops types or statuses live items reference,
    re-prefixes or re-folders a type against a non-empty corpus, or shrinks a badge collection a
    live value still names (see :func:`validate_against_index`); a dropped ref kind live refs still
    spell is not one, refusing at ``sq workflow lint`` and the write boundary instead.
    ``compose_service`` calls it after ``load_workflow_spec`` succeeds, reading the index
    synchronously, and the error lists every offending ID and points to ``sq workflow lint``. It is
    a no-op if the index is absent, empty or unreadable, and lint calls ``lint_workflow_spec``
    instead, which reports without aborting.
    """
    db = _load_index_sync(squad_dir)
    if db is None:
        return

    errors = validate_against_index(spec, db, bundled=bundled)
    if not errors:
        return

    bullet_list = "\n".join(f"  - {e}" for e in errors)
    raise SquadsError(
        f"workflow spec is incompatible with the live index — "
        f"run `sq workflow lint` to see details:\n{bullet_list}"
    )
