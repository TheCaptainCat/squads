"""Role resolver: a role is one base, a per-slug file layered over it, then the item's stored
per-role values.

The **base** is chosen from the item's stored facts only, in this order
(:func:`role_base_from_item`):

1. the item stores ``template`` -- the ``[templates.<name>]`` table of the catalog the squad
   resolves, instantiated with the item's ``tech``;
2. the item stores ``mission`` -- the item's own definition fields;
3. otherwise the slug's entry in the catalog (the bundled ``roles.toml`` with the project's
   ``.overrides/roles.toml`` merged in).

The catalog is never consulted to decide the kind, so a later catalog entry cannot swap a live
role's definition. A base that does not resolve (a catalog slug the catalog no longer declares,
an undeclared template) leaves the role to materialise from what the item stores
(:meth:`~squads._roles._catalog.RoleDef.from_item`); ``sq check`` reports it.

The per-slug file ``<squad-dir>/.overrides/roles/<slug>.toml``, when present, merges field-wise
over the base. :class:`StoredRoleValues` -- the name, default designation and model a role verb
set on the item -- is applied last and wins over every layer.

The merge itself is the shared engine (:mod:`squads._specmerge`) and the validation is the
typed :class:`~squads._roles._models.RoleSpec`, exactly as the workflow and playbook overrides
already do. A role is materialised into the agent hosts' own files, so a bad value here writes
a broken agent definition rather than making an ``sq`` view odd; a quoting mistake in
``can_spawn``, a misspelt model, a non-string colour or an unknown key is refused, and splat-refs
resolve before validation.

The resolver keeps no state: it reads the per-slug files from disk on every call and takes the
role catalog from the caller as a :data:`~squads._roles._models.CatalogSource`, which whoever
owns the squad's documents builds once. A caller that wants the bundled catalog alone passes
:func:`~squads._roles._catalog.get_catalog`.

A role's name is the one its item stores. It is chosen once, when the role is created: ``--name``
when given, otherwise a per-slug file's ``full_name``, the catalog entry's, or the template's
``name`` pattern. No later configuration change renames the role.
"""

import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, cast

from squads._errors import RoleNotFoundError, SquadsError
from squads._models import _attributes as attrs
from squads._models._item import Item
from squads._pronouns import pronouns
from squads._roles._catalog import (
    PREDEFINED,
    RoleDef,
    instantiate_template,
    role_spec_to_def,
    stored_model,
)
from squads._roles._loader import VALID_MODELS, refuse_pronouns_key
from squads._roles._models import (
    CAPABILITY_NAME_PATTERN,
    CatalogSource,
    RoleCatalogSpec,
    RoleSpec,
    malformed_capability_names,
)
from squads._roles._templates import proposed_name, takes_parameter
from squads._specload import ROLE_OVERRIDE_MESSAGES, override_present, read_override_text
from squads._specmerge import RawMapping, describe_spec_error, merge_override

_PREDEFINED_BY_SLUG: dict[str, RoleDef] = {r.slug: r for r in PREDEFINED}


def _predefined_for_slug(slug: str, catalog: CatalogSource) -> RoleDef | None:
    """The predefined base for *slug* — the bundled catalog, with any project catalog-document
    override (``.overrides/roles.toml``) already merged in.

    This is where the second precedence layer (bundled base -> the catalog document) is
    realised: the *catalog* the caller resolved carries the merge, and every caller of
    :func:`resolve_role`/:func:`resolve_role_with_base` picks it up with no call-site change,
    since a per-slug ``.overrides/roles/<slug>.toml`` file (the third and most specific layer)
    is still layered on top by the caller of *this* function exactly as it already was.
    """
    for role_spec in catalog().roles:
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


def model_problem(model: str | None) -> str | None:
    """Why *model* is not a model a role may name, ``None`` when it is (or is unset)."""
    if model is None or model in VALID_MODELS:
        return None
    return f"model {model!r} is not one of {sorted(VALID_MODELS)}"


def read_role_toml(path: Path) -> dict[str, Any]:
    """Read a role definition file; surface a :class:`SquadsError` when it cannot be read or
    parsed."""
    return _read_toml(path)


def _read_toml(path: Path) -> dict[str, Any]:
    """Read *path* as TOML; surface a :class:`SquadsError` when it cannot be read or parsed."""
    text = read_override_text(path, ROLE_OVERRIDE_MESSAGES)
    try:
        return tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise SquadsError(ROLE_OVERRIDE_MESSAGES.malformed.format(path=path, exc=exc)) from exc


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
                f"the file for {slug!r} is a layer with no base (no role or catalog entry holds "
                "it) and lacks the required fields: " + ", ".join(missing)
            )

    refuse_pronouns_key({**data, "slug": slug}, f"invalid role override {origin}")
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
    problem = model_problem(spec.model)
    if problem is not None:
        raise SquadsError(f"invalid role override {origin}: {problem}")
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


