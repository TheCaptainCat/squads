"""Load and validate the bundled role catalog, merging a project's ``.overrides/roles.toml``.

That is the fourth spec override document, shaped like the workflow and playbook loaders.
``load_role_catalog(squad_dir=None)`` is the single entry point. Without *squad_dir* it reads
``roles.toml`` from the ``squads._specs`` package (``importlib.resources``, parsed with
``tomllib``), builds the pydantic models, validates fail-closed and returns a
``RoleCatalogSpec``; a corrupt bundled catalog raises ``SquadsError``.

With a *squad_dir*, ``<squad_dir>/.overrides/roles.toml``, when present, is merged over the
bundled default by the shared engine ``squads._specmerge`` at the raw parsed-TOML layer,
before any model is built: splat-refs resolve against the bundled mapping, the override
deep-merges leaf by leaf, ``[selected]`` shrinks ``roles`` and ``bundles`` to the surviving
keys, and the top-level key space is closed to ``{roles, bundles, templates, defaults}`` plus
the engine's reserved ``selected``.

One shape adaptation lives here and nowhere else. The bundled ``roles`` is a TOML array of
tables (``[[roles]]``), a plain list with no key for the engine's field-wise merge or
``[selected]`` to act on. Before either mapping reaches the engine, :func:`_keyed_for_merge`
re-keys a present ``roles`` list by each entry's ``slug``, and :func:`_unkeyed_from_merge`
turns the merged table back into the list :func:`_build_catalog` expects. That lets a
catalog-document ``[[roles]]`` entry field-merge onto its bundled counterpart by slug, as a
per-slug ``.overrides/roles/<slug>.toml`` file does, and lets ``[selected].roles`` drop a
slug. The engine stays list-of-tables-blind, as the playbook loader's reshaping
(``_interactions._loader._base_raw_for``) keeps it.

Precedence, most specific last: bundled base, then the catalog document, then a per-slug file.
This module resolves the first two; :mod:`squads._roles._resolver` layers the per-slug file
and threads *squad_dir* into every resolution, so a catalog-document change needs no
call-site change.

``[bundles]`` and ``[templates]`` are dict-shaped and need no reshaping: a declared name
replaces its bundled counterpart field-wise, a new name is added, and ``[selected]`` can drop
either. A legacy ``[dev]`` table is refused with the rename to ``[templates.dev]``.
"""

import re
from pathlib import Path
from typing import Any, cast

from squads._errors import SquadsError
from squads._pronouns import pronouns_problem
from squads._roles._models import (
    CAPABILITY_NAME_PATTERN,
    DefaultsSpec,
    RoleCatalogSpec,
    RoleSpec,
    RoleTemplateSpec,
    malformed_capability_names,
)
from squads._roles._templates import NAME_PLACEHOLDER, placeholder_problems, placeholders
from squads._specload import (
    OverrideFiles,
    OverrideMessages,
    SpecDocument,
    bundled_raw,
    bundled_text,
    load_override,
)
from squads._specmerge import RawMapping, describe_spec_error

VALID_MODELS: frozenset[str] = frozenset({"sonnet", "opus", "haiku", "inherit"})

#: Canonical location for the project role-catalog override (relative to squad_dir).
ROLES_OVERRIDE_FILENAME = ".overrides/roles.toml"

#: The role catalog document's closed top-level key space — enforced at the raw-mapping layer
#: by the merge engine before any model is built.
ROLES_TOP_LEVEL_KEYS: frozenset[str] = frozenset({"roles", "bundles", "templates", "defaults"})

#: The catalog document's deselectable ``[selected]`` section names.
ROLES_SELECTED_SECTIONS: frozenset[str] = frozenset({"roles", "bundles", "templates"})

