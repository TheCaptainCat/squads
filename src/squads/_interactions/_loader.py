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
import tomllib
from pathlib import Path
from typing import Any, cast

from squads._errors import SquadsError
from squads._interactions._models import (
    ItemPlaybookSpec,
    PlaybookSpec,
    RoleGuideSpec,
)
from squads._interactions._role_guidance import (
    CAPABILITY_SUBJECT_PREFIX,
    CAPABILITY_TOKEN_CANDIDATE,
    guide_text_lines,
)
from squads._overrides._manifest import PLAYBOOK_KEY, artifact_changed_since
from squads._roles._models import (
    CAPABILITY_NAME_PATTERN,
    CatalogSource,
    RoleCatalogSpec,
    malformed_capability_names,
)
from squads._roles._resolver import project_role_slugs
from squads._specload import (
    OverrideFiles,
    OverrideMessages,
    SpecDocument,
    bundled_raw,
    bundled_text,
    load_override,
    override_mapping,
)
from squads._specmerge import RawMapping, describe_spec_error
from squads._workflow._loader import as_entry_list, as_table
from squads._workflow._models import WorkflowSpec

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


_DOCUMENT = SpecDocument(
    bundled_file="playbook.toml",
    override_file=PLAYBOOK_OVERRIDE_FILENAME,
    override_name="playbook override",
    top_level_keys=PLAYBOOK_TOP_LEVEL_SECTIONS,
    selected_sections=PLAYBOOK_SELECTED_SECTIONS,
    messages=OverrideMessages(
        malformed="Malformed playbook override {path}: {exc}",
        unreadable="Cannot read playbook override {path}: {exc}",
        malformed_hint="Fix the TOML syntax and re-run `sq override diff playbook`.",
        unreadable_hint="Check file permissions and re-run `sq override diff playbook`.",
    ),
    empty_selected_hint=PLAYBOOK_NO_SELECTED_HINT,
)


def _bundled_raw() -> RawMapping:
    return bundled_raw(_DOCUMENT)


def bundled_playbook_toml_text() -> str:
    """The bundled ``playbook.toml``'s raw text — the ``sq override diff playbook`` Δ-mine
    baseline, mirroring :func:`squads._workflow._loader.bundled_workflow_toml_text`."""
    return bundled_text(_DOCUMENT)


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


def load_playbook(
    catalog: RoleCatalogSpec,
    spec: WorkflowSpec,
    squad_dir: Path | None = None,
    *,
    project_catalog: CatalogSource | None = None,
    files: OverrideFiles | None = None,
) -> PlaybookSpec:
    """Read, parse, merge (if a project override is present), and validate the playbook.

    Takes the already-loaded ``RoleCatalogSpec`` as the slug authority for cross-spec
    referential integrity — with *squad_dir* given, joined by the project's own roles: the
    per-slug role files, and the roles *project_catalog* (the squad's merged catalog, built by
    the caller) defines beyond the bundled ones — and a ``WorkflowSpec`` as the type
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

    Called once, on first use, by ``_playbook.get_playbook_spec`` (no ``squad_dir``) to build the
    bundled singleton, and by the squad's document resolver for the active/merged playbook.
    Raises ``SquadsError`` on any violation.
    """
    raw = _base_raw_for(spec)
    loaded = load_override(_DOCUMENT, squad_dir, lambda: raw, files)
    origin: str | None = None
    if loaded is not None:
        raw = loaded.raw
        origin = loaded.origin

    catalog_slugs = {r.slug for r in catalog.roles}
    if squad_dir is not None:
        # The per-request slug authority: bundled catalog union the project's own role
        # overrides on disk. A wholly-new or renamed-into project role is never in the
        # bundled catalog singleton and cannot be, so validating against the catalog alone
        # refuses every guide slug for a live project role — the mechanism by which a custom
        # role is meant to enter a type's playbook guidance. The bundled-only module-level
        # load below (no squad_dir) deliberately does not gain this — there is no project to
        # read overrides for.
        catalog_slugs |= project_role_slugs(
            squad_dir, project_catalog if project_catalog is not None else (lambda: catalog)
        )

    try:
        return _build_spec(raw, catalog_slugs, spec)
    except SquadsError as exc:
        if origin is None:
            raise
        raise SquadsError(f"{origin}: {exc}") from exc


