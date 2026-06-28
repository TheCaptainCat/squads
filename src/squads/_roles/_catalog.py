"""Bundled agent-role definitions.

Each role has a real name ("Robert Architect") and a slug ("architect"); agents are referred to
by full name in files and conversation. Stack-specific developers are created on demand via
``sq dev add`` using :data:`DEV_NAME_POOL`.

The role data is loaded from the bundled ``roles.toml`` via ``load_role_catalog()`` (ADR-000221).
``RoleDef`` and all public constants/functions are thin shims over the loaded
``RoleCatalogSpec`` singleton — behavior is byte-identical to the previous hardcoded literals.
"""

from dataclasses import dataclass
from typing import Any

from squads._errors import RoleNotFoundError
from squads._models._extras import ExtraKey as X
from squads._roles._loader import load_role_catalog
from squads._roles._models import RoleCatalogSpec, RoleSpec
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

    def to_extra(self) -> dict[str, Any]:
        """Type-specific fields stored on the ROLE item."""
        return {
            X.FULL_NAME: self.full_name,
            X.SLUG: self.slug,
            X.TITLE: self.title,
            X.MISSION: self.mission,
            X.RESPONSIBILITIES: list(self.responsibilities),
            X.AGREEMENTS: list(self.agreements),
            X.MODEL: self.model,
            X.COLOR: self.color,
            X.IS_DEFAULT: self.is_default,
            X.CAN_SPAWN: self.can_spawn,
        }

    @classmethod
    def from_extra(cls, extra: dict[str, Any]) -> RoleDef:
        return cls(
            slug=extra[X.SLUG],
            full_name=extra[X.FULL_NAME],
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


def _role_spec_to_def(rs: RoleSpec) -> RoleDef:
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
PREDEFINED: tuple[RoleDef, ...] = tuple(_role_spec_to_def(rs) for rs in _CATALOG.roles)

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


def dev_role(
    tech: str, *, name: str | None = None, seq: int = 0, model: str | None = None
) -> RoleDef:
    """Build a stack-specific developer role on demand.

    If ``name`` is omitted, a first name is taken from :data:`DEV_NAME_POOL` (by ``seq``) and the
    surname is the tech (→ "Elias Dotnet"); the slug is ``<tech>-dev``.

    The name pool, default model, and default color are sourced from the loaded catalog's
    ``dev`` spec (ADR-000221 §3).  The logic is unchanged.
    """
    tech_label = tech.strip()
    surname = tech_label[:1].upper() + tech_label[1:]
    if name:
        full_name = name
    else:
        pool = DEV_NAME_POOL
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
        model=model or _CATALOG.dev.model,
        color=_CATALOG.dev.color,
    )
