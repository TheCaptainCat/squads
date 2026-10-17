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
from squads._models import _attributes as attrs
from squads._models._attributes import AttributeKey
from squads._models._item import Item
from squads._pronouns import pronouns
from squads._roles._loader import load_role_catalog
from squads._roles._models import DevPoolSpec, RoleCatalogSpec, RoleSpec
from squads._util import slugify

#: The spelling ``sq dev add`` proposes for a developer's slug; a stored slug is never read for it.
PROPOSED_DEVELOPER_SLUG_SUFFIX = "-dev"


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
    capabilities: tuple[str, ...] = ()  # resolved from the catalog; never stored on an item
    pronouns: str | None = None  # the item's own value, else the catalog's declared default

    def __post_init__(self) -> None:
        """Refuse a blank/whitespace-only ``full_name`` at the one point every construction
        path actually goes through: the override merge (:func:`~squads._roles._resolver.
        _apply_override`, via :func:`role_spec_to_def`), ``sq role activate --name`` (via
        ``dataclasses.replace``, which re-invokes ``__post_init__`` on a frozen dataclass same
        as the constructor), and ``sq dev add --name`` (via :func:`dev_role_from_pool`'s
        constructor call). All three end in a ``RoleDef`` whose ``full_name`` is the
        operator-supplied string, so this is the single seam that closes the hole for every one
        of them at once rather than a check repeated at each call site.

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

    #: The attributes a bundled role item stores: none. A role's title, mission,
    #: responsibilities, agreements, colour and spawn authority are catalog answers resolved on
    #: every read (:func:`~squads._roles._resolver.resolve_role_for_item`), and the resolved full
    #: name lands on the item's own ``title`` field via :data:`_ITEM_FIELD_PROJECTION`; storing
    #: any of them again would be a second copy that can only go stale. ``slug`` is a core key
    #: and ``tech``/``is_default`` are each written by their own verb.
    _ATTRIBUTE_FIELDS: ClassVar[tuple[tuple[str, Callable[[RoleDef], Any]], ...]] = ()

    #: A second table in exactly :data:`_ATTRIBUTE_FIELDS`' shape, written for a **templated**
    #: role only: ``sq dev add --model`` is an operator setting with no catalog answer, and
    #: :func:`~squads._roles._resolver.dev_base_from_item` reads it straight back off the item.
    _DEV_ATTRIBUTE_FIELDS: ClassVar[tuple[tuple[str, Callable[[RoleDef], Any]], ...]] = (
        (AttributeKey.MODEL, lambda r: r.model),
    )

    #: The pairing between a resolved ``RoleDef`` field and the top-level ``Item`` field it
    #: projects onto — ``title`` from ``full_name``, ``description`` from ``mission``. Declared
    #: beside :data:`_ATTRIBUTE_FIELDS`, in the same shape, so a field that lands on a
    #: core item field (not just an attribute) can never be half-wired: the reconciler
    #: loops over :meth:`to_item_fields` exactly as it loops over :meth:`to_attributes`.
    _ITEM_FIELD_PROJECTION: ClassVar[tuple[tuple[str, Callable[[RoleDef], Any]], ...]] = (
        ("title", lambda r: r.full_name),
        ("description", lambda r: r.mission),
    )

    def to_attributes(self, *, templated: bool = False) -> dict[str, Any]:
        """The attributes stored on the ROLE item — see :data:`_ATTRIBUTE_FIELDS` for why this
        is a short list and what answers the rest.

        *templated* selects whether :data:`_DEV_ATTRIBUTE_FIELDS` (today: ``model``) is written
        too. It is a parameter rather than derived from ``self.slug`` deliberately: the shape
        lives on the *item* (it carries ``tech``), and every caller already knows which shape it
        is writing.
        """
        table = self._ATTRIBUTE_FIELDS
        if templated:
            table = (*table, *self._DEV_ATTRIBUTE_FIELDS)
        return {key: getter(self) for key, getter in table}

    def to_item_fields(self) -> dict[str, Any]:
        """Core ``Item`` fields this role's resolved definition projects onto — ``title`` from
        ``full_name``, ``description`` from ``mission``. The reconciler assigns these directly
        onto the item's own fields, mirroring :meth:`to_attributes`'s shape for a different
        destination.
        """
        return {field: getter(self) for field, getter in self._ITEM_FIELD_PROJECTION}

    @classmethod
    def stored_attribute_keys(cls, *, templated: bool) -> frozenset[str]:
        """The attribute keys :meth:`to_attributes` writes for a role of **this** shape: the key
        column of :data:`_ATTRIBUTE_FIELDS`, plus :data:`_DEV_ATTRIBUTE_FIELDS`' when *templated*.

        Reads the tables' key columns rather than an instance's output, so a value-side change
        to :meth:`to_attributes` cannot silently shrink the set.
        """
        table = cls._ATTRIBUTE_FIELDS
        if templated:
            table = (*table, *cls._DEV_ATTRIBUTE_FIELDS)
        return frozenset(key for key, _ in table)

    @classmethod
    def attribute_keys(cls) -> frozenset[str]:
        """Every key :meth:`to_attributes` can populate, for a role of any shape."""
        return cls.stored_attribute_keys(templated=True)

    @classmethod
    def from_item(cls, item: Item) -> RoleDef:
        """Build a ``RoleDef`` from a role item alone: its own ``title``/``slug``/``description``
        and the ``model``/``is_default`` attributes it stores.

        The read boundary for a role item whose backing definition has vanished (no catalog
        entry, no dev shape, no override file) and for a bare ``Service.create('role', …)``;
        there is nothing to resolve against. Never raises for a well-formed item: ``title`` and
        ``slug`` are required, non-blank ``Item`` fields.
        """
        return cls(
            slug=item.slug,
            full_name=item.title,
            title=item.title,
            description=item.description or item.title,
            mission=item.description or item.title,
            model=attrs.model(item),
            is_default=attrs.is_default(item) is True,
            pronouns=pronouns(item),
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
        capabilities=tuple(dict.fromkeys(rs.capabilities)),
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
    """Build a stack-specific developer role from the ``dev`` pool spec of the catalog the
    caller resolved (the bundled one, or a project's with its ``[dev]`` override merged in).

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
    slug = f"{slugify(tech_label)}{PROPOSED_DEVELOPER_SLUG_SUFFIX}"
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
        capabilities=tuple(dict.fromkeys(dev.capabilities)),
    )
