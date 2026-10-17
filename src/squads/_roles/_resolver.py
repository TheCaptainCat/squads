"""Role resolver: layer ``<squad-dir>/.overrides/roles/<slug>.toml`` over ``PREDEFINED``.

Call :func:`resolve_role` instead of :func:`~squads._roles._catalog.role_by_slug` whenever a
squad directory is available (i.e. from service-level code).  Call :func:`resolve_dev_role`
for the ``sq dev add`` call site specifically — that one call site is an *assignment* (a new
name being chosen), not a resolve. Every *other* consumer that needs a role's merge base for a
role that may already have a live item — sync's catalog refresh, ``sq role <slug> show``,
``sq check`` — goes through :func:`resolve_role_with_base` with a base built by
:func:`role_base_from_item`, the one seam both a bundled role and a developer role build their
base through — see its docstring for the field split. A slug no source declares resolves to
nothing.

Merge semantics:
- **Bundled slug** — only the fields present in the TOML override the merge base (the item's
  own base when the caller supplied one, else the ``PREDEFINED`` default); absent fields are
  inherited as-is.  This lets a project rename ``architect`` or change its model without
  restating the full mission.
- **New slug, no supplied base** (:func:`resolve_role`, or :func:`resolve_role_with_base` with
  ``base=None``) — a TOML for a slug not in ``PREDEFINED`` defines a wholly-new role; all
  required ``RoleDef`` fields must be present (``slug``, ``full_name``, ``title``,
  ``description``, ``mission``), otherwise a :class:`~squads._errors.SquadsError` is raised
  with a clear message.
- **Supplied base** (:func:`resolve_role_with_base` with a non-``None`` base) — the base is the
  merge base regardless of whether ``slug`` is in ``PREDEFINED``: a caller that already knows a
  role's live identity never has to restate every required field just to change one of them,
  and a bundled role's item-carried name is never discarded in favour of the catalog default.
- **No override file** — falls through to the base (the supplied base, or else the bundled
  catalog) unchanged.

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

A role's name is the one its item stores. Configuration supplies it once, when the role is
created: ``--name`` when given, otherwise the bundled catalog, the project's
``.overrides/roles.toml``, the per-slug ``.overrides/roles/<slug>.toml`` (the most specific
wins) or, for a developer, the pool. No later configuration change renames the role.
"""

import tomllib
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

from squads._errors import RoleNotFoundError, SquadsError
from squads._models import _attributes as attrs
from squads._models._item import Item
from squads._roles._catalog import (
    PREDEFINED,
    RoleDef,
    dev_role_from_pool,
    role_spec_to_def,
)
from squads._roles._loader import VALID_MODELS, load_role_catalog
from squads._roles._models import CAPABILITY_NAME_PATTERN, RoleSpec, malformed_capability_names
from squads._specmerge import RawMapping, describe_spec_error, merge_override

_PREDEFINED_BY_SLUG: dict[str, RoleDef] = {r.slug: r for r in PREDEFINED}


def _predefined_for_slug(slug: str, squad_dir: Path | None) -> RoleDef | None:
    """The predefined base for *slug* — the bundled catalog, with any project catalog-document
    override (``.overrides/roles.toml``) already merged in.

    This is where the second precedence layer (bundled base -> the catalog document) is
    realised: :func:`load_role_catalog` does the merge, and every existing caller of
    :func:`resolve_role`/:func:`resolve_role_with_base` picks it up with no call-site change,
    since a per-slug ``.overrides/roles/<slug>.toml`` file (the third and most specific layer)
    is still layered on top by the caller of *this* function exactly as it already was.

    With *squad_dir* ``None`` this is exactly ``_PREDEFINED_BY_SLUG.get(slug)`` — the bundled
    catalog alone, unchanged. With a *squad_dir*, the catalog is reloaded (and, if present, the
    override re-merged) on every call — consistent with this module's own stated stance that
    the resolver is stateless and reads from disk on every call.
    """
    if squad_dir is None:
        return _PREDEFINED_BY_SLUG.get(slug)
    catalog = load_role_catalog(squad_dir)
    for role_spec in catalog.roles:
        if role_spec.slug == slug:
            return role_spec_to_def(role_spec)
    return None


# Required fields for a *new-slug* TOML (slug is derived from the filename, not the TOML).
_REQUIRED_FOR_NEW = ("full_name", "title", "description", "mission")

