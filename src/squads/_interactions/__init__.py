"""The team playbook: which roles interact with each item type, and how.

Drives two things:
  - the per-item-type managed skills (one role-directed section per interacting role), and
  - the reverse mapping (which skills each role's Claude pointer preloads).

A role that does not interact with an item type does not get that item's skill.

The playbook data is loaded from the bundled ``playbook.toml`` via
``load_playbook()``.  All public constants/functions are thin shims over the
loaded ``PlaybookSpec`` singleton.

Membership is spec-driven and checked (a type the active workflow spec does not declare has no
entry and no skill); guide **prose** is not, and a surviving type's guidance can go on naming a
type that a workflow override dropped or renamed. See ``_loader``'s module docstring for the full
statement of that limitation and its remedy — the two halves are deliberately scoped apart, and
only the first is enforced.
"""

from collections.abc import Container, Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TypedDict

from squads import _badges as badges
from squads._errors import RoleNotFoundError
from squads._interactions._loader import load_playbook
from squads._interactions._models import (
    ItemPlaybookSpec,
    PlaybookSpec,
    RoleGuideSpec,
)
from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._roles._catalog import get_catalog, role_by_slug
from squads._workflow import bundled_spec
from squads._workflow._models import ROSTER_ROLE, ROSTER_SKILL, Field, WorkflowSpec

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
    authors: bool = False  # in-lane author of this guide's type — see RoleGuideSpec.authors


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
        authors=rg.authors,
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
    """Return the bundled playbook singleton (public accessor for cross-module use and tests).

    Always the bundled document, regardless of any project override. The per-request merged
    playbook (bundled base + any ``.overrides/playbook.toml``) is carried on ``Service.playbook``
    instead — the single carrier for that fact; every production consumer here that needs the
    active/merged view takes it as an explicit ``playbook`` parameter (defaulting to this
    singleton) rather than reading it off an ambient context. Kept name-stable for existing
    callers/tests; nothing about this changed.
    """
    return _PLAYBOOK_SPEC


# ---------------------------------------------------------------------------
# Public constants — backed by the singleton (behavior-identical shims).
# ---------------------------------------------------------------------------

#: A ``MappingProxyType``, not a plain ``dict`` — this is a module-level CODE constant (the
#: bundled document, shared process-wide), and a plain dict is mutable at runtime regardless of
#: its annotation: ``PLAYBOOK["x"] = ...`` would succeed silently and corrupt every caller's
#: view. The proxy makes that a ``TypeError`` at the mutation site instead of a convention
#: nothing enforces — the same guarantee :class:`~squads._interactions._models.PlaybookSpec`'s
#: ``types`` field gets from its ``Mapping`` annotation, but real at runtime here since this
#: constant is never validated through pydantic.
PLAYBOOK: Mapping[str, ItemPlaybook] = MappingProxyType(
    {t: _spec_to_item_playbook(pb) for t, pb in _PLAYBOOK_SPEC.types.items()}
)

SQUADS_SKILL = "squads"
#: Always-loaded skill for the start-of-conversation ritual (detect the human, register, greet).
GREETING_SKILL = "greeting"
#: Always-loaded skill for the memory workflow + curation discipline (cross-role, not per-type).
MEMORY_SKILL = "sq-memory"

# Skill description registry — single source of truth. Both the backend (write_managed /
# _write_item_skills) and the seeding/migration code read from this map; nothing else should
# hard-code these strings.

#: Slug → one-line description for each of the three always-on cross-role skills. A per-type
#: ``sq-<type>`` description is never looked up here — it is generated on the fly by
#: :func:`skill_description`, from the same template :func:`custom_item_skill_description` uses,
#: so a type gaining playbook coverage through a project override (moving it from the "custom,
#: thin skill" bucket to the "rich, PLAYBOOK-backed" one at render time) needs no entry added
#: here to get a correct description — the two buckets' descriptions were always the same string
#: for the same type name, keyed off the type only, never off playbook content.
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
}


