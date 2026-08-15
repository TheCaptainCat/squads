"""Role resolver: layer ``<squad-dir>/.overrides/roles/<slug>.toml`` over ``PREDEFINED``.

Call :func:`resolve_role` instead of :func:`~squads._roles._catalog.role_by_slug` whenever a
squad directory is available (i.e. from service-level code).  Call :func:`resolve_dev_role`
instead of :func:`~squads._roles._catalog.dev_role` for stack-specific developer roles.

Merge semantics:
- **Bundled slug** — only the fields present in the TOML override the ``PREDEFINED`` defaults;
  absent fields are inherited as-is.  This lets a project rename ``architect`` or change its
  model without restating the full mission.
- **New slug** — a TOML for a slug not in ``PREDEFINED`` defines a wholly-new role; all required
  ``RoleDef`` fields must be present (``slug``, ``full_name``, ``title``, ``description``,
  ``mission``), otherwise a :class:`~squads._errors.SquadsError` is raised with a clear message.
- **No override file** — falls through to the bundled catalog unchanged.

The merge itself is the shared engine (:mod:`squads._specmerge`) and the validation is the
typed :class:`~squads._roles._models.RoleSpec`, exactly as the workflow and playbook overrides
already do — this document is not the one override kind with its own hand-rolled rules. The
difference that matters is what a loose role override *does*: a role is materialised into the
agent hosts' own files, so a bad value here writes a broken agent definition rather than making
an ``sq`` view odd. Assigning raw TOML values into a plain dataclass had four consequences, each
persisted with ``sq check`` clean — ``can_spawn = "false"`` is a non-empty string and therefore
truthy, so a *quoting mistake granted spawn authority*; ``model = "opuss"`` was stored despite
the bundled catalog's own model whitelist; a non-string ``color`` landed verbatim in the
generated pointer; and an unknown key was silently discarded, so a typo'd field simply had no
effect. Splat-refs were unresolved too, writing the literal ``"$(*self)"`` into frontmatter and
into the rendered body — the very idiom the override scaffold teaches.

The resolver is *stateless*: it reads from disk on every call.  The service layer is already the
cached / transactional boundary; there is no need to cache here.

``full_name`` in a role TOML seeds the name when the role is activated.  The key is
passed through to ``RoleDef.full_name``; downstream code (``extra.full_name``,
roster, pointers, CLAUDE.md section) reads from there.
"""

import tomllib
from pathlib import Path
from typing import Any, cast

from squads._errors import RoleNotFoundError, SquadsError
from squads._roles._catalog import PREDEFINED, RoleDef, dev_role, role_spec_to_def
from squads._roles._loader import VALID_MODELS
from squads._roles._models import RoleSpec
from squads._specmerge import RawMapping, merge_override

_PREDEFINED_BY_SLUG: dict[str, RoleDef] = {r.slug: r for r in PREDEFINED}

# Required fields for a *new-slug* TOML (slug is derived from the filename, not the TOML).
_REQUIRED_FOR_NEW = ("full_name", "title", "description", "mission")

#: The role document's closed top-level key space — the fields of ``RoleSpec``, read off the
#: model rather than restated, so it grows with the model instead of going stale beside it.
#: Deriving it is also what lets this document be *closed* without costing forward
#: compatibility: the old resolver silently dropped any key it did not recognise, on a
#: forward-compat argument that in practice made every typo a no-op the adopter could not see.
_ROLE_TOP_LEVEL_KEYS: frozenset[str] = frozenset(RoleSpec.model_fields)

#: A role TOML has no keyed sub-sections, so there is nothing a ``[selected]`` table could
#: shrink — the engine still refuses one, with this reason instead of an empty menu.
_NO_SELECTED_HINT = (
    "a role override has no keyed sections to shrink — its top level IS the field set; "
    "remove the [selected] table"
)


def _overrides_dir(squad_dir: Path) -> Path:
    return squad_dir / ".overrides" / "roles"


def project_role_slugs(squad_dir: Path) -> frozenset[str]:
    """The slugs with a project role override on disk at ``<squad_dir>/.overrides/roles/``.

    A project-defined (wholly new, or renamed-into) slug is not in the bundled catalog and
    never will be — its only record is this override file. Callers that must accept such a
    slug as valid on the per-request path (e.g. the playbook loader's cross-spec role-slug
    check) union this with the bundled catalog's own slugs rather than reading the index —
    the override files are readable before the index is, and are the same source this
    resolver itself reads. Returns an empty set when the directory is absent.
    """
    d = _overrides_dir(squad_dir)
    if not d.is_dir():
        return frozenset()
    return frozenset(p.stem for p in d.glob("*.toml"))


def _read_toml(path: Path) -> dict[str, Any]:
    """Read *path* as TOML; surface a :class:`SquadsError` on parse failure."""
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise SquadsError(f"malformed role override {path}: {exc}") from exc


