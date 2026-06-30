"""The team playbook: which roles interact with each item type, and how.

Drives two things:
  - the per-item-type managed skills (one role-directed section per interacting role), and
  - the reverse mapping (which skills each role's Claude pointer preloads).

A role that does not interact with an item type does not get that item's skill.

The playbook data is loaded from the bundled ``playbook.toml`` via
``load_playbook()`` (ADR-000226).  All public constants/functions are thin shims
over the loaded ``PlaybookSpec`` singleton — behavior is byte-identical to the
previous hardcoded literals.
"""

from dataclasses import dataclass

from squads._interactions._loader import load_playbook
from squads._interactions._models import (
    ItemPlaybookSpec,
    PlaybookSpec,
    RoleGuideSpec,
)
from squads._models._enums import ItemType
from squads._roles._catalog import get_catalog
from squads._workflow._models import WorkflowSpec

#: Sentinel interacting "role" that expands to every developer role (slug ``<tech>-dev``).
DEV = "*dev"


@dataclass(frozen=True)
class RoleGuide:
    """Precise, structured guidance for one actor on one item type.

    Rendered under fixed labels in the per-item skill, so every actor reads the same shape:
    what to check first, what to do, what moves the work on, and what to stay out of.
    """

    slug: str  # a role slug, or the DEV sentinel
    enter: tuple[str, ...] = ()  # read/confirm before acting
    do: tuple[str, ...] = ()  # the core actions (with concrete `sq …` commands)
    handoff: tuple[str, ...] = ()  # the trigger + target that moves work on
    watch: tuple[str, ...] = ()  # scope discipline / pitfalls ("don't … — that's <role>")


@dataclass(frozen=True)
class ItemPlaybook:
    overview: str
    lifecycle: str
    commands: tuple[str, ...]
    roles: tuple[RoleGuide, ...]


def _spec_to_role_guide(rg: RoleGuideSpec) -> RoleGuide:
    return RoleGuide(
        slug=rg.slug,
        enter=tuple(rg.enter),
        do=tuple(rg.do),
        handoff=tuple(rg.handoff),
        watch=tuple(rg.watch),
    )


def spec_to_item_playbook(pb: ItemPlaybookSpec) -> ItemPlaybook:
    """Convert an ``ItemPlaybookSpec`` to the public ``ItemPlaybook`` dataclass.

    Public so golden-lock tests can verify the conversion is lossless without
    reaching for the private singleton.
    """
    return ItemPlaybook(
        overview=pb.overview,
        lifecycle=pb.lifecycle,
        commands=tuple(pb.commands),
        roles=tuple(_spec_to_role_guide(rg) for rg in pb.roles),
    )


# Keep the private alias for the existing module-level dict comprehension.
_spec_to_item_playbook = spec_to_item_playbook

# ---------------------------------------------------------------------------
# Module-level singleton — loaded once on first import.
# ---------------------------------------------------------------------------

_PLAYBOOK_SPEC: PlaybookSpec = load_playbook(get_catalog())


def get_playbook_spec() -> PlaybookSpec:
    """Return the loaded playbook singleton (public accessor for cross-module use and tests)."""
    return _PLAYBOOK_SPEC


# ---------------------------------------------------------------------------
# Public constants — backed by the singleton (behavior-identical shims).
# ---------------------------------------------------------------------------

PLAYBOOK: dict[ItemType, ItemPlaybook] = {
    t: _spec_to_item_playbook(pb) for t, pb in _PLAYBOOK_SPEC.types.items()
}

SQUADS_SKILL = "squads"
#: Always-loaded skill for the start-of-conversation ritual (detect the human, register, greet).
GREETING_SKILL = "greeting"

# ---------------------------------------------------------------------------
# Skill description registry — single source of truth (TASK-000204)
#
# Every bundled skill's description lives here exactly once.  Both the backend
# (write_managed / _write_item_skills) and the seeding/migration code read from
# this map when they set the description on the SKILL item and the .claude
# pointer.  Nothing else should hard-code these strings.
# ---------------------------------------------------------------------------