def skill_description(slug: str) -> str:
    """Return the canonical description for a bundled or ``sq-<type>`` skill slug.

    The three always-on skills come from :data:`SKILL_DESCRIPTIONS`; any other ``sq-<type>``
    slug gets the generic per-type description computed from its type name — the same template
    :func:`custom_item_skill_description` uses, so this needs no playbook-derived lookup table
    to stay correct for a type a project override newly covers. Falls back to the slug itself
    for anything not shaped like ``sq-<type>`` (should not happen for a real skill slug, but
    avoids ever raising for an unknown one).
    """
    if slug in SKILL_DESCRIPTIONS:
        return SKILL_DESCRIPTIONS[slug]
    if slug.startswith("sq-"):
        return custom_item_skill_description(slug.removeprefix("sq-"))
    return slug


def is_dev_slug(slug: str) -> bool:
    return slug.endswith("-dev")


#: Advisory threshold (characters) for sub-entity titles on add-finding/add-subtask/add-story:
#: above it, a warn-and-proceed message fires. Not .squads.toml-configurable; revisit on demand.
TITLE_ADVISORY_MAX: int = 120

# The advisory create-lane is DERIVED from the playbook document, per role guide, from the
# declared `authors` flag — never from a second table beside it, and never scanned out of the
# guide's prose. A prose scan was rejected for the reason the flag exists: the create verb for a
# type does not always live in that type's own section (the reviewer's `sq create review` is
# written in the task playbook's reviewer guide), so the scan has to match across sections and
# still misses a role whose guidance never spells the verb. A declaration says it once, in the
# document an adopter can override.


def create_lanes(playbook: PlaybookSpec | None = None) -> dict[str, set[str]]:
    """Role slug → the set of item types that slug is in-lane to author, derived from the
    role guides of *playbook* (defaulting to the bundled singleton) that declare ``authors``.

    Computed per call rather than cached in a module constant: the answer depends on the
    active/merged playbook, and a process serves many squads. The ``DEV`` sentinel appears
    here only if some guide declares it an author — the bundled document never does, so a
    ``<tech>-dev`` slug derives an empty lane by declaration, not by a special case.
    """
    active = playbook if playbook is not None else _PLAYBOOK_SPEC
    lanes: dict[str, set[str]] = {}
    for item_type, entry in active.types.items():
        for guide in entry.roles:
            if guide.authors:
                lanes.setdefault(guide.slug, set()).add(item_type)
    return lanes


def laned_types(playbook: PlaybookSpec | None = None) -> frozenset[str]:
    """The item types that participate in the create-lane domain at all — every type some
    guide in *playbook* declares an author for.

    A function, not a module constant: computed once at import off the bundled document, a
    renamed or project-declared type could never enter the domain, so the lane check
    short-circuited and lane discipline went dark for every type an adopter declared.
    """
    return frozenset(t for lane in create_lanes(playbook).values() for t in lane)


def is_lane_exempt(slug: str, default_slug: str | None = None) -> bool:
    """Return True for slugs that are fully exempt from all advisory lane checks.

    Exempt: the squad's **default role** — the orchestrator that authors any type for
    coordination — and any ``op-*`` operator (humans coordinate freely). The default role is
    resolved from *default_slug* when the caller has the live roster in hand, otherwise from
    the role catalog's own ``is_default`` designation; it is never a hard-coded slug, so a
    squad that renamed or reassigned its coordinator keeps the exemption where it declared it.
    """
    if slug.startswith("op-"):
        return True
    resolved = default_slug if default_slug is not None else catalog_default_slug()
    return resolved is not None and slug == resolved


def catalog_default_slug() -> str | None:
    """The bundled role catalog's ``is_default`` slug, or ``None`` if none is designated."""
    return next((r.slug for r in get_catalog().roles if r.is_default), None)


def allowed_create_types(
    slug: str, spec: WorkflowSpec | None = None, playbook: PlaybookSpec | None = None
) -> set[str]:
    """Return the set of item types *slug* is in-lane to author via ``sq create``.

    Derived from :func:`create_lanes` over *playbook*.  The ``*dev``/``DEV`` sentinel covers
    any ``<tech>-dev`` slug.  The default role and ``op-*`` slugs should be checked via
    :func:`is_lane_exempt` **before** calling this — the exemption is the meaningful check for
    those slugs; this function answers only what the playbook declares for them.

    ``spec`` mirrors :func:`item_types_for_role`'s own membership filter: a type a guide still
    names that *spec* has dropped (via ``[selected]``, or renamed away to a new key) is
    filtered out here — a role's advertised create-lane never keeps naming a type that no
    longer exists.

    Both default to the bundled documents (``None``) for callers with no live squad in hand
    (tests, any call before a spec is resolved); production call sites thread the
    active/merged spec and playbook explicitly.
    """
    active_spec = spec if spec is not None else bundled_spec()
    lanes = create_lanes(playbook)
    lane = lanes.get(DEV, set()) if is_dev_slug(slug) else lanes.get(slug, set())
    return {t for t in lane if t in active_spec.items}


