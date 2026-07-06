"""Load and validate the bundled role catalog.

``load_role_catalog()`` is the single entry point.  It reads ``roles.toml`` via
``importlib.resources`` (offline, no filesystem assumption), parses with stdlib
``tomllib``, constructs the pydantic models, runs fail-closed validation, and
returns a ``RoleCatalogSpec``.  A corrupt or invalid catalog raises
``SquadsError``.
"""

import importlib.resources
import tomllib
from typing import Any

from squads._errors import SquadsError
from squads._roles._models import DevPoolSpec, RoleCatalogSpec, RoleSpec

_VALID_MODELS: frozenset[str] = frozenset({"sonnet", "opus", "haiku", "inherit"})


def load_role_catalog() -> RoleCatalogSpec:
    """Read, parse, validate, and return the bundled ``roles.toml``.

    Called once at module level in ``_catalog.py`` to build the singleton.
    Raises ``SquadsError`` on any violation.
    """
    try:
        pkg = importlib.resources.files("squads._roles")
        toml_bytes = (pkg / "roles.toml").read_bytes()
    except Exception as exc:
        raise SquadsError(f"Failed to read bundled roles.toml: {exc}") from exc

    try:
        raw: dict[str, Any] = tomllib.loads(toml_bytes.decode())
    except tomllib.TOMLDecodeError as exc:
        raise SquadsError(f"Malformed bundled roles.toml: {exc}") from exc

    return _build_catalog(raw)


def _build_catalog(raw: dict[str, Any]) -> RoleCatalogSpec:
    # --- roles ---
    roles: list[RoleSpec] = [_parse_role(rdata, i) for i, rdata in enumerate(raw.get("roles", []))]

    # --- bundles ---
    bundles: dict[str, list[str]] = {
        name: list(slugs) for name, slugs in raw.get("bundles", {}).items()
    }

    # --- dev pool ---
    dev_raw: dict[str, Any] = raw.get("dev", {})
    try:
        # model_validate so extra="forbid" fires on unknown keys.
        dev = DevPoolSpec.model_validate(dev_raw)
    except Exception as exc:
        raise SquadsError(f"Invalid bundled role catalog [dev]: {exc}") from exc

    # --- validation ---
    _validate(roles, bundles, dev)

    try:
        spec = RoleCatalogSpec(roles=roles, bundles=bundles, dev=dev)
    except Exception as exc:
        raise SquadsError(f"Invalid bundled role catalog: {exc}") from exc

    return spec


def _parse_role(data: dict[str, Any], idx: int) -> RoleSpec:
    ctx = f"roles[{idx}]"
    try:
        # model_validate so extra="forbid" fires on unknown keys.
        return RoleSpec.model_validate(data)
    except Exception as exc:
        raise SquadsError(f"Invalid role entry {ctx}: {exc}") from exc


def _check_slugs(roles: list[RoleSpec], errors: list[str]) -> set[str]:
    """Unique slugs + required fields non-empty."""
    seen: dict[str, int] = {}
    for i, r in enumerate(roles):
        if r.slug in seen:
            errors.append(f"duplicate slug {r.slug!r} at index {i} (first seen at {seen[r.slug]})")
        seen[r.slug] = i
        for field in ("slug", "full_name", "title", "description", "mission"):
            val = getattr(r, field)
            if not val or not val.strip():
                errors.append(f"role {r.slug!r}: required field {field!r} is empty")
    return set(seen)


def _check_defaults(roles: list[RoleSpec], errors: list[str]) -> None:
    """At most one is_default."""
    defaults = [r.slug for r in roles if r.is_default]
    if len(defaults) > 1:
        errors.append(f"more than one role has is_default=true: {defaults}")


def _check_bundles(bundles: dict[str, list[str]], all_slugs: set[str], errors: list[str]) -> None:
    """Bundle referential integrity; 'all' bundle == full role set."""
    errors.extend(
        f"bundle {bname!r} references unknown slug {s!r}"
        for bname, slugs in bundles.items()
        for s in slugs
        if s not in all_slugs
    )
    if "all" in bundles:
        all_bundle = set(bundles["all"])
        missing = all_slugs - all_bundle
        extra = all_bundle - all_slugs
        if missing:
            errors.append(f"'all' bundle missing roles: {sorted(missing)}")
        if extra:
            errors.append(f"'all' bundle has unknown slugs: {sorted(extra)}")


def _check_dev(dev: DevPoolSpec, errors: list[str]) -> None:
    """Dev pool well-formed."""
    if not dev.name_pool:
        errors.append("dev.name_pool is empty")
    elif len(dev.name_pool) != len(set(dev.name_pool)):
        dupes = sorted({n for n in dev.name_pool if dev.name_pool.count(n) > 1})
        errors.append(f"dev.name_pool has duplicates: {dupes}")
    if not dev.model.strip():
        errors.append("dev.model is empty")
    if not dev.color.strip():
        errors.append("dev.color is empty")
    if dev.model not in _VALID_MODELS:
        errors.append(f"dev.model {dev.model!r} not in allowed set {sorted(_VALID_MODELS)}")


def _check_models(roles: list[RoleSpec], errors: list[str]) -> None:
    """Model whitelist."""
    errors.extend(
        f"role {r.slug!r}: model {r.model!r} not in allowed set {sorted(_VALID_MODELS)}"
        for r in roles
        if r.model is not None and r.model not in _VALID_MODELS
    )


def _validate(
    roles: list[RoleSpec],
    bundles: dict[str, list[str]],
    dev: DevPoolSpec,
) -> None:
    errors: list[str] = []
    all_slugs = _check_slugs(roles, errors)
    _check_defaults(roles, errors)
    _check_bundles(bundles, all_slugs, errors)
    _check_dev(dev, errors)
    _check_models(roles, errors)
    if errors:
        raise SquadsError("Invalid bundled role catalog:\n" + "\n".join(f"  - {e}" for e in errors))
