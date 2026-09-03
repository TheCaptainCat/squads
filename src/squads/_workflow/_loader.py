"""Load and validate the workflow spec, merging a project override that may **shadow** (not
only add to) the bundled vocabulary.

``load_workflow_spec()`` is the single entry point.  With no ``squad_dir`` it reads
``workflow.toml`` from the ``squads._specs`` package via ``importlib.resources`` (offline, no
filesystem assumption), parses with stdlib ``tomllib`` (both item type keys and status keys
stay plain ``str`` — neither vocabulary enum survives), builds the derived reverse indexes, and
runs ``WorkflowSpec.validate()`` (the pydantic ``model_validator``).  A corrupt or invalid
bundled spec raises ``SquadsError`` — fail closed.

With a ``squad_dir`` given, ``<squad_dir>/.overrides/workflow.toml`` — when present — is merged
over the bundled default via the shared, loader-agnostic engine (``squads._specmerge``), entirely
at the **raw parsed-TOML mapping** layer, before any model is built — this is what lets the
override shadow rather than only add to the bundled vocabulary: splat-refs
resolve against the bundled mapping, the override deep-merges over it leaf-by-leaf (a hand-written
value replaces its bundled counterpart — this is what makes the override *shadowing* rather than
additive-only), ``[selected]`` shrinks named sections to their surviving key set and is stripped.
The merge itself carries no floor of its own — the engine's own docstring is explicit that it owns
no roster-locked rule, no lifecycle floor, no category catalog, no drift stamping, no live-index
cross-check. Every one of those stays here:

1. **The roster type-key lock** (``_collect_floor_violations``) — checked on the raw
   merged mapping, before any model is built: the three roster type keys (``role``/``skill``/
   ``operator``) must survive the merge and keep ``category = "roster"``; no other key may claim
   that category.  Written on the key set plus ``category`` immobility only — **never** on
   ``prefix``, which is ordinary field-mergeable customisation like any other type's.
2. **Structural + referential validation** (``_build_spec`` → ``WorkflowSpec._validate``) — the
   universal lifecycle floor and the roster R1/R1'/R2 clauses are unchanged; they simply now run
   against the *merged* mapping instead of only the bundled one, so a shadowed lifecycle that
   violates them fails exactly the same way a bundled one always has.  A violation that traces
   back to a ``[selected]`` drop is annotated with that provenance (``_annotate_deselections``) —
   an adopter who cannot see their own line caused a violation cannot fix it.
3. **The live-index cross-check** (``validate_against_index`` / ``..._fail_closed``) — runs last,
   after the merge, the deselect, and the spec's own validation, so a drop that strands a live
   item still fails closed listing the offending IDs. Also carries the corpus-alignment check
   gating a prefix/folder/badge-collection change against a live corpus: for every type with at
   least one live item, the merged spec's declared ``prefix``/``folder`` must still match what
   those items were written under, and every stored badge-field value (``priority``,
   ``severity``, …) must still name a code in its bound collection — fields on a walk that
   already exists, not a new floor clause, because a re-prefixing or collection-shrinking spec
   is valid in the abstract and wrong only against *this* corpus.

``lint_workflow_spec(squad_dir)`` runs every one of the above in collect-all-errors mode for
``sq workflow lint`` — pure-spec validation plus the live-index cross-check.  Returns a list of
``(level, location, message, fix_hint)`` 4-tuples; never raises.

``validate_against_index_fail_closed(spec, squad_dir)`` is the enforcement point called by
``open_service``.  It reads the index synchronously (bypassing the async layer) and raises
``SquadsError`` listing every offending item ID when the merged spec drops a type or status
still used by live items, or when a type's prefix/folder no longer matches its own corpus.
``sq workflow lint`` bypasses this by calling ``lint_workflow_spec`` directly,
which reports the same findings in collect mode without aborting.
"""

import importlib.resources
import tomllib
from pathlib import Path, PurePosixPath
from re import MULTILINE
from re import compile as re_compile
from typing import Any, cast

from squads._errors import SquadsError

# Import-direction note: `_overrides/_service.py` imports from this module, so `_workflow` and
# `_overrides` form a cycle at *package* granularity. At *module* granularity there is no cycle:
# `_overrides._manifest` (where `artifact_changed_since` lives) imports nothing beyond
# `squads._util`, so it never imports this module back, directly or transitively. Python resolves
# this import by first running `_overrides/__init__.py` (a docstring only, no imports) and then
# loading `_overrides/_manifest` as a leaf — no partially-initialised module is ever observed.
# `_interactions/_loader.py` already takes this same module-granular edge into `_overrides`
# for the playbook's identical stamp obligation, so this follows established precedent rather
# than opening a new one.
from squads._overrides._manifest import WORKFLOW_KEY, artifact_changed_since
from squads._specmerge import Deselection, RawMapping, merge_override
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
    StatusSpec,
    SubentityKindSpec,
    ViewField,
    ViewSource,
    ViewSpec,
    WorkflowSpec,
)

#: Canonical location for the project workflow override (relative to squad_dir).
WORKFLOW_OVERRIDE_FILENAME = ".overrides/workflow.toml"

#: The workflow document's closed top-level section-key space — closing what an override may
#: declare at all — enforced at the raw-mapping layer by the merge engine before any model is
#: built. Doubles as the ``[selected]``
#: table's own accepted section-name set — the two are the same vocabulary: every top-level table
#: an override may declare is a section ``[selected]`` may also name. ``selected`` itself is
#: accepted unconditionally by the engine and needs no entry here (``_specmerge`` docstring).
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
    }
)

#: Generic fix hint attached to every roster-lock finding in collect mode — the lock has exactly
#: one remedy shape (revert the key/category change), unlike a structural violation where the
#: fix varies per clause.
_ROSTER_LOCK_FIX_HINT = (
    "role/skill/operator are locked by key identity and fixed category; revert "
    "the change in .overrides/workflow.toml."
)