def in_lane_owner(item_type: str, playbook: PlaybookSpec | None = None) -> set[str]:
    """Return the set of role slugs that are in-lane to create *item_type*.

    This is the inverse of :func:`allowed_create_types`: which role slug(s)
    have ``item_type`` in their derived lane.  Expands the ``*dev``/``DEV``
    sentinel using its literal slug string (not all possible tech stacks) — the
    result is used for advisory warning text, not access control.
    """
    return {
        slug for slug, types in create_lanes(playbook).items() if item_type in types and slug != DEV
    }


def item_skill_name(item_type: str) -> str:
    return f"sq-{item_type}"


def custom_item_skill_name(type_name: str) -> str:
    """Return the skill slug for a custom (non-built-in) item type."""
    return f"sq-{type_name}"


def cheatsheet_anchor_type(spec: WorkflowSpec) -> str | None:
    """The single non-roster type used to build a "Common commands" example block (the
    squads skill, AGENTS.md) — chosen generically from *spec* so a squad that drops or
    renames the type this block used to hardcode (``"task"``) still gets a fully runnable,
    representative example instead of one built from a type that no longer exists.

    Scored by how much of the example surface a type can actually demonstrate: a
    sub-entity kind (for ``add-<kind>``), a required parent (for ``--parent``), and an
    ordered badge field (for ``--priority``-shaped metadata) each add a point. The
    highest-scoring type wins; ties break by declared registration order
    (``ItemSpec.order``, then type name) for determinism — on the bundled spec this
    reproduces ``"task"`` exactly, since it's the only type that scores on all three axes.

    ``None`` only when *spec* has no non-roster type at all (every work/records type
    dropped) — there is nothing left to anchor an example on.
    """
    types = sorted(spec.non_roster_types(), key=lambda t: (spec.items[t].order, t))
    if not types:
        return None

    def score(item_type: str) -> int:
        points = 0
        if spec.item_subentity_kind(item_type):
            points += 1
        if spec.item_parent_required(item_type):
            points += 1
        if any(spec.collection(f.collection).ordered for f in spec.fields_for(item_type)):
            points += 1
        return points

    best = max(score(t) for t in types)
    return next(t for t in types if score(t) == best)


class CheatsheetAnchorContext(TypedDict):
    """Return shape of :func:`cheatsheet_anchor_context` — see there for what each key means."""

    anchor: str | None
    anchor_prefix: str
    anchor_kind: str | None
    anchor_parent_prefix: str | None
    anchor_active: str | None
    anchor_settled: str | None
    priority_field: Field | None
    priority_values: list[str]


def cheatsheet_anchor_context(spec: WorkflowSpec) -> CheatsheetAnchorContext:
    """Bundle of spec-derived values a "Common commands" example block needs to build a
    fully runnable, representative example: the anchor type
    (:func:`cheatsheet_anchor_type`) plus everything about it an example command might
    show — its prefix, sub-entity kind, required-parent prefix, first active/settled
    status — and the ordered "priority" field/values any surviving type carries (never
    just the anchor's own, since :func:`squads._badges.first_ordered_field` scans every
    type — see its docstring for why one type can't be trusted to answer for all of them).

    Shared by the squads skill and AGENTS.md templates (registered as a Jinja global) and
    by the ``agents_md`` backend's Python-side ``also_creatable_types`` computation, so
    the two render paths derive this from one place rather than independently.

    Every value degrades to ``None`` (or, where a string is unavoidable in-line, a
    generic placeholder like ``"TYPE"``) when *spec* has no non-roster type left to
    anchor on at all.
    """
    anchor = cheatsheet_anchor_type(spec)
    anchor_parent = spec.item_parent_required(anchor) if anchor else None
    priority_field = badges.first_ordered_field(spec)
    return {
        "anchor": anchor,
        "anchor_prefix": spec.items[anchor].prefix if anchor else "TYPE",
        "anchor_kind": spec.item_subentity_kind(anchor) if anchor else None,
        "anchor_parent_prefix": (spec.items[anchor_parent].prefix if anchor_parent else None),
        "anchor_active": spec.first_active_status(anchor) if anchor else None,
        "anchor_settled": spec.first_settled_status(anchor) if anchor else None,
        "priority_field": priority_field,
        "priority_values": (
            [b.code for b in spec.collection(priority_field.collection).badges]
            if priority_field
            else []
        ),
    }


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


