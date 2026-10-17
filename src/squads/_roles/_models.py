"""RoleCatalogSpec pydantic v2 value objects.

Captures the full :class:`RoleDef` field set so the golden-lock test can
assert structural equality between the loaded TOML and the hardcoded data.
"""

import re
from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict

#: The spelling of a capability name: lowercase letters, digits and hyphens, not starting with
#: a hyphen. A playbook subject ``*<name>`` uses the same pattern.
CAPABILITY_NAME_PATTERN = r"[a-z0-9][a-z0-9-]*"


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


class DevPoolSpec(BaseModel):
    """Dev-role factory inputs: the name pool and the default model/color."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name_pool: list[str]
    model: str = "sonnet"
    color: str = "green"
    capabilities: list[str] = []  # held by every templated developer


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
    dev: DevPoolSpec
    defaults: DefaultsSpec = DefaultsSpec()
