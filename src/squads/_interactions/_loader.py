"""Load and validate the playbook spec, merging a project override over the bundled base.

``load_playbook(catalog, spec, squad_dir)`` is the single entry point.  With no ``squad_dir``
(or none present on disk) it reads ``playbook.toml`` from the ``squads._specs`` package via
``importlib.resources`` (offline, no filesystem assumption), parses with stdlib ``tomllib``,
constructs the pydantic models, runs fail-closed validation against the already-loaded role
catalog and the given ``WorkflowSpec`` (the bundled spec by default), and returns a
``PlaybookSpec``.  A corrupt or invalid playbook raises ``SquadsError``.

With a ``squad_dir`` given, ``<squad_dir>/.overrides/playbook.toml`` — when present — is merged
over the bundled default via the shared, loader-agnostic engine (``squads._specmerge``), entirely
at the **raw parsed-TOML mapping** layer, before any model is built — the same
splat/deep-merge mechanics the workflow loader uses (see that module's docstring). Two things are
deliberately narrower here than the workflow override, both settled by the governing decision:

- **Single-file, keyed-table delta, one top-level section (``types``).** The playbook is one
  referentially-coupled document — an entry names role slugs and a type — so it takes the
  workflow override's addressing shape, not the roles override's per-slug-file shape.
- **No independent deselect.** The playbook's active type set is *derived*, not declarable:
  :func:`_check_coverage` already requires exactly one entry per *spec*'s non-roster type, so
  dropping a type from the workflow spec drops its playbook entry as a consequence, with no
  ``[selected]`` key of its own. Passing an empty ``frozenset()`` as the engine's deselectable
  ``section_names`` makes this a *refusal*, not a silent no-op: an override that writes
  ``[selected]`` at all is rejected as naming an unknown section, rather than being accepted and
  quietly doing nothing.

Coverage — and every other structural/referential check — always validates against *spec*, the
caller-supplied ``WorkflowSpec``. On the per-request path that is the **merged, active** spec,
never the bundled one — this is what makes a workflow override's dropped/renamed/added type
correctly drop, rename, or newly require a playbook entry, with no separate wiring: passing the
active spec through is the entire mechanism.

**Known limitation: guide prose is text, and coverage is the only thing checked against the
spec.** Everything above is *structural* — which types have an entry, which role slugs an entry
names. A guide's guidance is free prose, and the bundled document's prose sometimes names another
type by name, because the guidance would not otherwise be runnable ("create tasks with this
feature as parent (``sq create task … --parent FEAT-<n>``)" in ``feature``'s product-owner guide).
A workflow override that drops or renames a type correctly withdraws *that* type's own skill and
entry, and leaves such a line standing in a **surviving** type's skill — so the generated
instruction is confidently wrong rather than absent, and nothing reports it.

This is a limitation with a supported remedy, not a defect awaiting a fix: the remedy is to
override the playbook alongside the workflow, which is what makes it the fourth overridable
document. Templating the prose was considered and declined — a placeholder in place of the type
name costs an actionable command an agent cannot reconstruct, which is worse than a stale one it
can adapt. The bundled prose is instead kept deliberately sparse in cross-type references, so
that an adopter who renames a type has as little to rewrite as possible; adding a gratuitous one
back is a regression against this paragraph.
"""

import functools
import importlib.resources
import tomllib
from pathlib import Path
from typing import Any, cast

from squads._errors import SquadsError
from squads._interactions._models import (
    ItemPlaybookSpec,
    PlaybookSpec,
    RoleGuideSpec,
)
from squads._roles._models import RoleCatalogSpec
from squads._roles._resolver import project_role_slugs
from squads._specmerge import RawMapping, merge_override
from squads._workflow import bundled_spec
from squads._workflow._models import WorkflowSpec

#: The DEV sentinel — exempt from role-catalog slug validation.
DEV = "*dev"

#: Canonical location for the project playbook override (relative to squad_dir).
PLAYBOOK_OVERRIDE_FILENAME = ".overrides/playbook.toml"

#: The playbook document's closed top-level section-key space — enforced at the raw-mapping
#: layer by the merge engine before any model is built. ``selected`` is accepted unconditionally
#: by the engine (see ``_specmerge`` docstring) but needs no entry here since it is never a valid
#: deselect target for this document (see :data:`PLAYBOOK_SELECTED_SECTIONS`).
PLAYBOOK_TOP_LEVEL_SECTIONS: frozenset[str] = frozenset({"types"})

