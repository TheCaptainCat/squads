"""What the playbook gives a role: the item types and skills a role slug maps to, its create
lane, the per-role skill sections, and the example assignee a generated command shows.

A slug is judged by its spelling (``<tech>-dev`` addresses the ``*dev`` guides). Every function
takes the workflow spec and playbook it answers from; none falls back to the bundled documents.
"""

from collections.abc import Iterable, Mapping
from typing import Any

from squads._interactions._models import ItemPlaybookSpec, PlaybookSpec
from squads._roles._models import RoleCatalogSpec
from squads._roles._projection import RoleView
from squads._workflow._models import WorkflowSpec

#: Sentinel interacting "role" that expands to every developer role (slug ``<tech>-dev``).
DEV = "*dev"


def is_dev_slug(slug: str) -> bool:
    return slug.endswith("-dev")


# The advisory create-lane is DERIVED from the playbook document, per role guide, from the
# declared `authors` flag — never from a second table beside it, and never scanned out of the
# guide's prose. A prose scan was rejected for the reason the flag exists: the create verb for a
# type does not always live in that type's own section (the reviewer's `sq create review` is
# written in the task playbook's reviewer guide), so the scan has to match across sections and
# still misses a role whose guidance never spells the verb. A declaration says it once, in the
# document an adopter can override.


def create_lanes(playbook: PlaybookSpec) -> dict[str, set[str]]:
    """Role slug → the set of item types that slug is in-lane to author, derived from the
    role guides of *playbook* that declare ``authors``.

    Computed per call rather than cached in a module constant: the answer depends on the
    active/merged playbook, and a process serves many squads. The ``DEV`` sentinel appears
    here only if some guide declares it an author — the bundled document never does, so a
    ``<tech>-dev`` slug derives an empty lane by declaration, not by a special case.
    """
    lanes: dict[str, set[str]] = {}
    for item_type, entry in playbook.types.items():
        for guide in entry.roles:
            if guide.authors:
                lanes.setdefault(guide.slug, set()).add(item_type)
    return lanes


def laned_types(playbook: PlaybookSpec) -> frozenset[str]:
    """The item types that participate in the create-lane domain at all — every type some
    guide in *playbook* declares an author for.

    Computed per call from *playbook*, so a renamed or project-declared type enters the domain
    when some guide declares an author for it.
    """
    return frozenset(t for lane in create_lanes(playbook).values() for t in lane)


def is_lane_exempt(slug: str, default_slug: str | None) -> bool:
    """Return True for slugs that are fully exempt from all advisory lane checks.

    Exempt: the squad's **default role** — the orchestrator that authors any type for
    coordination — and any ``op-*`` operator (humans coordinate freely). The default role is
    the caller's *default_slug*, never a hard-coded slug, so a squad that renamed or reassigned
    its coordinator keeps the exemption where it declared it; ``None`` means no default role.
    """
    if slug.startswith("op-"):
        return True
    return default_slug is not None and slug == default_slug


def catalog_default_slug(catalog: RoleCatalogSpec) -> str | None:
    """The ``is_default`` slug of *catalog*, or ``None`` if none is designated."""
    return next((r.slug for r in catalog.roles if r.is_default), None)


def allowed_create_types(slug: str, spec: WorkflowSpec, playbook: PlaybookSpec) -> set[str]:
    """Return the set of item types *slug* is in-lane to author via ``sq create``.

    Derived from :func:`create_lanes` over *playbook*.  The ``*dev``/``DEV`` sentinel covers
    any ``<tech>-dev`` slug.  The default role and ``op-*`` slugs should be checked via
    :func:`is_lane_exempt` **before** calling this — the exemption is the meaningful check for
    those slugs; this function answers only what the playbook declares for them.

    ``spec`` mirrors :func:`item_types_for_role`'s own membership filter: a type a guide still
    names that *spec* has dropped (via ``[selected]``, or renamed away to a new key) is
    filtered out here — a role's advertised create-lane never keeps naming a type that no
    longer exists.
    """
    lanes = create_lanes(playbook)
    lane = lanes.get(DEV, set()) if is_dev_slug(slug) else lanes.get(slug, set())
    return {t for t in lane if t in spec.items}


def in_lane_owner(item_type: str, playbook: PlaybookSpec) -> set[str]:
    """Return the set of role slugs that are in-lane to create *item_type*.

    This is the inverse of :func:`allowed_create_types`: which role slug(s)
    have ``item_type`` in their derived lane.  Expands the ``*dev``/``DEV``
    sentinel using its literal slug string (not all possible tech stacks) — the
    result is used for advisory warning text, not access control.
    """
    return {
        slug for slug, types in create_lanes(playbook).items() if item_type in types and slug != DEV
    }


