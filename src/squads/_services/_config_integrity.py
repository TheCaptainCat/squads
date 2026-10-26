"""Roster config-integrity clauses (``no_live_role``, ``preloaded_skill``) as pure predicates over
an already-loaded index snapshot, shared by the ``sq check`` reporter and the retirement gate so
neither restates the logic. "Live" is membership in ``WorkflowSpec.live_statuses(item_type)``, never
a single status name. Clause and kind identifiers are internal; user-facing text is the condition
plus its remedy (see :func:`render_finding`).
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from squads._interactions._models import PlaybookSpec
from squads._interactions._role_guidance import item_types_for_role, skills_for_role
from squads._interactions._skills import item_skill_name
from squads._models._index import SquadsDB
from squads._models._item import Item, effective_prefix, ref_id_matches, split_ref
from squads._roles._catalog import RoleDef
from squads._roles._models import CatalogSource
from squads._roles._resolver import resolve_role_tolerantly
from squads._workflow._models import ROSTER_ROLE, ROSTER_SKILL, WorkflowSpec

# Clause identifiers, internal and never rendered; named for the condition each checks.
type Clause = Literal["no_live_role", "preloaded_skill"]

NO_LIVE_ROLE: Clause = "no_live_role"
PRELOADED_SKILL: Clause = "preloaded_skill"

# ``preloaded_skill``'s dependency kinds, ordered by the remedy available (severable to none): an
# ordering of remedies only, not a severity or evaluation order, and every kind a skill is caught by
# is reported.
type Kind = Literal["scoped_edge", "type_implied", "always_on_floor"]

SCOPED_EDGE: Kind = "scoped_edge"
TYPE_IMPLIED: Kind = "type_implied"
ALWAYS_ON_FLOOR: Kind = "always_on_floor"

#: How many implicating types/roles a finding enumerates before capping and summarising the
#: tail — the same shape a collected conflict report uses, not a protocol limit.
_ENUMERATION_CAP = 5


@dataclass(frozen=True)
class ConfigIntegrityFinding:
    """One clause violation against state already on disk. ``entry`` is the roster item id, or
    ``""`` when squad-wide. ``message`` states the condition and ``remedy`` the next step (``None``
    if none), composed only by :func:`render_finding`. ``kind`` is ``None`` for ``no_live_role``,
    else ``scoped_edge`` (severable), ``type_implied`` or ``always_on_floor``; ``severable_targets``
    names the ids a ``scoped_edge`` is stored on, so ``--unlink`` severs exactly what was named.
    """

    clause: Clause
    entry: str
    message: str
    remedy: str | None = None
    kind: Kind | None = None
    severable_targets: frozenset[str] = frozenset()
    dependency: str = ""
    removal_remedy: str | None = None


# ``scoped_edge``'s remedy when the caller is not retiring the finding's own ``entry`` (the
# reporter, or a reactivation naming a bystander skill); it never mentions ``--unlink``, which
# neither can perform.
_SCOPED_EDGE_NO_UNLINK_REMEDY = (
    "sever the edge with `sq skill <addr> unlink-role <role>`, or reactivate the skill"
)


def render_finding(
    finding: ConfigIntegrityFinding, *, unlink_available: bool = False, removal: bool = False
) -> str:
    """The finding's condition plus its remedy when one exists; the one place ``message`` and
    ``remedy`` are joined, so every caller renders the same condition.

    The remedy depends on the caller: ``--unlink`` is offered only when ``unlink_available``
    (default ``False``, the reporter's case) says the caller is retiring the finding's own
    ``entry``, and only ``scoped_edge``'s stored remedy varies by it.
    """
    if removal:
        # A removal leaves the entry live in its own right: only the dependency and the step
        # that clears it apply, never a status the entry would reach or a way to reactivate it.
        text = finding.dependency or finding.message
        if finding.removal_remedy is not None:
            return f"{text} — remedy: {finding.removal_remedy}"
        return text
    remedy = finding.remedy
    if finding.kind == SCOPED_EDGE and not unlink_available:
        remedy = _SCOPED_EDGE_NO_UNLINK_REMEDY
    if remedy is not None:
        return f"{finding.message} — remedy: {remedy}"
    return finding.message


def _live_role_items(index: SquadsDB, spec: WorkflowSpec) -> list[Item]:
    """Every ``role``-type item currently live — filtered from the index snapshot itself,
    never ``Service.roster()`` (see module docstring)."""
    live = spec.live_statuses(ROSTER_ROLE)
    return [it for it in index.items.values() if it.type == ROSTER_ROLE and it.status in live]


def _cap_and_join(values: Iterable[str]) -> str:
    """Sorted, deduped, comma-joined — capping the tail past :data:`_ENUMERATION_CAP` rather
    than printing an unbounded list."""
    ordered = sorted(set(values))
    if len(ordered) <= _ENUMERATION_CAP:
        return ", ".join(ordered)
    shown = ordered[:_ENUMERATION_CAP]
    return ", ".join(shown) + f", and {len(ordered) - _ENUMERATION_CAP} more"


def _scopes_role(skill: Item, role: Item, spec: WorkflowSpec) -> bool:
    """Whether *skill* carries a forward ``preload``-role ref to *role* (the ``scoped_edge``),
    read directly off the skill's own ``refs`` (the skill is the referrer), never inverted via
    ``backrefs`` since both ends are in hand. Resolved through the declared ``preload`` semantic
    (:meth:`WorkflowSpec.preload_ref_kind`), never the bundled ``"scopes"`` spelling."""
    role_prefix = effective_prefix(role.prefix)
    preload_kind = spec.preload_ref_kind()
    for r in skill.refs:
        rid, kind = split_ref(r)
        if kind == preload_kind and ref_id_matches(rid, role_prefix, role.sequence_id):
            return True
    return False


def _always_on_floor(
    live_roles: Sequence[RoleDef], spec: WorkflowSpec, playbook: PlaybookSpec
) -> frozenset[str]:
    """Whatever ``skills_for_role`` implies for every live role: the un-retirable floor, derived
    rather than listed. Each role's own ``sq-<type>`` implications are subtracted before
    intersecting, or a single live role would sweep its whole resolved list into the floor; an empty
    ``live_roles`` yields the empty set rather than the universal one.
    """
    if not live_roles:
        return frozenset()
    sets: list[frozenset[str]] = []
    for r in live_roles:
        implied = {item_skill_name(t) for t in item_types_for_role(r, spec, playbook)}
        sets.append(frozenset(skills_for_role(r, spec, playbook)) - implied)
    floor = sets[0]
    for s in sets[1:]:
        floor &= s
    return floor


def check_no_live_role(
    index: SquadsDB, spec: WorkflowSpec, active_backends: Sequence[str]
) -> list[ConfigIntegrityFinding]:
    """``no_live_role`` — already broken: no ``role`` entry is live while at least one backend
    is active. With ``active_backends`` empty there is no generated config to break — the
    sq-only squad stays blessed — so the clause stays silent."""
    if not active_backends:
        return []
    if _live_role_items(index, spec):
        return []
    return [
        ConfigIntegrityFinding(
            clause=NO_LIVE_ROLE,
            entry="",
            message=(
                f"no role entry is live, but backend(s) {_cap_and_join(active_backends)} "
                "are active — the generated config can present no agent"
            ),
            remedy="activate another role first",
            removal_remedy="activate another role first",
        )
    ]


def check_preloaded_skill(
    index: SquadsDB,
    spec: WorkflowSpec,
    active_backends: Sequence[str],
    playbook: PlaybookSpec,
    squad_dir: Path | None,
    catalog: CatalogSource,
) -> list[ConfigIntegrityFinding]:
    """``preloaded_skill``: a non-live ``skill`` entry still named by a live role's resolved preload
    list, classified as a stored ``scopes`` edge, a ``sq-<type>`` implication or the always-on
    floor. A skill caught by several kinds yields one finding per kind, ``scoped_edge`` first.
    ``always_on_floor`` does not depend on ``active_backends`` (its authority is the roster
    contract), and the clause stays silent with no live role.
    """
    live_roles = _live_role_items(index, spec)
    if not live_roles:
        return []
    resolved = {r.id: resolve_role_tolerantly(r, squad_dir, catalog=catalog) for r in live_roles}
    floor = _always_on_floor(list(resolved.values()), spec, playbook)
    live_skill_statuses = spec.live_statuses(ROSTER_SKILL)
    findings: list[ConfigIntegrityFinding] = []
    for skill in index.items.values():
        if skill.type != ROSTER_SKILL or skill.status in live_skill_statuses:
            continue
        slug = skill.slug

        if slug in floor:
            findings.append(
                ConfigIntegrityFinding(
                    clause=PRELOADED_SKILL,
                    entry=skill.id,
                    message=(
                        "not live but every role preloads it unconditionally — a permanent "
                        "floor of the roster contract; no remedy exists"
                    ),
                    remedy=None,  # no code path from which one could ever be offered
                    kind=ALWAYS_ON_FLOOR,
                    dependency=(
                        "every role preloads it unconditionally; it is part of the roster's "
                        "permanent floor and cannot be removed"
                    ),
                )
            )
            continue

        if not active_backends:
            # scoped_edge/type_implied both protect a *generated* entry; with no backend
            # there is no entry for either dependency to break.
            continue

        scoped_role_ids: set[str] = set()
        scoped_roles: set[str] = set()
        implicating_types: set[str] = set()
        for role in live_roles:
            role_slug = role.slug
            implicating_types.update(
                t
                for t in item_types_for_role(resolved[role.id], spec, playbook)
                if item_skill_name(t) == slug
            )
            if _scopes_role(skill, role, spec):
                scoped_roles.add(role_slug)
                scoped_role_ids.add(role.id)

        if scoped_roles:
            findings.append(
                ConfigIntegrityFinding(
                    clause=PRELOADED_SKILL,
                    entry=skill.id,
                    message=(
                        f"not live but still scoped to live role(s): {_cap_and_join(scoped_roles)}"
                    ),
                    remedy="pass --unlink, or run `sq skill <addr> unlink-role <role>` first",
                    kind=SCOPED_EDGE,
                    severable_targets=frozenset(scoped_role_ids),
                    dependency=f"scoped to live role(s): {_cap_and_join(scoped_roles)}",
                    removal_remedy="run `sq skill <addr> unlink-role <role>` first",
                )
            )
        if implicating_types:
            findings.append(
                ConfigIntegrityFinding(
                    clause=PRELOADED_SKILL,
                    entry=skill.id,
                    message=(
                        f"not live but implied by declared type(s): "
                        f"{_cap_and_join(implicating_types)}"
                    ),
                    remedy=(
                        "make the skill live again; it stays implied for as long as those "
                        "types are declared, and can retire once no declared type implies it"
                    ),
                    kind=TYPE_IMPLIED,
                    dependency=f"implied by declared type(s): {_cap_and_join(implicating_types)}",
                    removal_remedy=(
                        "it stays implied for as long as those types are declared, and can "
                        "be removed once no declared type implies it"
                    ),
                )
            )
    return findings


def check_all(
    index: SquadsDB,
    spec: WorkflowSpec,
    active_backends: Sequence[str],
    playbook: PlaybookSpec,
    squad_dir: Path | None,
    catalog: CatalogSource,
) -> list[ConfigIntegrityFinding]:
    """Every clause's findings, ``no_live_role`` then ``preloaded_skill``: the one entry point for
    the reporter and the gate, in a fixed order so output is deterministic. ``playbook``,
    *squad_dir* and *catalog* go to ``check_preloaded_skill`` alone, so the floor and type-implied
    kinds reflect overrides.
    """
    return [
        *check_no_live_role(index, spec, active_backends),
        *check_preloaded_skill(index, spec, active_backends, playbook, squad_dir, catalog),
    ]