#: Slug → one-line description for each bundled skill.
SKILL_DESCRIPTIONS: dict[str, str] = {
    SQUADS_SKILL: (
        "How to track work on this project with the squads (`sq`) CLI: create/transition "
        "items, comment, link context. Use whenever you start, hand off, or update work."
    ),
    GREETING_SKILL: (
        "Start of a conversation with a human: detect & register the operator, then greet "
        "them — match their tone, say how you help, and give a quick read of the project. "
        "Use when a person opens a session; skip it when spawned as a subagent for a job."
    ),
    # sq-<type> descriptions — iterate PLAYBOOK directly (same source as managed_item_types()
    # and bundled_skill_slugs()) so the set stays in sync if a new ItemType is added to the
    # playbook (F2 — no duplicate hand-written exclusion list).
    **{
        f"sq-{item_type.value}": (
            f"Working with {item_type.value} items in this squad: "
            "lifecycle, commands, and role-specific guidance."
        )
        for item_type in PLAYBOOK
    },
}


def skill_description(slug: str) -> str:
    """Return the canonical description for a bundled skill slug.

    Falls back to the slug itself if the slug is not in the registry (should
    not happen for bundled skills, but avoids a KeyError for unknown slugs).
    """
    return SKILL_DESCRIPTIONS.get(slug, slug)


def is_dev_slug(slug: str) -> bool:
    return slug.endswith("-dev")


# ---------------------------------------------------------------------------
# Advisory sub-entity title threshold (ADR-000167 / FEAT-000166)
#
# Titles above this limit trigger an advisory warn-and-proceed message on all three
# add-* entry points (add-finding, add-subtask, add-story).  Titles at or below this
# value are silent.  Single source of truth — not .squads.toml-configurable; revisit
# only on demand.
# ---------------------------------------------------------------------------

#: Advisory threshold for sub-entity titles (characters).
#: Titles > 120 trigger a warn-and-proceed advisory; titles ≤ 120 are silent.
TITLE_ADVISORY_MAX: int = 120

# ---------------------------------------------------------------------------
# Advisory create-lane derivation (ADR-000163 / FEAT-000122 Slice B)
#
# The lane is derived from PLAYBOOK using a declarative CREATE_LANES map that is
# co-located here and asserted-equal-to-the-playbook prose in the mandatory
# table-pinning test (tests/test_lane_derivation.py).  This is the ADR §2
# fallback: prose-scanning was considered but the "sq create <type>" author verb
# is not always in the item type's own playbook section (e.g. reviewer's
# "sq create review" appears in the task playbook's reviewer guide, not in the
# review playbook's reviewer guide).  The declarative map is one source, still
# in this module, still test-locked to the playbook.
#
# ADD a new entry here when a playbook edit makes a role an in-lane author of a
# new type; the table-pinning test will fail if the two diverge.
# ---------------------------------------------------------------------------

#: Declarative create-lane map: role slug → set of item types it is in-lane to author.
#: ``DEV`` sentinel covers all ``<tech>-dev`` slugs → empty lane (devs have no sq create verbs).
#: Asserted-equal-to-the-playbook in tests/test_lane_derivation.py (table-pinning test).
CREATE_LANES: dict[str, set[ItemType]] = {
    "product-owner": {ItemType.FEATURE, ItemType.EPIC},
    "tech-lead": {ItemType.TASK},
    "architect": {ItemType.DECISION, ItemType.GUIDE},
    "reviewer": {ItemType.REVIEW},
    "qa": {ItemType.BUG},
    "tech-writer": {ItemType.GUIDE},
    DEV: set(),  # *dev sentinel: any <tech>-dev slug derives an empty lane
}

#: The union of all item types that participate in the create-lane domain.
#: Derived from CREATE_LANES (single source); types outside this set (role, skill, operator)
#: are internal artifact types that are never lane-checked.
LANED_TYPES: frozenset[ItemType] = frozenset(t for lane in CREATE_LANES.values() for t in lane)


def is_lane_exempt(slug: str) -> bool:
    """Return True for slugs that are fully exempt from all advisory lane checks.

    Exempt slugs: the ``manager`` orchestrator (authors any type for
    coordination) and any ``op-*`` operator (humans coordinate freely).
    """
    return slug == "manager" or slug.startswith("op-")


def allowed_create_types(slug: str) -> set[ItemType]:
    """Return the set of item types *slug* is in-lane to author via ``sq create``.

    Derived from :data:`CREATE_LANES`.  The ``*dev``/``DEV`` sentinel covers any
    ``<tech>-dev`` slug (empty lane).  ``manager`` and ``op-*`` slugs should be
    checked via :func:`is_lane_exempt` **before** calling this — the exemption
    is the meaningful check for those slugs; this function returns an empty set
    for them since they have no explicit entry in CREATE_LANES.
    """
    if is_dev_slug(slug):
        return set(CREATE_LANES.get(DEV, set()))
    return set(CREATE_LANES.get(slug, set()))


