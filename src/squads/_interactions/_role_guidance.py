"""What the playbook gives a role: the item types and skills a role maps to, its create lane,
the per-role skill sections, and the example assignee a generated command shows.

A guide addresses a role by its slug, or every role holding a capability with ``*<name>``. A
role is judged by its resolved ``slug`` and ``capabilities``, never by how its slug is spelled.
Every function takes the workflow spec and playbook it answers from; none falls back to the
bundled documents.
"""

from collections.abc import Iterable, Mapping
from dataclasses import replace
from typing import Any, Protocol

from squads._interactions._models import ItemPlaybookSpec, PlaybookSpec
from squads._roles._models import RoleCatalogSpec
from squads._roles._projection import RoleView
from squads._workflow._models import WorkflowSpec

#: Prefix of a guide subject that addresses a capability rather than one role.
CAPABILITY_SUBJECT_PREFIX = "*"


class RoleLike(Protocol):
    """A resolved role: a ``RoleDef`` or a ``RoleView``."""

    @property
    def slug(self) -> str: ...

    @property
    def capabilities(self) -> tuple[str, ...]: ...


def addresses(subject: str, role: RoleLike) -> bool:
    """Whether a guide with *subject* (a role slug or ``*<capability>``) addresses *role*."""
    if subject.startswith(CAPABILITY_SUBJECT_PREFIX):
        return subject[len(CAPABILITY_SUBJECT_PREFIX) :] in role.capabilities
    return subject == role.slug


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
    active/merged playbook, and a process serves many squads. A capability subject
    (``*<name>``) is a key like any other; :func:`allowed_create_types` expands it to the roles
    that hold the capability.
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


def allowed_create_types(role: RoleLike, spec: WorkflowSpec, playbook: PlaybookSpec) -> set[str]:
    """Return the set of item types *role* is in-lane to author via ``sq create``.

    Derived from :func:`create_lanes` over *playbook*: the lanes of every guide that addresses
    *role* by slug or by a capability it holds. The default role and ``op-*`` slugs should be
    checked via :func:`is_lane_exempt` **before** calling this — the exemption is the
    meaningful check for those slugs; this function answers only what the playbook declares.

    ``spec`` mirrors :func:`item_types_for_role`'s own membership filter: a type a guide still
    names that *spec* has dropped (via ``[selected]``, or renamed away to a new key) is
    filtered out here — a role's advertised create-lane never keeps naming a type that no
    longer exists.
    """
    lane = {
        t
        for subject, types in create_lanes(playbook).items()
        if addresses(subject, role)
        for t in types
    }
    return {t for t in lane if t in spec.items}


def in_lane_owner(item_type: str, playbook: PlaybookSpec, roster: Iterable[RoleLike]) -> set[str]:
    """Return the slugs of the roles in *roster* that are in-lane to create *item_type*.

    This is the inverse of :func:`allowed_create_types`: a slug-addressed guide names its
    role, a capability-addressed one names every role in *roster* holding the capability. The
    result is used for advisory warning text, not access control.
    """
    roles = list(roster)
    owners: set[str] = set()
    for subject, types in create_lanes(playbook).items():
        if item_type not in types:
            continue
        if subject.startswith(CAPABILITY_SUBJECT_PREFIX):
            owners.update(r.slug for r in roles if addresses(subject, r))
        else:
            owners.add(subject)
    return owners


