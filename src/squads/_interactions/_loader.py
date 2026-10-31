"""Load and validate the playbook spec, merging a project override over the bundled base.

``load_playbook(catalog, spec, squad_dir)`` is the single entry point. It reads
``playbook.toml`` from the ``squads._specs`` package (``importlib.resources``, parsed with
``tomllib``), builds the pydantic models, validates fail-closed against the role catalog and
*spec* (the bundled ``WorkflowSpec`` by default) and returns a ``PlaybookSpec``; a corrupt or
invalid playbook raises ``SquadsError``.

With a ``squad_dir``, ``<squad_dir>/.overrides/playbook.toml``, when present, is merged over
the bundled default at the raw parsed-TOML layer, before any model is built, by the shared
engine ``squads._specmerge`` (the splat and deep-merge mechanics the workflow loader uses).
Two things are narrower than the workflow override:

- It is a single file with a keyed-table delta and one top-level section (``types``). The
  playbook is one referentially-coupled document (an entry names role slugs and a type), so
  it takes the workflow override's addressing shape, not the roles override's per-slug files.
- It has no independent deselect. The active type set is derived: :func:`_check_coverage`
  requires one entry per non-roster type of *spec*, so dropping a type from the workflow spec
  drops its entry. An empty ``frozenset()`` as the engine's deselectable ``section_names``
  makes any ``[selected]`` in the override a refusal (unknown section), not a silent no-op.

Every structural and referential check validates against the caller's *spec*, on the
per-request path the merged active one, so a workflow override's dropped, renamed or added
type drops, renames or newly requires a playbook entry with no separate wiring.

Known limitation: coverage is the only thing checked against the spec; guide prose is text.
The bundled prose sometimes names another type where the guidance would not otherwise be
runnable (``feature``'s product-owner guide: ``sq create task … --parent FEAT-<n>``). A
workflow override that drops or renames a type withdraws that type's own skill and entry but
leaves such a line in a surviving type's skill, so the instruction is confidently wrong and
nothing reports it. The supported remedy is to override the playbook alongside the workflow.
Templating the prose was declined: a placeholder costs an agent a command it cannot
reconstruct, which is worse than a stale one it can adapt. The bundled prose is kept sparse
in cross-type references, so an adopter who renames a type has little to rewrite; adding a
gratuitous reference is a regression against this paragraph.
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
from squads._models._participants import (
    group_verb_problem,
    is_valid_slug,
    reserved_role_slug_problem,
)
from squads._roles._models import CAPABILITY_NAME_PATTERN, malformed_capability_names
from squads._specload import (
    OverrideFiles,
    OverrideMessages,
    SpecDocument,
    bundled_raw,
    bundled_text,
    load_override,
    override_mapping,
    override_present,
)
from squads._specmerge import RawMapping, describe_spec_error
from squads._workflow._loader import as_entry_list, as_table
from squads._workflow._models import WorkflowSpec

#: Canonical location for the project playbook override (relative to squad_dir).
PLAYBOOK_OVERRIDE_FILENAME = ".overrides/playbook.toml"

#: The playbook's closed top-level section keys, enforced by the merge engine on the raw mapping.
#: ``selected`` is accepted by the engine itself and needs no entry, since it is never a valid
#: deselect target here (:data:`PLAYBOOK_SELECTED_SECTIONS`).
PLAYBOOK_TOP_LEVEL_SECTIONS: frozenset[str] = frozenset({"types"})

#: The playbook's deselectable ``[selected]`` sections, empty on purpose: the active type set
#: derives from the workflow spec's coverage rule, so any ``[selected]`` table is refused.
PLAYBOOK_SELECTED_SECTIONS: frozenset[str] = frozenset()

#: The fix hint for a ``[selected]`` table in a playbook override. The generic "use one of the
#: accepted sections: []" would offer an empty menu, so this gives the reason: coverage is
#: derived, so there is nothing to deselect.
PLAYBOOK_NO_SELECTED_HINT = (
    "the playbook has no [selected] sections to deselect — its active type set is derived "
    "from .overrides/workflow.toml's coverage, not declared here; drop a type there instead"
)


PLAYBOOK_OVERRIDE_MESSAGES = OverrideMessages(
    malformed="Malformed playbook override {path}: {exc}",
    unreadable="Cannot read playbook override {path}: {exc}",
    not_utf8="Playbook override {path} is not valid UTF-8; save it as UTF-8 and re-run.",
    malformed_hint="Fix the TOML syntax and re-run `sq override diff playbook`.",
    unreadable_hint="Check file permissions and re-run `sq override diff playbook`.",
)


_DOCUMENT = SpecDocument(
    bundled_file="playbook.toml",
    override_file=PLAYBOOK_OVERRIDE_FILENAME,
    override_name="playbook override",
    top_level_keys=PLAYBOOK_TOP_LEVEL_SECTIONS,
    selected_sections=PLAYBOOK_SELECTED_SECTIONS,
    messages=PLAYBOOK_OVERRIDE_MESSAGES,
    empty_selected_hint=PLAYBOOK_NO_SELECTED_HINT,
)


def _bundled_raw() -> RawMapping:
    return bundled_raw(_DOCUMENT)


def bundled_playbook_toml_text() -> str:
    """The bundled ``playbook.toml``'s raw text — the ``sq override diff playbook`` Δ-mine
    baseline, mirroring :func:`squads._workflow._loader.bundled_workflow_toml_text`."""
    return bundled_text(_DOCUMENT)


def _base_raw_for(spec: WorkflowSpec) -> RawMapping:
    """The bundled raw ``[types]`` table without entries for types *spec* lacks as non-roster.

    This is what makes playbook coverage derived, not just checked: an entry for a type a
    workflow override dropped must not reach the merge and validation layer as an "extra" entry
    to refuse, so it is never carried into this call's base. The merge engine stays spec-blind;
    the filtering happens strictly before it. It is a no-op when *spec*'s non-roster set equals
    the bundled document's, the no-override case.
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
    spec: WorkflowSpec,
    squad_dir: Path | None = None,
    *,
    files: OverrideFiles | None = None,
) -> PlaybookSpec:
    """Read, parse, merge (if a project override is present), and validate the playbook.

    *spec* is the type authority: every one of its ``non_roster_types()`` needs a playbook entry
    and no entry may name anything else. Passing the active (possibly merged) workflow spec, not
    the bundled one, is what makes a workflow override's dropped, renamed or added type change
    the coverage requirement.

    With *squad_dir* ``None`` or no ``<squad_dir>/.overrides/playbook.toml``, the playbook is
    built from the bundled raw mapping. Otherwise the override is merged over it first (shared
    engine, fail-fast: ``SquadsError`` on the first violation), then the merged mapping is built
    and validated as the bundled one is.

    It is called once, on first use, by ``_playbook.get_playbook_spec`` (no ``squad_dir``) for
    the bundled singleton, and by the squad's document resolver for the active playbook.
    """
    raw = _base_raw_for(spec)
    loaded = load_override(_DOCUMENT, squad_dir, lambda: raw, files)
    origin: str | None = None
    if loaded is not None:
        raw = loaded.raw
        origin = loaded.origin

    try:
        return _build_spec(raw, spec)
    except SquadsError as exc:
        if origin is None:
            raise
        raise SquadsError(f"{origin}: {exc}") from exc


