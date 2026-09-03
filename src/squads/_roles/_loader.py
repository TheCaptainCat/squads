"""Load and validate the bundled role catalog, merging a project's whole-document
``.overrides/roles.toml`` override — the fourth spec override document, on the same shape as
the workflow and playbook loaders.

``load_role_catalog(squad_dir=None)`` is the single entry point. With no *squad_dir* it reads
``roles.toml`` from the ``squads._specs`` package via ``importlib.resources`` (offline, no
filesystem assumption), parses with stdlib ``tomllib``, constructs the pydantic models, runs
fail-closed validation, and returns a ``RoleCatalogSpec``. A corrupt or invalid bundled catalog
raises ``SquadsError`` — fail closed.

With a *squad_dir* given, ``<squad_dir>/.overrides/roles.toml`` — when present — is merged over
the bundled default via the shared, loader-agnostic engine (``squads._specmerge``), entirely at
the **raw parsed-TOML mapping** layer, before any model is built: splat-refs resolve against the
bundled mapping, the override deep-merges over it leaf-by-leaf, ``[selected]`` shrinks ``roles``
and ``bundles`` to their surviving key set, and the document's top-level key space is closed to
``{roles, bundles, dev}`` (plus the engine's own reserved ``selected``).

**One shape adaptation, done here and nowhere else:** the bundled document declares ``roles`` as
a TOML array of tables (``[[roles]]``) — a plain list, with no key of its own for the merge
engine's field-wise dict-merge or ``[selected]`` deselect to operate on. Before either mapping
ever reaches the engine, :func:`_keyed_for_merge` re-keys a present ``roles`` list by each
entry's own ``slug`` field; :func:`_unkeyed_from_merge` turns the merged, slug-keyed table back
into the plain list :func:`_build_catalog` expects, once merging is done. This is what lets a
catalog-document ``[[roles]]`` entry field-merge onto its bundled counterpart by slug — the same
field-wise behaviour a per-slug ``.overrides/roles/<slug>.toml`` file gets — and what lets
``[selected].roles`` name a slug to drop. The engine itself stays entirely list-of-tables-blind;
this reshaping is the loader's own job, mirroring how the playbook loader reshapes its raw
mapping before merging (see ``_interactions._loader._base_raw_for``).

**Precedence: bundled base, then the catalog document, then a per-slug
``.overrides/roles/<slug>.toml`` file** — most specific last, the same direction template
resolution already runs. This module resolves only the first two layers; the per-slug layer is
layered on top by :mod:`squads._roles._resolver`, which threads *squad_dir* into every role
resolution and so picks up a catalog-document change with no call-site changes of its own.

``[bundles]`` and ``[dev]`` are ordinary dict-shaped tables and need no reshaping: a bundle name
or a dev-pool field the override declares replaces its bundled counterpart field-wise, and a new
bundle name is simply added. ``dev`` carries no ``[selected]`` entry — it is one object, not a
keyed collection, so there is nothing in it to shrink (mirrors the playbook document's own
empty-``[selected]``-menu treatment of a field that isn't a keyed collection).
"""

import importlib.resources
import tomllib
from pathlib import Path
from typing import Any, cast

from squads._errors import SquadsError
from squads._roles._models import DevPoolSpec, RoleCatalogSpec, RoleSpec
from squads._specmerge import RawMapping, merge_override

VALID_MODELS: frozenset[str] = frozenset({"sonnet", "opus", "haiku", "inherit"})

#: Canonical location for the project role-catalog override (relative to squad_dir).
ROLES_OVERRIDE_FILENAME = ".overrides/roles.toml"

#: The role catalog document's closed top-level key space — enforced at the raw-mapping layer
#: by the merge engine before any model is built.
ROLES_TOP_LEVEL_KEYS: frozenset[str] = frozenset({"roles", "bundles", "dev"})

#: The catalog document's deselectable ``[selected]`` section names. ``dev`` is deliberately
#: absent — see the module docstring.
ROLES_SELECTED_SECTIONS: frozenset[str] = frozenset({"roles", "bundles"})


def _read_bundled_bytes() -> bytes:
    try:
        pkg = importlib.resources.files("squads._specs")
        return (pkg / "roles.toml").read_bytes()
    except Exception as exc:
        raise SquadsError(f"Failed to read bundled roles.toml: {exc}") from exc


def _bundled_raw() -> RawMapping:
    """The bundled ``roles.toml``, parsed but not yet built into a model — the merge engine's
    ``base`` input."""
    try:
        return tomllib.loads(_read_bundled_bytes().decode())
    except tomllib.TOMLDecodeError as exc:
        raise SquadsError(f"Malformed bundled roles.toml: {exc}") from exc


def bundled_roles_toml_text() -> str:
    """The bundled ``roles.toml``'s raw text — the ``sq override diff roles`` Δ-mine baseline,
    mirroring ``_workflow._loader.bundled_workflow_toml_text``/
    ``_interactions._loader.bundled_playbook_toml_text``."""
    return _read_bundled_bytes().decode()