def in_lane_owner(item_type: str) -> set[str]:
    """Return the set of role slugs that are in-lane to create *item_type*.

    This is the inverse of :func:`allowed_create_types`: which role slug(s)
    have ``item_type`` in their derived lane.  Expands the ``*dev``/``DEV``
    sentinel using its literal slug string (not all possible tech stacks) — the
    result is used for advisory warning text, not access control.
    """
    return {slug for slug, types in CREATE_LANES.items() if item_type in types and slug != DEV}


def item_skill_name(item_type: ItemType) -> str:
    return f"sq-{item_type.value}"


def custom_item_skill_name(type_name: str) -> str:
    """Return the skill slug for a custom (non-built-in) item type."""
    return f"sq-{type_name}"


def custom_item_skill_commands(type_name: str) -> list[str]:
    """Return the standard command list for a custom item type.

    Custom types have no PLAYBOOK entry, so we emit the generic verb set
    (create, show, list, update, status, ref, comment, body, remove, retype).
    """
    return [
        f'sq create {type_name} "…" --author <slug>',
        f"sq {type_name} <n> show --full --comments",
        f"sq list -t {type_name}",
        f"sq {type_name} <n> update --status <status>",
        f"sq {type_name} <n> status <status>",
        f"sq {type_name} <n> ref add <id> [--kind <kind>]",
        f'sq {type_name} <n> comment --as <slug> -m "…"',
        f'sq {type_name} <n> body -m "…"',
        f"sq {type_name} <n> remove",
        f"sq {type_name} <n> retype <new-type>",
    ]


def custom_item_skill_description(type_name: str) -> str:
    """Return the canonical description for a custom type's skill slug."""
    return (
        f"Working with {type_name} items in this squad: "
        "lifecycle, commands, and role-specific guidance."
    )


def managed_item_types() -> list[ItemType]:
    return list(PLAYBOOK)


def item_types_for_role(slug: str) -> list[ItemType]:
    """Item types this role interacts with (DEV sentinel matches any ``*-dev`` slug)."""
    dev = is_dev_slug(slug)
    out: list[ItemType] = []
    for item_type, pb in PLAYBOOK.items():
        slugs = {g.slug for g in pb.roles}
        if slug in slugs or (dev and DEV in slugs):
            out.append(item_type)
    return out


def skills_for_role(slug: str) -> list[str]:
    """Skill names a role's pointer preloads: the always-on skills + the role's item skills."""
    return [SQUADS_SKILL, GREETING_SKILL, *(item_skill_name(t) for t in item_types_for_role(slug))]


def bundled_skill_slugs() -> list[str]:
    """All bundled skill slugs in deterministic lexical order.

    This is the **single shared ordering primitive** consumed by both ``sq init`` seeding and
    the migration (TASK-000188 / ADR-000181 decision #5).  Any code that allocates SKILL ids
    must iterate this list so migration and fresh-init assign the same relative ordinal to
    each skill (identical absolute numbers are impossible because the global counter may differ).
    """
    all_slugs = [SQUADS_SKILL, GREETING_SKILL, *(item_skill_name(t) for t in managed_item_types())]
    return sorted(set(all_slugs))


def custom_skill_slugs(spec: WorkflowSpec) -> list[str]:
    """All custom (non-built-in) type skill slugs for *spec*, in lexical order.

    Extends the FEAT-178 allocation primitive to custom types: each custom type
    declared in the spec (beyond the built-in ``ItemType`` members) gets a
    ``sq-<type>`` skill slug allocated in the same lexical-by-slug order so
    there is no churn of existing SKILL ids (AC#6).

    The returned list contains only custom type slugs (not the bundled ones
    returned by ``bundled_skill_slugs()``).  Callers that need the full merged
    set should sort ``bundled_skill_slugs() + custom_skill_slugs(spec)``
    lexically — the natural extension of ADR-000181 decision #5.
    """
    builtin_type_names: frozenset[str] = frozenset(t.value for t in ItemType)
    return sorted(
        custom_item_skill_name(ctype)
        for ctype in spec.items
        if ctype not in builtin_type_names and not spec.items[ctype].is_meta
    )