#: The playbook's deselectable ``[selected]`` section names — deliberately empty. The active
#: type set derives from the workflow spec's coverage rule, not an independent declaration, so
#: any ``[selected]`` table an override writes names no valid section and is refused outright
#: (see the module docstring).
PLAYBOOK_SELECTED_SECTIONS: frozenset[str] = frozenset()

#: The fix hint the merge engine reports for a ``[selected]`` table in a playbook override —
#: :data:`PLAYBOOK_SELECTED_SECTIONS` being empty means the generic "use one of the accepted
#: [selected] sections: []" template would offer an empty menu, so this document supplies the
#: actual reason instead: there is nothing to deselect here because coverage is derived, not
#: declared (see the module docstring).
PLAYBOOK_NO_SELECTED_HINT = (
    "the playbook has no [selected] sections to deselect — its active type set is derived "
    "from .overrides/workflow.toml's coverage, not declared here; drop a type there instead"
)


def _read_bundled_bytes() -> bytes:
    try:
        pkg = importlib.resources.files("squads._specs")
        return (pkg / "playbook.toml").read_bytes()
    except Exception as exc:
        raise SquadsError(f"Failed to read bundled playbook.toml: {exc}") from exc


def _bundled_raw() -> RawMapping:
    """The bundled ``playbook.toml``, parsed but not yet built into a model — the merge
    engine's ``base`` input."""
    try:
        return tomllib.loads(_read_bundled_bytes().decode())
    except tomllib.TOMLDecodeError as exc:
        raise SquadsError(f"Malformed bundled playbook.toml: {exc}") from exc


def bundled_playbook_toml_text() -> str:
    """The bundled ``playbook.toml``'s raw text — the ``sq override diff playbook`` Δ-mine
    baseline, mirroring :func:`squads._workflow._loader.bundled_workflow_toml_text`."""
    return _read_bundled_bytes().decode()


def _base_raw_for(spec: WorkflowSpec) -> RawMapping:
    """The bundled raw mapping's ``[types]`` table, with any entry for a type *spec* no longer
    declares as a non-roster type silently dropped — this is the mechanism that makes playbook
    coverage *derived*, not just checked: a type a workflow override dropped must not surface as
    an "extra" playbook entry to refuse (coverage's own docstring), and the only way to keep
    that entry from ever reaching the merge/validation layer at all is to never carry it into
    *this* call's base in the first place. The merge engine itself stays entirely spec-blind —
    this filtering happens strictly before the engine ever sees the mapping.

    A no-op whenever *spec*'s non-roster type set equals the bundled document's own — which is
    exactly the untouched (no workflow override) case, so this changes nothing for a squad with
    no override at all: the bundled-only load stays byte-identical.
    """
    raw = _bundled_raw()
    types_raw = raw.get("types", {})
    if not isinstance(types_raw, dict):
        return raw
    types_map = cast("dict[str, Any]", types_raw)
    creatable = spec.non_roster_types()
    filtered_types = {k: v for k, v in types_map.items() if k in creatable}
    if len(filtered_types) == len(types_map):
        return raw  # nothing dropped — return the original object, not a rebuilt copy
    return {**raw, "types": filtered_types}