def item_types_for_role(role: RoleLike, spec: WorkflowSpec, playbook: PlaybookSpec) -> list[str]:
    """Item types this role interacts with: those with a guide that addresses it.

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
    return [
        item_type
        for item_type, pb in playbook.types.items()
        if item_type in spec.items and any(addresses(g.slug, role) for g in pb.roles)
    ]


def skills_for_role(role: RoleLike, spec: WorkflowSpec, playbook: PlaybookSpec) -> list[str]:
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
        *(item_skill_name(t) for t in item_types_for_role(role, spec, playbook)),
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

    - a guide addressed to a capability (``*<name>``) renders only while at least one live role
      holds it, under a heading that names the capability and lists those holders;
    - a guide addressed to a role renders only while that role is in the live roster.
    """
    if pb is None:
        return []
    roles = list(roster)
    by_slug = {r.slug: r for r in roles}
    out: list[dict[str, Any]] = []
    for guide in pb.roles:
        if guide.slug.startswith(CAPABILITY_SUBJECT_PREFIX):
            holders = [r for r in roles if addresses(guide.slug, r)]
            if not holders:
                continue
            title = f"`{guide.slug}`: " + ", ".join(f"{r.full_name} (`{r.slug}`)" for r in holders)
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


def developer_roles[R: RoleLike](roster: Iterable[R], catalog: RoleCatalogSpec) -> list[R]:
    """The roles in *roster* that hold a capability the *catalog*'s ``[dev]`` table declares, in
    roster order — a templated developer and a declared one alike."""
    developer = set(catalog.dev.capabilities)
    return [r for r in roster if developer.intersection(r.capabilities)]


def slug_only_role(slug: str) -> RoleView:
    """A role-like value for a slug that is not a live role: it holds no capability."""
    return RoleView(slug=slug, full_name=slug, title=slug, is_default=False)


def delegate_example_slugs(
    roster: Iterable[RoleView], default_slug: str | None, developers: Iterable[str]
) -> list[str]:
    """Up to four live role slugs a generated "delegate" sentence shows as examples of a
    ``subagent_type``: roster order, never the default role itself, and a developer among them
    when one is live (it takes the last place when the first four hold none)."""
    slugs = [r.slug for r in roster if r.slug != default_slug]
    chosen = slugs[:4]
    developer = next((s for s in slugs if s in set(developers)), None)
    if developer is not None and developer not in chosen:
        chosen[-1:] = [developer]
    return [s for s in slugs if s in chosen]


def _role_slug(role: Mapping[str, str] | RoleView) -> str:
    if isinstance(role, Mapping):
        return role.get("slug") or ""
    return role.slug or ""


def role_like(role: Mapping[str, Any] | RoleView) -> RoleView:
    """*role* as a ``RoleView``: a roster entry passed to a template as a plain mapping
    (``slug`` and optionally ``capabilities``) or as the view itself."""
    if isinstance(role, Mapping):
        slug = str(role.get("slug") or "")
        view = slug_only_role(slug)
        return replace(view, capabilities=tuple(role.get("capabilities") or ()))
    return role


def example_assignee_slug(
    roles: Iterable[Mapping[str, str] | RoleView] | None = None,
    developers: Iterable[str] = (),
) -> str:
    """A concrete ``--assignee`` value for a generated "common commands" example, taken from
    the **live** roster rather than named as a literal.

    The generated squads skill and AGENTS.md both show one metadata-update example. Naming a
    bundled slug there hands an agent a command that exits 1 with an unknown-slug error on any
    squad that doesn't carry that role — ``sq init --roles minimal`` being the documented way
    to get one.

    Prefers a slug in *developers* (the slugs of the live developer roles; implementation work
    is what gets assigned), then the first roster entry, and degrades to the ``<slug>``
    placeholder the surrounding block already uses for the reader's own slug when the roster is
    empty or wasn't threaded in.

    Accepts either shape a caller's roster comes in — a plain ``{"slug": ...}`` mapping
    (``templates/agents_md/agents_section.md.j2``'s ``roles``) or a real ``RoleView``
    (``templates/views/squads_skill.md.j2``'s ``source.roster``, unflattened rather than
    converted to a dict for that call) — so neither of the two template call sites needs a
    reshaping step of its own.
    """
    slugs = [s for s in (_role_slug(r) for r in roles or ()) if s]
    preferred = set(developers)
    return next((s for s in slugs if s in preferred), None) or next(iter(slugs), "<slug>")