@dataclass(frozen=True)
class StoredRoleValues:
    """The per-role values a role verb stores on the item, each ``None`` when unset. They win
    over every layer of the definition."""

    name: str | None = None
    is_default: bool | None = None
    model: str | None = None


def stored_values(item: Item | None) -> StoredRoleValues | None:
    """The per-role values *item* stores, ``None`` when there is no item. A blank stored name
    reads as unset."""
    if item is None:
        return None
    return StoredRoleValues(
        name=item.title if item.title.strip() else None,
        is_default=attrs.is_default(item),
        model=stored_model(item),
    )


def resolve_role(slug: str, squad_dir: Path | None, *, catalog: CatalogSource) -> RoleDef:
    """Return the ``RoleDef`` for catalog *slug*, applying any per-slug file.

    Raises :class:`~squads._errors.RoleNotFoundError` when the catalog does not declare *slug*.
    """
    return resolve_role_with_base(slug, squad_dir, base=None, catalog=catalog)


def resolve_role_with_base(
    slug: str,
    squad_dir: Path | None,
    *,
    base: RoleDef | None,
    catalog: CatalogSource,
    stored: StoredRoleValues | None = None,
) -> RoleDef:
    """Resolve *slug* over *base*, or over its catalog entry when no base is given: the per-slug
    file merges over the base, then *stored* wins over the result.

    A caller with a live item builds the base with :func:`role_base_from_item` and passes
    :func:`stored_values`. Raises :class:`~squads._errors.RoleNotFoundError` when there is no
    base: a per-slug file alone does not define a role.
    """
    effective_base = base if base is not None else _predefined_for_slug(slug, catalog)
    if effective_base is None:
        raise RoleNotFoundError(
            f"no role {slug!r}: the catalog does not declare it "
            f"(known: {', '.join(_PREDEFINED_BY_SLUG)})"
        )
    role = effective_base
    if squad_dir is not None:
        toml_path = _overrides_dir(squad_dir) / f"{slug}.toml"
        if override_present(toml_path):
            role = _apply_override(effective_base, _read_toml(toml_path), slug, str(toml_path))
    return _apply_stored(role, stored)


def _apply_stored(role: RoleDef, stored: StoredRoleValues | None) -> RoleDef:
    """*role* with the item's stored name, default designation and model laid over it."""
    if stored is None:
        return role
    changes: dict[str, Any] = {}
    if stored.name is not None and stored.name != role.full_name:
        changes["full_name"] = stored.name
    if stored.is_default is not None and stored.is_default != role.is_default:
        changes["is_default"] = stored.is_default
    if stored.model is not None and stored.model != role.model:
        changes["model"] = stored.model
    return replace(role, **changes) if changes else role


def override_full_name(slug: str, squad_dir: Path | None) -> str | None:
    """The ``full_name`` the per-slug file for *slug* declares, ``None`` without a file or key."""
    if squad_dir is None:
        return None
    toml_path = _overrides_dir(squad_dir) / f"{slug}.toml"
    if not override_present(toml_path):
        return None
    value = _read_toml(toml_path).get("full_name")
    return value if isinstance(value, str) else None


def role_defined_by_file(slug: str, squad_dir: Path | None) -> RoleDef | None:
    """The role the per-slug file for *slug* defines by itself, ``None`` without a file.

    Raises :class:`~squads._errors.SquadsError` when the file does not load as a complete role.
    """
    if squad_dir is None:
        return None
    toml_path = _overrides_dir(squad_dir) / f"{slug}.toml"
    if not override_present(toml_path):
        return None
    return _apply_override(None, _read_toml(toml_path), slug, str(toml_path))


def merge_definition_delta(current: RoleDef, delta: RawMapping, slug: str, origin: str) -> RoleDef:
    """*current* with the per-slug file grammar *delta* merged over it field-wise: the same
    engine and validation an override file gets, ``$(*self)`` resolving against *current*."""
    return _apply_override(current, delta, slug, origin)


def override_file_keys(slug: str, squad_dir: Path | None) -> frozenset[str]:
    """The keys the per-slug file for *slug* sets; empty without a file or when it does not
    parse (``sq check`` reports that)."""
    if squad_dir is None:
        return frozenset()
    toml_path = _overrides_dir(squad_dir) / f"{slug}.toml"
    if not override_present(toml_path):
        return frozenset()
    try:
        return frozenset(_read_toml(toml_path))
    except SquadsError:
        return frozenset()


def role_from_definition(data: RawMapping, slug: str, origin: str) -> RoleDef:
    """The role a complete definition *data* (the per-slug file grammar) describes, validated
    as a file would be; *origin* names the source in a refusal."""
    return _apply_override(None, data, slug, origin)