def spec_refusal(override_path: Path | str, cause: object) -> str:
    """The one refusal text every surface prints when the declared workflow override will not
    resolve — composed here, where the file and the loader's own cause are both in hand, so
    ``open_service``'s hard stop and the CLI's per-invocation binding say the same thing.

    Worth three lines rather than one. This failure changes ``sq`` from answering *wrongly* to
    not answering at all, so the message has to carry everything needed to act: **which file**
    (an adopter may not know an override exists at all — it can be inherited with the repo),
    **what is actually wrong** (the loader's own key-level cause, not a generic "invalid
    spec"), and **what to do**. A hard stop that does not say what to fix is a worse defect
    than the quiet wrong answer it replaces.

    Does *not* claim to be the one command that still runs while this stands — driven, it
    isn't: ``sq repair`` (through its documented bypass) and ``sq check`` (through its
    documented bundled-spec fallback) both run too, disprovable in one line by running either.
    """
    return (
        f"this squad's workflow override could not be loaded, so no command can answer with "
        f"the vocabulary it declares.\n"
        f"  file:  {override_path}\n"
        f"  cause: {cause}\n"
        f"  Fix the file, then re-run. `sq workflow lint` reports every problem at once with "
        f"a fix hint."
    )


def load_workflow_spec(squad_dir: Path | None = None) -> WorkflowSpec:
    """Read, parse, merge (if a project override is present), and validate the workflow spec.

    When ``squad_dir`` is ``None`` (the default), returns the fully-validated bundled-only
    ``WorkflowSpec`` singleton exactly as before (no filesystem access beyond
    ``importlib.resources``).

    When ``squad_dir`` is given and ``<squad_dir>/.overrides/workflow.toml`` exists, the override
    is merged over the bundled default with **shadowing** semantics: a hand-written
    key replaces its bundled counterpart, a new key is added, and ``[selected]`` drops any key by
    name — the only floor is the roster type-key lock (module docstring) plus whatever the
    spec's own structural/referential validation and the live-index cross-check catch. With no
    override file present the bundled spec is returned unchanged — not a single byte differs.

    Raises ``SquadsError`` on any violation, naming the offending key/item and pointing to
    ``sq workflow lint`` for the full diagnostic where the caller (``open_service``) adds that.
    """
    if squad_dir is None:
        return _load_bundled_spec()

    override_path = squad_dir / WORKFLOW_OVERRIDE_FILENAME
    if not override_path.is_file():
        return _load_bundled_spec()

    raw_override, parse_error = _read_raw_override(override_path)
    if parse_error is not None:
        raise SquadsError(parse_error[0])

    origin = str(override_path)
    result = merge_override(
        _bundled_raw(),
        raw_override,
        WORKFLOW_TOP_LEVEL_SECTIONS,
        origin,
        top_level_keys=WORKFLOW_TOP_LEVEL_SECTIONS,
        collect_all=False,
    )
    merged = result.merged
    if merged is None:
        # Unreachable in fail-fast mode: merge_override raises on its own first violation
        # before ever returning one. Fails closed rather than asserting, matching the
        # "never a traceback" contract even for a case that should not occur.
        raise SquadsError(f"workflow override merge failed with no violation reported — {origin}")

    _raise_on_floor_violation(merged, origin)
    _prune_orphaned_type_owned_views(merged, result.deselections)
    _strip_ref_rule_targets_of_dropped_types(merged, result.deselections)

    try:
        return _build_spec(merged)
    except SquadsError as exc:
        raise SquadsError(_annotate_deselections(str(exc), result.deselections)) from exc


# ---------------------------------------------------------------------------
# Bundled loader
# ---------------------------------------------------------------------------


def _read_bundled_bytes() -> bytes:
    try:
        pkg = importlib.resources.files("squads._specs")
        return (pkg / "workflow.toml").read_bytes()
    except Exception as exc:
        raise SquadsError(f"Failed to read bundled workflow.toml: {exc}") from exc


def _bundled_raw() -> RawMapping:
    """The bundled ``workflow.toml``, parsed but not yet built into a model — the merge
    engine's ``base`` input."""
    try:
        return tomllib.loads(_read_bundled_bytes().decode())
    except tomllib.TOMLDecodeError as exc:
        raise SquadsError(f"Malformed bundled workflow.toml: {exc}") from exc


def bundled_workflow_toml_text() -> str:
    """The bundled ``workflow.toml``'s raw text — the ``sq override diff workflow`` Δ-mine
    baseline now that the override can shadow: an empty reference described "what
    the team added" back when shadowing was impossible; against a shadowing override the
    meaningful diff is what changed relative to the real bundled document."""
    return _read_bundled_bytes().decode()


def _load_bundled_spec() -> WorkflowSpec:
    """Read, parse, coerce, and validate the bundled ``workflow.toml``."""
    return _build_spec(_bundled_raw())


# ---------------------------------------------------------------------------
# Raw-mapping -> model (shared by the bundled-only load and the merged load — one parser
# family, run once over whichever raw mapping the caller hands it).
# ---------------------------------------------------------------------------