def managed_item_types(playbook: PlaybookSpec | None = None) -> list[str]:
    """Item types with a rich, role-guidance-bearing playbook entry.

    ``playbook`` defaults to the bundled singleton (``None``) — same contract as every other
    function here: tests and any call before a per-request playbook is resolved get the bundled
    view; a production call site (skill generation, seeding order) threads the active/merged
    playbook (``Service.playbook``) explicitly so a project override's added/removed type
    coverage is reflected.
    """
    active = playbook if playbook is not None else _PLAYBOOK_SPEC
    return list(active.types)


def item_types_for_role(
    slug: str, spec: WorkflowSpec | None = None, playbook: PlaybookSpec | None = None
) -> list[str]:
    """Item types this role interacts with (DEV sentinel matches any ``*-dev`` slug).

    ``playbook`` (defaulting to the bundled singleton) is a keyed-by-built-in-type-name view
    with no override mechanism of its own *unless the caller threads the merged one* — passing
    the active/merged playbook is what lets a project-added role guide or project-added type
    entry actually change a role's interacting-type list; passing nothing (the bundled default)
    reproduces today's behaviour exactly. Independent of that: a type the playbook still names
    but *spec* has dropped (via ``[selected]``, directly, or by renaming it away to a new key)
    is filtered out here, so a role's preload list never keeps naming a type that no longer
    exists. A type *spec* declares that has no playbook entry at all — a project-declared custom
    type with no override coverage, or the new name a rename produced — contributes nothing
    here (there is no interaction data to derive from), the same "no preload, but the thin
    auto-generated skill still exists and is still loadable by hand" degradation any custom type
    already gets.

    ``spec`` defaults to the bundled spec (``None``) for callers with no live squad in hand
    (tests, and any call before a spec is resolved); every production call site threads the
    active/merged spec explicitly.
    """
    active_spec = spec if spec is not None else bundled_spec()
    active_playbook = playbook if playbook is not None else _PLAYBOOK_SPEC
    dev = is_dev_slug(slug)
    out: list[str] = []
    for item_type, pb in active_playbook.types.items():
        if item_type not in active_spec.items:
            continue
        slugs = {g.slug for g in pb.roles}
        if slug in slugs or (dev and DEV in slugs):
            out.append(item_type)
    return out


def skills_for_role(
    slug: str, spec: WorkflowSpec | None = None, playbook: PlaybookSpec | None = None
) -> list[str]:
    """Skill names a role's pointer preloads: the always-on skills + the role's item skills.

    See :func:`item_types_for_role` for how *spec*/*playbook* keep this list correct — a
    dropped/renamed type's skill never lingers, and a project override's guidance changes are
    reflected once the caller threads the active/merged playbook.
    """
    return [
        SQUADS_SKILL,
        GREETING_SKILL,
        MEMORY_SKILL,
        *(item_skill_name(t) for t in item_types_for_role(slug, spec, playbook)),
    ]