def item_types_for_role(slug: str, spec: WorkflowSpec, playbook: PlaybookSpec) -> list[str]:
    """Item types this role interacts with (DEV sentinel matches any ``*-dev`` slug).

    ``playbook`` is the active (merged) one, so a project-added role guide or type entry changes
    a role's interacting-type list. A type the playbook still names
    but *spec* has dropped (via ``[selected]``, directly, or by renaming it away to a new key)
    is filtered out here, so a role's preload list never keeps naming a type that no longer
    exists. A type *spec* declares that has no playbook entry at all — a project-declared custom
    type with no override coverage, or the new name a rename produced — contributes nothing
    here (there is no interaction data to derive from), the same "no preload, but the thin
    auto-generated skill still exists and is still loadable by hand" degradation any custom type
    already gets.
    """
    dev = is_dev_slug(slug)
    out: list[str] = []
    for item_type, pb in playbook.types.items():
        if item_type not in spec.items:
            continue
        slugs = {g.slug for g in pb.roles}
        if slug in slugs or (dev and DEV in slugs):
            out.append(item_type)
    return out


def skills_for_role(slug: str, spec: WorkflowSpec, playbook: PlaybookSpec) -> list[str]:
    """Skill names a role's pointer preloads: the always-on skills + the role's item skills.

    See :func:`item_types_for_role` for how *spec*/*playbook* keep this list correct — a
    dropped/renamed type's skill never lingers, and a project override's guidance changes are
    reflected once the caller threads the active/merged playbook.
    """
    from squads._interactions import (
        GREETING_SKILL,
        MEMORY_SKILL,
        SQUADS_SKILL,
        item_skill_name,
    )

    return [
        SQUADS_SKILL,
        GREETING_SKILL,
        MEMORY_SKILL,
        *(item_skill_name(t) for t in item_types_for_role(slug, spec, playbook)),
    ]


def item_skill_role_sections(
    pb: ItemPlaybookSpec | None, roster: Iterable[RoleView]
) -> list[dict[str, Any]]:
    """The ordered per-role section blocks a per-item-type skill's presentation template
    renders for one item type — empty for a type the active playbook does not cover (the thin
    skill's "no role sections" degradation).

    Registered as a Jinja filter (``_rendering/_engine.py``), so the roster lookup stays in
    Python rather than in template logic.

    Two rules depend on the roster:

    - the shared ``developers`` section (the ``*dev`` sentinel guide) renders only when the
      roster carries at least one ``<tech>-dev`` role, so a squad with no developer yet does
      not carry guidance for an actor that cannot act;
    - a named role's guide renders only while that role is in the live roster.
    """
    if pb is None:
        return []
    by_slug = {r.slug: r for r in roster}
    has_dev = any(is_dev_slug(r.slug) for r in roster)
    out: list[dict[str, Any]] = []
    for guide in pb.roles:
        if guide.slug == DEV:
            if not has_dev:
                continue
            title = "developers"
        elif guide.slug in by_slug:
            r = by_slug[guide.slug]
            title = f"{r.full_name} (`{r.slug}`)"
        else:
            continue
        out.append(
            {
                "title": title,
                "enter": guide.enter,
                "do": guide.do,
                "handoff": guide.handoff,
                "watch": guide.watch,
            }
        )
    return out


def _role_slug(role: Mapping[str, str] | RoleView) -> str:
    if isinstance(role, Mapping):
        return role.get("slug") or ""
    return role.slug or ""


def example_assignee_slug(
    roles: Iterable[Mapping[str, str] | RoleView] | None = None,
) -> str:
    """A concrete ``--assignee`` value for a generated "common commands" example, taken from
    the **live** roster rather than named as a literal.

    The generated squads skill and AGENTS.md both show one metadata-update example. Naming a
    bundled slug there hands an agent a command that exits 1 with an unknown-slug error on any
    squad that doesn't carry that role — ``sq init --roles minimal`` being the documented way
    to get one.

    Prefers a ``<tech>-dev`` slug (implementation work is what gets assigned), then the first
    roster entry, and degrades to the ``<slug>`` placeholder the surrounding block already uses
    for the reader's own slug when the roster is empty or wasn't threaded in.

    Accepts either shape a caller's roster comes in — a plain ``{"slug": ...}`` mapping
    (``templates/agents_md/agents_section.md.j2``'s ``roles``) or a real ``RoleView``
    (``templates/views/squads_skill.md.j2``'s ``source.roster``, unflattened rather than
    converted to a dict for that call) — so neither of the two template call sites needs a
    reshaping step of its own.
    """
    slugs = [s for s in (_role_slug(r) for r in roles or ()) if s]
    return next((s for s in slugs if is_dev_slug(s)), None) or next(iter(slugs), "<slug>")