def _role_entry_slug(entry: Any, *, origin: str, index: int) -> str:
    """The ``slug`` a ``[[roles]]`` entry declares — required, since it is the only thing that
    tells the merge which bundled role (if any) this entry field-merges onto."""
    if not isinstance(entry, dict):
        raise SquadsError(f"{origin}: roles[{index}] must be a table (did you mean '[[roles]]'?)")
    slug = cast("RawMapping", entry).get("slug")
    if not isinstance(slug, str) or not slug.strip():
        raise SquadsError(
            f"{origin}: roles[{index}] is missing a string 'slug' — every [[roles]] entry "
            "must declare which role it defines or overrides"
        )
    return slug


def _roles_list_to_dict(roles: list[Any], *, origin: str) -> dict[str, RawMapping]:
    """Key a ``[[roles]]`` array by its own ``slug`` field — see the module docstring's shape
    adaptation. Fails closed (naming *origin*) on a missing/blank ``slug``, or the same slug
    declared twice in one document — a silent last-writer-wins would drop one entry's fields
    without saying so."""
    result: dict[str, RawMapping] = {}
    for i, entry in enumerate(roles):
        slug = _role_entry_slug(entry, origin=origin, index=i)
        if slug in result:
            raise SquadsError(
                f"{origin}: slug {slug!r} is declared more than once in [[roles]] — each role "
                "may appear only once per document"
            )
        result[slug] = cast("RawMapping", entry)
    return result


def _keyed_for_merge(raw: RawMapping, *, origin: str) -> RawMapping:
    """*raw*, with a present list-shaped ``roles`` key re-keyed by slug. A no-op for a mapping
    with no ``roles`` key at all."""
    roles = raw.get("roles")
    if not isinstance(roles, list):
        return raw
    return {**raw, "roles": _roles_list_to_dict(cast("list[Any]", roles), origin=origin)}


def _unkeyed_from_merge(raw: RawMapping) -> RawMapping:
    """Reverse of :func:`_keyed_for_merge`: the merged, slug-keyed ``roles`` table back to the
    plain list :func:`_build_catalog` expects, in the merge's own key order — base order, with
    any override-only (brand-new) slug appended in override order (``deep_merge``'s own
    ordering guarantee)."""
    roles = raw.get("roles")
    if not isinstance(roles, dict):
        return raw
    return {**raw, "roles": list(cast("RawMapping", roles).values())}


def _read_raw_override(path: Path) -> RawMapping:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise SquadsError(f"malformed role catalog override {path}: {exc}") from exc
    except OSError as exc:
        raise SquadsError(f"cannot read role catalog override {path}: {exc}") from exc


def load_role_catalog(squad_dir: Path | None = None) -> RoleCatalogSpec:
    """Read, parse, merge (if a project catalog-document override is present), validate, and
    return the role catalog.

    With *squad_dir* ``None`` (the module-level singleton's own call) or
    ``<squad_dir>/.overrides/roles.toml`` absent, this builds the catalog straight from the
    bundled raw mapping — byte-identical to today's bundled-only load.

    When the override file is present, it is merged over the bundled raw mapping first (shared
    engine, fail-fast — raises ``SquadsError`` on the first violation), then the merged mapping
    is built and validated exactly as the bundled-only path validates the bundled mapping —
    including the referential/floor checks in :func:`_validate` (bundle referential integrity,
    at-most-one-default), which is what makes a ``[selected]`` deselect that empties a bundle or
    removes the default agent fail with no deselect-specific guard of its own.

    Called once at module level in ``_catalog.py`` (no *squad_dir*) to build the bundled
    singleton, and per-request wherever a squad's own catalog is needed — most directly by
    :mod:`squads._roles._resolver`, which layers a per-slug file on top of whatever this
    returns. Raises ``SquadsError`` on any violation.

    A validation failure is reported against whichever document is actually at fault: the
    bundled catalog when no project override was merged in, or the override file by path when
    one was — never the other way around, so a refusal never asserts a cause the reader can
    open the named file and disprove (see :func:`_catalog_error_prefix`).
    """
    raw = _bundled_raw()
    origin: str | None = None
    bundled_slugs: frozenset[str] | None = None

    if squad_dir is not None:
        override_path = squad_dir / ROLES_OVERRIDE_FILENAME
        if override_path.is_file():
            bundled_slugs = _known_slugs(raw.get("roles"))
            raw_override = _read_raw_override(override_path)
            origin = str(override_path)
            result = merge_override(
                _keyed_for_merge(raw, origin="<bundled roles.toml>"),
                _keyed_for_merge(raw_override, origin=origin),
                ROLES_SELECTED_SECTIONS,
                origin,
                top_level_keys=ROLES_TOP_LEVEL_KEYS,
                collect_all=False,
            )
            merged = result.merged
            if (
                merged is None
            ):  # pragma: no cover - fail-fast mode raises on its own first violation
                raise SquadsError(
                    f"role catalog override merge failed with no violation reported — {origin}"
                )
            raw = _unkeyed_from_merge(merged)

    return _build_catalog(raw, origin=origin, bundled_slugs=bundled_slugs)