#: The refusal of a ``[dev]`` table, which an earlier catalog document declared.
LEGACY_DEV_TABLE_MESSAGE = (
    f"{ROLES_OVERRIDE_FILENAME}: [dev] is not a key of the role catalog; rename it to "
    "[templates.dev] (its name_pool, model, color and capabilities keys are unchanged)"
)


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


def _check_override_shape(raw: RawMapping, origin: str) -> None:
    if "dev" in raw:
        raise SquadsError(LEGACY_DEV_TABLE_MESSAGE)
    for key, kind, expected in (
        ("roles", (list, dict), "an array or a table"),
        ("bundles", dict, "a table"),
        ("templates", dict, "a table"),
    ):
        if key in raw and not isinstance(raw[key], kind):
            raise SquadsError(
                f"{origin}: '{key}' must be {expected}, got {type(raw[key]).__name__}"
            )


ROLES_OVERRIDE_MESSAGES = OverrideMessages(
    malformed="malformed role catalog override {path}: {exc}",
    unreadable="cannot read role catalog override {path}: {exc}",
    not_utf8="role catalog override {path} is not valid UTF-8; save it as UTF-8 and re-run.",
)


_DOCUMENT = SpecDocument(
    bundled_file="roles.toml",
    override_file=ROLES_OVERRIDE_FILENAME,
    override_name="role catalog override",
    top_level_keys=ROLES_TOP_LEVEL_KEYS,
    selected_sections=ROLES_SELECTED_SECTIONS,
    messages=ROLES_OVERRIDE_MESSAGES,
    check_override=_check_override_shape,
    to_merge_form=lambda raw, origin: _keyed_for_merge(raw, origin=origin),
    from_merge_form=_unkeyed_from_merge,
)


def bundled_roles_toml_text() -> str:
    """The bundled ``roles.toml``'s raw text — the ``sq override diff roles`` Δ-mine baseline,
    mirroring ``_workflow._loader.bundled_workflow_toml_text``/
    ``_interactions._loader.bundled_playbook_toml_text``."""
    return bundled_text(_DOCUMENT)


def _bundled_raw() -> RawMapping:
    return bundled_raw(_DOCUMENT)


def bundled_roles_raw() -> RawMapping:
    """A copy of the packaged ``roles.toml``'s parse, for the ``sq check`` shadow predicate."""
    return _bundled_raw()


def load_role_catalog(
    squad_dir: Path | None = None, files: OverrideFiles | None = None
) -> RoleCatalogSpec:
    """Read, parse, merge (if a project override is present), validate and return the catalog.

    With *squad_dir* ``None`` (the module-level singleton's call) or no
    ``<squad_dir>/.overrides/roles.toml``, it builds from the bundled raw mapping. With the file,
    the override is merged over it first (shared engine, fail-fast: ``SquadsError`` on the first
    violation), then the merged mapping is built and validated as the bundled one is, including
    :func:`_validate`'s referential and floor checks (bundle integrity, at-most-one-default),
    which is why a ``[selected]`` deselect that empties a bundle or removes the default agent
    needs no guard of its own.

    It is called once in ``_catalog.py`` (no *squad_dir*) for the bundled singleton, and
    per request wherever a squad's catalog is needed, chiefly :mod:`squads._roles._resolver`,
    which layers a per-slug file on top.

    A validation failure is reported against the document actually at fault: the bundled catalog
    when no override was merged, else the override file by path, so a refusal never asserts a
    cause the reader can disprove by opening the named file (see :func:`_catalog_error_prefix`).
    """
    raw = _bundled_raw()
    loaded = load_override(_DOCUMENT, squad_dir, lambda: raw, files)
    if loaded is None:
        return _build_catalog(raw, origin=None, bundled_slugs=None)
    return _build_catalog(
        loaded.raw, origin=loaded.origin, bundled_slugs=_known_slugs(raw.get("roles"))
    )