def _build_spec(raw: dict[str, Any], spec: WorkflowSpec) -> PlaybookSpec:
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

    _validate(types, spec)

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
    errors: list[str],
) -> None:
    """A guide's subject is checked for grammar only: a role slug in the slug grammar, or a
    capability subject (``*<name>``) with a well-formed name. Whether a role holds it is
    ``sq check``'s finding, since the loader reads no role item."""
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
            elif not is_valid_slug(guide.slug):
                errors.append(
                    f"types.{item_type}: role slug {guide.slug!r} is not a slug "
                    "(lowercase letters, digits and hyphens)"
                )
            elif problem := (
                reserved_role_slug_problem(guide.slug) or group_verb_problem("role", guide.slug)
            ):
                errors.append(
                    f"types.{item_type}: role slug {guide.slug!r} {problem}, so no role can hold it"
                )


def _check_duplicate_slugs(types: dict[str, ItemPlaybookSpec], errors: list[str]) -> None:
    """Refuse a role slug that appears more than once in one type's ``roles`` array.

    ``roles`` is keyed by slug: the generated skill renders one H2 section per slug (see
    ``_backends._claude_code._backend._write_item_skills``), so a second guide for a slug is
    not a second voice but a truncated second section under the first. The usual cause is
    ``roles = ["$(*self)", { slug = "<already-bundled>", ... }]``, which spreads a slug the
    bundled array already carries. The renderer has no merge-by-slug behaviour, so fail closed.
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
    """Every bundled non-roster type active in *spec* needs an entry; no other type may have one.

    *spec* is the sole authority on which types exist; on the per-request path it is the merged
    active spec, so a type a workflow override dropped stops being required (and cannot be
    covered: an entry for a type absent from *spec* fails the second check).

    The "missing" direction covers bundled type names only. A custom or renamed-into type with
    no entry gets the sanctioned thin-skill fallback; requiring one would turn "add a custom
    type via a workflow override", already legal, into a hard failure for any project that does
    not also write an entry. This never narrows what the bundled self-check catches: a bundled
    type still active already has its entry, since the loader's base filtering keeps it, so this
    direction fires only for the bundled document validating against itself, the maintainer
    safety net for a missing bundled entry.
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