def role_base_from_item(item: Item, catalog: CatalogSource) -> RoleDef | None:
    """The base of a live role item, chosen from its stored facts only: ``template``, then
    ``mission``, then the catalog. ``None`` when the chosen base does not resolve: a template
    the catalog does not declare, or a catalog slug the catalog no longer declares.

    The item's stored name is the base's name; the per-slug file and the other stored values
    are laid over it by :func:`resolve_role_with_base`.
    """
    template = attrs.template(item)
    if template is not None:
        spec = catalog().templates.get(template)
        if spec is None:
            return None
        tech = attrs.tech(item)
        name = item.title.strip() or proposed_name(spec, tech, 0) or item.slug
        return instantiate_template(spec, tech=tech, slug=item.slug, full_name=name)
    if attrs.mission(item) is not None:
        return RoleDef.from_item(item)
    predefined = _predefined_for_slug(item.slug, catalog)
    if predefined is None or not item.title.strip():
        return predefined
    return replace(predefined, full_name=item.title)


def base_problems(item: Item, catalog: RoleCatalogSpec) -> list[str]:
    """Why the base *item* stores does not resolve against *catalog*, one sentence each, each
    ending with its remedy; empty when it resolves. Reads only the documents in hand."""
    slug = item.slug
    template = attrs.template(item)
    mission = attrs.mission(item)
    problems: list[str] = []
    if template is not None and mission is not None:
        problems.append(
            "stores both `template` and `mission`, so it has two bases; remove one of the two "
            "keys from its file"
        )
    if template is not None:
        spec = catalog.templates.get(template)
        if spec is None:
            declared = ", ".join(sorted(catalog.templates)) or "none"
            problems.append(
                f"names the role template {template!r}, which the role catalog does not declare "
                f"(declared: {declared}); declare it in .overrides/roles.toml"
            )
        else:
            takes = takes_parameter(spec)
            if takes and attrs.tech(item) is None:
                problems.append(
                    f"was built from template {template!r}, which takes a technology, and stores "
                    "no `tech`"
                )
            if not takes and attrs.tech(item) is not None:
                problems.append(f"stores `tech`, which template {template!r} does not take")
    elif mission is not None:
        missing = [
            name
            for name, value in (
                ("job_title", attrs.job_title(item)),
                ("description", item.description),
                ("mission", mission),
            )
            if not (value or "").strip()
        ]
        if missing:
            problems.append(
                f"defines itself but stores no {', '.join(missing)}; set "
                f"`sq role {slug} update --job-title … --desc … --mission …`"
            )
        bad = malformed_capability_names(attrs.capabilities(item) or [])
        if bad:
            problems.append(
                f"stores capabilities that do not match {CAPABILITY_NAME_PATTERN}: "
                f"{', '.join(bad)}; set them with `sq role {slug} update --capabilities …`"
            )
    elif not any(r.slug == slug for r in catalog.roles):
        problems.append(
            "is backed by no catalog entry: restore the entry, or make the role define itself "
            f"with `sq role {slug} update --job-title … --desc … --mission …`"
        )
    return problems


def materialised_base(item: Item, catalog: CatalogSource) -> RoleDef:
    """:func:`role_base_from_item`, or what the item stores when that base does not resolve."""
    return role_base_from_item(item, catalog) or RoleDef.from_item(item)


def resolve_role_for_item(item: Item, squad_dir: Path | None, *, catalog: CatalogSource) -> RoleDef:
    """The one seam every consumer that needs a live role item's full ``RoleDef`` goes
    through: the roster projection, a backend's per-entry render, ``sq check``'s pointer-currency
    comparison. Base, then the per-slug file, then the item's stored values; a project override
    or a catalog change reaches every consumer without a prior ``sq sync``.
    """
    role = resolve_role_with_base(
        item.slug,
        squad_dir,
        base=materialised_base(item, catalog),
        catalog=catalog,
        stored=stored_values(item),
    )
    return replace(role, pronouns=resolve_pronouns(pronouns(item), catalog))


def resolve_pronouns(own: str | None, catalog: CatalogSource) -> str | None:
    """A role's pronouns: its *own* value, else the role catalog document's declared
    ``[defaults].pronouns``, else ``None``. The result is never written to an item."""
    if own is not None:
        return own
    return catalog().defaults.pronouns


def resolve_role_tolerantly(
    item: Item, squad_dir: Path | None, *, catalog: CatalogSource
) -> RoleDef:
    """:func:`resolve_role_for_item`, or the item's own :meth:`RoleDef.from_item` when a role
    document refuses to load.

    For derivations that must keep answering next to a broken override (a lane check, a
    preload list, a config-integrity scan): the refusal is already a ``sq check`` finding in its
    own right, and these callers report on or act on other things.
    """
    try:
        return resolve_role_for_item(item, squad_dir, catalog=catalog)
    except SquadsError:
        return RoleDef.from_item(item)


def holds_default_designation(
    item: Item, squad_dir: Path | None, *, catalog: CatalogSource
) -> bool:
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
        return resolve_role_for_item(item, squad_dir, catalog=catalog).is_default
    except SquadsError:
        return attrs.is_default(item) is True
