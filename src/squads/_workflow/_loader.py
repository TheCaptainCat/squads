"""Load and validate the bundled default workflow spec.

``load_workflow_spec()`` is the single entry point.  It reads
``default_workflow.toml`` via ``importlib.resources`` (offline, no filesystem
assumption), parses with stdlib ``tomllib`` (both item type keys and status keys stay
plain ``str`` — neither vocabulary enum survives), builds the derived reverse indexes,
and runs ``WorkflowSpec.validate()`` (the pydantic ``model_validator``).  A corrupt or
invalid bundled spec raises ``SquadsError`` — fail closed.

The loader routes through ``model_validate(...)`` for each spec model so
``extra="forbid"`` fires at parse time, not just at pydantic construction,
giving consistent fail-closed behaviour across all sub-models.

``load_workflow_spec(squad_dir=...)`` merges a project override from
``<squad_dir>/.overrides/workflow.toml`` over the bundled default with
**additive-only** semantics.  New types/statuses/lifecycles are accepted;
shadowing a built-in type, status, or lifecycle raises ``SquadsError``.

``lint_workflow_spec(squad_dir, db)`` runs ALL checks in collect-all-errors
mode for ``sq workflow lint`` — pure-spec validation plus the live-index
cross-check.  Returns a list of ``(level, location, message)`` triples; never
raises.

``validate_against_index_fail_closed(spec, squad_dir)`` is the enforcement
point called by ``open_service``.  It reads the index synchronously (bypassing
the async layer) and raises ``SquadsError`` listing every offending item ID
when the merged spec drops a type or status still used by live items.
``sq workflow lint`` bypasses this by calling ``lint_workflow_spec`` directly,
which reports the same findings in collect mode without aborting.
"""

import importlib.resources
import tomllib
from pathlib import Path
from typing import Any

from squads._errors import SquadsError
from squads._workflow._models import ItemSpec, Lifecycle, RefRule, StatusSpec, WorkflowSpec

#: Canonical location for the project workflow override (relative to squad_dir).
WORKFLOW_OVERRIDE_FILENAME = ".overrides/workflow.toml"