def bundled_skill_slugs() -> list[str]:
    """All bundled skill slugs in deterministic lexical order.

    This is the **single shared ordering primitive** consumed by both ``sq init`` seeding and
    the migration.  Any code that allocates SKILL ids must iterate this list so migration and
    fresh-init assign the same relative ordinal to each skill (identical absolute numbers are
    impossible because the global counter may differ).

    Deliberately, unconditionally **bundled-blind** — no ``playbook`` parameter at all, not even
    an optional one a caller could thread the active/merged value into. This is the exact
    property :func:`is_system_skill`'s reclaim logic depends on: a type dropped or renamed via a
    workflow override is filtered OUT of the *merged* playbook by design (coverage must not see
    it as an "extra" entry — see ``_interactions._loader._base_raw_for``), so a caller-supplied
    merged playbook here would make a renamed-away built-in's stale ``sq-<type>`` skill
    invisible to every check built on this list, exactly the "outlives the type it described"
    failure the design note below already warns against. The seeding call site
    (``seed_bundled_skills``) does not need the merged playbook either — a type it excludes
    already produced no body file for ``refresh_managed()`` to seed, so the seeding loop's own
    ``legacy_path.is_file()`` gate is the real filter regardless of what this list enumerates.
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
    with no *bundled* playbook entry (the thin-auto-generated-skill boundary — regardless of
    whether it's a built-in or a project-declared type) gets a ``sq-<type>`` skill slug
    allocated in the same lexical-by-slug order so there is no churn of existing SKILL ids.

    Deliberately checked against the bundled ``PLAYBOOK``/``_PLAYBOOK_SPEC``, never a
    caller-supplied merged one — see :func:`bundled_skill_slugs`'s docstring for why: a
    project-declared type is never in the bundled document regardless of whether it has
    override coverage, so this enumeration is already correct (and stable) without knowing
    about the override at all. Its generated CONTENT (rich vs. thin) is decided entirely by
    :func:`managed_item_types` at the point that actually needs the merged playbook
    (the backend's per-type skill writer); this function only decides *seeding order*.

    The returned list contains only these types' slugs (not the bundled ones returned by
    :func:`bundled_skill_slugs`).  Callers that need the full merged set should sort
    ``bundled_skill_slugs() + custom_skill_slugs(spec)`` lexically.
    """
    return sorted(
        custom_item_skill_name(ctype)
        for ctype in spec.items
        if ctype not in PLAYBOOK and spec.items[ctype].category != "roster"
    )


def active_skill_slugs(spec: WorkflowSpec) -> frozenset[str]:
    """Every ``sq-<type>`` skill slug *spec* should currently have, plus the three always-on
    cross-role skills — the orphan-detection vocabulary now that a type can be dropped, renamed,
    or re-prefixed: unlike
    ``bundled_skill_slugs() | custom_skill_slugs(spec)`` (each an *allocation-order* primitive
    for ``sq init``/``sq sync`` seeding, deliberately covering every historically-bundled slug
    regardless of the active spec), this is the set that should exist *right now*. A dropped or
    renamed built-in's old ``sq-<type>`` slug is not in it — reusing it for orphan detection
    would keep exempting a stale skill from ever being flagged, silently outliving the type it
    described.

    ``item_skill_name``/``custom_item_skill_name`` are the identical ``f"sq-{type}"`` naming
    scheme either way, so one loop over ``spec.items`` covers both a rich (PLAYBOOK-backed) and
    a thin (custom) skill — there is no "built-in vs custom" split at the slug-naming layer,
    only at the *content* layer (``_write_item_skills``).
    """
    return frozenset(
        {SQUADS_SKILL, GREETING_SKILL, MEMORY_SKILL}
        | {item_skill_name(t) for t, ts in spec.items.items() if ts.category != "roster"}
    )


def is_system_skill(slug: str, spec: WorkflowSpec) -> bool:
    """Whether *slug* names a template-owned skill (bundled or a per-type ``sq-<type>``).

    A pure function of the slug and the active spec — derived, not stored, so a project
    that renames/drops a type re-derives cleanly. Any SKILL slug outside this union is
    author-defined ("custom").

    Deliberately bundled-blind on the built-in half (``bundled_skill_slugs()`` takes no
    *spec*, and no *playbook* either — not even optionally): this is the allocation-order/
    no-hand-editing membership test, not the "is this still on offer right now" test — a
    dropped or renamed built-in's stale skill is still a template-owned file nobody should
    hand-edit, and still stays out of the seeding order's churn. Use
    :func:`orphaned_skill_item_type` for "should this per-type skill still be materialised
    today". No ``playbook`` parameter here at all — passing the *merged* playbook into
    :func:`bundled_skill_slugs` would defeat exactly the bundled-blindness this function
    depends on: a workflow-override-renamed built-in's OLD name is filtered out of the merged
    playbook by design (coverage must not see it as a stray "extra" entry), so a caller-supplied
    merged value here would make the renamed-away slug invisible to reclaim, letting its stale
    file silently outlive the type it described — the one failure mode this check exists to
    prevent.
    """
    return slug in bundled_skill_slugs() or slug in custom_skill_slugs(spec)