def _base_raw(base: RoleDef | None) -> RawMapping:
    """*base* as the raw mapping the merge engine composes against — the same shape the TOML
    itself parses to, so a splat-ref addresses a bundled field by its document name.

    Tuples become lists deliberately: ``$(*self)`` spreads a *list*, and a base whose
    ``responsibilities`` arrived as a tuple would make the append idiom fail against the
    bundled catalog while succeeding against an identical hand-written array.
    """
    if base is None:
        return {}
    raw: RawMapping = {}
    for name in RoleSpec.model_fields:
        value: Any = getattr(base, name)
        if value is None:
            continue
        raw[name] = list(cast("tuple[Any, ...]", value)) if isinstance(value, tuple) else value
    return raw


def _apply_override(base: RoleDef | None, data: RawMapping, slug: str, origin: str) -> RoleDef:
    """Merge *data* from a TOML file over *base* (or build a new role if base is ``None``),
    then validate the result as a :class:`RoleSpec`.

    *origin* is the override file's path, carried into every violation the engine reports so
    a refusal names the file the adopter has to edit.

    A ``slug`` key inside the TOML is accepted only when it agrees with the filename, which is
    canonical: a disagreeing one is a declaration that would silently do nothing, and this
    document has no other way to say what it meant.
    """
    if base is None:
        # New-slug path: all required fields must be present. Checked before the merge so the
        # message names the missing *document* fields, rather than four pydantic entries.
        missing = [f for f in _REQUIRED_FOR_NEW if f not in data]
        if missing:
            raise SquadsError(
                f"role override for new slug {slug!r} is missing required fields: "
                + ", ".join(missing)
            )

    declared_slug = data.get("slug")
    if declared_slug is not None and declared_slug != slug:
        raise SquadsError(
            f"role override {origin}: declares slug {declared_slug!r} but the filename says "
            f"{slug!r} — the filename is canonical; rename the file or drop the 'slug' key"
        )

    result = merge_override(
        _base_raw(base),
        data,
        frozenset(),
        origin,
        top_level_keys=_ROLE_TOP_LEVEL_KEYS,
        collect_all=False,
        empty_selected_hint=_NO_SELECTED_HINT,
    )
    merged = result.merged
    if merged is None:  # pragma: no cover - fail-fast mode raises on its own first violation
        raise SquadsError(f"role override merge failed with no violation reported — {origin}")
    merged["slug"] = slug

    try:
        spec = RoleSpec.model_validate(merged)
    except Exception as exc:
        raise SquadsError(f"invalid role override {origin}: {exc}") from exc
    if spec.model is not None and spec.model not in VALID_MODELS:
        raise SquadsError(
            f"invalid role override {origin}: model {spec.model!r} is not one of "
            f"{sorted(VALID_MODELS)}"
        )
    return role_spec_to_def(spec)


def resolve_role(slug: str, squad_dir: Path | None) -> RoleDef:
    """Return the ``RoleDef`` for *slug*, applying any project override.

    Resolution order:
    1. ``<squad_dir>/.overrides/roles/<slug>.toml`` — if present, merge field-wise.
    2. ``PREDEFINED`` catalog — the bundled default.

    Raises :class:`~squads._errors.RoleNotFoundError` if *slug* is neither predefined nor has a
    project TOML.
    """
    base = _PREDEFINED_BY_SLUG.get(slug)  # None for new slugs

    if squad_dir is not None:
        toml_path = _overrides_dir(squad_dir) / f"{slug}.toml"
        if toml_path.is_file():
            data = _read_toml(toml_path)
            return _apply_override(base, data, slug, str(toml_path))

    if base is not None:
        return base

    raise RoleNotFoundError(
        f"no predefined role {slug!r} and no project override found "
        f"(known: {', '.join(_PREDEFINED_BY_SLUG)})"
    )


def resolve_dev_role(
    tech: str,
    *,
    name: str | None = None,
    seq: int = 0,
    model: str | None = None,
    squad_dir: Path | None = None,
) -> RoleDef:
    """Build a stack-specific developer role, applying any project override.

    If ``<squad_dir>/.overrides/roles/<tech>-dev.toml`` exists, its fields are merged over the
    generated ``dev_role()`` defaults.  ``name`` is still honoured as before (explicit name wins
    over both the pool and any TOML ``full_name``).
    """
    slug = f"{tech.strip().lower()}-dev"
    base = dev_role(tech, name=name, seq=seq, model=model)

    if squad_dir is not None:
        toml_path = _overrides_dir(squad_dir) / f"{slug}.toml"
        if toml_path.is_file():
            data = _read_toml(toml_path)
            # If caller passed an explicit name, honour it — don't let TOML override it.
            if name and "full_name" in data:
                data = {k: v for k, v in data.items() if k != "full_name"}
            return _apply_override(base, data, slug, str(toml_path))

    return base
