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
from typing import Any, TypedDict

from squads import _badges as badges
from squads._errors import RoleNotFoundError
from squads._interactions._loader import load_playbook
from squads._interactions._models import (
    ItemPlaybookSpec,
    PlaybookSpec,
    RoleGuideSpec,
)
from squads._interactions._role_guidance import (
    CAPABILITY_SUBJECT_PREFIX,
    RoleLike,
    addresses,
    in_lane_owner,
    role_like,
)
from squads._models._item import Item
from squads._roles._catalog import get_catalog, role_by_slug
from squads._roles._projection import RoleView
from squads._workflow._models import (
    DEFAULT_SUBENTITY_TITLE_MAX,
    ROSTER_ROLE,
    ROSTER_SKILL,
    Field,
    WorkflowSpec,
)


@dataclass(frozen=True)
class RoleGuide:
    """Precise, structured guidance for one actor on one item type.

    Rendered under fixed labels in the per-item skill, so every actor reads the same shape:
    what to check first, what to do, what moves the work on, and what to stay out of.
    """

    slug: str  # a role slug, or ``*<capability>``
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


#: Slug -> the view name that renders each of the three always-on skills' definition, seeded
#: as a ``sq:view:<name>`` placement tag into the skill item's ``sq:body`` at creation
#: (``_write_managed_skill``) and backfilled onto an already-existing, still-empty one by
#: ``sq repair`` (``MaintenanceMixin._repair_body_tag``) — the two writers this table is
#: shared between, so the slug->view mapping is declared in exactly one place. A per-item-type
#: ``sq-<type>`` skill has no entry here: every one of them shares the single
#: :data:`ITEM_SKILL_VIEW_NAME` instead (see its own docstring for why one name, not N).
SYSTEM_SKILL_VIEW_NAMES: dict[str, str] = {
    SQUADS_SKILL: "squads_skill",
    GREETING_SKILL: "greeting_skill",
    MEMORY_SKILL: "memory_skill",
}

#: The one view name every per-item-type ``sq-<type>`` skill's placement tag names — bundled or
#: project-declared alike, seeded at skill creation (``_write_managed_skill``, called from
#: ``_write_item_skills``) and backfilled onto an already-existing body by ``sq repair``
#: (``MaintenanceMixin._repair_body_tag``), the same two writers :data:`SYSTEM_SKILL_VIEW_NAMES`
#: is shared between. One name for every type rather than one synthesized view per type: a view
#: name that embedded a type name would put that type's name in corpus bytes, so a rename or a
#: dropped type would dangle the tag on every skill body carrying it — the `playbook` source
#: resolves the documented type from the *host's own slug* at read time instead
#: (``squads._views._playbook_subject``), so one declared view and one template
#: (``templates/views/item_skill.md.j2``) serve every declared type.
ITEM_SKILL_VIEW_NAME = "item_skill"

#: The view name a role's placement tag names, seeded into a role item's ``sq:body`` at
#: activation (``templates/agents/role.md.j2``'s static tag, reasserted belt-and-suspenders by
#: ``ServiceCore._create_core``) and backfilled onto an already-existing, still-empty one by
#: ``sq repair`` (``MaintenanceMixin._repair_body_tag``) — the third writer this name must agree
#: with, alongside the other two constants above. Declared as ``[views.role_definition]`` in
#: ``_specs/workflow.toml``, the source of truth all three are checked against.
ROLE_DEFINITION_VIEW_NAME = "role_definition"


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


#: Re-exported bundled default for the advisory threshold (characters) sub-entity titles are
#: checked against -- what a bare ``subentity_title_max`` selection resolves to, for callers that
#: want "the bundled number" without touching validator machinery (e.g. a test building an
#: over-threshold title). The threshold a type actually gets is spec-resolved and per-type
#: (``WorkflowSpec.item_subentity_title_max``): nothing reads this constant as a live threshold.
TITLE_ADVISORY_MAX: int = DEFAULT_SUBENTITY_TITLE_MAX


def item_skill_name(item_type: str) -> str:
    return f"sq-{item_type}"


def custom_item_skill_name(type_name: str) -> str:
    """Return the skill slug for a custom (non-built-in) item type."""
    return f"sq-{type_name}"


