"""The team playbook: which roles interact with each item type, and how.

Drives two things:
  - the per-item-type managed skills (one role-directed section per interacting role), and
  - the reverse mapping (which skills each role's Claude pointer preloads).

A role that does not interact with an item type does not get that item's skill.

The playbook data is loaded from the bundled ``playbook.toml`` via
``load_playbook()``.  All public constants/functions are thin shims over the
loaded ``PlaybookSpec`` singleton.
"""

from dataclasses import dataclass

from squads._errors import RoleNotFoundError
from squads._interactions._loader import load_playbook
from squads._interactions._models import (
    ItemPlaybookSpec,
    PlaybookSpec,
    RoleGuideSpec,
)
from squads._roles._catalog import get_catalog, role_by_slug
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

PLAYBOOK: dict[str, ItemPlaybook] = {
    t: _spec_to_item_playbook(pb) for t, pb in _PLAYBOOK_SPEC.types.items()
}

SQUADS_SKILL = "squads"
#: Always-loaded skill for the start-of-conversation ritual (detect the human, register, greet).
GREETING_SKILL = "greeting"
#: Always-loaded skill for the memory workflow + curation discipline (cross-role, not per-type).
MEMORY_SKILL = "sq-memory"

# Skill description registry — single source of truth. Both the backend (write_managed /
# _write_item_skills) and the seeding/migration code read from this map; nothing else should
# hard-code these strings.

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
    MEMORY_SKILL: (
        "Your role's committed memory notebook and the team bulletin board: check your "
        "index at the start of a run, jot one fact per memory, prune what's stale or wrong, "
        "post/clear board notices, and the memory-vs-board boundary. Use whenever you learn "
        "something worth remembering, or need to announce something to the whole team."
    ),
    # sq-<type> descriptions — iterate PLAYBOOK directly (same source as managed_item_types()
    # and bundled_skill_slugs()) so the set stays in sync if a new type is added to the
    # playbook — no duplicate hand-written exclusion list.
    **{
        f"sq-{item_type}": (
            f"Working with {item_type} items in this squad: "
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


#: Advisory threshold (characters) for sub-entity titles on add-finding/add-subtask/add-story:
#: above it, a warn-and-proceed message fires. Not .squads.toml-configurable; revisit on demand.
TITLE_ADVISORY_MAX: int = 120

# Declarative CREATE_LANES map, not prose-scanned from PLAYBOOK: the "sq create <type>" verb
# isn't always in that type's own playbook section (e.g. reviewer's "sq create review" lives
# in the task playbook's reviewer guide). Table-pinning test (tests/test_lane_derivation.py)
# fails if this map and the playbook prose diverge — add an entry here when a playbook edit
# makes a role an in-lane author of a new type.

#: Declarative create-lane map: role slug → set of item type names it is in-lane to author.
#: ``DEV`` sentinel covers all ``<tech>-dev`` slugs → empty lane (devs have no sq create verbs).
#: Asserted-equal-to-the-playbook in tests/test_lane_derivation.py (table-pinning test).
CREATE_LANES: dict[str, set[str]] = {
    "product-owner": {"feature", "epic"},
    "tech-lead": {"task"},
    "architect": {"decision", "guide"},
    "reviewer": {"review"},
    "qa": {"bug"},
    "tech-writer": {"guide"},
    DEV: set(),  # *dev sentinel: any <tech>-dev slug derives an empty lane
}

#: The union of all item types that participate in the create-lane domain.
#: Derived from CREATE_LANES (single source); types outside this set (role, skill, operator)
#: are internal artifact types that are never lane-checked.
LANED_TYPES: frozenset[str] = frozenset(t for lane in CREATE_LANES.values() for t in lane)


def is_lane_exempt(slug: str) -> bool:
    """Return True for slugs that are fully exempt from all advisory lane checks.

    Exempt slugs: the ``manager`` orchestrator (authors any type for
    coordination) and any ``op-*`` operator (humans coordinate freely).
    """
    return slug == "manager" or slug.startswith("op-")


def allowed_create_types(slug: str) -> set[str]:
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


def item_skill_name(item_type: str) -> str:
    return f"sq-{item_type}"


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


def managed_item_types() -> list[str]:
    return list(PLAYBOOK)


def item_types_for_role(slug: str) -> list[str]:
    """Item types this role interacts with (DEV sentinel matches any ``*-dev`` slug)."""
    dev = is_dev_slug(slug)
    out: list[str] = []
    for item_type, pb in PLAYBOOK.items():
        slugs = {g.slug for g in pb.roles}
        if slug in slugs or (dev and DEV in slugs):
            out.append(item_type)
    return out


def skills_for_role(slug: str) -> list[str]:
    """Skill names a role's pointer preloads: the always-on skills + the role's item skills."""
    return [
        SQUADS_SKILL,
        GREETING_SKILL,
        MEMORY_SKILL,
        *(item_skill_name(t) for t in item_types_for_role(slug)),
    ]


def bundled_skill_slugs() -> list[str]:
    """All bundled skill slugs in deterministic lexical order.

    This is the **single shared ordering primitive** consumed by both ``sq init`` seeding and
    the migration.  Any code that allocates SKILL ids must iterate this list so migration and
    fresh-init assign the same relative ordinal to each skill (identical absolute numbers are
    impossible because the global counter may differ).
    """
    all_slugs = [
        SQUADS_SKILL,
        GREETING_SKILL,
        MEMORY_SKILL,
        *(item_skill_name(t) for t in managed_item_types()),
    ]
    return sorted(set(all_slugs))


def custom_skill_slugs(spec: WorkflowSpec) -> list[str]:
    """All custom type skill slugs for *spec*, in lexical order.

    Extends the same allocation primitive to custom types: each type declared in the spec
    with no ``PLAYBOOK`` entry (F4's thin-auto-generated-skill boundary — regardless of
    whether it's a built-in or a project-declared type) gets a ``sq-<type>`` skill slug
    allocated in the same lexical-by-slug order so there is no churn of existing SKILL ids.

    The returned list contains only these types' slugs (not the bundled ones returned by
    ``bundled_skill_slugs()``).  Callers that need the full merged set should sort
    ``bundled_skill_slugs() + custom_skill_slugs(spec)`` lexically.
    """
    return sorted(
        custom_item_skill_name(ctype)
        for ctype in spec.items
        if ctype not in PLAYBOOK and not spec.items[ctype].is_meta
    )


def is_system_skill(slug: str, spec: WorkflowSpec) -> bool:
    """Whether *slug* names a template-owned skill (bundled or a per-type ``sq-<type>``).

    A pure function of the slug and the active spec — derived, not stored, so a project
    that renames/drops a type re-derives cleanly. Any SKILL slug outside this union is
    author-defined ("custom").
    """
    return slug in bundled_skill_slugs() or slug in custom_skill_slugs(spec)


# Role -> type authoring prose: the "who authors what" cheatsheet (workflow.md.j2) renders
# from CREATE_LANES + the role catalog (title lookup) + the WorkflowSpec (prefix, parent
# chain, sub-entity kind) — so a project-added custom type is surfaced generically.
#
# CREATE_LANES is a fixed bundled-role map with no override mechanism for custom roles
# authoring custom types; a custom type with no lane owner just gets no authoring bullet
# (see custom_item_skill_commands for its generic command surface).


def authoring_owner(item_type: str) -> tuple[str, str] | None:
    """The (slug, display title) of the single in-lane role that authors *item_type*.

    *item_type* is the plain type-name string (e.g. ``"feature"``, ``"task"`` — the
    same string keys ``spec.items`` and the template loop over them use).

    Returns ``None`` when the type has no lane owner, more than one (ambiguous), or
    the owner has no bundled catalog entry (e.g. a ``<tech>-dev`` slug) — the generic
    cheatsheet line is skipped rather than guessing.
    """
    owners = in_lane_owner(item_type)
    if len(owners) != 1:
        return None
    (slug,) = owners
    try:
        return slug, role_by_slug(slug).title
    except RoleNotFoundError:
        # e.g. the *dev sentinel or an as-yet-uncataloged slug: no bundled title to show.
        return None


def parent_chain(spec: WorkflowSpec, item_type: str) -> list[str]:
    """Walk *item_type*'s single-parent chain up to its root, e.g. ``task`` ->

    ``["epic", "feature", "task"]``. Stops (without erroring) on multi-parent or
    cyclical configurations — returns just ``[item_type]`` in that case, since the
    cheatsheet only renders a hierarchy line for a clean linear chain.
    """
    chain = [item_type]
    seen = {item_type}
    current = item_type
    while True:
        parents = spec.items[current].parents
        if len(parents) != 1 or parents[0] in seen:
            break
        current = parents[0]
        chain.insert(0, current)
        seen.add(current)
    return chain
