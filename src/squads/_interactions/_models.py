"""PlaybookSpec pydantic v2 value objects.

Captures the full ``ItemPlaybook``/``RoleGuide`` field set so the golden-lock
test can assert structural equality between the loaded TOML and the hardcoded
data.  ``extra="forbid"`` on all models so a TOML typo errors immediately
rather than silently reverting to a default.
"""

from pydantic import BaseModel, ConfigDict


class RoleGuideSpec(BaseModel):
    """Guidance for one actor on one item type — mirrors :class:`RoleGuide` exactly."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    slug: str  # a role slug, or the "*dev" DEV sentinel
    enter: list[str] = []  # read/confirm before acting
    do: list[str] = []  # core actions (with concrete `sq …` commands)
    handoff: list[str] = []  # trigger + target that moves work on
    watch: list[str] = []  # scope discipline / pitfalls


class ItemPlaybookSpec(BaseModel):
    """Playbook entry for one item type — mirrors :class:`ItemPlaybook` exactly."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    overview: str
    lifecycle: str  # human lifecycle line, e.g. "Draft → Ready → … (+ Blocked)"
    commands: list[str]
    roles: list[RoleGuideSpec]  # ORDERED — section order in the generated skill is significant


class PlaybookSpec(BaseModel):
    """The full loaded playbook specification.

    Built by ``load_playbook()``; a module-level singleton is used via the
    shims in ``_interactions/__init__.py``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    types: dict[str, ItemPlaybookSpec]  # keyed by item-type name; work types only
