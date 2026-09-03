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


def _or_fallback(stored: Any, fallback: str) -> str:
    """*stored* when it is a real value, else *fallback* — the one place
    :meth:`RoleDef.from_extra_or_item` decides what "the item's ``extra`` is silent on this
    key" means.

    Absent (``None``) and blank (empty or whitespace-only) are treated alike, deliberately: a
    stored ``"   "`` is a shape a previous release wrote and called healthy, and a read
    boundary that carried it through would hand it to a constructor whose whole job is to
    refuse operator input of exactly that shape. A non-string stored value is coerced with
    ``str`` rather than refused — the same read-boundary rule, one type over.
    """
    if stored is None:
        return fallback
    text = stored if isinstance(stored, str) else str(stored)
    return text if text.strip() else fallback


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
    #:
    #: **This table is the stored *residue* of a role, not a copy of its definition.** A role's
    #: title, mission, responsibilities, agreements, colour and spawn authority are catalog
    #: answers resolved on every read (:func:`~squads._roles._resolver.resolve_role_for_item`),
    #: and the resolved full name lands on the item's own ``title`` field via
    #: :data:`_ITEM_FIELD_PROJECTION` rather than here. Storing any of them again would be a
    #: second copy that can only go stale, so what is left is what no document answers:
    #:
    #: - ``slug`` — the dispatch identity, frozen non-renamable, and the key every roster
    #:   lookup matches on;
    #: - ``model`` — written for a **developer** role only (:meth:`to_extra`'s ``is_dev``
    #:   argument), because ``sq dev add --model`` is an operator setting with no catalog
    #:   answer and :func:`~squads._roles._resolver.dev_base_from_item` reads it straight back
    #:   off the item. A bundled role's model comes from the catalog, so writing it here would
    #:   be a mirror again.
    #:
    #: ``is_dev``/``tech`` (the developer marker) and ``is_default`` (``sq role set-default``)
    #: are stored on a role item too, and are deliberately *not* members: each is written by
    #: its own verb, and reasserting one here from a resolved definition on every sync is
    #: exactly the revert this table's shrink removes.
    _EXTRA_FIELD_KEYS: ClassVar[tuple[tuple[str, Callable[[RoleDef], Any]], ...]] = (
        (X.SLUG, lambda r: r.slug),
    )

    #: A second table in exactly :data:`_EXTRA_FIELD_KEYS`' shape, written for a **developer**
    #: role only — see that table's note on ``model``. A separate table rather than a branch
    #: inside :meth:`to_extra` so :meth:`extra_keys` can read both key columns and answer for
    #: a role of any shape, without either table having to know why the other exists.
    _DEV_EXTRA_FIELD_KEYS: ClassVar[tuple[tuple[str, Callable[[RoleDef], Any]], ...]] = (
        (X.MODEL, lambda r: r.model),
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

    def to_extra(self, *, is_dev: bool = False) -> dict[str, Any]:
        """Type-specific fields stored on the ROLE item — see :data:`_EXTRA_FIELD_KEYS` for
        why this is a short list and what answers the rest.

        *is_dev* selects whether :data:`_DEV_EXTRA_FIELD_KEYS` (today: ``model``) is written
        too. It is a parameter rather than something derived from ``self.slug`` deliberately:
        the developer marker lives on the *item* (``extra.is_dev``), and every caller here
        already knows which shape it is writing — ``add_dev`` and the reconciler reading that
        marker back off the item. Deriving it from the slug's spelling would make a bundled
        role that happens to end in ``-dev`` store a model nothing reads.
        """
        table = self._EXTRA_FIELD_KEYS
        if is_dev:
            table = (*table, *self._DEV_EXTRA_FIELD_KEYS)
        return {key: getter(self) for key, getter in table}

    def to_item_fields(self) -> dict[str, Any]:
        """Top-level ``Item`` fields this role's resolved definition projects onto, once
        resolved — ``title`` from ``full_name``, ``description`` from ``mission``. The
        reconciler assigns these directly onto the item's own fields (never through ``extra``),
        mirroring :meth:`to_extra`'s shape for a different destination.
        """
        return {field: getter(self) for field, getter in self._ITEM_FIELD_PROJECTION}

    @classmethod
    def stored_extra_keys(cls, *, is_dev: bool) -> frozenset[str]:
        """The ``extra`` keys :meth:`to_extra` writes for a role of **this** shape — the key
        column of :data:`_EXTRA_FIELD_KEYS`, plus :data:`_DEV_EXTRA_FIELD_KEYS`' when *is_dev*.

        :meth:`extra_keys` answers the shape-independent union (every name a guard keyed on
        the *field* has to know about); this answers the per-item question of which of them a
        particular role actually stores, which is what a caller deciding whether a stored key
        is still written needs. Both read the tables' key columns rather than an instance's
        :meth:`to_extra` output, for the reason recorded on :meth:`extra_keys`.
        """
        table = cls._EXTRA_FIELD_KEYS
        if is_dev:
            table = (*table, *cls._DEV_EXTRA_FIELD_KEYS)
        return frozenset(key for key, _ in table)

    @classmethod
    def extra_keys(cls) -> frozenset[str]:
        """Every key name :meth:`to_extra` can populate, for a role of any shape — the union
        of both key columns, read without constructing an instance.

        Reading the tables' key column rather than an instance's :meth:`to_extra` *output* is
        what pins the two together: a required field added to ``RoleDef`` later must not turn a
        throwaway construction here into a startup crash, and a value-side change to
        ``to_extra`` (e.g. omitting a falsy value, or the ``is_dev`` branch) must not silently
        shrink this set out from under it. The dev-only column is included for the same
        reason the skew guard is a property of the *field* rather than of whichever writer
        persists it — :func:`~squads._itemfile._exempt_extra_keys` is where the per-item
        question of which of these actually applies is answered.
        """
        return cls.stored_extra_keys(is_dev=True)

    @classmethod
    def from_extra_or_item(
        cls, extra: dict[str, Any], *, title: str, slug: str, description: str
    ) -> RoleDef:
        """Build a ``RoleDef`` from a role item alone — its ``extra`` for whatever that still
        carries, its own top-level ``title``/``slug``/``description`` for the rest.

        This is the read boundary for the two shapes that cannot resolve through the role
        catalog at all, and it must tolerate **both** corpus vintages: an item written by a
        release that stored the full definition in ``extra``, and one written since, whose
        ``extra`` carries only the residue :data:`_EXTRA_FIELD_KEYS` names. It therefore falls
        back field by field whenever ``extra`` is silent on a key — absent *or* blank, treated
        alike, because a stored blank is a fact some earlier release wrote and called healthy
        and a read boundary must never re-refuse one.

        Its two callers:

        - :meth:`~squads._services._base.ServiceCore._create_core`, for a bare
          ``Service.create('role', …)`` whose ``extra`` carries no role projection at all (no
          CLI verb reaches this; ``activate_role``/``add_dev`` always pass a full
          ``role.to_extra()``);
        - :func:`~squads._roles._resolver.resolve_role_for_item`, for a role item whose backing
          definition has vanished — no catalog entry, no dev shape, no override file — where
          there is nothing left to resolve against.

        "Silent" means absent **or** blank, and blank means whitespace-only, not just the
        empty string: ``sq dev add --tech python --name "   "`` succeeded on v0.13.0 and the
        value survived every later sync, so a stored ``"   "`` is a real corpus shape and a
        truthiness test alone would carry it through to
        :class:`RoleDef.__post_init__`'s refusal — weaponising an input-side check against a
        fact this codebase itself wrote. :func:`_or_fallback` is where that is decided, once,
        for every field rather than per call site.

        Never raises for any well-formed item: ``title``/``slug`` are required, non-blank
        ``Item`` fields, so ``full_name``/``slug`` always resolve to *something*. If a title
        were somehow whitespace-only, :class:`RoleDef`'s own ``__post_init__`` still refuses it
        — as the clean :class:`~squads._errors.SquadsError` it already is, never a bare
        ``KeyError`` out of a dict subscript.
        """
        return cls(
            slug=_or_fallback(extra.get(X.SLUG), slug),
            full_name=_or_fallback(extra.get(X.FULL_NAME), title),
            title=_or_fallback(extra.get(X.TITLE), title),
            description=_or_fallback(extra.get(X.DESCRIPTION), description),
            mission=_or_fallback(extra.get(X.MISSION), description),
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