def _pop_legacy_is_meta(name: str, data: dict[str, Any]) -> dict[str, Any]:
    """One-release read-compat shim, per the accepted back-compat policy: translate a
    deprecated ``is_meta`` key before ``model_validate`` sees it, so ``ItemSpec``'s
    ``extra="forbid"`` stays intact.

    ``is_meta`` absent or ``false`` is a no-op (``category`` falls to its ``"work"`` default).
    ``is_meta = true`` on a type outside the closed, locked roster set is refused — roster
    membership isn't adopter-declarable. Dropped at 1.0 (see CHANGELOG).
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


# ---------------------------------------------------------------------------
# Shape guards. The merged mapping is adopter-authored data, not a trusted document: TOML
# happily produces `items = "oops"` or `[items] task = "oops"`, and every walk below then
# calls `.items()`/`.get()` on a `str`. Those escaped as a raw `AttributeError`/`TypeError`
# carrying internal file paths — including out of `sq workflow lint`, whose contract is that
# it never raises and reports every problem as a finding, so the one diagnostic an adopter
# has died on exactly the shape it exists to diagnose. Every section, entry and inline list
# is shape-checked here, and a mismatch becomes the same clean `SquadsError` a type error
# inside an entry already produced.
# ---------------------------------------------------------------------------


def _as_table(value: Any, what: str) -> dict[str, Any]:
    """*value* as a keyed table, or a clean refusal naming *what* and the shape found."""
    if not isinstance(value, dict):
        raise SquadsError(
            f"{what} must be a table (got {type(value).__name__}) — "
            f"declare it as [{what}] with one key per entry"
        )
    return cast(dict[str, Any], value)


def _as_entry_list(value: Any, what: str) -> list[Any]:
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
    section = _as_table(raw.get(name, {}), name)
    return {key: _as_table(data, f"{name}.{key}") for key, data in section.items()}


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
        raise SquadsError(f"Invalid lifecycle {name!r}: {exc}") from exc


def _parse_ref_rules(raw_rules: Any, ctx: str, declared_kinds: frozenset[str]) -> list[RefRule]:
    """Parse a list of ref-rule dicts into ``RefRule`` objects.

    Passes the raw dict directly to ``model_validate`` so ``extra="forbid"`` rejects
    any unknown keys in a ref-rule table. Each rule's ``kind`` must name an entry of
    *declared_kinds* — the document's own ``[ref_kinds]`` section, parsed before this is ever
    called: a rule declared for a kind no ref surface accepts can never fire, so it is a
    declaration that silently does nothing — refused here rather than carried as an inert
    hint. This validates a declaration *against* the declared set; it never widens it.
    """
    rules: list[RefRule] = []
    for i, rule_data in enumerate(_as_entry_list(raw_rules, f"{ctx}.ref_rules")):
        try:
            rule = RefRule.model_validate(rule_data)
        except Exception as exc:
            raise SquadsError(f"{ctx} ref_rule[{i}]: {exc}") from exc
        if rule.kind not in declared_kinds:
            raise SquadsError(
                f"{ctx} ref_rule[{i}]: kind {rule.kind!r} is not one of the declared ref "
                f"kinds {sorted(declared_kinds)} — every ref surface would reject it, so a "
                f"rule for it can never apply"
            )
        rules.append(rule)
    return rules


def _parse_fields(raw_fields: Any, ctx: str) -> list[Field]:
    """Parse a list of field dicts into ``Field`` objects (``extra="forbid"`` per entry)."""
    fields: list[Field] = []
    for i, field_data in enumerate(_as_entry_list(raw_fields, f"{ctx}.fields")):
        try:
            fields.append(Field.model_validate(field_data))
        except Exception as exc:
            raise SquadsError(f"{ctx} field[{i}]: {exc}") from exc
    return fields


def _parse_badges(raw_badges: Any, ctx: str) -> list[Badge]:
    """Parse a list of badge dicts into ``Badge`` objects (``extra="forbid"`` per entry)."""
    badges: list[Badge] = []
    for i, badge_data in enumerate(_as_entry_list(raw_badges, f"{ctx}.badges")):
        try:
            badges.append(Badge.model_validate(badge_data))
        except Exception as exc:
            raise SquadsError(f"{ctx} badge[{i}]: {exc}") from exc
    return badges


def _parse_collection(code: str, data: dict[str, Any]) -> Collection:
    """Parse one ``[collections.<code>]`` table (its ``badges`` list is pre-coerced)."""
    badges = _parse_badges(data.get("badges", []), f"collections.{code}")
    payload: dict[str, Any] = {**data, "badges": badges}
    try:
        return Collection.model_validate(payload)
    except Exception as exc:
        raise SquadsError(f"Invalid collection {code!r}: {exc}") from exc


def _parse_role(code: str, data: dict[str, Any]) -> RoleSpec:
    """Parse one ``[roles.<code>]`` table into a ``RoleSpec`` (``extra="forbid"`` fires here)."""
    try:
        return RoleSpec.model_validate(data)
    except Exception as exc:
        raise SquadsError(f"Invalid role {code!r}: {exc}") from exc


def _parse_ref_kind(code: str, data: dict[str, Any]) -> RefKindSpec:
    """Parse one ``[ref_kinds.<code>]`` table into a ``RefKindSpec`` (``extra="forbid"`` fires
    here)."""
    try:
        return RefKindSpec.model_validate(data)
    except Exception as exc:
        raise SquadsError(f"Invalid ref_kinds entry {code!r}: {exc}") from exc


def _parse_view_fields(raw_fields: Any, ctx: str) -> list[ViewField]:
    """Parse a view's ``fields`` array into ``ViewField`` objects (``extra="forbid"`` per
    entry). Referential validation of each ``code`` against the source's own declared
    vocabulary happens later, on the merged spec (``_check_views``) — this only builds the
    typed list."""
    fields: list[ViewField] = []
    for i, field_data in enumerate(_as_entry_list(raw_fields, f"{ctx}.fields")):
        try:
            fields.append(ViewField.model_validate(field_data))
        except Exception as exc:
            raise SquadsError(f"{ctx} field[{i}]: {exc}") from exc
    return fields


def _parse_view(name: str, data: dict[str, Any]) -> ViewSpec:
    """Parse one ``[views.<name>]`` table into a ``ViewSpec``.

    ``source`` is required and itself a table (``{kind, name}``); everything else about a
    view is validated on the merged spec once every vocabulary section has been parsed
    (``_check_views``, run from ``WorkflowSpec._validate``) — this function only builds the
    typed value, it does not cross-reference.
    """
    ctx = f"views.{name}"
    raw_source = _as_table(data.get("source", {}), f"{ctx}.source")
    try:
        source = ViewSource.model_validate(raw_source)
    except Exception as exc:
        raise SquadsError(f"Invalid {ctx}.source: {exc}") from exc
    fields = _parse_view_fields(data.get("fields", []), ctx)
    payload: dict[str, Any] = {**data, "source": source, "fields": fields}
    try:
        return ViewSpec.model_validate(payload)
    except Exception as exc:
        raise SquadsError(f"Invalid view {name!r}: {exc}") from exc


def _parse_subentity_kind(kind: str, data: dict[str, Any]) -> SubentityKindSpec:
    """Parse one ``[subentity_kinds.<kind>]`` table (its ``fields`` list is pre-coerced)."""
    fields = _parse_fields(data.get("fields", []), f"subentity_kinds.{kind}")
    payload: dict[str, Any] = {**data, "fields": fields}
    try:
        return SubentityKindSpec.model_validate(payload)
    except Exception as exc:
        raise SquadsError(f"Invalid subentity_kinds entry {kind!r}: {exc}") from exc


def _build_spec(raw: dict[str, Any]) -> WorkflowSpec:
    """Build and validate a ``WorkflowSpec`` from a raw parsed-TOML mapping — the bundled one,
    or a bundled-plus-override mapping the merge engine has already produced. One parser
    family, run once, regardless of which raw mapping it is handed.

    Every section and entry is read through :func:`_section`/:func:`_as_entry_list`, so a
    malformed shape anywhere in the document is refused as a clean ``SquadsError`` — the shape
    guards' own comment above says why that matters more than the message quality suggests."""
    raw = _as_table(raw, "workflow spec")
    # --- lifecycles (merged item + sub-entity machines) ---
    lifecycles: dict[str, Lifecycle] = {
        name: _parse_lifecycle(name, data) for name, data in _section(raw, "lifecycles").items()
    }

    # --- statuses --- (keys stay plain str; the status-vocab enum was removed)
    statuses: dict[str, StatusSpec] = {}
    for name, data in _section(raw, "statuses").items():
        # Pass the full status data dict through model_validate so extra="forbid" fires
        # on any unknown keys.
        try:
            statuses[name] = StatusSpec.model_validate(data)
        except Exception as exc:
            raise SquadsError(f"Invalid status {name!r}: {exc}") from exc

    # --- ref_kinds (the declared ref-kind vocabulary) --- parsed before items:
    # ref_rules validation below refuses a rule naming an undeclared kind.
    ref_kinds: dict[str, RefKindSpec] = {
        code: _parse_ref_kind(code, data) for code, data in _section(raw, "ref_kinds").items()
    }
    declared_ref_kinds = frozenset(ref_kinds)

    # --- items --- (type keys/values stay plain str; the type-vocab enum was removed)
    items: dict[str, ItemSpec] = {}
    prefix_to_type: dict[str, str] = {}
    alias_to_type: dict[str, str] = {}

    for name, data in _section(raw, "items").items():
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
        fields = _parse_fields(data.get("fields", []), f"items.{name}")
        # Build the payload: start with the raw data, then override the pre-coerced fields
        # so model_validate sees the right types AND any unknown keys trigger extra="forbid".
        payload: dict[str, Any] = {
            **data,
            "parents": parents,
            "ref_rules": ref_rules,
            "fields": fields,
        }
        try:
            ts = ItemSpec.model_validate(payload)
        except Exception as exc:
            raise SquadsError(f"Invalid item spec {name!r}: {exc}") from exc
        items[name] = ts
        prefix_to_type[ts.prefix] = name
        for alias in ts.aliases:
            alias_to_type[alias] = name

    # --- collections (reusable badge libraries, keyed by collection code) ---
    collections: dict[str, Collection] = {
        code: _parse_collection(code, data) for code, data in _section(raw, "collections").items()
    }

    # --- subentity_kinds (per-kind machine binding, CLI vocab, and field declarations) ---
    subentity_kinds: dict[str, SubentityKindSpec] = {
        kind: _parse_subentity_kind(kind, data)
        for kind, data in _section(raw, "subentity_kinds").items()
    }

    # --- roles (the role catalog: settled/hidden/color per role name) ---
    roles: dict[str, RoleSpec] = {
        code: _parse_role(code, data) for code, data in _section(raw, "roles").items()
    }

    # --- views (declared derived-view projections) --- parsed last: cross-referenced
    # against items/subentity_kinds/ref_kinds by WorkflowSpec._validate, not here.
    views: dict[str, ViewSpec] = {
        name: _parse_view(name, data) for name, data in _section(raw, "views").items()
    }

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
            }
        )
    except SquadsError:
        raise
    except Exception as exc:
        raise SquadsError(f"Invalid workflow spec: {exc}") from exc

    return spec