def orphaned_skill_item_type(slug: str, spec: WorkflowSpec) -> str | None:
    """The item type a ``sq-<type>`` skill slug used to name, when *spec* no longer declares
    that type at all — ``None`` when *slug* is still current, was never a per-type skill at
    all, or names a type this call has no evidence it was ever generated for.

    The single membership test that decides whether a per-type skill's generated
    pointer/body should still be materialised (see ``ServiceCore._project_roster_item``) and
    whether ``sq check`` should flag a live one. Gated on :func:`is_system_skill` — the
    template-owned membership test — rather than the ``sq-`` prefix alone: the prefix is not
    reserved to squads, so an author-created skill named e.g. ``sq-onboarding`` is a real,
    live skill that happens to share the house naming convention, not the residue of a type
    that used to exist. ``is_system_skill`` stays bundled-blind on its built-in half (a
    dropped or renamed *built-in*'s stale ``sq-<type>`` is still reclaimed — it was always a
    template-owned slug, active spec or not), so that case keeps working exactly as before;
    the trade-off is a dropped *custom* type's skill no longer self-identifies here, since a
    custom type leaving the spec also removes its slug from ``custom_skill_slugs`` and this
    function has no other record that the skill was ever generated rather than authored.

    Pure and reversible by construction: nothing here is stored, so restoring the type to
    *spec* makes this return ``None`` again on the very next call — no separate undo step,
    the same way the type's own drop needed none.
    """
    if slug in active_skill_slugs(spec):
        return None
    if slug in (SQUADS_SKILL, GREETING_SKILL, MEMORY_SKILL):
        return None
    if not is_system_skill(slug, spec):
        return None
    return slug.removeprefix("sq-")


def is_live_roster_entry(item: Item, spec: WorkflowSpec) -> bool:
    """Whether *item* (a ``role`` or ``skill`` roster item) currently should have a
    materialised per-entry backend artifact — the same two-clause predicate
    ``ServiceCore._project_roster_item`` (:mod:`squads._services._base`) already applies
    while materialising/withdrawing, extracted here so that caller and every other reader of
    "is this roster entry live" — ``sq check``'s ``backend_reconciled`` rule and ``sync``'s
    own before/after regeneration report (both in :mod:`squads._services`) — derive it from
    this one function instead of growing a second, separately-maintained notion of the same
    fact. ``False`` for any other item type (an operator, or an ordinary work item, has no
    per-entry backend artifact at all).

    Two clauses, both required for a ``SKILL`` item, only the first for a ``ROLE`` item:

    - the item's own status carries the type's ``live`` flag
      (:meth:`WorkflowSpec.live_statuses`); and
    - for a ``SKILL`` item only, its slug still names a type the active spec declares
      (:func:`orphaned_skill_item_type` returns ``None``) — a dropped or renamed built-in's
      stale ``sq-<type>`` skill is withdrawn right alongside a manually-retired one, with no
      separate mechanism. Miss this clause and a squad whose workflow override dropped a type
      reports a permanent false positive no ``sq sync`` can clear.

    Pure: reads only *item* and *spec*, no index, no filesystem — safe for a backend-context
    caller that must not load the index itself.
    """
    if item.type not in (ROSTER_ROLE, ROSTER_SKILL):
        return False
    live = item.status in spec.live_statuses(item.type)
    if item.type == ROSTER_SKILL and live:
        slug = item.extra.get(X.SLUG, "")
        live = orphaned_skill_item_type(slug, spec) is None
    return live


