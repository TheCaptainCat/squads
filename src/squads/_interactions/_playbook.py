"""The team playbook: the bundled document, who authors and interacts with each item type, and
the checks that a project's guides still name live roles.

It drives the per-item-type managed skills (one role-directed section per interacting role)
and the reverse mapping (which skills each role's pointer preloads). A role that does not
interact with an item type does not get that item's skill.

Membership is spec-driven and checked (a type the active workflow spec does not declare has
no entry and no skill); guide prose is not, so a surviving type's guidance can keep naming a
type a workflow override dropped or renamed. See ``_loader``'s module docstring for that
limitation and its remedy.
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
from squads._roles._catalog import role_by_slug
from squads._roles._projection import RoleView
from squads._workflow import bundled_spec
from squads._workflow._models import WorkflowSpec


@functools.cache
def _bundled_playbook() -> PlaybookSpec:
    return load_playbook(bundled_spec())


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
    """Every adopter guide ``(item_type, role_slug)`` the ``sq-<type>`` skill drops silently.

    A guide is dropped when *role_slug* names no live role. The loader's slug authority is
    permissive: the bundled catalog plus the ``.overrides/roles/*.toml`` stems, read by filename
    because they must be readable before the index (coupling it to the roster would refuse every
    guide while an index is mid-repair). The renderer gates each guide on live roster membership
    and drops the rest, so where the sets differ the adopter's guidance evaporates unreported.
    This predicate reports it; ``check`` and ``sync`` carry the news, as they do for the skill
    side of the same event.

    Three shapes reach it: a role not yet created (a guide written before ``sq role add``), a
    role activated and later retired with the guide left behind, and a stray or malformed file in
    ``.overrides/roles/`` whose stem the loader accepts as a slug but which never becomes a role.

    Two exemptions:

    * A guide addressed to a bundled capability (``*<name>``), which renders only while a live
      role holds it, so a squad without a holder has no guidance for an actor that cannot act.
    * A guide whose pair *override_guides* does not carry, i.e. one only in the bundled playbook.
      The exemption keys on who wrote the guide because that decides whether the report is
      actionable: an adopter's guide is theirs, and the remedy can name its file and table;
      the bundled document is package data no adopter can edit, and its only remedy would be to
      undo a reversible roster change (retirement). That is squads' own graceful degradation and
      stays silent, as it does for a bundled role a ``--roles minimal`` squad never installed.

    Whether the squad has a roster entry for the slug is not the discriminator: it separates
    never-installed from retired, which are the same event for the adopter. Retiring a bundled
    role that the bundled playbook names (six do) would otherwise mint an unclearable warning.

    A type *spec* no longer declares is skipped: its whole ``sq-<type>`` skill is withdrawn,
    which :func:`orphaned_skill_item_type` reports, and reporting each guide would bury that line.
    A merged playbook is already spec-filtered, so no caller reaches this branch; it holds
    the property for a caller pairing the bundled playbook with an overridden spec, the defence
    ``_write_item_skills`` also keeps. Pure, and returns sorted pairs.
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
    item_type: str, slug: str, *, retired: bool, live_status: str, in_catalog: bool = False
) -> str:
    """The one wording for a dropped playbook guide, shared by ``sq check`` and ``sq sync``.

    It states the condition and both ways out, make the role live or drop the guide. Both are
    nameable only because of the exemption in :func:`orphaned_playbook_guides`: every guide
    reaching this wording is the adopter's own in ``.overrides/playbook.toml``, so the file and
    ``[types.<type>]`` table exist and removing the guide clears the report.

    *retired* selects between two commands that are not interchangeable. ``activate`` is a create
    verb: ``activate_role`` refuses an existing non-live entry with the ``sq role <slug> status
    <live_status>`` hint, so pointing a retired role at ``sq role activate <slug>`` would hand
    the reader a command that errors. A slug with a roster entry is revived by that status
    transition (as ``_retired_participant_hint`` does); a slug with no entry yet, the
    guide-first order, is created. *in_catalog* says the catalog declares the slug, so activating
    it works; any other slug is created with ``sq role add`` or from a template. *live_status*
    is the roster role type's live initial status, not a hard-coded ``Active``, so a renamed
    roster lifecycle reads its own vocabulary.
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
        else (
            f"activate the role (`sq role activate {slug}`)"
            if in_catalog
            else f"create the role (`sq role add {slug} …`, or `sq role activate {slug} --from "
            "<template>`)"
        )
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
    """Every ``(item_type, capability)`` an adopter guide or command uses as an unheld ``@*<cap>``.

    No live role holds it, so the generated skill renders ``*<capability>`` and mentions nobody.
    Only a guide *override_guides* carries and a command line *override_commands* carries are
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
    """The ``(slug, display title)`` of every in-lane role that authors *item_type*.

    They come in the order the type's playbook guides declare them, a capability guide expanding
    to the roster's holders in place. *item_type* is the plain type-name string. Empty when the
    type has no lane owner. An owner is dropped when it has no resolvable display title, or, with
    *roster* given, when it is not on the live roster; a capability guide needs the roster to
    name anyone. *roster* is opt-in (``None`` skips the check): the playbook and bundled catalog
    cannot know who is active, so a bundled reference render gets the unfiltered answer, while
    CLAUDE.md and the squads skill pass the live roster so the cheatsheet never assigns authorship
    to a role the squad lacks. An entry is a ``RoleView`` or a mapping with ``slug`` and
    optionally ``capabilities``.

    *role_titles*, the live slug-to-title map, is consulted first because only it sees a project
    override. A roster entry's ``title`` is the role title in the catalog's casing, resolved
    through the overrides; the display-cased name is ``full_name``, which this never reads. With
    the catalog first, a managed region rendered a retitled role two ways: the roster line
    resolved and the authoring bullet did not. The bundled catalog is the fallback for a caller
    with no live roster. A project role declared only in ``.overrides/roles/`` and absent from the
    map has no title and loses its bullet rather than being named by its slug.
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
