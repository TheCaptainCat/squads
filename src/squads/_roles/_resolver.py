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

The resolver is *stateless*: it reads from disk on every call.  The service layer is already the
cached / transactional boundary; there is no need to cache here.

``full_name`` in a role TOML seeds the name when the role is activated.  The key is
passed through to ``RoleDef.full_name``; downstream code (``extra.full_name``,
roster, pointers, CLAUDE.md section) reads from there.
"""

import tomllib
from dataclasses import fields as dc_fields
from pathlib import Path
from typing import cast

from squads._errors import RoleNotFoundError, SquadsError
from squads._roles._catalog import PREDEFINED, RoleDef, dev_role

_PREDEFINED_BY_SLUG: dict[str, RoleDef] = {r.slug: r for r in PREDEFINED}

# Required fields for a *new-slug* TOML (slug is derived from the filename, not the TOML).
_REQUIRED_FOR_NEW = ("full_name", "title", "description", "mission")


def _overrides_dir(squad_dir: Path) -> Path:
    return squad_dir / ".overrides" / "roles"


def _read_toml(path: Path) -> dict[str, object]:
    """Read *path* as TOML; surface a :class:`SquadsError` on parse failure."""
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise SquadsError(f"malformed role override {path}: {exc}") from exc


def _apply_override(base: RoleDef | None, data: dict[str, object], slug: str) -> RoleDef:
    """Merge *data* from a TOML file over *base* (or build a new role if base is ``None``).

    For tuple fields (``responsibilities``, ``agreements``) the TOML supplies a list of strings.
    The ``slug`` field inside the TOML is ignored — the filename's stem is always canonical.
    """
    if base is None:
        # New-slug path: all required fields must be present.
        missing = [f for f in _REQUIRED_FOR_NEW if f not in data]
        if missing:
            raise SquadsError(
                f"role override for new slug {slug!r} is missing required fields: "
                + ", ".join(missing)
            )

    # Build a dict of current field values (start from base, then overlay TOML).
    # For a new slug we build from scratch using TOML values only.
    known = {f.name for f in dc_fields(RoleDef)}
    current: dict[str, object] = {}
    if base is not None:
        current = {f.name: getattr(base, f.name) for f in dc_fields(RoleDef)}

    for key, value in data.items():
        if key == "slug":
            # slug is non-renamable — silently ignore any attempt to override it.
            continue
        if key not in known:
            # Silently skip unknown TOML keys for forward compatibility.
            continue
        if key in ("responsibilities", "agreements"):
            if not isinstance(value, list):
                raise SquadsError(
                    f"role override {slug!r}: field {key!r} must be a list of strings"
                )
            current[key] = tuple(str(item) for item in cast("list[object]", value))
        else:
            current[key] = value

    # Ensure slug is correct (the canonical one from the filename / call-site).
    current["slug"] = slug

    try:
        return RoleDef(**current)  # type: ignore[arg-type]
    except TypeError as exc:
        raise SquadsError(f"role override {slug!r} produced an invalid RoleDef: {exc}") from exc


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
            return _apply_override(base, data, slug)

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
            return _apply_override(base, data, slug)

    return base
