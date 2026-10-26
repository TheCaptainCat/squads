"""Bundled agent-role definitions.

Each role has a real name ("Robert Architect") and a slug ("architect"); agents are referred to
by full name in files and conversation. Stack-specific developers are created on demand via
``sq dev add`` from the ``dev`` role template.

The role data is loaded from the bundled ``roles.toml`` via ``load_role_catalog()``.
``RoleDef`` and all public constants/functions are thin shims over the loaded
``RoleCatalogSpec`` singleton.
"""

from dataclasses import dataclass

from squads._errors import RoleNotFoundError, SquadsError
from squads._models import _attributes as attrs
from squads._models._item import Item
from squads._pronouns import pronouns
from squads._roles._loader import VALID_MODELS, load_role_catalog
from squads._roles._models import RoleCatalogSpec, RoleSpec, RoleTemplateSpec
from squads._roles._templates import parameter_values, substitute


def stored_model(item: Item) -> str | None:
    """The model *item* stores when it is one a role may name, else ``None``: an unrenderable
    value is reported by ``sq check`` and read as unset."""
    model = attrs.model(item)
    return model if model in VALID_MODELS else None


def refuse_blank_name(name: str) -> None:
    """Raise when *name* is blank or whitespace-only: every role needs a real name."""
    if not name.strip():
        raise SquadsError(
            "role full_name is blank or whitespace-only — every role needs a real name"
        )


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
    capabilities: tuple[str, ...] = ()  # names a playbook guide addresses as ``*<name>``
    pronouns: str | None = None  # the item's own value, else the catalog's declared default

    def __post_init__(self) -> None:
        """Refuse a blank/whitespace-only ``full_name`` at the one point every construction
        path actually goes through: the override merge (:func:`~squads._roles._resolver.
        _apply_override`, via :func:`role_spec_to_def`), ``sq role activate --name`` (via
        ``dataclasses.replace``, which re-invokes ``__post_init__`` on a frozen dataclass same
        as the constructor), and ``sq dev add --name`` (via :func:`instantiate_template`'s
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
        refuse_blank_name(self.full_name)

    @classmethod
    def from_item(cls, item: Item) -> RoleDef:
        """The role a role item stores: the definition fields it holds, with its ``title`` and
        ``description`` standing in for the ones it lacks.

        The base of an item-defined role, and what a role whose base does not resolve
        materialises from. Never raises for a well-formed item: ``title`` and ``slug`` are
        required, non-blank ``Item`` fields.
        """
        name = (item.title.strip() and item.title) or item.slug
        description = item.description or name
        return cls(
            slug=item.slug,
            full_name=name,
            title=attrs.job_title(item) or name,
            description=description,
            mission=attrs.mission(item) or description,
            responsibilities=tuple(attrs.responsibilities(item) or ()),
            agreements=tuple(attrs.agreements(item) or ()),
            model=stored_model(item),
            color=attrs.color(item),
            is_default=attrs.is_default(item) is True,
            can_spawn=attrs.can_spawn(item) is True,
            capabilities=tuple(dict.fromkeys(attrs.capabilities(item) or ())),
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


def role_by_slug(slug: str) -> RoleDef:
    try:
        return _BY_SLUG[slug]
    except KeyError:
        raise RoleNotFoundError(
            f"no predefined role {slug!r} (known: {', '.join(_BY_SLUG)})"
        ) from None


def resolve_roles(spec: str, catalog: RoleCatalogSpec) -> list[RoleDef]:
    """Resolve a ``--roles`` spec against *catalog*: a bundle name, or a comma-separated list of
    the slugs its roles declare."""
    by_slug = {rs.slug: rs for rs in catalog.roles}

    def role(slug: str) -> RoleDef:
        try:
            return role_spec_to_def(by_slug[slug])
        except KeyError:
            raise RoleNotFoundError(_unknown_name(slug, spec, catalog, list(by_slug))) from None

    spec = spec.strip()
    if spec in catalog.bundles:
        return [role(s) for s in catalog.bundles[spec]]
    return [role(s) for s in (p.strip() for p in spec.split(",")) if s]


def _unknown_name(name: str, spec: str, catalog: RoleCatalogSpec, slugs: list[str]) -> str:
    """The refusal for a ``--roles`` *name* the catalog holds neither as a bundle nor as a role."""
    default = " (the --roles default)" if name == spec == "all" else ""
    hint = (
        "; it is a role template, build a role from it with `sq role activate --from`"
        if name in catalog.templates
        else ""
    )
    return (
        f"no bundle or role {name!r}{default} (bundles: {', '.join(catalog.bundles) or 'none'}; "
        f"roles: {', '.join(slugs)}){hint}"
    )


def instantiate_template(
    template: RoleTemplateSpec, *, tech: str | None, slug: str, full_name: str
) -> RoleDef:
    """The role *template* defines for *tech*, stored under *slug* and named *full_name*."""
    values = parameter_values(tech)

    def text(value: str) -> str:
        return substitute(value, values)

    return RoleDef(
        slug=slug,
        full_name=full_name,
        title=text(template.title),
        description=text(template.description),
        mission=text(template.mission),
        responsibilities=tuple(text(r) for r in template.responsibilities),
        agreements=tuple(text(a) for a in template.agreements),
        model=template.model,
        color=template.color,
        can_spawn=template.can_spawn,
        capabilities=tuple(dict.fromkeys(template.capabilities)),
    )