#: Post-validation blank-string check, alongside the model whitelist below rather than declared
#: on ``RoleSpec`` itself: a bare ``pydantic.ValidationError`` reads as framework noise to an
#: adopter (a "1 validation error for RoleSpec" header naming an internal class, a truncated
#: ``input_value`` dict dump, a link to pydantic's own error docs) -- compare the clean,
#: hand-written sentence the model check below already produces for the same seam. These three
#: groups mirror RoleSpec's own field shape: required fields are never ``None``; the optional
#: ``model``/``color`` keep ``None`` as their legitimate "not set" value and are only checked
#: when a string was actually declared; list fields are checked per element.
_REQUIRED_NON_BLANK_FIELDS = ("full_name", "title", "description", "mission")
_OPTIONAL_NON_BLANK_FIELDS = ("model", "color")
_LIST_NON_BLANK_FIELDS = ("responsibilities", "agreements")

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
    """The slugs with a project role override — a per-slug file at
    ``<squad_dir>/.overrides/roles/<slug>.toml``, or a wholly-new ``[[roles]]`` entry in the
    catalog document (``.overrides/roles.toml``) that names a slug outside the
    bundled catalog.

    A project-defined (wholly new, or renamed-into) slug is not in the bundled catalog and
    never will be — its only record is one of these two files. Callers that must accept such a
    slug as valid on the per-request path (e.g. the playbook loader's cross-spec role-slug
    check) union this with the bundled catalog's own slugs rather than reading the index —
    the override files are readable before the index is, and are the same source this
    resolver itself reads. Returns an empty set when neither source declares one.
    """
    d = _overrides_dir(squad_dir)
    file_slugs: frozenset[str] = (
        frozenset(p.stem for p in d.glob("*.toml")) if d.is_dir() else frozenset()
    )
    catalog_slugs = frozenset(r.slug for r in load_role_catalog(squad_dir).roles)
    return file_slugs | (catalog_slugs - _PREDEFINED_BY_SLUG.keys())


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
        raise SquadsError(
            f"invalid role override {origin}: {describe_spec_error(exc, RoleSpec)}"
        ) from exc
    _refuse_blank_strings(spec, origin)
    if spec.model is not None and spec.model not in VALID_MODELS:
        raise SquadsError(
            f"invalid role override {origin}: model {spec.model!r} is not one of "
            f"{sorted(VALID_MODELS)}"
        )
    bad_capabilities = malformed_capability_names(spec.capabilities)
    if bad_capabilities:
        raise SquadsError(
            f"invalid role override {origin}: "
            + "; ".join(
                f"capabilities entry {name!r} must match {CAPABILITY_NAME_PATTERN}"
                for name in bad_capabilities
            )
        )
    return role_spec_to_def(spec)


def _refuse_blank_strings(spec: RoleSpec, origin: str) -> None:
    """Refuse a declared-but-blank string field with the same clean shape as the model
    whitelist check just below this call site: the file, then one sentence naming every
    offending field, nothing pydantic wrote.

    An empty (or whitespace-only -- ``.strip()`` before the length check, on the same
    reasoning: it renders exactly as broken and is exactly as clearly not an intentional
    value) string is never a legitimate "inherit the base value" signal, because omitting the
    key already means that. Runs on the *validated* ``spec`` (types are already guaranteed),
    exactly where the model check runs, so a future field added to ``RoleSpec`` is not
    automatically covered here the way a declarative constraint would be -- that trade is
    deliberate: this is the only seam where the offending value has a *file* to name, so a
    clean adopter-facing message pointing at it matters more here than defence in depth for a
    construction path this function alone can see. This is **not** the only place a
    ``RoleSpec``-shaped role is built from adopter-editable text, though -- ``sq role
    activate --name``/``sq dev add --name`` reach ``RoleDef`` directly with an operator's raw
    CLI string, no ``RoleSpec`` in between (a hole a past fix here left open, since neither
    path calls this function). Those two converge on ``RoleDef.__post_init__`` instead, which
    refuses the same way on ``full_name`` alone -- the field either CLI path can set -- and
    this function's checks on the file's *other* fields stay the file-path's own job.
    """
    blank = [name for name in _REQUIRED_NON_BLANK_FIELDS if not getattr(spec, name).strip()]
    blank += [
        name
        for name in _OPTIONAL_NON_BLANK_FIELDS
        if (value := getattr(spec, name)) is not None and not value.strip()
    ]
    blank += [
        name
        for name in _LIST_NON_BLANK_FIELDS
        if any(not entry.strip() for entry in getattr(spec, name))
    ]
    if blank:
        raise SquadsError(
            f"invalid role override {origin}: field(s) blank or whitespace-only "
            "(omit the key instead to inherit): " + ", ".join(blank)
        )