def item_type_for_skill_slug(slug: str, spec: WorkflowSpec) -> str | None:
    """The non-roster item type whose per-item-type skill is named *slug* under *spec* —
    the inverse of :func:`item_skill_name`, composed over the same declared-type
    enumeration :func:`active_skill_slugs` builds from (``item_skill_name(t) == slug`` for a
    non-roster ``t``). ``None`` when *slug* names no declared type's skill: one of the three
    permanently-system slugs, an author-created skill sharing the ``sq-`` naming convention by
    coincidence, or a dropped/renamed type's now-stale slug.

    This is the emptiness case, not a failure — the one call site resolving a ``playbook``
    source's subject from a skill host's own slug (``squads._views._playbook_subject``) falls
    back to the host's own type rather than treating a miss as a refusal, and this function
    makes no claim about which is which; it only answers the inversion.
    """
    return next(
        (
            t
            for t, ts in spec.items.items()
            if ts.category != "roster" and item_skill_name(t) == slug
        ),
        None,
    )


def cheatsheet_anchor_type(spec: WorkflowSpec) -> str | None:
    """The single non-roster type used to build a "Common commands" example block (the
    squads skill, AGENTS.md) — chosen generically from *spec* so a squad that drops or
    renames ``"task"`` still gets a fully runnable,
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
    cross-role skills — the orphan-detection vocabulary, since a type can be dropped, renamed,
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
        live = orphaned_skill_item_type(item.slug, spec) is None
    return live


def orphaned_playbook_guides(
    playbook: PlaybookSpec,
    spec: WorkflowSpec,
    *,
    live_roles: Iterable[RoleLike],
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

    * a guide addressed to a capability (``*<name>``) that is bundled, not one an override
      declares — it renders only while a live role holds the capability, so a squad without a
      holder carries no guidance for an actor that cannot act;
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
    roles = list(live_roles)
    for item_type in managed_item_types(playbook):
        if item_type not in spec.items:
            continue
        for guide in playbook.types[item_type].roles:
            if any(addresses(guide.slug, r) for r in roles):
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
    if slug.startswith(CAPABILITY_SUBJECT_PREFIX):
        return (
            f"playbook guide for capability {slug!r} on type {item_type!r} names no live role, so "
            f"its guidance is dropped from the generated `sq-{item_type}` skill — declare "
            f'`capabilities = ["{slug[1:]}"]` on a live role, or remove the guide from '
            f"`.overrides/playbook.toml` under `[types.{item_type}]`"
        )
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
    roster: Iterable[Mapping[str, Any] | RoleView] | None = None,
    playbook: PlaybookSpec | None = None,
    role_titles: Mapping[str, str] | None = None,
) -> tuple[str, str] | None:
    """The (slug, display title) of the single in-lane role that authors *item_type*.

    *item_type* is the plain type-name string (e.g. ``"feature"``, ``"task"`` — the
    same string keys ``spec.items`` and the template loop over them use).

    Returns ``None`` when the type has no lane owner, more than one (ambiguous), the
    owner has no resolvable display title (an as-yet-uncataloged slug), or — when *roster* is
    given — the owner isn't actually on this squad's live roster. A guide addressed to a
    capability names the roster's holders, so it needs the roster to name anyone. *roster* is
    opt-in (``None`` skips the roster check): the playbook and the bundled catalog have no
    notion of who's actually active, so a caller with no roster in hand (e.g. a bundled
    reference render) gets the unfiltered answer; a caller that *does* have the live roster
    (CLAUDE.md, the squads skill) should pass it, so the cheatsheet never assigns authorship
    to a role that doesn't exist in this squad. A roster entry is a ``RoleView`` or a mapping
    with ``slug`` and optionally ``capabilities``.

    *role_titles* is the live slug→title map and is consulted **first**, because it is the only
    one of the two sources that can see a project override. A roster entry's ``title`` is the
    role *title* — the same value in the same casing the bundled catalog carries, only resolved
    through the project's role overrides; the person's display-cased name is ``full_name``, a
    different field this function never reads. So on a squad with no override the two sources
    agree and the ordering is invisible, and on one that retitles a role only the live map is
    right — with the catalog first, one compiled managed region rendered a role's title two
    different ways, the roster line resolved and the authoring bullet not.

    The bundled catalog is the fallback, for a caller that threads no live roster at all (a
    bundled reference render). Past it, a project role declared solely in ``.overrides/roles/``
    that is also absent from the map has no title in hand, and loses its authoring bullet rather
    than naming a role by its slug.
    """
    roles = None if roster is None else [role_like(r) for r in roster]
    owners = in_lane_owner(
        item_type, playbook if playbook is not None else get_playbook_spec(), roles or ()
    )
    if len(owners) != 1:
        return None
    (slug,) = owners
    if roles is not None and slug not in {r.slug for r in roles}:
        return None
    if role_titles is not None and slug in role_titles:
        return slug, role_titles[slug]
    try:
        return slug, role_by_slug(slug).title
    except RoleNotFoundError:
        # Neither a live roster title nor a catalog entry: an as-yet-uncataloged slug.
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