def load_workflow_spec(squad_dir: Path | None = None) -> WorkflowSpec:
    """Read, parse, coerce, and validate the workflow spec.

    When ``squad_dir`` is ``None`` (the default), returns the fully-validated
    bundled-only ``WorkflowSpec`` singleton exactly as before (no filesystem
    access beyond importlib.resources).

    When ``squad_dir`` is given, reads ``<squad_dir>/.overrides/workflow.toml``
    (if it exists) and merges it **additively** over the bundled default:

    - New types, statuses, and lifecycles are accepted.
    - Redefining a built-in type, status, or lifecycle raises ``SquadsError``.
    - Unknown TOML keys raise via ``extra="forbid"``.
    - If no override file is present the bundled spec is returned unchanged.

    Raises ``SquadsError`` on any violation.
    """
    bundled = _load_bundled_spec()
    if squad_dir is None:
        return bundled

    override_path = squad_dir / WORKFLOW_OVERRIDE_FILENAME
    if not override_path.is_file():
        return bundled

    try:
        raw_override: dict[str, Any] = tomllib.loads(override_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise SquadsError(f"Malformed workflow override {override_path}: {exc}") from exc

    return _merge_override(bundled, raw_override, override_path)


# ---------------------------------------------------------------------------
# Bundled loader (unchanged path)
# ---------------------------------------------------------------------------


def _load_bundled_spec() -> WorkflowSpec:
    """Read, parse, coerce, and validate the bundled ``default_workflow.toml``."""
    try:
        pkg = importlib.resources.files("squads._workflow")
        toml_bytes = (pkg / "default_workflow.toml").read_bytes()
    except Exception as exc:
        raise SquadsError(f"Failed to read bundled default_workflow.toml: {exc}") from exc

    try:
        raw: dict[str, Any] = tomllib.loads(toml_bytes.decode())
    except tomllib.TOMLDecodeError as exc:
        raise SquadsError(f"Malformed bundled default_workflow.toml: {exc}") from exc

    return _build_spec(raw)


# ---------------------------------------------------------------------------
# Bundled-path parsers — status keys stay plain str (no enum coercion; the loaded spec
# is the sole status vocabulary, same as the type axis).
# ---------------------------------------------------------------------------


def _parse_lifecycle(name: str, data: dict[str, Any]) -> Lifecycle:
    initial: str = data["initial"]
    raw_trans: dict[str, list[str]] = data.get("transitions", {})
    # Build the dict with ONLY the known keys, then also pass through any extras so
    # model_validate's extra="forbid" fires on unknown fields.
    # The lifecycle TOML format has exactly "initial" + "transitions"; unknown top-level
    # keys should be rejected, but the transitions sub-table must not be passed as extra.
    known_keys = {"initial", "transitions"}
    extra_keys = {k: data[k] for k in data if k not in known_keys}
    payload: dict[str, Any] = {"initial": initial, "transitions": raw_trans, **extra_keys}
    try:
        return Lifecycle.model_validate(payload)
    except Exception as exc:
        raise SquadsError(f"Invalid lifecycle {name!r}: {exc}") from exc


def _parse_ref_rules(raw_rules: list[dict[str, Any]], ctx: str) -> list[RefRule]:
    """Parse a list of ref-rule dicts into ``RefRule`` objects.

    Passes the raw dict directly to ``model_validate`` so ``extra="forbid"`` rejects
    any unknown keys in a ref-rule table.
    """
    rules: list[RefRule] = []
    for i, rule_data in enumerate(raw_rules):
        try:
            rules.append(RefRule.model_validate(rule_data))
        except Exception as exc:
            raise SquadsError(f"{ctx} ref_rule[{i}]: {exc}") from exc
    return rules


def _build_spec(raw: dict[str, Any]) -> WorkflowSpec:
    # --- lifecycles (merged item + sub-entity machines) ---
    lifecycles: dict[str, Lifecycle] = {
        name: _parse_lifecycle(name, data) for name, data in raw.get("lifecycles", {}).items()
    }

    # --- statuses --- (keys stay plain str; the status-vocab enum was removed)
    statuses: dict[str, StatusSpec] = {}
    for name, data in raw.get("statuses", {}).items():
        # Pass the full status data dict through model_validate so extra="forbid" fires
        # on any unknown keys.
        try:
            statuses[name] = StatusSpec.model_validate(data)
        except Exception as exc:
            raise SquadsError(f"Invalid status {name!r}: {exc}") from exc

    # --- items --- (type keys/values stay plain str; the type-vocab enum was removed)
    items: dict[str, ItemSpec] = {}
    prefix_to_type: dict[str, str] = {}
    alias_to_type: dict[str, str] = {}

    for name, data in raw.get("items", {}).items():
        # parents stays a list of plain strings; cross-refs are checked in WorkflowSpec._validate.
        parents: list[str] = list(data.get("parents", []))
        ref_rules_raw: list[dict[str, Any]] = data.get("ref_rules", [])
        ref_rules = _parse_ref_rules(ref_rules_raw, f"items.{name}")
        # Build the payload: start with the raw data, then override the pre-coerced fields
        # so model_validate sees the right types AND any unknown keys trigger extra="forbid".
        payload: dict[str, Any] = {**data, "parents": parents, "ref_rules": ref_rules}
        try:
            ts = ItemSpec.model_validate(payload)
        except Exception as exc:
            raise SquadsError(f"Invalid item spec {name!r}: {exc}") from exc
        items[name] = ts
        prefix_to_type[ts.prefix] = name
        for alias in ts.aliases:
            alias_to_type[alias] = name

    # WorkflowSpec construction triggers the model_validator (pydantic v2).
    # Route through model_validate so extra="forbid" fires at construction.
    try:
        spec = WorkflowSpec.model_validate(
            {
                "items": items,
                "statuses": statuses,
                "lifecycles": lifecycles,
                "prefix_to_type": prefix_to_type,
                "alias_to_type": alias_to_type,
            }
        )
    except SquadsError:
        raise
    except Exception as exc:
        raise SquadsError(f"Invalid bundled workflow spec: {exc}") from exc

    return spec


# ---------------------------------------------------------------------------
# Override-specific parsers (plain strings, not coerced to enums)
# ---------------------------------------------------------------------------


def _parse_lifecycle_str(name: str, data: dict[str, Any]) -> Lifecycle:
    """Parse a lifecycle for a custom override (values stay as plain strings)."""
    initial: str = data.get("initial", "")
    if not initial:
        raise SquadsError(f"lifecycle {name!r} override: missing 'initial' key")
    raw_trans: dict[str, list[str]] = data.get("transitions", {})
    known_keys = {"initial", "transitions"}
    extra_keys = {k: data[k] for k in data if k not in known_keys}
    payload: dict[str, Any] = {"initial": initial, "transitions": raw_trans, **extra_keys}
    try:
        return Lifecycle.model_validate(payload)
    except Exception as exc:
        raise SquadsError(f"Invalid lifecycle {name!r} in workflow override: {exc}") from exc


def _parse_item_spec_str(name: str, data: dict[str, Any]) -> ItemSpec:
    """Parse an ItemSpec for a custom override (parent type names stay as plain strings)."""
    parents: list[str] = data.get("parents", [])
    ref_rules_raw: list[dict[str, Any]] = data.get("ref_rules", [])
    ref_rules = _parse_ref_rules(ref_rules_raw, f"override items.{name}")
    payload: dict[str, Any] = {**data, "parents": parents, "ref_rules": ref_rules}
    try:
        return ItemSpec.model_validate(payload)
    except Exception as exc:
        raise SquadsError(f"Invalid item spec {name!r} in workflow override: {exc}") from exc


def _parse_status_spec_str(name: str, data: dict[str, Any]) -> StatusSpec:
    """Parse a StatusSpec for a custom override."""
    try:
        return StatusSpec.model_validate(data)
    except Exception as exc:
        raise SquadsError(f"Invalid status {name!r} in workflow override: {exc}") from exc


# ---------------------------------------------------------------------------
# Additive-only merge
# ---------------------------------------------------------------------------


def _collect_additive_conflicts(
    bundled: WorkflowSpec,
    raw: dict[str, Any],
    override_path: Path,
) -> list[str]:
    """Return a list of human-readable conflict messages for every additive-only violation.

    Called in two modes:
    - **Collect** (lint): caller accumulates all messages and reports them.
    - **Fail-fast** (``_merge_override``): caller raises on the first non-empty return.

    Checks every key in the override's ``lifecycles``, ``statuses``, and ``items``
    sections against the bundled built-ins.  Parsing errors inside custom entries
    are NOT detected here — those surface via ``_parse_lifecycle_str`` /
    ``_parse_item_spec_str`` / ``_parse_status_spec_str`` when the caller actually
    builds the merged maps.

    Returns an empty list when there are no conflicts.
    """
    builtin_lifecycles: frozenset[str] = frozenset(bundled.lifecycles)
    builtin_statuses: frozenset[str] = frozenset(bundled.statuses)
    builtin_types: frozenset[str] = frozenset(bundled.items)

    lc_conflicts = [
        f"workflow override may not redefine built-in lifecycle {name!r} "
        f"(additive-only; you may add new lifecycles but not change built-ins) "
        f"— {override_path}"
        for name in raw.get("lifecycles", {})
        if name in builtin_lifecycles
    ]
    st_conflicts = [
        f"workflow override may not redefine built-in status {name!r} "
        f"(additive-only; you may add new statuses but not change built-ins) "
        f"— {override_path}"
        for name in raw.get("statuses", {})
        if name in builtin_statuses
    ]
    it_conflicts = [
        f"workflow override may not redefine built-in type {name!r} "
        f"(additive-only; you may add new types but not change built-ins) "
        f"— {override_path}"
        for name in raw.get("items", {})
        if name in builtin_types
    ]
    return lc_conflicts + st_conflicts + it_conflicts


def _merge_override(
    bundled: WorkflowSpec,
    raw: dict[str, Any],
    override_path: Path,
) -> WorkflowSpec:
    """Merge the raw override dict additively over the bundled spec.

    Rules:
    - New lifecycles, statuses, and item types are accepted.
    - Redefining a built-in lifecycle, status, or item type raises ``SquadsError``
      (fail-fast on the first conflict; lint uses ``_collect_additive_conflicts``
      directly to surface ALL conflicts in one pass).
    - ``extra="forbid"`` fires on unknown keys via ``model_validate``.
    - A new type's prefix/folder/alias colliding with a built-in is caught by
      the existing ``_check_item_refs`` uniqueness checks in ``WorkflowSpec._validate``.
    """
    # Fail-fast additive check: raise on the first conflict (open_service path).
    conflicts = _collect_additive_conflicts(bundled, raw, override_path)
    if conflicts:
        raise SquadsError(conflicts[0])

    builtin_lifecycles: frozenset[str] = frozenset(bundled.lifecycles)
    builtin_statuses: frozenset[str] = frozenset(bundled.statuses)
    builtin_types: frozenset[str] = frozenset(bundled.items)

    # Start with copies of bundled maps (WorkflowSpec is frozen; we build new dicts).
    merged_lifecycles: dict[str, Lifecycle] = dict(bundled.lifecycles)
    merged_statuses: dict[str, StatusSpec] = dict(bundled.statuses)
    merged_items: dict[str, ItemSpec] = dict(bundled.items)

    # --- override lifecycles ---
    for name, data in raw.get("lifecycles", {}).items():
        if name not in builtin_lifecycles:
            merged_lifecycles[name] = _parse_lifecycle_str(name, data)

    # --- override statuses ---
    for name, data in raw.get("statuses", {}).items():
        if name not in builtin_statuses:
            merged_statuses[name] = _parse_status_spec_str(name, data)

    # --- override item types ---
    for name, data in raw.get("items", {}).items():
        if name not in builtin_types:
            merged_items[name] = _parse_item_spec_str(name, data)

    # Rebuild derived reverse indexes over the MERGED set.
    prefix_to_type: dict[str, str] = {ts.prefix: t for t, ts in merged_items.items()}
    alias_to_type: dict[str, str] = {}
    for t, ts in merged_items.items():
        for alias in ts.aliases:
            alias_to_type[alias] = t

    # Validate the merged spec — uniqueness checks in _check_item_refs catch
    # prefix/folder/alias collisions with built-ins.
    try:
        spec = WorkflowSpec.model_validate(
            {
                "items": merged_items,
                "statuses": merged_statuses,
                "lifecycles": merged_lifecycles,
                "prefix_to_type": prefix_to_type,
                "alias_to_type": alias_to_type,
            }
        )
    except SquadsError:
        raise
    except Exception as exc:
        raise SquadsError(
            f"Invalid merged workflow spec (override: {override_path}): {exc}"
        ) from exc

    return spec


# ---------------------------------------------------------------------------
# Index cross-check
# ---------------------------------------------------------------------------


def validate_against_index(spec: WorkflowSpec, db: Any) -> list[str]:
    """Cross-check live index items against the merged workflow spec.

    Returns a list of human-readable error strings (empty = clean).

    Checks:
    - Any item whose ``type`` is not declared in ``spec.items`` → error listing the item ID.
    - Any item whose ``status`` is not declared in ``spec.statuses`` → error listing the item ID.
    - Any sub-entity whose ``status`` is not declared in ``spec.statuses`` → error.

    Removing a status/type from the override that is still referenced by live
    items fails closed, listing the offending item IDs.

    ``db`` is a ``SquadsDB`` instance; typed ``Any`` here to avoid an import cycle
    (``_workflow`` must not import ``_models._index`` at module level).
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


# ---------------------------------------------------------------------------
# Collect-all-errors mode for sq workflow lint
# ---------------------------------------------------------------------------

#: A lint finding: (level, location, message, fix_hint)
LintFinding = tuple[str, str, str, str]


def lint_workflow_spec(squad_dir: Path) -> list[LintFinding]:
    """Run ALL workflow spec checks in collect-all-errors mode.

    Returns a (possibly empty) list of ``(level, location, message, fix_hint)``
    4-tuples.  Never raises — all errors are captured as findings.

    Designed for ``sq workflow lint``: reports every error and warning with
    context so the spec author sees everything at once.  Because this function
    is called directly (not through ``open_service``), a spec that would cause
    ``open_service`` to hard-stop is still fully diagnosed here — the
    "self-blocking" problem does not apply.

    Three-phase check:

    1. **Additive-only conflicts** via ``_collect_additive_conflicts``.  Runs
       over all keys in the raw override and returns ONE finding per conflicting
       key — all of them, not just the first.  If any conflicts are found the
       spec cannot be merged; structural validation and the index cross-check
       are skipped (fixing conflicts is a prerequisite).

    2. **Structural validation** via ``load_workflow_spec``.  If phase 1 is
       clean this is expected to succeed; if it still raises (e.g. an unknown
       lifecycle reference), the error is captured as a single finding and the
       index cross-check is skipped (no valid merged spec to cross-check).

    3. **Live-index cross-check** via ``validate_against_index``.
       Only runs when phases 1 and 2 both pass.  Index is read synchronously
       via ``_load_index_sync``; if the index is absent or unreadable the
       cross-check is skipped.
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

    conflict_fix = (
        "Remove the redefined key from .overrides/workflow.toml — "
        "the override is additive-only; built-in types/statuses/lifecycles may not be changed."
    )

    # Phase 1 — additive-only conflict scan (ALL conflicts, not just the first).
    bundled = _load_bundled_spec()
    conflicts = _collect_additive_conflicts(bundled, raw_override, override_path)
    if conflicts:
        findings.extend(
            ("error", WORKFLOW_OVERRIDE_FILENAME, msg, conflict_fix) for msg in conflicts
        )
        # Can't proceed to structural validation without a valid merged spec.
        return findings

    # Phase 2 — structural validation via load_workflow_spec.
    spec: WorkflowSpec | None = None
    try:
        spec = load_workflow_spec(squad_dir=squad_dir)
    except SquadsError as exc:
        findings.append(
            (
                "error",
                WORKFLOW_OVERRIDE_FILENAME,
                str(exc),
                "Fix the TOML at .overrides/workflow.toml and re-run `sq workflow lint`.",
            )
        )
        return findings  # can't cross-check without a valid spec

    # Phase 3 — live-index cross-check.
    db_raw = _load_index_sync(squad_dir)
    if db_raw is not None:
        fix = (
            "Add the missing type/status to .overrides/workflow.toml, "
            "or update the affected items with `sq <type> <n> status <new>`."
        )
        index_errors = validate_against_index(spec, db_raw)
        findings.extend(("error", "index cross-check", msg, fix) for msg in index_errors)

    return findings


def _read_raw_override(
    override_path: Path,
) -> tuple[dict[str, Any], None] | tuple[dict[str, Any], tuple[str, str]]:
    """Read and parse the raw TOML override file.

    Returns ``(raw_dict, None)`` on success, or ``({}, (message, fix_hint))``
    on any read/parse error.  Used by ``lint_workflow_spec`` to separate the
    raw-TOML loading step from additive-conflict detection.
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
    referenced by live index items.

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