def resolve_role(slug: str, squad_dir: Path | None) -> RoleDef:
    """Return the ``RoleDef`` for *slug*, applying any project override.

    Resolution order:
    1. ``<squad_dir>/.overrides/roles/<slug>.toml`` — if present, merge field-wise.
    2. ``PREDEFINED`` catalog — the bundled default.

    Raises :class:`~squads._errors.RoleNotFoundError` if *slug* is neither predefined nor has a
    project TOML. Unchanged by, and unaware of, :func:`resolve_role_with_base` below — this is
    the ``base=None`` case of that function, kept as its own entry point so every existing
    caller keeps today's exact signature and behaviour.
    """
    return resolve_role_with_base(slug, squad_dir, base=None)


def resolve_role_with_base(
    slug: str,
    squad_dir: Path | None,
    *,
    base: RoleDef | None,
    pinned_name: str | None = None,
) -> RoleDef:
    """Like :func:`resolve_role`, but the caller may supply the merge base — for a slug outside
    ``PREDEFINED``, instead of leaving new-slug validation to demand every required field; for a
    slug inside it, to start from an already-live item's own stored identity.

    ``base=None`` reproduces :func:`resolve_role` exactly. A supplied base always wins over
    ``PREDEFINED``, whether or not ``slug`` is in it; the caller builds it with
    :func:`role_base_from_item` (an item exists) or :func:`dev_base_from_item`. The per-slug
    file merges over the base.

    *pinned_name* is the role's stored name (:func:`pinned_name_of`): it is the result's
    ``full_name`` whatever any layer, the per-slug file included, declares.
    """
    predefined = _predefined_for_slug(slug, squad_dir)  # None for a slug neither source declares
    effective_base = base if base is not None else predefined

    if squad_dir is not None:
        toml_path = _overrides_dir(squad_dir) / f"{slug}.toml"
        if toml_path.is_file():
            data = _read_toml(toml_path)
            applied = _apply_override(effective_base, data, slug, str(toml_path))
            return _pin_name(applied, pinned_name)

    if effective_base is not None:
        return _pin_name(effective_base, pinned_name)

    raise RoleNotFoundError(
        f"no predefined role {slug!r} and no project override found "
        f"(known: {', '.join(_PREDEFINED_BY_SLUG)})"
    )


def _pin_name(role: RoleDef, pinned_name: str | None) -> RoleDef:
    """*role* named *pinned_name* when one is given, else unchanged."""
    if pinned_name is None or role.full_name == pinned_name:
        return role
    return replace(role, full_name=pinned_name)


def pinned_name_of(item: Item | None) -> str | None:
    """The name a role item stores, or ``None`` when there is no item or the stored name is
    blank, which reads as unset."""
    if item is None or not item.title.strip():
        return None
    return item.title


def dev_base_from_item(item: Item, squad_dir: Path | None) -> RoleDef:
    """The dev-role merge base for a developer role that already exists on the roster.

    Reads the item's own stored facts — tech, name, model, default designation — and the
    ``[dev]`` table of the catalog the squad resolves, so the stored name is inherited instead
    of re-rolled from the pool; the pool position is never consulted. A stored name that is
    blank is treated as absent, so the role self-heals on its next sync instead of being
    refused. Every other field (title, mission, responsibilities, colour, ``can_spawn``,
    agreements, capabilities) is regenerated from the template on every call: a stored value
    for any of them is staleness for the sync to converge, never a designation to preserve.

    The stored name is pinned over every layer by the caller (:func:`pinned_name_of`).
    """
    name = item.title if item.title and item.title.strip() else None
    base = dev_role_from_pool(
        attrs.tech(item) or "",
        load_role_catalog(squad_dir).dev,
        name=name,
        model=attrs.model(item),
    )
    # The stored slug is the role's identity; the pool builder only proposes one at creation.
    base = replace(base, slug=item.slug)
    stored_default = attrs.is_default(item)
    if stored_default is None or stored_default == base.is_default:
        return base
    return replace(base, is_default=stored_default)


def role_base_from_item(item: Item, squad_dir: Path | None) -> RoleDef | None:
    """The resolver base for a role that already has a live roster item — the one seam every
    consumer that resolves against an item (sync's catalog refresh, ``sq role <slug> show``,
    ``sq check``) builds its base through, for a bundled role and a developer role alike.

    The item supplies only the facts an operator sets through a dedicated verb; everything else
    comes from the current catalog on every call:

    - **Developer role** — :func:`dev_base_from_item`.
    - **Bundled role** — the slug's current catalog entry (the bundled catalog with the
      project's ``.overrides/roles.toml`` merged in when *squad_dir* is given), with
      ``is_default`` swapped for the stored designation (``sq role set-default``). The name
      is pinned to the stored name by the caller (:func:`pinned_name_of`).
    - **Anything else** — a role no catalog declares (a project-defined role with no per-slug
      file yet) has no base: ``None``.

    A *squad_dir* of ``None`` means no squad: the bundled catalog alone.
    """
    if attrs.is_templated(item):
        return dev_base_from_item(item, squad_dir)
    predefined = _predefined_for_slug(item.slug, squad_dir)
    if predefined is None:
        return None
    stored_default = attrs.is_default(item)
    if stored_default is None or stored_default == predefined.is_default:
        return predefined
    return replace(predefined, is_default=stored_default)