def _validate(types: dict[str, ItemPlaybookSpec], spec: WorkflowSpec) -> None:
    errors: list[str] = []
    _check_slugs(types, errors)
    _check_duplicate_slugs(types, errors)
    _check_coverage(types, spec, errors)
    _check_text(types, errors)
    _check_capability_tokens(types, errors)
    if errors:
        raise SquadsError("Invalid playbook:\n" + "\n".join(f"  - {e}" for e in errors))


# ---------------------------------------------------------------------------
# Drift stamping: whether a playbook override shadows the bundled spec, a raw key-set
# intersection with no merge. Mirrors ``_workflow._loader``'s equivalent.
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
    if not override_present(override_path):
        return False
    try:
        override_raw: RawMapping = override_mapping(override_path, files)
    except (tomllib.TOMLDecodeError, OSError, UnicodeDecodeError):  # fmt: skip
        return False
    return _raw_shadows_bundled(_bundled_raw(), override_raw)


def _declared_guide_slugs(entry: Any) -> list[str]:
    """The role slugs one raw ``[types.<name>]`` table declares literally in its ``roles`` array.

    It skips a splat-ref entry (``"$(*self)"`` and friends), which names no slug of its own and
    spreads the bundled array, and anything that is not a mapping with a string ``slug``; the
    loader's validation reports a malformed guide. It answers only "which slugs did the adopter
    write" and never raises for an unexpected shape.
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
    """Every ``(item_type, role_slug)`` guide ``.overrides/playbook.toml`` declares, read raw.

    It reads the override mapping before any merge, because the question is who wrote the guide
    and the merged ``PlaybookSpec`` holds no provenance. That separates an actionable
    dropped-guide report from an unactionable one: an adopter's own guide is theirs to remove,
    while a guide only in the bundled document is squads' own graceful degradation, which no
    adopter can edit (see :func:`~squads._interactions._playbook.orphaned_playbook_guides`).

    The result is empty when the override is absent, unreadable or malformed TOML, with the same
    tolerance as :func:`playbook_override_shadows_bundled`: ``sq check`` and ``sq sync`` must not
    fail over this, and an unparseable file declared nothing.
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
    if not override_present(override_path):
        return {}
    try:
        raw: RawMapping = override_mapping(override_path, files)
    except (tomllib.TOMLDecodeError, OSError, UnicodeDecodeError):  # fmt: skip
        return {}
    types_raw = raw.get("types")
    return cast("dict[str, Any]", types_raw) if isinstance(types_raw, dict) else {}


def playbook_stamp_finding(
    squad_dir: Path, stamp: str | None, files: OverrideFiles | None = None
) -> tuple[str, str] | None:
    """The playbook override's stamp obligation: ``(level, message)``, or ``None`` if none is owed.

    - Shadowing and unstamped gives ``("error", ...)``: a shadowing override stopped tracking the
      bundled spec, so it carries the provenance obligation every shadowing override kind does.
    - Stamped, older than running, and the bundled ``playbook.toml`` changed since the stamp gives
      ``("warn", ...)``. Drift is content-gated: an old stamp alone is never a warning, so an
      add-only override with no bundled change behind it reports clean.
    - Stamped at the running version, unchanged since the stamp, or add-only and unstamped gives
      ``None``.
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
    from squads._overrides._manifest import PLAYBOOK_KEY, artifact_changed_since

    if stamp != __version__ and artifact_changed_since(PLAYBOOK_KEY, stamp):
        return (
            "warn",
            f"playbook override may be stale: bundled playbook.toml changed since v{stamp}; "
            "run `sq override diff playbook` to review, then `sq override update playbook` "
            "to re-stamp",
        )
    return None