def orphaned_playbook_guides(
    playbook: PlaybookSpec,
    spec: WorkflowSpec,
    *,
    live_role_slugs: Container[str],
    override_guides: Container[tuple[str, str]],
) -> list[tuple[str, str]]:
    """Every ``(item_type, role_slug)`` playbook guide the generated ``sq-<type>`` skill will
    **silently drop**, because *role_slug* names no live role **and** the adopter is the one who
    wrote the guide.

    The playbook loader's slug authority is deliberately permissive — the bundled catalog union
    whatever ``.overrides/roles/*.toml`` files exist, read by filename because those files must
    be readable before the index is (coupling the loader to the roster would refuse every guide
    in a squad whose index is mid-repair). The *renderer* is not permissive: it gates each guide
    on live roster membership and drops the rest with ``continue``. Where the two sets differ the
    adopter's guidance evaporates with nothing reported, so this is the predicate that reports
    it — the loader stays permissive and ``check``/``sync`` carry the news, which is also where
    the skill side of the same event is already reported.

    Three shapes reach it, all driven: a role scaffolded but not yet activated (``sq override
    scaffold --new <slug>`` prints activation as its *next* step, so writing the guide first is
    the natural order); a role activated and later retired, the guide left behind; and a stray or
    malformed file in ``.overrides/roles/`` whose stem the loader accepts as a slug but which
    never becomes a role at all.

    Two exemptions, both deliberate:

    * the ``*dev`` sentinel — it means "any ``<tech>-dev`` role", and rendering it is already
      conditioned on the roster having one (``has_dev``);
    * a guide whose ``(item_type, slug)`` pair *override_guides* does not carry — i.e. one that
      exists only in the **bundled** playbook document. This keys the exemption on **who wrote
      the guide**, which is what decides whether the report is actionable at all: a guide the
      adopter declared in ``.overrides/playbook.toml`` is theirs and the remedy can name the file
      and table it sits in, whereas the bundled document is package data sq never writes and no
      adopter can edit. For a bundled guide the reported remedy would name a file the squad may
      not even have, and the only way to clear it would be to undo the roster change — so a
      warning nobody can act on, produced by a first-class reversible operation (retirement).
      That is squads' own graceful degradation, and it stays silent, exactly as it already did
      for a bundled role a ``--roles minimal`` squad never installed.

    Deliberately **not** the discriminator: whether this squad has a roster entry for the slug.
    That tells never-installed apart from retired, but those two are the same event from the
    adopter's side — the bundled document names a role they do not have — with the same
    non-remedy. Retiring a bundled role the bundled playbook names (six of them do) would
    otherwise mint a permanent, unclearable warning.

    A type the active spec no longer declares is skipped: its whole ``sq-<type>`` skill is
    withdrawn, which :func:`orphaned_skill_item_type` already reports, and re-reporting each of
    its guides would bury that one line under a per-role pile. Belt and braces, verified by
    driving it: a merged playbook is *already* spec-filtered (dropping ``bug`` from a workflow
    override removes ``types.bug`` from the merged playbook), so no caller reaches this branch
    today — it holds the property for a caller that pairs the **bundled** playbook with an
    overridden spec, which is a legal call and the same defence ``_write_item_skills`` keeps.

    Pure, and returns sorted pairs so every caller's output is deterministic.
    """
    out: list[tuple[str, str]] = []
    for item_type in managed_item_types(playbook):
        if item_type not in spec.items:
            continue
        for guide in playbook.types[item_type].roles:
            if guide.slug == DEV or guide.slug in live_role_slugs:
                continue
            if (item_type, guide.slug) not in override_guides:
                continue
            out.append((item_type, guide.slug))
    return sorted(out)


def orphaned_playbook_guide_message(
    item_type: str, slug: str, *, retired: bool, live_status: str
) -> str:
    """The one wording for a dropped playbook guide, shared by ``sq check`` and ``sq sync`` so
    the two surfaces cannot drift into describing the same event differently.

    States the condition and both ways out, because either is legitimate depending on which of
    the reachable shapes produced it: make the role live, or drop the guide.

    Both remedies are only nameable because of the exemption in
    :func:`orphaned_playbook_guides`: every guide that reaches this wording is one the adopter
    declared in ``.overrides/playbook.toml``, so the file exists, the ``[types.<type>]`` table is
    theirs, and removing the guide genuinely clears the report. A message that also fired for a
    bundled guide could not honestly say either sentence.

    *retired* selects between the **two different commands** that make a role live, because they
    are not interchangeable and naming the wrong one is naming a remedy that cannot work.
    ``activate`` is a create verb: ``activate_role`` refuses an existing entry that is not live
    (with this same ``sq role <slug> status <live_status>`` hint), so pointing a retired role's
    warning at ``sq role activate <slug>`` would hand the reader a command that errors out.
    A slug with a roster entry is revived by a status transition (``sq role <slug> status
    <live_status>``, the spelling ``_retired_participant_hint`` already uses for the same
    situation); a slug with no entry yet — the scaffold-then-forget order — is activated.
    *live_status* is the roster role type's own live initial status, never a hard-coded
    ``Active``, so a project that renamed its roster lifecycle reads its own vocabulary.
    """
    revive = (
        f"reactivate the role (`sq role {slug} status {live_status}`)"
        if retired
        else f"activate the role (`sq role activate {slug}`)"
    )
    return (
        f"playbook guide for role {slug!r} on type {item_type!r} names no live role, so its "
        f"guidance is dropped from the generated `sq-{item_type}` skill — {revive}, or remove "
        f"the guide from `.overrides/playbook.toml` under `[types.{item_type}]`"
    )


