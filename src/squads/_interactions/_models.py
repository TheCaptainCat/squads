"""PlaybookSpec pydantic v2 value objects.

Captures the full ``ItemPlaybook``/``RoleGuide`` field set so the golden-lock
test can assert structural equality between the loaded TOML and the hardcoded
data.  ``extra="forbid"`` on all models so a TOML typo errors immediately
rather than silently reverting to a default.
"""

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict


class RoleGuideSpec(BaseModel):
    """Guidance for one actor on one item type — mirrors :class:`RoleGuide` exactly."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    slug: str  # a role slug, or the "*dev" DEV sentinel
    enter: list[str] = []  # read/confirm before acting
    do: list[str] = []  # core actions (with concrete `sq …` commands)
    handoff: list[str] = []  # trigger + target that moves work on
    watch: list[str] = []  # scope discipline / pitfalls
    authors: bool = False
    """This role is an in-lane **author** of the type this guide hangs under — the declared
    create-lane, and the only source of it.

    Declared rather than inferred from the guide's prose. The lane used to live in a separate
    hand-maintained slug→type map beside the playbook, which meant an adopter who added an
    authoring guide through ``.overrides/playbook.toml`` got a generated skill telling them to
    run the create command and an advisory saying they were not the in-lane author for it. It
    also drifted from the prose it was supposed to mirror: nothing checked the two agreed,
    because the map was pinned to a literal table instead of to this document.

    Defaults ``False``, so a guide that only reads/triages/verifies a type declares nothing —
    including the ``*dev`` sentinel, whose lane is empty by declaration rather than by a
    special case."""


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

    # Mapping, not dict: ``frozen=True`` blocks reassigning this attribute, but a dict-typed
    # field is still a plain, mutable dict at runtime — ``spec.types["x"] = ...`` would succeed
    # and corrupt every holder of this spec (the bundled singleton included) process-wide.
    # ``Mapping`` has no ``__setitem__``, so that same statement is a pyright error instead —
    # every read site here (``.items()``, ``.keys()``, indexing, ``in``) is unaffected.
    types: Mapping[str, ItemPlaybookSpec]  # keyed by item-type name; work types only