# ---------------------------------------------------------------------------
# The loader's own floor: the roster type-key lock.
#
# Everything else the floor needs — the universal lifecycle floor, the roster R1/R1'/R2
# clauses, every referential-integrity cross-reference — already lives in
# WorkflowSpec._validate and simply runs against the merged mapping via _build_spec above.
# This is the one clause that has to run BEFORE a model is even built: nothing in the typed
# models stops a non-roster type from declaring category="roster", because a bare Literal
# check has no idea the roster's three names are reserved.
# ---------------------------------------------------------------------------


def _collect_floor_violations(merged: RawMapping, origin: str) -> list[str]:
    """The roster type-key lock: the three roster type keys (``role``/``skill``/``operator``)
    must exist in *merged* with ``category = "roster"``, and no other key may claim that
    category. Written on the key set plus ``category`` immobility only — **never** on
    ``prefix``, which is ordinary field-mergeable customisation under the same full floor
    every other type faces (``WorkflowSpec._validate``, run afterwards by ``_build_spec``).

    Collects every violation regardless of caller — the caller decides whether to raise on
    the first (fail-fast) or report all (collect-all), mirroring ``merge_override``'s own
    two-mode contract. Returns an empty list when the lock holds.
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


def _prune_orphaned_type_owned_views(
    merged: RawMapping, deselections: tuple[Deselection, ...]
) -> None:
    """Take a bundled view with its type, when ``[selected].items`` drops the type that owns it.

    A ``ViewSpec`` never names the type(s) it's shown on (:class:`~squads._workflow._models.
    ViewSource` names a ref kind/sub-entity kind/subtree type, never "the item this is attached
    to") — the only place that binding exists is the *type's* own ``items.<type>.views`` list
    (:class:`~squads._workflow._models.ItemSpec.views`). So dropping a type via ``[selected]``
    does not, by itself, touch ``[views]`` at all: without this, a bundled view attached only by
    a now-dropped type would survive the merge as an orphaned entry — still declared, still
    listed by ``sq workflow views``, resolvable against any item, but over vocabulary (the type
    it was written to describe) that no longer exists. An adopter who dropped one key would
    have to remember to drop a second, unrelated-looking one to actually be rid of it.

    Scoped precisely so a genuinely freestanding view is never touched: only a view named in a
    *dropped* bundled type's own ``views`` list, and in no *surviving* type's ``views`` list
    (bundled or override-added), is pruned. A view no type ever attached — the shape every
    adopter-declared view in this project's own test suite takes — has nothing here to trigger
    on. Mutates *merged* in place, before any model is built — the same raw-mapping layer
    ``[selected]`` itself operates at.
    """
    dropped_types = {d.key for d in deselections if d.section == "items"}
    if not dropped_types:
        return
    bundled_items = cast(dict[str, Any], _bundled_raw().get("items", {}))
    owned_by_dropped: set[str] = set()
    for t in dropped_types:
        owned_by_dropped.update(cast(dict[str, Any], bundled_items.get(t, {})).get("views", []))
    if not owned_by_dropped:
        return
    surviving_items = cast(dict[str, Any], merged.get("items", {}))
    still_attached = {
        v for it in surviving_items.values() for v in cast(dict[str, Any], it).get("views", [])
    }
    to_prune = owned_by_dropped - still_attached
    if not to_prune:
        return
    views_table = cast(dict[str, Any], merged.get("views", {}))
    for name in to_prune:
        views_table.pop(name, None)


def _strip_ref_rule_targets_of_dropped_types(
    merged: RawMapping, deselections: tuple[Deselection, ...]
) -> None:
    """Take a surviving type's declarations that name a type ``[selected].items`` just
    dropped, the same courtesy :func:`_prune_orphaned_type_owned_views` already gives a
    dropped type's own bundled view.

    ``RefRule.target`` and a ``ref_rule_target_present:<T>`` validator entry both name another
    item type by string, from the *targeting* type's own block — dropping ``<T>`` leaves that
    block referring to vocabulary that no longer exists, and both
    :func:`~squads._workflow._models._check_ref_rule_targets` clauses refuse it (the bundled
    ``feature`` entry hits exactly this dropping ``contract``: it declares an ``implements``
    rule targeting it, plus ``ref_rule_target_present:contract``). Without this, an adopter
    dropping a non-reserved type through ``[selected].items`` bricks the whole squad until they
    also find and edit the unrelated-looking type block that targets it — the one courtesy the
    view-owning case above already gets.

    Scoped to declarations that *target* a dropped type only — never ``parents``, which is the
    pre-existing, deliberately-unchanged coupling between ``epic`` and ``feature``. Mutates
    *merged* in place, at the same raw-mapping layer the prune above operates at.
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
                    and v.startswith("ref_rule_target_present:")
                    and v.partition(":")[2] in dropped_types
                )
            ]


# ---------------------------------------------------------------------------
# Deselection provenance — annotate a structural-validation error that traces back to a
# `[selected]` drop, so the message says "dropped from a selected list" rather than "never
# declared" — the same ruling that lets a shadowing override drop a key by name.
# ---------------------------------------------------------------------------

#: Matches a single-quoted identifier the way every WorkflowSpec._validate error message
#: names one (``f"...{name!r}..."`` on a plain str always renders as ``'name'``). Used only to
#: recover the LAST such identifier in one error line — by convention, every check in
#: WorkflowSpec._validate names the *missing* key last (the referrer first, the dangling
#: reference last), so this is a mechanical, uniform way to spot it without re-deriving each
#: check's own wording.
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
    """Normalise a declared ``ItemSpec.folder`` string for comparison against
    :func:`_expected_folder`, which is always ``PurePosixPath``-normalised.

    ``ItemSpec.folder`` is a bare, unconstrained ``str`` — a hand-written override is free to
    spell the same directory as ``"guides/"``, ``"./guides"``, or ``"guides//sub"``, and every
    one of those is textually different from the normalised form the item's own stored path
    produces, even though the two name the same directory. Folding both sides through
    ``PurePosixPath`` before comparing (trailing slash, redundant ``./``/``//`` all collapse)
    is what makes the comparison a real *alignment* check rather than a string diff.

    Deliberately NOT folded here: letter case. Unlike separator syntax, "same directory" under
    case is a filesystem property, not a path-syntax one — a case-insensitive filesystem (the
    typical macOS/Windows default) would tolerate ``Guides`` vs ``guides``, but a case-sensitive
    one (the typical Linux default, and the one CI runs on) would not, so folding case here
    would turn a real mismatch on a case-sensitive filesystem into a silently-accepted override.
    """
    return PurePosixPath(folder).as_posix()


def _collect_corpus_alignment_errors(spec: WorkflowSpec, db: Any) -> list[str]:
    """The corpus-alignment check: for every type in *spec* with at least one live item, the
    declared ``prefix``/``folder`` must equal what those items were actually written under.

    Stores nothing new — the expected prefix is recovered from each item's own derived
    ``.prefix`` (parsed from its ``id``), the expected folder from its stored ``.path`` — so no
    per-type prefix/folder ever enters the index, which is forbidden to hold what the ``.md``
    files already carry. A mismatch fails closed, grouped per type, listing every offending
    item ID, and naming only the two performable ways forward — revert the field, or change it
    only while the type has no items — never a migration: no shipped verb realigns an existing
    corpus (``repad`` renames files for a padding change only; ``retype`` moves one item while
    also changing its type).

    An item whose type is not declared in *spec* at all is skipped here — already reported by
    the type-name check above; there is no ``ItemSpec`` left to compare its prefix/folder
    against.
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
    """The ref-kind counterpart to :func:`_collect_corpus_alignment_errors`: a ref kind is
    durable on-disk data no scan re-derives, on exactly the terms the type/prefix/folder
    alignment check above already uses. For every kind the merged spec drops or
    renames, list the items whose ``refs`` still spell it literally.

    Unlike the type/prefix/folder/badge families, this collector is **not** part of
    :func:`validate_against_index` and so never gates the load boundary — an undeclared ref
    kind on a live edge is bounded (every item still loads, every edge is still readable, `sq
    graph` reports it with a null semantic). It is called directly by ``sq workflow lint``
    (which does refuse) and is what the write-boundary gates (``_services/_refs.py``,
    ``_services/_base.py::create``, the bulk importer) check a *new* ref's kind against.

    Stores nothing new — the expected set is recovered from the corpus itself, since every
    edge carries its own kind inline. An empty corpus (no live ref spells the kind) is
    unaffected — that is the case the capability was actually asked for: choosing your own
    ref-kind vocabulary at adoption time.

    A **bare** (unspelled) ref carries no literal kind at all — it decodes through the merged
    spec's own declared ``default`` (:meth:`WorkflowSpec.default_ref_kind`), so renaming which
    kind carries that role relabels those edges rather than stranding them; only a kind
    actually spelled here can ever appear in the result. That is ordinarily also "spelled by
    hand", but a legacy ``extra.ref_kinds``-mapped edge whose recorded kind no longer equals
    the live default folds to a spelled form too, at the fold's input — nothing was typed by
    an adopter. `sq repair` canonicalises such an edge back to bare, on the index and (see its
    own docstring) the file, closing the gap on its next run.

    ``spec`` is accessed duck-typed for ``ref_kinds`` (``getattr`` with an empty default),
    matching :func:`_collect_badge_alignment_errors`'s own contract of accepting a minimal
    object that only carries ``items``/``statuses`` in the narrower call sites that don't
    exercise this axis at all — a real ``WorkflowSpec`` never has an empty ``ref_kinds`` (the
    per-capability floor requires at least the ``default`` role), so an empty mapping here
    always means "nothing to check against", never a genuinely empty declared vocabulary.
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
    """``(field_code, collection_code, bad_value)`` for every *fields* entry whose value on
    *obj* (an ``Item`` or ``SubEntity``, read via the shared ``badge_value`` accessor both
    carry) is no longer a member of its bound collection's badge codes. A field with no stored
    value is skipped — unset is always valid; only a live, stale code is a mismatch."""
    mismatches: list[tuple[str, str, str]] = []
    for f in fields:
        value = obj.badge_value(f.code)
        if value is None:
            continue
        coll = collections.get(f.collection)
        if coll is None or value not in coll.badge_codes:
            mismatches.append((f.code, f.collection, value))
    return mismatches


def _code_removed_by_override(
    coll_code: str, bad_value: str, collections: dict[str, Any], bundled_collections: dict[str, Any]
) -> bool:
    """Whether *bad_value*, found on a live item's field bound to *coll_code*, can be honestly
    attributed to the override — per **value**, not per collection: the code must actually
    have been valid under the bundled collection and must actually be missing from the merged
    one. A collection that only ever *grew* relative to bundled still has every one of its
    original codes accepted, so a stale value that was never valid under bundled OR under the
    merged spec either is a plain corpus/frontmatter data problem, not something this
    cross-check plane (which exists to catch an override regressing a live corpus) has any
    business reporting — that is the load-boundary vocab check's job
    (``_index/_store.py::_validate_badge_codes``), whose message stays cause-agnostic for
    exactly this reason.
    """
    bundled_coll = bundled_collections.get(coll_code)
    if bundled_coll is None or bad_value not in bundled_coll.badge_codes:
        return False  # never valid under bundled — not an override regression
    coll = collections.get(coll_code)
    if coll is None:
        return True  # the merged spec dropped the whole collection
    return bad_value not in coll.badge_codes


def _collect_badge_alignment_errors(spec: WorkflowSpec, db: Any) -> list[str]:
    """The badge-vocabulary counterpart to :func:`_collect_corpus_alignment_errors`, on the
    same live-index cross-check plane as the type/status/prefix/folder walks: for every live
    item (and sub-entity) whose stored badge-field value no longer names a code in its bound
    collection **and whose specific code the override actually removed** — this fails closed
    here, at load, rather than surfacing only later at the load-boundary vocab check
    (``_index/_store.py::_validate_badge_codes``) every ordinary command already runs.

    The per-**value** attribution (:func:`_code_removed_by_override`) is load-bearing, not an
    optimisation: this plane's whole justification is catching an override regressing a
    *live* corpus, so it must only report what the override actually did. Reading a live
    item's stored code and treating any mismatch against the *current* spec as override-caused
    would blame configuration for a plain corpus data problem whenever the two disagree for
    any other reason (a hand-edited or otherwise corrupted stored value, most notably a
    rebuildable-index entry stale relative to the frontmatter it should mirror, or a
    collection that only ever grew and so never stopped accepting the stale code) —
    asserting a cause this check cannot actually establish, and refusing to load over a
    problem ``sq repair`` exists to fix, blocking the very command whose job is fixing it.

    Stores nothing new: the mismatched codes are the item's/sub-entity's own already-persisted
    values. Grouped per (owning type or sub-entity kind, field code, offending code) so one
    override change that strands several items on the same removed code reports as one
    finding, not one per item.

    ``spec`` is accessed duck-typed for ``collections``/``item_subentity_kind``/
    ``subentity_kinds`` (``getattr`` with an empty/``None`` default), matching this module's own
    ``validate_against_index`` contract of accepting a minimal object that only carries
    ``items``/``statuses`` in the narrower call sites that don't exercise badge fields at all —
    a real ``WorkflowSpec`` always has every one of these populated.
    """
    collections: dict[str, Any] = getattr(spec, "collections", {})
    subentity_kinds: dict[str, Any] = getattr(spec, "subentity_kinds", {})
    kind_for_type = getattr(spec, "item_subentity_kind", None)
    if not collections:
        return []  # nothing to check a field's code against

    bundled_collections: dict[str, Any] = _load_bundled_spec().collections

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
    """Every live item's/sub-entity's ``type``/``status`` still named in the merged spec.

    The **fail-closed** family, and deliberately the weaker of the two status questions: it
    asks whether the merged spec can still *read* this corpus at all. A status the spec no
    longer declares anywhere leaves the item unreadable, so refusing to load is the only safe
    answer. A status that is declared but unreachable in the entity's own machine is a
    different question with a different remedy — see :func:`_collect_unreachable_status_errors`,
    which reports it rather than refusing.
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
    """Every live item/sub-entity resting on a status its own machine cannot reach — declared
    somewhere in the spec, but not a state of the lifecycle that entity is actually driven by.

    This is the **reporting** family, not a load refusal, and the split is the point. Judging a
    status against the flat, spec-wide set (:func:`_collect_type_status_errors`) accepts an
    entity parked on a state it can never transition out of, which is how ``sq workflow lint``
    said a corpus was clean while ``sq check`` — which has always validated per lifecycle, via
    ``_services._validators._item_status_valid`` / ``_subentity_status_valid`` — called the
    same item an error. Asking the question against the *declaring* scope rather than a global
    set is what makes the two agree.

    It stays a report on both planes rather than becoming a fifth fail-closed clause, because
    the remedy is per item and needs the tool to keep working: ``sq <type> <n> status <s>
    --force`` moves the item off, and it is reachable only while commands still run. The
    fail-closed families refuse for the opposite reason — a dropped type, a re-prefixed folder
    or a stranded badge code leave the corpus genuinely unreadable, and no per-item verb fixes
    those from inside.
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


def validate_against_index(spec: WorkflowSpec, db: Any) -> list[str]:
    """Cross-check live index items against the merged workflow spec.

    Returns a list of human-readable error strings (empty = clean).

    Checks:
    - Any item whose ``type`` is not declared in ``spec.items`` → error listing the item ID.
    - Any item whose ``status`` is not declared in ``spec.statuses`` → error listing the item ID.
    - Any sub-entity whose ``status`` is not declared in ``spec.statuses`` → error.
    - For every type with at least one live item, its declared ``prefix``/``folder`` still
      matches what those items were written under → error listing the item IDs.
    - Any item's/sub-entity's stored badge-field value (``priority``, ``severity``, …) still
      names a code in its bound collection, when the active spec's collection actually
      differs from bundled → error listing the item IDs.

    A dropped/renamed ref kind still spelled on a live edge is deliberately **not** one of
    these checks, unlike the other durable-on-disk axes above: an undeclared ref kind is a
    ``sq check`` finding, never a load failure — nothing vanishes from the on-disk scan the way
    a re-prefixed type does, and `sq graph`/`refs` already traverse such an edge and report a
    null semantic rather than dropping it. ``_collect_ref_kind_alignment_errors`` still exists
    and still gates ``sq workflow lint`` and every *write* of a ref of that kind — it is simply
    not one of the families that locks the whole squad at load. See its own docstring.

    Removing a status/type from the override that is still referenced by live items, or
    re-prefixing/re-foldering a type, or shrinking/replacing a badge collection a live item's
    field value still names, against a non-empty corpus fails closed, listing the offending
    item IDs.

    ``db`` is a ``SquadsDB`` instance; typed ``Any`` here to avoid an import cycle
    (``_workflow`` must not import ``_models._index`` at module level).

    This is the combined contract every call site outside this module uses (the fail-closed
    raise, and every pre-existing test) — one flat list, cause-blind about which of the three
    families below produced which entry. ``lint_workflow_spec`` needs to tell them apart (each
    family's fix is different, and it additionally runs the ref-kind axis this function does
    not), so it calls the collectors (:func:`_collect_type_status_errors`,
    :func:`_collect_corpus_alignment_errors`, :func:`_collect_badge_alignment_errors`,
    :func:`_collect_ref_kind_alignment_errors`) directly instead of this function.
    """
    return [
        *_collect_type_status_errors(spec, db),
        *_collect_corpus_alignment_errors(spec, db),
        *_collect_badge_alignment_errors(spec, db),
    ]


# ---------------------------------------------------------------------------
# Drift stamping — whether a workflow override shadows the bundled spec: a raw
# key-set intersection, no merge required. Shared by `sq check` and `sq workflow lint` so the
# two never disagree about the same file.
# ---------------------------------------------------------------------------


def _raw_shadows_bundled(bundled_raw: RawMapping, override_raw: RawMapping) -> bool:
    return any(
        set(bundled_raw.get(section, {})) & set(override_raw.get(section, {}))
        for section in WORKFLOW_TOP_LEVEL_SECTIONS
    )


def workflow_override_shadows_bundled(squad_dir: Path) -> bool:
    """Whether ``<squad_dir>/.overrides/workflow.toml`` redeclares (shadows) at least one
    bundled key in any section — a raw key-set intersection, no merge required.

    Returns ``False`` when the override is absent, unreadable, or malformed TOML: the drift-
    stamp obligation is moot for a file that cannot even be parsed — that failure surfaces at
    load time instead, with its own message.
    """
    override_path = squad_dir / WORKFLOW_OVERRIDE_FILENAME
    if not override_path.is_file():
        return False
    try:
        override_raw: RawMapping = tomllib.loads(override_path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):  # fmt: skip
        return False
    return _raw_shadows_bundled(_bundled_raw(), override_raw)


def workflow_stamp_finding(squad_dir: Path, stamp: str | None) -> tuple[str, str] | None:
    """The stamp obligation for the workflow override, evaluated once so ``sq check`` and
    ``sq workflow lint`` always agree. Returns ``(level, message)``, or ``None``
    when nothing is owed:

    - shadowing **and** unstamped → ``("error", ...)`` — a shadowing override has stopped
      tracking the bundled spec and so inherits the provenance obligation every other
      shadowing override kind already carries.
    - stamped, older than running, **and the bundled workflow.toml actually changed** since
      that stamp → ``("warn", ...)``. Drift is content-gated: an old stamp alone is never a
      warning, so an add-only override with no bundled change behind it reports clean, not
      "may be stale".
    - stamped at the running version, content unchanged since the stamp, or add-only and
      unstamped → ``None``.

    Absent provenance never changes whether the merged spec satisfies the floor — this is
    reported, never a load-time refusal; the floor's own refusals stay hard stops.
    """

    from squads import __version__

    if stamp is None:
        if workflow_override_shadows_bundled(squad_dir):
            return (
                "error",
                "shadowing workflow override has no squads:override-base stamp; run "
                "`sq override update workflow` to re-stamp",
            )
        return None
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

_STAMP_FIX_HINT = "Run `sq override update workflow` after reviewing `sq override diff workflow`."


def lint_workflow_spec(squad_dir: Path) -> list[LintFinding]:  # noqa: PLR0911 — one return per gate below
    """Run ALL workflow spec checks in collect-all-errors mode.

    Returns a (possibly empty) list of ``(level, location, message, fix_hint)``
    4-tuples.  Never raises — all errors are captured as findings.

    Designed for ``sq workflow lint``: reports every error and warning with
    context so the spec author sees everything at once.  Because this function
    is called directly (not through ``open_service``), a spec that would cause
    ``open_service`` to hard-stop is still fully diagnosed here — the
    "self-blocking" problem does not apply.

    Phases:

    1. **The stamp obligation** (``workflow_stamp_finding``) — always evaluated when an
       override file exists, independent of whether it merges cleanly; a raw key-set
       intersection needs no valid merge to compute.
    2. **Engine-level failures** (splat/merge/``[selected]`` violations from
       ``squads._specmerge.merge_override``, run in collect-all mode) block the merge — one
       finding per violation, all of them, not just the first. If any are found, the
       structural validation and the index cross-check below are skipped: there is no valid
       merged mapping to run them against.
    3. **The roster type-key lock** (``_collect_floor_violations``) — the loader's own floor,
       run on the merged mapping. Any violation here blocks the same downstream phases.
    4. **Structural + referential validation** (``_build_spec``). If it still raises (e.g. an
       unknown lifecycle reference, or a status the merge dropped that a surviving lifecycle
       still names), each bullet becomes its own finding, annotated with ``[selected]``
       provenance where it applies; the index cross-check is skipped (no valid spec to
       cross-check).
    5. **The live-index cross-check** (``validate_against_index``) — only runs when every
       phase above is clean. Index is read synchronously via ``_load_index_sync``; if the
       index is absent or unreadable the cross-check is skipped.
    """
    findings: list[LintFinding] = []

    override_path = squad_dir / WORKFLOW_OVERRIDE_FILENAME
    if not override_path.is_file():
        # No override; bundled spec is always clean — nothing to report.
        return findings

    raw_override, parse_error = _read_raw_override(override_path)
    if parse_error is not None:
        findings.append(("error", WORKFLOW_OVERRIDE_FILENAME, parse_error[0], parse_error[1]))
        return findings

    stamp_finding = workflow_stamp_finding(squad_dir, _read_toml_stamp(override_path))
    if stamp_finding is not None:
        level, message = stamp_finding
        findings.append((level, WORKFLOW_OVERRIDE_FILENAME, message, _STAMP_FIX_HINT))

    # Phase 2 — engine-level failures (collect-all): splat/merge/[selected] violations.
    origin = str(override_path)
    result = merge_override(
        _bundled_raw(),
        raw_override,
        WORKFLOW_TOP_LEVEL_SECTIONS,
        origin,
        top_level_keys=WORKFLOW_TOP_LEVEL_SECTIONS,
        collect_all=True,
    )
    if result.violations:
        findings.extend(
            ("error", v.path or WORKFLOW_OVERRIDE_FILENAME, v.reason, v.hint)
            for v in result.violations
        )
        return findings
    merged = result.merged
    if merged is None:  # pragma: no cover - contradicts merge_override's own contract
        findings.append(("error", WORKFLOW_OVERRIDE_FILENAME, "workflow override merge failed", ""))
        return findings

    # Phase 3 — the roster type-key lock.
    floor_violations = _collect_floor_violations(merged, origin)
    if floor_violations:
        findings.extend(
            ("error", WORKFLOW_OVERRIDE_FILENAME, msg, _ROSTER_LOCK_FIX_HINT)
            for msg in floor_violations
        )
        return findings

    _strip_ref_rule_targets_of_dropped_types(merged, result.deselections)

    # Phase 4 — structural + referential validation.
    try:
        spec = _build_spec(merged)
    except SquadsError as exc:
        bullets = [_annotate_line(b, result.deselections) for b in _split_spec_errors(str(exc))]
        findings.extend(
            ("error", WORKFLOW_OVERRIDE_FILENAME, b, _SPEC_ERROR_FIX_HINT) for b in bullets
        )
        return findings

    # Phase 5 — live-index cross-check. Each family gets its OWN fix hint (called separately
    # rather than through the combined validate_against_index) — a dropped type/status, a
    # re-prefixed/re-foldered type, a stale badge code, and a dropped/renamed ref kind each
    # have a genuinely different remedy, and `sq <type> <n> status <new>` (a status transition)
    # is nonsensical advice for, say, a badge-field mismatch it can never fix.
    db_raw = _load_index_sync(squad_dir)
    if db_raw is not None:
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
            for msg in _collect_badge_alignment_errors(spec, db_raw)
        )
        findings.extend(
            ("error", "index cross-check", msg, ref_kind_fix)
            for msg in _collect_ref_kind_alignment_errors(spec, db_raw)
        )
        # The one family here that is NOT a fail-closed clause: an entity resting on a status
        # its own machine cannot reach is reported, never refused (see the collector). Lint
        # missed it entirely while `sq check` reported it, which is the disagreement this
        # closes; the fix hint names the per-item verb, since no override edit moves an item.
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


#: Mirrors ``_overrides._stamp``'s TOML stamp regex exactly (same format: a
#: ``# squads:override-base:<version>`` comment). Duplicated rather than imported: ``_workflow``
#: has no dependency on ``_overrides`` today (``_overrides`` depends on ``_workflow``, not the
#: reverse), and this loader needs only the read side of a two-line regex — not worth inverting
#: that layering for.
_TOML_STAMP_RE = re_compile(r"^#\s*squads:override-base:([A-Za-z0-9._-]+)\s*$", MULTILINE)


def _read_toml_stamp(override_path: Path) -> str | None:
    """Read the ``# squads:override-base:<version>`` stamp straight off disk, tolerating a
    read failure (returns ``None``) — the caller has already confirmed the file parses as TOML
    by this point, but the stamp itself is a plain-text comment, read independent of that."""
    try:
        text = override_path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = _TOML_STAMP_RE.search(text)
    return m.group(1) if m else None


def _read_raw_override(
    override_path: Path,
) -> tuple[dict[str, Any], None] | tuple[dict[str, Any], tuple[str, str]]:
    """Read and parse the raw TOML override file.

    Returns ``(raw_dict, None)`` on success, or ``({}, (message, fix_hint))``
    on any read/parse error.  Used by ``lint_workflow_spec`` to separate the
    raw-TOML loading step from merge/floor-violation detection.
    """
    try:
        raw: dict[str, Any] = tomllib.loads(override_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        return (
            {},
            (
                f"Malformed workflow override {override_path}: {exc}",
                "Fix the TOML syntax and re-run `sq workflow lint`.",
            ),
        )
    except OSError as exc:
        return (
            {},
            (
                f"Cannot read workflow override {override_path}: {exc}",
                "Check file permissions and re-run `sq workflow lint`.",
            ),
        )
    else:
        return raw, None


def _load_index_sync(squad_dir: Path) -> Any:
    """Read and parse the squad index synchronously.

    Returns a ``SquadsDB``-like object (has ``.items`` dict) on success, or
    ``None`` if the index is absent or unreadable.  Used by ``lint_workflow_spec``
    to avoid the async ``store.load()`` path.

    NOTE: this bypasses ``_validate_item_vocab`` — intentionally.  Lint needs
    to see items with unknown statuses/types so it can report them; the normal
    load-boundary check would suppress them.
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
# Fail-closed index cross-check for open_service
# ---------------------------------------------------------------------------


def validate_against_index_fail_closed(spec: WorkflowSpec, squad_dir: Path) -> None:
    """Raise ``SquadsError`` if the merged spec drops types/statuses still
    referenced by live index items, re-prefixes/re-folders a type against a non-empty corpus,
    or shrinks/replaces a badge collection a live value still names — see
    :func:`validate_against_index` for the full list. A dropped/renamed ref kind live refs
    still spell is deliberately **not** one of these: it refuses at ``sq workflow lint`` and
    at the write boundary, never here.

    Called by ``open_service`` after ``load_workflow_spec`` succeeds, before the spec
    is passed to ``Service``.  Reads the index synchronously so no async context
    is required.

    Raises ``SquadsError`` listing every offending item ID and pointing to
    ``sq workflow lint`` for the full diagnostic.  If the index is absent, empty,
    or unreadable, this is a no-op (nothing to cross-check).

    This is NOT called by ``sq workflow lint`` — lint calls ``lint_workflow_spec``
    directly, which reports the same errors in collect mode without aborting.
    """
    db = _load_index_sync(squad_dir)
    if db is None:
        return

    errors = validate_against_index(spec, db)
    if not errors:
        return

    bullet_list = "\n".join(f"  - {e}" for e in errors)
    raise SquadsError(
        f"workflow spec is incompatible with the live index — "
        f"run `sq workflow lint` to see details:\n{bullet_list}"
    )