def _catalog_error_prefix(origin: str | None) -> str:
    """The role-catalog validation-error prefix, naming the document actually at fault.

    ``origin`` is ``None`` on the bundled-only path (no *squad_dir*, or no override file
    present) — the only case in which "bundled" is a claim the reader can verify by opening
    the shipped ``roles.toml``. Once a project override has been merged in, every failure is
    reported against *that* file by path instead: the merged mapping is what actually failed
    to validate, and the bundled document alone may be perfectly valid (a ``[selected]``
    deselect is the common case — see :func:`_check_bundles`'s hint).
    """
    if origin is None:
        return "Invalid bundled role catalog"
    return f"{origin}: role catalog invalid after merge"


def _known_slugs(roles: Any) -> frozenset[str]:
    """Every string ``slug`` a (possibly malformed) raw ``roles`` list declares.

    Used only to build the ``[selected]``-deselection hint in :func:`_check_bundles`, so a
    malformed entry is skipped here rather than raised on — the real raise for a malformed
    entry happens in :func:`_build_catalog`/:func:`_parse_role` itself."""
    if not isinstance(roles, list):
        return frozenset()
    slugs: set[str] = set()
    for entry in cast("list[Any]", roles):
        if isinstance(entry, dict):
            slug = cast("RawMapping", entry).get("slug")
            if isinstance(slug, str):
                slugs.add(slug)
    return frozenset(slugs)


def _build_catalog(
    raw: dict[str, Any],
    *,
    origin: str | None = None,
    bundled_slugs: frozenset[str] | None = None,
) -> RoleCatalogSpec:
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
        raise SquadsError(f"{_catalog_error_prefix(origin)} [dev]: {exc}") from exc

    # --- validation ---
    _validate(roles, bundles, dev, origin=origin, bundled_slugs=bundled_slugs)

    try:
        spec = RoleCatalogSpec(roles=roles, bundles=bundles, dev=dev)
    except Exception as exc:
        raise SquadsError(f"{_catalog_error_prefix(origin)}: {exc}") from exc

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


def _deselect_hint(slug: str, bundled_slugs: frozenset[str] | None) -> str:
    """A remedy clause for *slug* when it looks ``[selected]``-deselected — present in the
    bundled catalog (so it isn't simply a typo) but absent from the surviving role set. Empty
    when *bundled_slugs* is unknown (the bundled-only path, where no ``[selected]`` deselect
    could have produced this) or *slug* was never a bundled slug to begin with."""
    if bundled_slugs is None or slug not in bundled_slugs:
        return ""
    return (
        f" — {slug!r} looks deselected via [selected].roles; deselecting a role also means "
        "deselecting it from (or rewriting) every bundle that still names it"
    )


def _check_bundles(
    bundles: dict[str, list[str]],
    all_slugs: set[str],
    errors: list[str],
    *,
    bundled_slugs: frozenset[str] | None = None,
) -> None:
    """Bundle referential integrity; 'all' bundle == full role set."""
    errors.extend(
        f"bundle {bname!r} references unknown slug {s!r}{_deselect_hint(s, bundled_slugs)}"
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
            msg = f"'all' bundle has unknown slugs: {sorted(extra)}"
            deselected = sorted(
                s for s in extra if bundled_slugs is not None and s in bundled_slugs
            )
            if deselected:
                msg += (
                    f" — {deselected} look deselected via [selected].roles; deselecting a role "
                    "also means deselecting it from (or rewriting) every bundle that still "
                    "names it"
                )
            errors.append(msg)


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
    if dev.model not in VALID_MODELS:
        errors.append(f"dev.model {dev.model!r} not in allowed set {sorted(VALID_MODELS)}")


def _check_models(roles: list[RoleSpec], errors: list[str]) -> None:
    """Model whitelist."""
    errors.extend(
        f"role {r.slug!r}: model {r.model!r} not in allowed set {sorted(VALID_MODELS)}"
        for r in roles
        if r.model is not None and r.model not in VALID_MODELS
    )


def _validate(
    roles: list[RoleSpec],
    bundles: dict[str, list[str]],
    dev: DevPoolSpec,
    *,
    origin: str | None = None,
    bundled_slugs: frozenset[str] | None = None,
) -> None:
    errors: list[str] = []
    all_slugs = _check_slugs(roles, errors)
    _check_defaults(roles, errors)
    _check_bundles(bundles, all_slugs, errors, bundled_slugs=bundled_slugs)
    _check_dev(dev, errors)
    _check_models(roles, errors)
    if errors:
        raise SquadsError(
            f"{_catalog_error_prefix(origin)}:\n" + "\n".join(f"  - {e}" for e in errors)
        )