def _build_spec(raw: dict[str, Any], catalog_slugs: set[str], spec: WorkflowSpec) -> PlaybookSpec:
    types_raw = as_table(raw.get("types", {}), "types")
    types: dict[str, ItemPlaybookSpec] = {}

    for name, entry_raw in types_raw.items():
        data = as_table(entry_raw, f"types.{name}")
        role_tables = as_entry_list(data.get("roles", []), f"types.{name}.roles")
        roles = [_parse_role_guide(r, name, i) for i, r in enumerate(role_tables)]
        try:
            # Route through model_validate so extra="forbid" fires on unknown keys.
            entry = ItemPlaybookSpec.model_validate({**data, "roles": roles})
        except Exception as exc:
            raise SquadsError(
                f"Invalid playbook entry for {name!r}: {describe_spec_error(exc, ItemPlaybookSpec)}"
            ) from exc
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
        raise SquadsError(
            f"Invalid role guide {ctx}: {describe_spec_error(exc, RoleGuideSpec)}"
        ) from exc


def _check_slugs(
    types: dict[str, ItemPlaybookSpec],
    catalog_slugs: set[str],
    errors: list[str],
) -> None:
    """Cross-spec slug referential integrity. A capability subject (``*<name>``) names no
    catalog slug and is exempt; a malformed one is refused."""
    for item_type, entry in types.items():
        for guide in entry.roles:
            if guide.slug.startswith(CAPABILITY_SUBJECT_PREFIX):
                name = guide.slug[len(CAPABILITY_SUBJECT_PREFIX) :]
                if malformed_capability_names([name]):
                    errors.append(
                        f"types.{item_type}: capability subject {guide.slug!r} must be "
                        f"{CAPABILITY_SUBJECT_PREFIX}<name>, with a name matching "
                        f"{CAPABILITY_NAME_PATTERN}"
                    )
            elif guide.slug not in catalog_slugs:
                errors.append(f"types.{item_type}: role slug {guide.slug!r} not in role catalog")


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
def bundled_type_names() -> frozenset[str]:
    """The bundled playbook document's ``[types]`` key set, built once from the shared parse of
    the packaged file: the item types squads ships guidance, and so a managed skill, for."""
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
    bundled_names = bundled_type_names()
    errors.extend(
        f"missing required work-type entry: {wt!r}"
        for wt in sorted(creatable_types & bundled_names)
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


def _check_capability_tokens(types: dict[str, ItemPlaybookSpec], errors: list[str]) -> None:
    """Refuse an ``@*`` in command or guide text whose name is not a well-formed capability."""
    for item_type, entry in types.items():
        texts = [*entry.commands, *(line for g in entry.roles for line in guide_text_lines(g))]
        names = (n for line in texts for n in CAPABILITY_TOKEN_CANDIDATE.findall(line))
        errors.extend(
            f"types.{item_type}: capability token '@*{name}' must be "
            f"@{CAPABILITY_SUBJECT_PREFIX}<name>, with a name matching {CAPABILITY_NAME_PATTERN}"
            for name in names
            if malformed_capability_names([name])
        )


def _validate(
    types: dict[str, ItemPlaybookSpec], catalog_slugs: set[str], spec: WorkflowSpec
) -> None:
    errors: list[str] = []
    _check_slugs(types, catalog_slugs, errors)
    _check_duplicate_slugs(types, errors)
    _check_coverage(types, spec, errors)
    _check_text(types, errors)
    _check_capability_tokens(types, errors)
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


def playbook_override_shadows_bundled(squad_dir: Path, files: OverrideFiles | None = None) -> bool:
    """Whether ``<squad_dir>/.overrides/playbook.toml`` redeclares (shadows) at least one
    bundled type entry — a raw key-set intersection, no merge required.

    Returns ``False`` when the override is absent, unreadable, or malformed TOML: the drift-
    stamp obligation is moot for a file that cannot even be parsed.
    """
    override_path = squad_dir / PLAYBOOK_OVERRIDE_FILENAME
    if not override_path.is_file():
        return False
    try:
        override_raw: RawMapping = override_mapping(override_path, files)
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


def playbook_override_guide_pairs(
    squad_dir: Path, files: OverrideFiles | None = None
) -> frozenset[tuple[str, str]]:
    """Every ``(item_type, role_slug)`` guide ``<squad_dir>/.overrides/playbook.toml`` declares —
    read from the **raw** override mapping, before any merge with the bundled base.

    The question this answers is *who wrote this guide*, which the merged ``PlaybookSpec`` cannot
    answer: the merged document is bundled-plus-override and holds no provenance. That distinction
    is what separates an actionable dropped-guide report from an unactionable one — a guide the
    adopter declared here is theirs to remove, whereas one that exists only in the bundled
    document is squads' own graceful degradation, which no adopter can edit and should therefore
    not be told about (see :func:`~squads._interactions._playbook.orphaned_playbook_guides`).

    Returns an empty set when the override is absent, unreadable, or malformed TOML — the same
    tolerance :func:`playbook_override_shadows_bundled` keeps, for the same reason: the callers
    are ``sq check``/``sq sync``, neither of which may fail over this question, and a file that
    cannot be parsed has declared nothing.
    """
    return frozenset(
        (item_type, slug)
        for item_type, entry in _override_types(squad_dir, files).items()
        for slug in _declared_guide_slugs(entry)
    )


def playbook_override_command_lines(
    squad_dir: Path, files: OverrideFiles | None = None
) -> frozenset[tuple[str, str]]:
    """Every ``(item_type, line)`` command line ``<squad_dir>/.overrides/playbook.toml`` declares
    in a type's ``commands`` (a splat-ref entry carries no token).

    Read from the raw override mapping for the same reason as
    :func:`playbook_override_guide_pairs`: only the adopter can clear a report about these lines.
    """
    lines: set[tuple[str, str]] = set()
    for item_type, entry in _override_types(squad_dir, files).items():
        commands = (
            cast("dict[str, Any]", entry).get("commands") if isinstance(entry, dict) else None
        )
        if isinstance(commands, list):
            lines.update(
                (item_type, line) for line in cast("list[Any]", commands) if isinstance(line, str)
            )
    return frozenset(lines)


def _override_types(squad_dir: Path, files: OverrideFiles | None) -> dict[str, Any]:
    """The raw ``[types]`` table of the playbook override, empty when the file is absent,
    unreadable, malformed TOML or has no such table."""
    override_path = squad_dir / PLAYBOOK_OVERRIDE_FILENAME
    if not override_path.is_file():
        return {}
    try:
        raw: RawMapping = override_mapping(override_path, files)
    except (tomllib.TOMLDecodeError, OSError):  # fmt: skip
        return {}
    types_raw = raw.get("types")
    return cast("dict[str, Any]", types_raw) if isinstance(types_raw, dict) else {}


def playbook_stamp_finding(
    squad_dir: Path, stamp: str | None, files: OverrideFiles | None = None
) -> tuple[str, str] | None:
    """The stamp obligation for the playbook override. Returns ``(level, message)``, or
    ``None`` when nothing is owed:

    - shadowing **and** unstamped -> ``("error", ...)`` — a shadowing override has stopped
      tracking the bundled spec and so carries the provenance obligation every other
      shadowing override kind carries.
    - stamped, older than running, **and the bundled playbook.toml actually changed** since
      that stamp -> ``("warn", ...)``. Drift is content-gated: an old stamp alone is never a
      warning, so an add-only override with no bundled change behind it reports clean, not
      "may be stale".
    - stamped at the running version, content unchanged since the stamp, or add-only and
      unstamped -> ``None``.
    """

    from squads import __version__

    if stamp is None:
        if playbook_override_shadows_bundled(squad_dir, files):
            return (
                "error",
                "shadowing playbook override has no squads:override-base stamp; run "
                "`sq override update playbook` to re-stamp",
            )
        return None
    if stamp != __version__ and artifact_changed_since(PLAYBOOK_KEY, stamp):
        return (
            "warn",
            f"playbook override may be stale: bundled playbook.toml changed since v{stamp}; "
            "run `sq override diff playbook` to review, then `sq override update playbook` "
            "to re-stamp",
        )
    return None