def _catalog_error_prefix(origin: str | None) -> str:
    """The role-catalog validation-error prefix, naming the document actually at fault.

    ``origin`` is ``None`` on the bundled-only path, the one case where "bundled" is a claim the
    reader can verify in the shipped ``roles.toml``. Once an override is merged, every failure is
    reported against that file by path: the merged mapping failed, and the bundled document alone
    may be valid (a ``[selected]`` deselect is the usual cause; see :func:`_check_bundles`).
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
    roles: list[RoleSpec] = [
        _parse_role(rdata, i, origin) for i, rdata in enumerate(raw.get("roles", []))
    ]

    # --- bundles ---
    bundles: dict[str, list[str]] = {
        name: list(slugs) for name, slugs in raw.get("bundles", {}).items()
    }

    templates = {
        name: _parse_template(name, tdata, origin)
        for name, tdata in raw.get("templates", {}).items()
    }

    defaults = _parse_defaults(raw.get("defaults", {}), origin)

    # --- validation ---
    _validate(roles, bundles, templates, origin=origin, bundled_slugs=bundled_slugs)

    try:
        spec = RoleCatalogSpec(roles=roles, bundles=bundles, templates=templates, defaults=defaults)
    except Exception as exc:
        raise SquadsError(f"{_catalog_error_prefix(origin)}: {exc}") from exc

    return spec


def _parse_defaults(raw: Any, origin: str | None) -> DefaultsSpec:
    """The ``[defaults]`` table, with its pronouns trimmed; a value that fails the pronouns
    shape rule is refused here, so a bad declaration never reaches a role."""
    prefix = f"{_catalog_error_prefix(origin)} [defaults]"
    try:
        defaults = DefaultsSpec.model_validate(raw)
    except Exception as exc:
        raise SquadsError(f"{prefix}: {describe_spec_error(exc, DefaultsSpec)}") from exc
    if defaults.pronouns is None:
        return defaults
    problem = pronouns_problem(defaults.pronouns)
    if problem is not None:
        raise SquadsError(f"{prefix}: pronouns {problem}")
    return DefaultsSpec(pronouns=defaults.pronouns.strip())


def refuse_pronouns_key(data: Any, where: str) -> None:
    """Refuse a ``pronouns`` key in a role definition, naming the verb that sets it.

    Pronouns belong to the role's item, not to the role document that defines the role; a value
    here would sit above the item in precedence and hide whatever the verb wrote."""
    if isinstance(data, dict) and "pronouns" in data:
        slug = cast("RawMapping", data).get("slug")
        addr = slug if isinstance(slug, str) else "<addr>"
        verb = f"sq role {addr} update --pronouns"
        raise SquadsError(
            f"{where}: 'pronouns' is not a role document field — set it on the role with "
            f"`{verb} <text>`, or declare a roster-wide default under [defaults]"
        )


def _parse_role(data: dict[str, Any], idx: int, origin: str | None) -> RoleSpec:
    slug = data.get("slug")
    ctx = f"roles[{idx}]" if origin is None else f"[[roles]] slug {slug!r}"
    where = f"{origin}: " if origin is not None else ""
    refuse_pronouns_key(data, f"{where}Invalid role entry {ctx}")
    try:
        # model_validate so extra="forbid" fires on unknown keys.
        return RoleSpec.model_validate(data)
    except Exception as exc:
        raise SquadsError(
            f"{where}Invalid role entry {ctx}: {describe_spec_error(exc, RoleSpec)}"
        ) from exc


def _refused_template_key_reason(key: str) -> str | None:
    """Why *key* is not a template key, naming what owns the value; ``None`` for any other."""
    if key == "full_name":
        return "the name is chosen at activation: `--name`, or the template's `name` pattern"
    if key == "is_default":
        return "the default designation belongs to a role item: `sq role <slug> set-default`"
    return None


_TEMPLATE_REQUIRED_KEYS: tuple[str, ...] = ("title", "description", "mission")


def _parse_template(name: str, data: Any, origin: str | None) -> RoleTemplateSpec:
    where = f"{origin}: " if origin is not None else ""
    ctx = f"{where}Invalid role template [templates.{name}]"
    if not isinstance(data, dict):
        raise SquadsError(f"{ctx}: must be a table")
    raw = cast("RawMapping", data)
    refuse_pronouns_key(raw, ctx)
    for key in raw:
        reason = _refused_template_key_reason(key)
        if reason is not None:
            raise SquadsError(f"{ctx}: {key!r} is not a template key — {reason}")
    missing = [k for k in _TEMPLATE_REQUIRED_KEYS if k not in raw]
    if missing:
        raise SquadsError(f"{ctx}: missing required key(s): {', '.join(missing)}")
    try:
        return RoleTemplateSpec.model_validate(raw)
    except Exception as exc:
        raise SquadsError(f"{ctx}: {describe_spec_error(exc, RoleTemplateSpec)}") from exc


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


def _check_templates(templates: dict[str, RoleTemplateSpec], errors: list[str]) -> None:
    """Every template well-formed: name, required text, placeholders, pool, model, capabilities."""
    for name, t in templates.items():
        owner = f"template {name!r}"
        if re.fullmatch(CAPABILITY_NAME_PATTERN, name) is None:
            errors.append(f"{owner}: the name must match {CAPABILITY_NAME_PATTERN}")
        errors.extend(f"{owner}: {problem}" for problem in placeholder_problems(t))
        errors.extend(
            f"{owner}: required field {field!r} is empty"
            for field in ("title", "description", "mission")
            if not getattr(t, field).strip()
        )
        for field in ("slug", "name", "model", "color"):
            value: str | None = getattr(t, field)
            if value is not None and not value.strip():
                errors.append(f"{owner}: {field!r} is blank")
        if t.model is not None and t.model not in VALID_MODELS:
            errors.append(f"{owner}: model {t.model!r} not in allowed set {sorted(VALID_MODELS)}")
        _check_template_pool(owner, t, errors)
        errors.extend(
            f"{owner}: capabilities entry {cap!r} must match {CAPABILITY_NAME_PATTERN}"
            for cap in malformed_capability_names(t.capabilities)
        )


def _check_template_pool(owner: str, t: RoleTemplateSpec, errors: list[str]) -> None:
    """The ``name_pool`` is non-empty where ``name`` draws from it, and holds no duplicate or
    blank entry."""
    if t.name is not None and NAME_PLACEHOLDER in placeholders(t.name) and not t.name_pool:
        errors.append(f"{owner}: `name` uses {{first}} but name_pool is empty")
    if len(t.name_pool) != len(set(t.name_pool)):
        dupes = sorted({n for n in t.name_pool if t.name_pool.count(n) > 1})
        errors.append(f"{owner}: name_pool has duplicates: {dupes}")
    if any(not n.strip() for n in t.name_pool):
        errors.append(f"{owner}: name_pool has a blank entry")


def _check_capabilities(roles: list[RoleSpec], errors: list[str]) -> None:
    """Capability names well-formed, for every role."""
    errors.extend(
        f"role {r.slug!r}: capabilities entry {name!r} must match {CAPABILITY_NAME_PATTERN}"
        for r in roles
        for name in malformed_capability_names(r.capabilities)
    )


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
    templates: dict[str, RoleTemplateSpec],
    *,
    origin: str | None = None,
    bundled_slugs: frozenset[str] | None = None,
) -> None:
    errors: list[str] = []
    all_slugs = _check_slugs(roles, errors)
    _check_defaults(roles, errors)
    _check_bundles(bundles, all_slugs, errors, bundled_slugs=bundled_slugs)
    _check_templates(templates, errors)
    _check_models(roles, errors)
    _check_capabilities(roles, errors)
    if errors:
        raise SquadsError(
            f"{_catalog_error_prefix(origin)}:\n" + "\n".join(f"  - {e}" for e in errors)
        )