# Role -> type authoring prose: the "who authors what" cheatsheet (workflow.md.j2) renders
# from the playbook's declared create-lanes + the role catalog (title lookup) + the
# WorkflowSpec (prefix, parent chain, sub-entity kind) — so a project-added custom type with
# an override-declared authoring guide is surfaced by the same derivation as a bundled one.
# A type with no declared author just gets no authoring bullet (see custom_item_skill_commands
# for its generic command surface).


def authoring_owner(
    item_type: str,
    roster_slugs: Container[str] | None = None,
    playbook: PlaybookSpec | None = None,
    role_titles: Mapping[str, str] | None = None,
) -> tuple[str, str] | None:
    """The (slug, display title) of the single in-lane role that authors *item_type*.

    *item_type* is the plain type-name string (e.g. ``"feature"``, ``"task"`` — the
    same string keys ``spec.items`` and the template loop over them use).

    Returns ``None`` when the type has no lane owner, more than one (ambiguous), the
    owner has no resolvable display title (e.g. a ``<tech>-dev`` slug — ``in_lane_owner``
    never returns the ``DEV`` sentinel itself, only concrete slugs, so this only excludes
    an as-yet-uncataloged one), or — when *roster_slugs* is given — the owner isn't
    actually on this squad's live roster. ``roster_slugs`` is opt-in (``None`` skips the
    roster check): the playbook and the bundled catalog have no notion of who's actually
    active, so a caller with no roster in hand (e.g. a bundled reference render) gets the
    unfiltered answer; a caller that *does* have the live roster (CLAUDE.md, the squads
    skill) should pass it, so the cheatsheet never assigns authorship to a role that doesn't
    exist in this squad.

    *role_titles* is the live slug→title map, consulted **only** when the catalog has no entry
    for the owner: a project role declared solely in ``.overrides/roles/`` has no bundled
    catalog entry, so without it an override-declared authoring role resolves to ``None`` and
    its type silently loses its authoring bullet. The catalog stays first because its titles
    are the lower-case sentence forms this prose is written around, while a live roster entry
    carries the display-cased form.
    """
    owners = in_lane_owner(item_type, playbook)
    if len(owners) != 1:
        return None
    (slug,) = owners
    if roster_slugs is not None and slug not in roster_slugs:
        return None
    try:
        return slug, role_by_slug(slug).title
    except RoleNotFoundError:
        # Not in the catalog: a project-declared role (title from the live roster, when the
        # caller supplied one), the *dev sentinel, or an as-yet-uncataloged slug.
        if role_titles is not None and slug in role_titles:
            return slug, role_titles[slug]
        return None


def example_assignee_slug(roles: Iterable[Mapping[str, str]] | None = None) -> str:
    """A concrete ``--assignee`` value for a generated "common commands" example, taken from
    the **live** roster rather than named as a literal.

    The generated squads skill and AGENTS.md both show one metadata-update example. Naming a
    bundled slug there hands an agent a command that exits 1 with an unknown-slug error on any
    squad that doesn't carry that role — ``sq init --roles minimal`` being the documented way
    to get one.

    Prefers a ``<tech>-dev`` slug (implementation work is what gets assigned), then the first
    roster entry, and degrades to the ``<slug>`` placeholder the surrounding block already uses
    for the reader's own slug when the roster is empty or wasn't threaded in.
    """
    slugs = [s for s in ((r.get("slug") or "") for r in roles or ()) if s]
    return next((s for s in slugs if is_dev_slug(s)), None) or next(iter(slugs), "<slug>")


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
