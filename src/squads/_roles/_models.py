"""RoleCatalogSpec pydantic v2 value objects.

Captures the full :class:`RoleDef` field set so the golden-lock test can
assert structural equality between the loaded TOML and the hardcoded data.
"""

import re
from collections.abc import Callable, Iterable

from pydantic import BaseModel, ConfigDict

#: The spelling of a capability name: lowercase letters, digits and hyphens, not starting with
#: a hyphen. A playbook subject ``*<name>`` uses the same pattern.
CAPABILITY_NAME_PATTERN = r"[a-z0-9][a-z0-9-]*"

#: The one capability the engine reads: the roles holding it author the type the review gate names.
REVIEW_CAPABILITY = "review"


def malformed_capability_names(names: Iterable[str]) -> list[str]:
    """The entries of *names* that do not match :data:`CAPABILITY_NAME_PATTERN`, in order."""
    return [n for n in names if re.fullmatch(CAPABILITY_NAME_PATTERN, n) is None]


class RoleSpec(BaseModel):
    """Spec for a single bundled agent role — mirrors the :class:`RoleDef` field set exactly."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    slug: str
    full_name: str
    title: str
    description: str  # one-liner for the Claude pointer frontmatter
    mission: str
    responsibilities: list[str] = []
    agreements: list[str] = []
    model: str | None = None  # sonnet | opus | haiku | inherit
    color: str | None = None
    is_default: bool = False
    can_spawn: bool = False  # True only for orchestrating roles (manager, tech-lead)
    capabilities: list[str] = []  # names a playbook guide addresses as ``*<name>``


class RoleTemplateSpec(BaseModel):
    """One ``[templates.<name>]`` table of the role catalog: a role definition with placeholders,
    instantiated into a role by ``sq role activate --from <name>``.

    The definition keys mean what they mean on a ``[[roles]]`` entry; ``slug``, ``name`` and
    ``name_pool`` are the template's own."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    slug: str | None = None  # the proposed slug pattern
    name: str | None = None  # the name pattern; ``{first}`` draws from ``name_pool``
    name_pool: list[str] = []
    title: str
    description: str
    mission: str
    responsibilities: list[str] = []
    agreements: list[str] = []
    model: str | None = None  # sonnet | opus | haiku | inherit
    color: str | None = None
    can_spawn: bool = False
    capabilities: list[str] = []  # names a playbook guide addresses as ``*<name>``


#: The template ``sq dev add`` instantiates, and whose capabilities define a developer.
DEV_TEMPLATE_NAME = "dev"


class DefaultsSpec(BaseModel):
    """The ``[defaults]`` table of the role catalog document: roster-wide values a role resolves
    when it holds none of its own."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pronouns: str | None = None


class RoleCatalogSpec(BaseModel):
    """The full loaded role catalog.

    Built by ``load_role_catalog()``; a module-level singleton is used
    via the shims in ``_catalog.py``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    roles: list[RoleSpec]  # 8 bundled roles, declaration order preserved
    bundles: dict[str, list[str]]  # all / core / minimal → slug lists
    templates: dict[str, RoleTemplateSpec] = {}
    defaults: DefaultsSpec = DefaultsSpec()

    def developer_capabilities(self) -> frozenset[str]:
        """The capabilities the ``dev`` template declares; empty when the squad dropped it."""
        template = self.templates.get(DEV_TEMPLATE_NAME)
        return frozenset(template.capabilities) if template is not None else frozenset()


#: A role catalog resolved on demand: calling it returns the catalog the squad resolves, built
#: once and kept by whoever owns it, so a caller that never asks never reads a roles override.
type CatalogSource = Callable[[], RoleCatalogSpec]