def _read_raw_override(
    override_path: Path,
) -> tuple[dict[str, Any], None] | tuple[dict[str, Any], tuple[str, str]]:
    """Read and parse the raw TOML override file.

    Returns ``(raw_dict, None)`` on success, or ``({}, (message, fix_hint))`` on any
    read/parse error — mirrors ``_workflow._loader._read_raw_override`` exactly.
    """
    try:
        raw: dict[str, Any] = tomllib.loads(override_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        return (
            {},
            (
                f"Malformed playbook override {override_path}: {exc}",
                "Fix the TOML syntax and re-run `sq override diff playbook`.",
            ),
        )
    except OSError as exc:
        return (
            {},
            (
                f"Cannot read playbook override {override_path}: {exc}",
                "Check file permissions and re-run `sq override diff playbook`.",
            ),
        )
    else:
        return raw, None


def load_playbook(
    catalog: RoleCatalogSpec,
    spec: WorkflowSpec | None = None,
    squad_dir: Path | None = None,
) -> PlaybookSpec:
    """Read, parse, merge (if a project override is present), and validate the playbook.

    Takes the already-loaded ``RoleCatalogSpec`` as the slug authority for cross-spec
    referential integrity, and a ``WorkflowSpec`` (the bundled spec by default) as the type
    authority: every one of *spec*'s ``non_roster_types()`` must have a playbook entry, and no
    entry may name anything else. Passing the *active* (possibly merged) workflow spec here —
    not the bundled one — is what makes a workflow override's dropped/renamed/added type
    correctly change the playbook's coverage requirement, with no separate wiring.

    When *squad_dir* is ``None`` or ``<squad_dir>/.overrides/playbook.toml`` is absent, this
    builds the playbook straight from the bundled raw mapping — byte-identical to today's
    bundled-only load whenever *spec* is also the bundled spec.

    When the override file is present, it is merged over the bundled raw mapping first (shared
    engine, fail-fast — raises ``SquadsError`` on the first violation), then the merged mapping
    is built and validated exactly as the bundled-only path validates the bundled mapping.

    Called once at module level in ``__init__.py`` (no ``squad_dir``) to build the bundled
    singleton, and per-request by the loader that resolves the active/merged playbook onto the
    request context. Raises ``SquadsError`` on any violation.
    """
    if spec is None:
        spec = bundled_spec()

    raw = _base_raw_for(spec)
    if squad_dir is not None:
        override_path = squad_dir / PLAYBOOK_OVERRIDE_FILENAME
        if override_path.is_file():
            raw_override, parse_error = _read_raw_override(override_path)
            if parse_error is not None:
                raise SquadsError(parse_error[0])
            origin = str(override_path)
            result = merge_override(
                raw,
                raw_override,
                PLAYBOOK_SELECTED_SECTIONS,
                origin,
                top_level_keys=PLAYBOOK_TOP_LEVEL_SECTIONS,
                collect_all=False,
                empty_selected_hint=PLAYBOOK_NO_SELECTED_HINT,
            )
            merged = result.merged
            if merged is None:
                # Unreachable in fail-fast mode: merge_override raises on its own first
                # violation before ever returning one. Fails closed rather than asserting,
                # matching the "never a traceback" contract even for a case that should
                # not occur.
                raise SquadsError(
                    f"playbook override merge failed with no violation reported — {origin}"
                )
            raw = merged

    catalog_slugs = {r.slug for r in catalog.roles}
    if squad_dir is not None:
        # The per-request slug authority: bundled catalog union the project's own role
        # overrides on disk. A wholly-new or renamed-into project role is never in the
        # bundled catalog singleton and cannot be, so validating against the catalog alone
        # refuses every guide slug for a live project role — the mechanism by which a custom
        # role is meant to enter a type's playbook guidance. The bundled-only module-level
        # load below (no squad_dir) deliberately does not gain this — there is no project to
        # read overrides for.
        catalog_slugs |= project_role_slugs(squad_dir)

    return _build_spec(raw, catalog_slugs, spec)


def _build_spec(raw: dict[str, Any], catalog_slugs: set[str], spec: WorkflowSpec) -> PlaybookSpec:
    types_raw: dict[str, Any] = raw.get("types", {})
    types: dict[str, ItemPlaybookSpec] = {}

    for name, data in types_raw.items():
        roles = [_parse_role_guide(r, name, i) for i, r in enumerate(data.get("roles", []))]
        try:
            # Route through model_validate so extra="forbid" fires on unknown keys.
            entry = ItemPlaybookSpec.model_validate({**data, "roles": roles})
        except Exception as exc:
            raise SquadsError(f"Invalid playbook entry for {name!r}: {exc}") from exc
        types[name] = entry

    _validate(types, catalog_slugs, spec)

    try:
        pb_spec = PlaybookSpec(types=types)
    except Exception as exc:
        raise SquadsError(f"Invalid playbook: {exc}") from exc

    return pb_spec


def _parse_role_guide(data: dict[str, Any], type_name: str, idx: int) -> RoleGuideSpec:
    ctx = f"types.{type_name}.roles[{idx}]"
    try:
        # model_validate so extra="forbid" fires on unknown keys (e.g. "doo", "entr").
        return RoleGuideSpec.model_validate(data)
    except Exception as exc:
        raise SquadsError(f"Invalid role guide {ctx}: {exc}") from exc


def _check_slugs(
    types: dict[str, ItemPlaybookSpec],
    catalog_slugs: set[str],
    errors: list[str],
) -> None:
    """Cross-spec slug referential integrity (*dev sentinel exempt)."""
    errors.extend(
        f"types.{item_type}: role slug {guide.slug!r} not in role catalog"
        for item_type, entry in types.items()
        for guide in entry.roles
        if guide.slug != DEV and guide.slug not in catalog_slugs
    )


def _check_duplicate_slugs(types: dict[str, ItemPlaybookSpec], errors: list[str]) -> None:
    """Refuse a role slug that appears more than once in one type's ``roles`` array.

    ``roles`` is semantically keyed by slug — the generated skill renders exactly one H2
    section per slug (see ``_backends._claude_code._backend._write_item_skills``) — so a
    second guide for the same slug is not a second voice for that role, it silently produces
    a truncated second section directly under the first bundled one. The idiom this most often
    catches: ``roles = ["$(*self)", { slug = "<already-bundled>", ... }]`` spreads a slug the
    bundled array already carries. Fail closed here rather than let it through to a document
    the renderer has no merge-by-slug behaviour for.
    """
    for item_type, entry in types.items():
        first_seen: dict[str, int] = {}
        for idx, guide in enumerate(entry.roles):
            prior = first_seen.get(guide.slug)
            if prior is not None:
                errors.append(
                    f"types.{item_type}.roles: slug {guide.slug!r} appears twice "
                    f"(positions {prior} and {idx}) — roles is keyed by slug; to change a "
                    'bundled guide\'s fields, omit "$(*self)" and restate the whole array '
                    "instead of spreading and re-adding the same slug"
                )
            else:
                first_seen[guide.slug] = idx


@functools.cache
def _bundled_type_names() -> frozenset[str]:
    """The bundled playbook document's ``[types]`` key set — parsed once per process and
    cached, unlike :func:`_bundled_raw` itself, which stays deliberately un-cached/reparsed on
    every call (see its docstring / the isolation guarantee that rests on it never handing out
    a shared mapping). A ``frozenset`` of plain strings has no mutable substructure a caller
    could alias into, so caching *this* carries none of that risk — the bundled document is a
    packaged, immutable-for-the-process resource, so its key set can never change mid-process.
    ``_check_coverage`` is the only caller, and needs nothing but this set from a full reparse.
    """
    return frozenset(_bundled_raw().get("types", {}))


def _check_coverage(
    types: dict[str, ItemPlaybookSpec], spec: WorkflowSpec, errors: list[str]
) -> None:
    """Every *bundled* non-roster type still active in *spec* needs a playbook entry; nothing
    outside *spec*'s non-roster set may have one.

    *spec* is the sole authority on which types exist and which are roster — on the per-request
    path this is the *merged*, active workflow spec, so a type a workflow override dropped stops
    being required here (and stops being coverable at all: an entry naming a type absent from
    *spec* fails the second check below).

    The "missing" direction is deliberately scoped to *bundled* type names only, never to a
    project-declared (or renamed-into) one: a custom type with no playbook entry is not a
    coverage violation — it is the existing, sanctioned thin-skill fallback every custom type
    already gets, regardless of whether this feature exists. Requiring an entry for every
    project-declared type would turn "add a custom type via a workflow override" (already legal,
    predates this feature) into a hard failure the moment a project doesn't ALSO write a
    matching playbook entry — breaking that existing, unrelated capability. In practice this
    scoping never actually narrows anything the bundled-document self-check would have caught:
    a bundled type still active in *spec* already has its entry, by construction (the loader's
    own base-filtering step keeps it), so this direction only ever fires for the true bundled
    document validating against itself — the maintainer safety net a missing bundled entry
    needs, preserved unchanged.
    """
    creatable_types = spec.non_roster_types()
    bundled_type_names = _bundled_type_names()
    errors.extend(
        f"missing required work-type entry: {wt!r}"
        for wt in sorted(creatable_types & bundled_type_names)
        if wt not in types
    )
    errors.extend(
        f"types.{name}: not a declared non-roster type in the workflow spec "
        "(role/skill/operator are managed separately; unknown type names are rejected)"
        for name in types
        if name not in creatable_types
    )


def _check_text(types: dict[str, ItemPlaybookSpec], errors: list[str]) -> None:
    """Required text non-empty."""
    for item_type, entry in types.items():
        if not entry.overview.strip():
            errors.append(f"types.{item_type}: overview is empty")
        if not entry.lifecycle.strip():
            errors.append(f"types.{item_type}: lifecycle is empty")


def _validate(
    types: dict[str, ItemPlaybookSpec], catalog_slugs: set[str], spec: WorkflowSpec
) -> None:
    errors: list[str] = []
    _check_slugs(types, catalog_slugs, errors)
    _check_duplicate_slugs(types, errors)
    _check_coverage(types, spec, errors)
    _check_text(types, errors)
    if errors:
        raise SquadsError("Invalid playbook:\n" + "\n".join(f"  - {e}" for e in errors))


# ---------------------------------------------------------------------------
# Drift stamping — whether a playbook override shadows the bundled spec: a raw key-set
# intersection, no merge required. Mirrors ``_workflow._loader``'s equivalent so `sq check`
# and a future `sq playbook lint` (if ever added) never disagree about the same file.
# ---------------------------------------------------------------------------


def _raw_shadows_bundled(bundled_raw: RawMapping, override_raw: RawMapping) -> bool:
    bundled_types = bundled_raw.get("types", {})
    override_types = override_raw.get("types", {})
    if not isinstance(bundled_types, dict) or not isinstance(override_types, dict):
        return False
    bundled_keys = cast("dict[str, Any]", bundled_types)
    override_keys = cast("dict[str, Any]", override_types)
    return bool(set(bundled_keys) & set(override_keys))


def playbook_override_shadows_bundled(squad_dir: Path) -> bool:
    """Whether ``<squad_dir>/.overrides/playbook.toml`` redeclares (shadows) at least one
    bundled type entry — a raw key-set intersection, no merge required.

    Returns ``False`` when the override is absent, unreadable, or malformed TOML: the drift-
    stamp obligation is moot for a file that cannot even be parsed.
    """
    override_path = squad_dir / PLAYBOOK_OVERRIDE_FILENAME
    if not override_path.is_file():
        return False
    try:
        override_raw: RawMapping = tomllib.loads(override_path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):  # fmt: skip
        return False
    return _raw_shadows_bundled(_bundled_raw(), override_raw)


def _declared_guide_slugs(entry: Any) -> list[str]:
    """The role slugs one raw ``[types.<name>]`` table declares **literally** in its ``roles``
    array.

    Skips a splat-ref entry (the string ``"$(*self)"`` and friends): it names no slug of its own
    and spreads the bundled array by reference, so the guides it pulls in are still squads' own.
    Skips anything that is not a mapping with a string ``slug`` too — the loader's own validation
    is what reports a malformed guide; this reader answers only "which slugs did the adopter
    write", and must never raise for a shape it did not expect.
    """
    if not isinstance(entry, dict):
        return []
    roles = cast("dict[str, Any]", entry).get("roles")
    if not isinstance(roles, list):
        return []
    slugs: list[str] = []
    for guide in cast("list[Any]", roles):
        slug = cast("dict[str, Any]", guide).get("slug") if isinstance(guide, dict) else None
        if isinstance(slug, str):
            slugs.append(slug)
    return slugs


def playbook_override_guide_pairs(squad_dir: Path) -> frozenset[tuple[str, str]]:
    """Every ``(item_type, role_slug)`` guide ``<squad_dir>/.overrides/playbook.toml`` declares —
    read from the **raw** override mapping, before any merge with the bundled base.

    The question this answers is *who wrote this guide*, which the merged ``PlaybookSpec`` cannot
    answer: the merged document is bundled-plus-override and holds no provenance. That distinction
    is what separates an actionable dropped-guide report from an unactionable one — a guide the
    adopter declared here is theirs to remove, whereas one that exists only in the bundled
    document is squads' own graceful degradation, which no adopter can edit and should therefore
    not be told about (see :func:`~squads._interactions.orphaned_playbook_guides`).

    Returns an empty set when the override is absent, unreadable, or malformed TOML — the same
    tolerance :func:`playbook_override_shadows_bundled` keeps, for the same reason: the callers
    are ``sq check``/``sq sync``, neither of which may fail over this question, and a file that
    cannot be parsed has declared nothing.
    """
    override_path = squad_dir / PLAYBOOK_OVERRIDE_FILENAME
    if not override_path.is_file():
        return frozenset()
    try:
        raw: RawMapping = tomllib.loads(override_path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):  # fmt: skip
        return frozenset()
    types_raw = raw.get("types")
    if not isinstance(types_raw, dict):
        return frozenset()
    return frozenset(
        (item_type, slug)
        for item_type, entry in cast("dict[str, Any]", types_raw).items()
        for slug in _declared_guide_slugs(entry)
    )


def playbook_stamp_finding(squad_dir: Path, stamp: str | None) -> tuple[str, str] | None:
    """The stamp obligation for the playbook override — mirrors
    ``_workflow._loader.workflow_stamp_finding`` exactly (same three-state contract), so
    ``sq check`` and ``sq override list`` agree on this kind the same way they already agree
    on ``workflow``. Returns ``(level, message)``, or ``None`` when nothing is owed."""

    from squads import __version__

    if stamp is None:
        if playbook_override_shadows_bundled(squad_dir):
            return (
                "error",
                "shadowing playbook override has no squads:override-base stamp; run "
                "`sq override update playbook` to re-stamp",
            )
        return None
    if stamp != __version__:
        return (
            "warn",
            f"playbook override may be stale: stamp v{stamp} predates running v{__version__}; "
            "run `sq override diff playbook` to review, then `sq override update playbook` "
            "to re-stamp",
        )
    return None
