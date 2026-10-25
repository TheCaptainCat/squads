"""The team playbook: the bundled document, who authors and interacts with each item type, and
the checks that a project's guides still name live roles.

Drives the per-item-type managed skills (one role-directed section per interacting role) and the
reverse mapping (which skills each role's pointer preloads). A role that does not interact with an
item type does not get that item's skill.

Membership is spec-driven and checked (a type the active workflow spec does not declare has no
entry and no skill); guide **prose** is not, and a surviving type's guidance can go on naming a
type that a workflow override dropped or renamed. See ``_loader``'s module docstring for the full
statement of that limitation and its remedy.
"""

import contextlib
import functools
from collections.abc import Container, Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from squads._errors import RoleNotFoundError
from squads._interactions._loader import load_playbook
from squads._interactions._models import ItemPlaybookSpec, PlaybookSpec, RoleGuideSpec
from squads._interactions._role_guidance import (
    CAPABILITY_SUBJECT_PREFIX,
    CAPABILITY_TOKEN,
    RoleLike,
    addresses,
    guide_text_lines,
    in_lane_owner,
    role_like,
)
from squads._roles._catalog import get_catalog, role_by_slug
from squads._roles._projection import RoleView
from squads._workflow import bundled_spec
from squads._workflow._models import WorkflowSpec


@functools.cache
def _bundled_playbook() -> PlaybookSpec:
    return load_playbook(get_catalog(), bundled_spec())


def get_playbook_spec() -> PlaybookSpec:
    """Return the bundled playbook, loaded on first use (public accessor for cross-module use and
    tests).

    Always the bundled document, regardless of any project override. The per-request merged
    playbook (bundled base + any ``.overrides/playbook.toml``) is carried on ``Service.playbook``
    instead; a consumer that needs the active view takes it as an explicit ``playbook`` parameter.
    """
    return _bundled_playbook()


@functools.cache
def bundled_item_playbooks() -> Mapping[str, ItemPlaybook]:
    """The bundled playbook's per-type entries as ``ItemPlaybook`` values.

    A ``MappingProxyType``, not a plain ``dict``: the result is shared process-wide, and a plain
    dict is mutable at runtime regardless of its annotation, so a write would corrupt every
    caller's view. The proxy makes it a ``TypeError`` at the mutation site.
    """
    return MappingProxyType(
        {t: spec_to_item_playbook(pb) for t, pb in _bundled_playbook().types.items()}
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


def managed_item_types(playbook: PlaybookSpec) -> list[str]:
    """Item types with a rich, role-guidance-bearing entry in *playbook*.

    A production call site (skill generation) threads the active/merged playbook
    (``Service.playbook``) so a project override's added/removed type coverage is reflected.
    """
    return list(playbook.types)


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


def unheld_capability_tokens(
    playbook: PlaybookSpec,
    spec: WorkflowSpec,
    *,
    live_roles: Iterable[RoleLike],
    override_guides: Container[tuple[str, str]],
    override_commands: Container[tuple[str, str]] = (),
) -> list[tuple[str, str]]:
    """Every ``(item_type, capability)`` pair for which a guide or command line the adopter
    declared uses an ``@*<capability>`` token that no live role holds, so the generated skill
    renders it as ``*<capability>`` and mentions nobody.

    Only a guide *override_guides* carries, and a command line *override_commands* carries, is
    read: the same token in the bundled playbook degrades silently, as no adopter can edit it. A
    type *spec* no longer declares is skipped. Pure, and returns sorted, unique pairs.
    """
    held = {c for r in live_roles for c in r.capabilities}
    out: set[tuple[str, str]] = set()
    for item_type in managed_item_types(playbook):
        if item_type not in spec.items:
            continue
        entry = playbook.types[item_type]
        lines = [ln for ln in entry.commands if (item_type, ln) in override_commands]
        for guide in entry.roles:
            if (item_type, guide.slug) in override_guides:
                lines.extend(guide_text_lines(guide))
        out.update(
            (item_type, name)
            for line in lines
            for name in CAPABILITY_TOKEN.findall(line)
            if name not in held
        )
    return sorted(out)


def unheld_capability_token_message(item_type: str, capability: str) -> str:
    """The one wording for an unheld capability token, shared by ``sq check`` and ``sq sync``."""
    return (
        f"playbook text on type {item_type!r} mentions `@*{capability}`, but no live role holds "
        f"the capability, so the generated `sq-{item_type}` skill renders it as `*{capability}` "
        f'and mentions nobody — declare `capabilities = ["{capability}"]` on a live role, or edit '
        f"the line in `.overrides/playbook.toml` under `[types.{item_type}]`"
    )


def authoring_owners(
    item_type: str,
    roster: Iterable[Mapping[str, Any] | RoleView] | None,
    playbook: PlaybookSpec,
    role_titles: Mapping[str, str] | None = None,
) -> list[tuple[str, str]]:
    """The ``(slug, display title)`` of every in-lane role that authors *item_type*, in the
    order the type's own playbook guides declare them (a capability guide expands to the
    roster's holders in place).

    *item_type* is the plain type-name string (e.g. ``"feature"``, ``"task"`` — the
    same string keys ``spec.items`` and the template loop over them use).

    Empty when the type has no lane owner. An owner is left out when it has no resolvable
    display title (an as-yet-uncataloged slug) or — when *roster* is given — when it isn't
    actually on this squad's live roster. A guide addressed to a capability names the roster's
    holders, so it needs the roster to name anyone. *roster* is opt-in (``None`` skips the
    roster check): the playbook and the bundled catalog have no notion of who's actually
    active, so a caller with no roster in hand (e.g. a bundled reference render) gets the
    unfiltered answer; a caller that *does* have the live roster (CLAUDE.md, the squads skill)
    should pass it, so the cheatsheet never assigns authorship to a role that doesn't exist in
    this squad. A roster entry is a ``RoleView`` or a mapping with ``slug`` and optionally
    ``capabilities``.

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
    owners = in_lane_owner(item_type, playbook, roles or ())
    entry = playbook.types.get(item_type)
    ordered: list[str] = []
    for guide in entry.roles if entry is not None else ():
        if not guide.authors:
            continue
        holders = [r.slug for r in roles or () if addresses(guide.slug, r)]
        for slug in (
            [guide.slug] if not guide.slug.startswith(CAPABILITY_SUBJECT_PREFIX) else holders
        ):
            if slug in owners and slug not in ordered:
                ordered.append(slug)
    titled: list[tuple[str, str]] = []
    for slug in ordered:
        if roles is not None and slug not in {r.slug for r in roles}:
            continue
        if role_titles is not None and slug in role_titles:
            titled.append((slug, role_titles[slug]))
            continue
        with contextlib.suppress(RoleNotFoundError):
            # Neither a live roster title nor a catalog entry: an as-yet-uncataloged slug.
            titled.append((slug, role_by_slug(slug).title))
    return titled


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