def resolve_role_for_item(item: Item, squad_dir: Path | None) -> RoleDef:
    """The one seam every consumer that needs a live role item's full ``RoleDef`` goes
    through — the roster projection, a backend's per-entry render, ``sq check``'s pointer-
    currency comparison. Resolves through the catalog (:func:`role_base_from_item` +
    :func:`resolve_role_with_base`, with the item's stored name pinned) so a project override
    or a catalog change reaches every one of them without a prior ``sq sync``.

    Falls back to :meth:`RoleDef.from_item` for the one case resolution cannot cover: an
    orphaned custom role item whose backing definition has vanished (no catalog entry, no dev
    shape, no override file). There the item is the only source.
    """
    base = role_base_from_item(item, squad_dir)
    try:
        return resolve_role_with_base(
            item.slug, squad_dir, base=base, pinned_name=pinned_name_of(item)
        )
    except RoleNotFoundError:
        return RoleDef.from_item(item)


def resolve_role_tolerantly(item: Item, squad_dir: Path | None) -> RoleDef:
    """:func:`resolve_role_for_item`, or the item's own :meth:`RoleDef.from_item` when a role
    document refuses to load.

    For derivations that must keep answering next to a broken override (a lane check, a
    preload list, a config-integrity scan): the refusal is already a ``sq check`` finding in its
    own right, and these callers report on or act on other things.
    """
    try:
        return resolve_role_for_item(item, squad_dir)
    except SquadsError:
        return RoleDef.from_item(item)


def holds_default_designation(item: Item, squad_dir: Path | None) -> bool:
    """Whether *item* holds this squad's default-role designation, as every reader of that
    designation sees it — the one seam the lane exemption, the retirement warning, ``sq check``'s
    duplicate-holder report and ``set_default_role``'s own move all ask.

    The designation is **resolved**, not read raw off the item: the stored ``is_default`` is an
    override on an answer the role catalog also gives, and a role item stores it only when
    something wrote it, so the role the catalog designates holds the designation with nothing
    stored. A raw read finds no holder there and leaves a squad generating config with two live
    defaults.

    Falls back to the stored key alone when resolution refuses — a role override document the
    resolver rejects. That refusal is already a ``sq check`` finding in its own right, and every
    caller here is either a reporter, which must survive one broken role to finish the scan, or
    a mutation that must not be blocked by a file it is not touching. The fallback can only
    under-report a holder.
    """
    try:
        return resolve_role_for_item(item, squad_dir).is_default
    except SquadsError:
        return attrs.is_default(item) is True


def resolve_dev_role(
    tech: str,
    *,
    name: str | None = None,
    seq: int = 0,
    model: str | None = None,
    slug: str | None = None,
    squad_dir: Path | None,
) -> RoleDef:
    """Build a stack-specific developer role, applying any project override.

    The generated base is built from the ``[dev]`` table of the catalog *squad_dir* resolves
    (the name pool, default model, colour and capabilities), via
    :func:`~squads._roles._catalog.dev_role_from_pool`; a *squad_dir* of ``None`` means the
    bundled catalog.

    If ``<squad_dir>/.overrides/roles/<slug>.toml`` exists (the slug the role is stored under),
    its fields are merged over that base as the third, most-specific precedence layer. ``name``
    is still honoured as before (explicit name wins over both the pool and any TOML
    ``full_name``).
    """
    base = dev_role_from_pool(
        tech, load_role_catalog(squad_dir).dev, name=name, seq=seq, model=model
    )
    if slug is not None:
        base = replace(base, slug=slug)
    slug = base.slug

    if squad_dir is not None:
        toml_path = _overrides_dir(squad_dir) / f"{slug}.toml"
        if toml_path.is_file():
            data = _read_toml(toml_path)
            # If caller passed an explicit name, honour it — don't let TOML override it.
            if name and "full_name" in data:
                data = {k: v for k, v in data.items() if k != "full_name"}
            return _apply_override(base, data, slug, str(toml_path))

    return base
