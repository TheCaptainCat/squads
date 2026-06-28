"""RoleCatalogSpec pydantic v2 value objects (ADR-000221 §1).

Captures the full :class:`RoleDef` field set so the golden-lock test can
assert structural equality between the loaded TOML and today's hardcoded data.
"""

from pydantic import BaseModel, ConfigDict


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


class DevPoolSpec(BaseModel):
    """Dev-role factory inputs: the name pool and the default model/color."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name_pool: list[str]
    model: str = "sonnet"
    color: str = "green"


class RoleCatalogSpec(BaseModel):
    """The full loaded role catalog (ADR-000221 §1).

    Built by ``load_role_catalog()``; a module-level singleton is used
    everywhere via the shims in ``_catalog.py``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    roles: list[RoleSpec]  # 8 bundled roles, declaration order preserved
    bundles: dict[str, list[str]]  # all / core / minimal → slug lists
    dev: DevPoolSpec
