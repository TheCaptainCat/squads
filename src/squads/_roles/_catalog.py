"""Bundled agent-role definitions.

Each role has a real name ("Robert Architect") and a slug ("architect"); agents are referred to
by full name in files and conversation. Stack-specific developers are created on demand via
``sq dev add`` using :data:`DEV_NAME_POOL`.

The role data is loaded from the bundled ``roles.toml`` via ``load_role_catalog()``.
``RoleDef`` and all public constants/functions are thin shims over the loaded
``RoleCatalogSpec`` singleton.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

from squads._errors import RoleNotFoundError, SquadsError
from squads._models._extras import ExtraKey as X
from squads._roles._loader import load_role_catalog
from squads._roles._models import DevPoolSpec, RoleCatalogSpec, RoleSpec
from squads._util import slugify


@dataclass(frozen=True)
class RoleDef:
    slug: str
    full_name: str
    title: str
    description: str  # one-liner for the Claude pointer frontmatter
    mission: str
    responsibilities: tuple[str, ...] = ()
    agreements: tuple[str, ...] = ()
    model: str | None = None  # sonnet | opus | haiku | inherit
    color: str | None = None
    is_default: bool = False
    can_spawn: bool = False  # True only for orchestrating roles (manager, tech-lead)

    def __post_init__(self) -> None:
        """Refuse a blank/whitespace-only ``full_name`` at the one point every construction
        path actually goes through: the override merge (:func:`~squads._roles._resolver.
        _apply_override`, via :func:`role_spec_to_def`), ``sq role activate --name`` (via
        ``dataclasses.replace``, which re-invokes ``__post_init__`` on a frozen dataclass same
        as the constructor), and ``sq dev add --name`` (via :func:`dev_role`'s own constructor
        call). All three end in a ``RoleDef`` whose ``full_name`` is the operator-supplied
        string, so this is the single seam that closes the hole for every one of them at once
        rather than a check repeated at each call site.

        Only ``full_name`` is checked here — the only field an operator can set directly
        through those two CLI flags. The override path's other string fields (``title``,
        ``description``, ``mission``, …) are declared-in-a-file values with no CLI equivalent,
        and stay validated where they already are, by
        :func:`~squads._roles._resolver._refuse_blank_strings`, which runs *before* this
        constructor and produces a message naming the offending override file — a message
        this generic check has no file to name and must not blur.

        Leading/trailing whitespace around real content (``"  Ada Lovelace  "``) is accepted
        and stored verbatim, not trimmed — ``.strip()`` is used only to decide blankness,
        exactly as :func:`~squads._roles._resolver._refuse_blank_strings` already treats the
        override path's own fields, so the two seams agree on what counts as a real value.
        """
        if not self.full_name.strip():
            raise SquadsError(
                "role full_name is blank or whitespace-only — every role needs a real name"
            )

    #: The single source of truth for :meth:`to_extra`'s shape: the ``extra`` key paired with
    #: the typed accessor that reads its value off an instance. :meth:`extra_keys` reads only
    #: the key column, so the key set and the values it's paired with can never drift apart —
    #: there is no second, separately maintained list of key names to forget to update.
    _EXTRA_FIELD_KEYS: ClassVar[tuple[tuple[str, Callable[[RoleDef], Any]], ...]] = (
        (X.FULL_NAME, lambda r: r.full_name),
        (X.SLUG, lambda r: r.slug),
        (X.TITLE, lambda r: r.title),
        (X.MISSION, lambda r: r.mission),
        (X.RESPONSIBILITIES, lambda r: list(r.responsibilities)),
        (X.AGREEMENTS, lambda r: list(r.agreements)),
        (X.MODEL, lambda r: r.model),
        (X.COLOR, lambda r: r.color),
        (X.IS_DEFAULT, lambda r: r.is_default),
        (X.CAN_SPAWN, lambda r: r.can_spawn),
    )

    #: Reconciled into ``extra`` by :meth:`to_extra` exactly like the fields above, but
    #: deliberately **not** read by :meth:`extra_keys` — and so not a member of
    #: ``PERMITTED_EXTRA_SKEW`` (``_itemfile.py``). Every key in ``_EXTRA_FIELD_KEYS`` is
    #: exempt from the skew guard because a squad synced by a release predating
    #: ``_refresh_catalog_extra``'s index mirror may hold an index that already lags on that
    #: key — the exemption is what lets such a squad's next sync converge instead of being
    #: refused outright. ``description`` is different: ``activate_role``/``add_dev``
    #: (``_services/_roster.py``) have always written ``extra.description`` explicitly, inside
    #: the same ``store.transaction()`` that commits the item's index entry — so markdown and
    #: index have never disagreed on it, and there is no lagging index for an exemption to
    #: forgive; a mismatch on it is a real skew to catch, not noise to exempt. A field belongs
    #: here, not in ``_EXTRA_FIELD_KEYS``, exactly when it was never written to markdown
    #: *outside* a transaction — never "was it ever written at all", since ``description``
    #: itself was, from inside one.
    _RECONCILED_EXTRA_KEYS: ClassVar[tuple[tuple[str, Callable[[RoleDef], Any]], ...]] = (
        (X.DESCRIPTION, lambda r: r.description),
    )

    #: The pairing between a resolved ``RoleDef`` field and the top-level ``Item`` field it
    #: projects onto — ``title`` from ``full_name``, ``description`` from ``mission``. Declared
    #: beside :data:`_EXTRA_FIELD_KEYS`, in the same shape, so a field that lands on a
    #: top-level item field (not just in ``extra``) can never be half-wired: the reconciler
    #: loops over :meth:`to_item_fields` exactly as it loops over :meth:`to_extra`.
    _ITEM_FIELD_PROJECTION: ClassVar[tuple[tuple[str, Callable[[RoleDef], Any]], ...]] = (
        ("title", lambda r: r.full_name),
        ("description", lambda r: r.mission),
    )

    def to_extra(self) -> dict[str, Any]:
        """Type-specific fields stored on the ROLE item."""
        return {
            key: getter(self)
            for key, getter in (*self._EXTRA_FIELD_KEYS, *self._RECONCILED_EXTRA_KEYS)
        }

    def to_item_fields(self) -> dict[str, Any]:
        """Top-level ``Item`` fields this role's resolved definition projects onto, once
        resolved — ``title`` from ``full_name``, ``description`` from ``mission``. The
        reconciler assigns these directly onto the item's own fields (never through ``extra``),
        mirroring :meth:`to_extra`'s shape for a different destination.
        """
        return {field: getter(self) for field, getter in self._ITEM_FIELD_PROJECTION}

    @classmethod
    def extra_keys(cls) -> frozenset[str]:
        """The key names :meth:`to_extra` populates that are exempt from the skew guard —
        derived from :data:`_EXTRA_FIELD_KEYS` alone (never :data:`_RECONCILED_EXTRA_KEYS`),
        without constructing an instance. A required field added to ``RoleDef`` later must not
        turn a throwaway construction here into a startup crash, and a description-only change
        to ``to_extra`` (e.g. omitting a falsy value) must not silently shrink this set out
        from under it — reading the table's key column instead of the table's *output* pins
        both.
        """
        return frozenset(key for key, _ in cls._EXTRA_FIELD_KEYS)

    @classmethod
    def from_extra(cls, extra: dict[str, Any]) -> RoleDef:
        """Build a ``RoleDef`` straight from an already-resolved item's stored ``extra`` —
        the cheap read path :meth:`~squads._services._items.ItemMixin.regen` and the sync
        roster sweep's per-entry projection use, deliberately *not* re-running the override
        merge (that would discard an operator's own project override; see ``role_base_from_item``'s
        docstring for the seam that does that resolution instead).

        A stored ``full_name`` that is blank or whitespace-only is tolerated the same way the
        override-merge seam tolerates it, via :func:`_fallback_full_name` — a read boundary
        must not weaponise :class:`RoleDef.__post_init__`'s refusal against a fact a previous
        release wrote and called healthy.
        """
        full_name = extra[X.FULL_NAME]
        if not full_name or not full_name.strip():
            full_name = _fallback_full_name(extra)
        return cls(
            slug=extra[X.SLUG],
            full_name=full_name,
            title=extra.get(X.TITLE, ""),
            description=extra.get(X.DESCRIPTION, extra.get(X.TITLE, "")),
            mission=extra.get(X.MISSION, ""),
            responsibilities=tuple(extra.get(X.RESPONSIBILITIES, [])),
            agreements=tuple(extra.get(X.AGREEMENTS, [])),
            model=extra.get(X.MODEL),
            color=extra.get(X.COLOR),
            is_default=extra.get(X.IS_DEFAULT, False),
            can_spawn=extra.get(X.CAN_SPAWN, False),
        )

    @classmethod
    def from_extra_or_item(
        cls, extra: dict[str, Any], *, title: str, slug: str, description: str
    ) -> RoleDef:
        """Build a ``RoleDef`` from a role item's own top-level fields, tolerating an
        ``extra`` that carries no role projection at all — the shape a bare
        ``Service.create('role', …)`` call produces (no CLI verb reaches this; the roster's
        own creators, ``activate_role``/``add_dev``, always pass a full ``role.to_extra()``
        as ``extra``, so this path is a fallback for that one, and only that one).

        Falls back field by field to the item's own ``title``/``slug``/``description``
        whenever ``extra`` is silent on the corresponding key — absent *or* blank, the same
        pair of cases :meth:`from_extra` already treats alike for ``full_name`` — the same
        graceful degradation the pre-inversion template applied inline via
        ``extra.get(key, item.title)``, so it happens once, here, rather than being
        re-litigated in Jinja. This is the create-time counterpart to
        :meth:`from_extra`'s stricter contract (a genuinely-resolved mirror): every caller
        that renders ``agents/role.md.j2`` must hand it a complete ``RoleDef``, never
        ``None`` and never a missing attribute — this method is how a caller with only a
        partial ``extra`` still produces one.

        Never raises for any well-formed item — ``title``/``slug`` are required, non-blank
        ``Item`` fields, so ``full_name``/``slug`` always resolve to *something*. If a title
        were somehow whitespace-only, :class:`RoleDef`'s own ``__post_init__`` still refuses
        it — as the clean :class:`~squads._errors.SquadsError` it already is, never a bare
        ``KeyError`` out of a dict subscript.
        """
        return cls(
            slug=extra.get(X.SLUG) or slug,
            full_name=extra.get(X.FULL_NAME) or title,
            title=extra.get(X.TITLE, "") or title,
            description=extra.get(X.DESCRIPTION, "") or description,
            mission=extra.get(X.MISSION, "") or description,
            responsibilities=tuple(extra.get(X.RESPONSIBILITIES, [])),
            agreements=tuple(extra.get(X.AGREEMENTS, [])),
            model=extra.get(X.MODEL),
            color=extra.get(X.COLOR),
            is_default=extra.get(X.IS_DEFAULT, False),
            can_spawn=extra.get(X.CAN_SPAWN, False),
        )


def role_spec_to_def(rs: RoleSpec) -> RoleDef:
    """Convert a ``RoleSpec`` from the loaded catalog to a ``RoleDef``."""
    return RoleDef(
        slug=rs.slug,
        full_name=rs.full_name,
        title=rs.title,
        description=rs.description,
        mission=rs.mission,
        responsibilities=tuple(rs.responsibilities),
        agreements=tuple(rs.agreements),
        model=rs.model,
        color=rs.color,
        is_default=rs.is_default,
        can_spawn=rs.can_spawn,
    )


# ---------------------------------------------------------------------------
# Module-level singleton — loaded once on first import.
# ---------------------------------------------------------------------------

_CATALOG: RoleCatalogSpec = load_role_catalog()


def get_catalog() -> RoleCatalogSpec:
    """Return the loaded role catalog singleton (the slug authority for cross-spec validation)."""
    return _CATALOG


# ---------------------------------------------------------------------------
# Public constants — backed by the singleton (behavior-identical shims).
# ---------------------------------------------------------------------------

#: The 8 bundled agent roles (declaration order preserved from roles.toml).
PREDEFINED: tuple[RoleDef, ...] = tuple(role_spec_to_def(rs) for rs in _CATALOG.roles)

_BY_SLUG: dict[str, RoleDef] = {r.slug: r for r in PREDEFINED}

#: Named bundles selectable at ``sq init --roles``.
BUNDLES: dict[str, tuple[str, ...]] = {
    name: tuple(slugs) for name, slugs in _CATALOG.bundles.items()
}

#: First-name pool for auto-named developers (surname = the tech).
DEV_NAME_POOL: tuple[str, ...] = tuple(_CATALOG.dev.name_pool)


def role_by_slug(slug: str) -> RoleDef:
    try:
        return _BY_SLUG[slug]
    except KeyError:
        raise RoleNotFoundError(
            f"no predefined role {slug!r} (known: {', '.join(_BY_SLUG)})"
        ) from None


def resolve_roles(spec: str) -> list[RoleDef]:
    """Resolve a ``--roles`` spec: a bundle name, or a comma-separated list of slugs."""
    spec = spec.strip()
    if spec in BUNDLES:
        return [role_by_slug(s) for s in BUNDLES[spec]]
    slugs = [s.strip() for s in spec.split(",") if s.strip()]
    return [role_by_slug(s) for s in slugs]


def dev_role_from_pool(
    tech: str,
    dev: DevPoolSpec,
    *,
    name: str | None = None,
    seq: int = 0,
    model: str | None = None,
) -> RoleDef:
    """Build a stack-specific developer role from an explicit ``dev`` pool spec — the
    parameterised form :func:`dev_role` is a thin wrapper over, letting
    :func:`~squads._roles._resolver.resolve_dev_role` build against a project's own
    catalog-document ``[dev]`` override (``.overrides/roles.toml``) instead of the
    bundled singleton's, with the same construction logic either way.

    If ``name`` is omitted (``None``), a first name is taken from ``dev.name_pool`` (by
    ``seq``) and the surname is the tech (→ "Elias Dotnet"); the slug is ``<tech>-dev``.
    ``name=""`` (or a whitespace-only string) is *not* "omitted" — an operator who explicitly
    passed a blank ``--name`` gets it stored as their ``full_name`` and refused by
    :meth:`RoleDef.__post_init__`, the same way a whitespace-only override field is refused,
    rather than silently falling back to the pool as a falsy check would.
    """
    tech_label = tech.strip()
    surname = tech_label[:1].upper() + tech_label[1:]
    if name is not None:
        full_name = name
    else:
        pool = dev.name_pool
        first = pool[seq % len(pool)]
        full_name = f"{first} {surname}"
    slug = f"{slugify(tech_label)}-dev"
    return RoleDef(
        slug=slug,
        full_name=full_name,
        title=f"{surname} developer",
        description=f"Implements {surname} code following the project's guides and standards.",
        mission=(
            f"Implement assigned tasks in {surname}, following the project's guides, with tests."
        ),
        responsibilities=(
            f"Implement tasks in {surname}",
            "Write tests for changes",
            "Follow the relevant guides; ask the architect when unsure",
        ),
        model=model or dev.model,
        color=dev.color,
    )


def dev_role(
    tech: str, *, name: str | None = None, seq: int = 0, model: str | None = None
) -> RoleDef:
    """Build a stack-specific developer role on demand, from the bundled catalog's own ``dev``
    spec — see :func:`dev_role_from_pool` for the parameterised form and the name
    pool/model/color source.
    """
    return dev_role_from_pool(tech, _CATALOG.dev, name=name, seq=seq, model=model)


def _fallback_full_name(extra: dict[str, Any]) -> str:
    """The name to substitute for a stored ``full_name`` that is blank or whitespace-only —
    used only by :meth:`RoleDef.from_extra`, at the read boundary.

    Mirrors what the next ``sq sync`` would converge the item onto: the bundled catalog's own
    name for a predefined slug, the generated pool name for a developer role (position 0 — the
    item does not carry the original ``seq``, exactly as :func:`~squads._roles._resolver.
    dev_base_from_item` re-derives it). A slug that is neither is the one shape the input
    boundary (``_refuse_blank_strings``, on every project role override file) already prevents
    from ever reaching a stored blank in the first place, so it falls back to the slug itself
    rather than raising — a placeholder, never a crash, for a shape that should not occur.
    """
    slug = extra.get(X.SLUG, "")
    if extra.get(X.IS_DEV):
        tech = extra.get(X.TECH, slug.removesuffix("-dev"))
        return dev_role(tech).full_name
    predefined = _BY_SLUG.get(slug)
    if predefined is not None:
        return predefined.full_name
    return slug or "unnamed role"
