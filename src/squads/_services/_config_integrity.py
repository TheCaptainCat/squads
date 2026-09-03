"""Roster config-integrity clauses — ``no_live_role`` and ``preloaded_skill`` — evaluated as
pure predicates over an already-loaded index snapshot rather than a proposed transition.

Shared by two callers that must never restate this logic themselves: the ``sq check`` reporter
(a squad-global validator in ``_services/_validators.py`` calls :func:`check_all` against state
already on disk) and the retirement gate (``_services/_retirement.py`` calls the same functions
against a transaction's prospective snapshot, scoped to the transition's own delta). Every
function here is therefore pure: no I/O, no ``Service`` instance — that purity is what lets one
predicate serve both a reporter over on-disk state and a gate over a transaction snapshot, with
neither restating the other's logic.

Vocabulary note: "live" here is exactly ``WorkflowSpec.live_statuses(item_type)`` membership —
never a role-name-keyed accessor and never a single-status equality: a lifecycle may declare
several live statuses at once, so a cardinality check must test membership in that set, not
equality against one status name.

Clause and kind identifiers (below) are internal vocabulary — code, the per-clause ref-kind
declaration in ``_retirement.py``, and tests. They never appear in user-facing text: a refusal
or a report reads as the condition plus its remedy, nothing else (see :func:`render_finding`).
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

from squads._interactions import item_skill_name, item_types_for_role, skills_for_role
from squads._interactions._models import PlaybookSpec
from squads._models._extras import ExtraKey as X
from squads._models._index import SquadsDB
from squads._models._item import Item, effective_prefix, ref_id_matches, split_ref
from squads._workflow._models import ROSTER_ROLE, ROSTER_SKILL, WorkflowSpec

#: Clause identifiers — internal, never rendered. Named for the condition each checks so the
#: set survives a clause being added or withdrawn. The withdrawn default-role clause
#: (``no_default_role``) has no runtime representation any more; it is recorded only in the
#: decision that governs this module as the history of a clause that was decided and then
#: withdrawn.
type Clause = Literal["no_live_role", "preloaded_skill"]

NO_LIVE_ROLE: Clause = "no_live_role"
PRELOADED_SKILL: Clause = "preloaded_skill"

#: ``preloaded_skill``'s three dependency kinds, named for what holds the dependency, and
#: ordered by the remedy available, from severable to none — an ordering of remedies only,
#: never a severity or an evaluation order, and never a licence to report just one kind a skill
#: happens to be caught by.
type Kind = Literal["scoped_edge", "type_implied", "always_on_floor"]

SCOPED_EDGE: Kind = "scoped_edge"
TYPE_IMPLIED: Kind = "type_implied"
ALWAYS_ON_FLOOR: Kind = "always_on_floor"

#: How many implicating types/roles a finding enumerates before capping and summarising the
#: tail — the same shape a collected conflict report uses, not a protocol limit.
_ENUMERATION_CAP = 5


@dataclass(frozen=True)
class ConfigIntegrityFinding:
    """One clause violation against state already on disk: an entry that a fresh retirement
    transition would refuse, sitting in that state because nothing ever refused it (a squad
    transitioned before the gate existed, or reached some other way). ``entry`` is the roster
    item id the finding is about, or ``""`` when the violation is squad-wide rather than
    attached to one entry (``no_live_role`` — there is no single entry to blame for zero live
    roles).

    ``message`` and ``remedy`` are deliberately two separate fields, not one composed string:
    ``message`` states the *condition* alone — the dependent entity/entities, and for a
    ``sq-<type>`` implication, the implicating type(s) — and never mentions what to do about it.
    ``remedy`` is the specific, satisfiable next step for the direction this finding was
    *computed* in, or ``None`` when no direction ever has one (``always_on_floor``). It is not
    necessarily the remedy every caller renders, though: :func:`render_finding` takes the
    situation the caller is actually in (a retirement in progress, or not) and substitutes a
    direction-appropriate remedy for the one kind whose only stored remedy names a flag
    (``--unlink``) that is not available in every situation a finding can be rendered in — see
    its own docstring. Two callers each render through it — the ``sq check`` reporter (no
    transition in play at all) and the retirement gate (a specific transition, in a specific
    direction) — so the composition happens in exactly one place and neither caller can
    accidentally concatenate two overlapping phrases, or offer a step the caller cannot
    actually perform.

    ``kind`` is ``None`` for ``no_live_role`` (no severable-vs-not classification) and, for
    ``preloaded_skill``, one of the three dependency shapes the retirement gate's ``--unlink``
    cares about: ``scoped_edge`` a stored ``scopes`` edge (severable), ``type_implied`` a
    ``sq-<type>`` implication (not severable, but temporary in principle), ``always_on_floor``
    the permanent floor (not severable, no remedy).

    ``severable_targets`` names the specific item ids a ``scoped_edge`` finding's dependency is
    stored on — empty for every other kind. ``--unlink`` consumes this directly rather than
    re-deriving which edges its own refusal enumerated, which is what keeps the flag from
    severing more than the finding that refused actually named (see ``_retirement.py``).
    """

    clause: Clause
    entry: str
    message: str
    remedy: str | None = None
    kind: Kind | None = None
    severable_targets: frozenset[str] = frozenset()


#: ``scoped_edge``'s remedy when the caller is not a retirement of the finding's own ``entry`` —
#: the reporter (no transition in play), or the retirement gate rendering this finding on a
#: *reactivation* (the finding's entry is a bystander skill, not the item transitioning, so
#: ``--unlink`` is refused as meaningless on that command). Never mentions ``--unlink``, the one
#: step neither situation can actually perform.
_SCOPED_EDGE_NO_UNLINK_REMEDY = (
    "sever the edge with `sq skill <addr> unlink-role <role>`, or reactivate the skill"
)


def render_finding(finding: ConfigIntegrityFinding, *, unlink_available: bool = False) -> str:
    """The finding's condition, plus its remedy when one exists — the single place
    ``message``/``remedy`` are ever concatenated, so the two halves are joined exactly once and
    never twice, and every caller renders the identical *condition* text for the same finding:
    they are two renderings of one predicate, and neither forks the wording for its own caller.

    The *remedy*, unlike the condition, is a property of the caller's own situation rather than
    of the predicate: ``--unlink`` is only ever a real option when the caller is a retirement in
    progress of the finding's own ``entry`` — never on the ``sq check`` reporter, which has no
    transition in play, and never on the retirement gate rendering a finding on a *different*
    transition's own item (a reactivation that would preload an already-non-live skill; the
    finding names that skill, not the role actually transitioning). ``unlink_available`` (default
    ``False``, matching the reporter's no-transition situation) is what lets one call site say so.
    Only ``scoped_edge``'s stored remedy ever varies by it — every other kind's remedy already
    holds regardless of direction.
    """
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
    """Whether *skill* carries a forward ``preload``-role ref to *role* — the ``scoped_edge``
    stored edge, read directly off the skill's own ``refs`` (the skill is always the referrer
    today), never inverted via ``backrefs`` since both ends are already in hand. Resolved
    through the declared ``preload`` semantic (:meth:`WorkflowSpec.preload_ref_kind`), never
    the bundled ``"scopes"`` spelling."""
    role_prefix = effective_prefix(role.prefix)
    preload_kind = spec.preload_ref_kind()
    for r in skill.refs:
        rid, kind = split_ref(r)
        if kind == preload_kind and ref_id_matches(rid, role_prefix, role.sequence_id):
            return True
    return False


def _always_on_floor(
    live_roles: Sequence[Item], spec: WorkflowSpec, playbook: PlaybookSpec | None = None
) -> frozenset[str]:
    """Whatever ``skills_for_role`` implies for *every* live role — the un-retirable floor,
    derived rather than a hand-maintained list of names: that formulation survives a rename and
    survives the set growing or shrinking, without a blocklist to maintain.

    Each role's own contribution is first stripped of *that role's own* ``sq-<type>``
    implications before the sets are intersected — never the resolved list as-is. Without that
    subtraction, a squad with exactly one live role would see the intersection collapse to that
    one role's *entire* resolved list (an intersection of one set is the set itself), sweeping
    its type-implied skills into the permanent floor by coincidence of roster size rather than
    by declared authority. Subtracting first keeps the floor exactly the always-on trio
    regardless of how many roles are live, not merely when two or more happen to disagree on
    their type-implied extras.

    An intersection over zero roles is mathematically the universal set, which would wrongly
    floor every non-live skill — guarded to the empty set instead. In practice this function is
    only ever called with a non-empty *live_roles* (its one caller already returns early when
    there are none), but the guard keeps the property honest standalone rather than relying on
    that caller discipline.
    """
    if not live_roles:
        return frozenset()
    sets: list[frozenset[str]] = []
    for r in live_roles:
        slug = r.extra.get(X.SLUG, r.slug)
        implied = {item_skill_name(t) for t in item_types_for_role(slug, spec, playbook)}
        sets.append(frozenset(skills_for_role(slug, spec, playbook)) - implied)
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
        )
    ]


def check_preloaded_skill(
    index: SquadsDB,
    spec: WorkflowSpec,
    active_backends: Sequence[str],
    playbook: PlaybookSpec | None = None,
) -> list[ConfigIntegrityFinding]:
    """``preloaded_skill`` — a referenced skill, already broken: a non-live ``skill`` entry
    still named by a live role's resolved preload list. Classified into three kinds — a stored
    ``scopes`` edge, a ``sq-<type>`` implication, or the always-on floor — because the kind
    changes the message and the available remedy, never the detection itself. A skill can be
    caught by more than one kind at once; each is reported as its own finding, in the declared
    severable-to-none order: ``scoped_edge`` before ``type_implied``.

    ``always_on_floor`` is the one kind not conditioned on ``active_backends``: its authority is
    a declared rule of the roster contract, not a derived property of the
    projection, so it still refuses in a squad with no active backend. Its other condition is
    unchanged and is about roles, not backends — a property quantified over every live role is
    vacuous when there are none, so the whole clause stays silent with no live role at all.
    """
    live_roles = _live_role_items(index, spec)
    if not live_roles:
        return []
    floor = _always_on_floor(live_roles, spec, playbook)
    live_skill_statuses = spec.live_statuses(ROSTER_SKILL)
    findings: list[ConfigIntegrityFinding] = []
    for skill in index.items.values():
        if skill.type != ROSTER_SKILL or skill.status in live_skill_statuses:
            continue
        slug = skill.extra.get(X.SLUG, skill.slug)

        if slug in floor:
            findings.append(
                ConfigIntegrityFinding(
                    clause=PRELOADED_SKILL,
                    entry=skill.id,
                    message=(
                        f"not live (status {skill.status!r}) but every role preloads it "
                        "unconditionally — a permanent floor of the roster contract; no "
                        "remedy exists"
                    ),
                    remedy=None,  # no code path from which one could ever be offered
                    kind=ALWAYS_ON_FLOOR,
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
            role_slug = role.extra.get(X.SLUG, role.slug)
            implicating_types.update(
                t
                for t in item_types_for_role(role_slug, spec, playbook)
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
                        f"not live (status {skill.status!r}) but still scoped to live "
                        f"role(s): {_cap_and_join(scoped_roles)}"
                    ),
                    remedy="pass --unlink, or run `sq skill <addr> unlink-role <role>` first",
                    kind=SCOPED_EDGE,
                    severable_targets=frozenset(scoped_role_ids),
                )
            )
        if implicating_types:
            findings.append(
                ConfigIntegrityFinding(
                    clause=PRELOADED_SKILL,
                    entry=skill.id,
                    message=(
                        f"not live (status {skill.status!r}) but implied by declared "
                        f"type(s): {_cap_and_join(implicating_types)}"
                    ),
                    # item_types_for_role is threaded the active spec, so dropping the
                    # implicating type genuinely un-implies the skill — the remedy names
                    # that action rather than disclaiming it.
                    remedy=(
                        "make the skill live again, or drop the implicating type via "
                        "`[selected]` in .overrides/workflow.toml"
                    ),
                    kind=TYPE_IMPLIED,
                )
            )
    return findings


def check_all(
    index: SquadsDB,
    spec: WorkflowSpec,
    active_backends: Sequence[str],
    playbook: PlaybookSpec | None = None,
) -> list[ConfigIntegrityFinding]:
    """Every clause's findings, ``no_live_role`` then ``preloaded_skill`` — the single entry
    point both the reporter and the gate call, rather than each composing the clauses itself.
    This fixed clause order, together with ``check_preloaded_skill``'s declared per-skill kind
    order, is what makes output deterministic wherever more than one finding renders together.

    ``playbook`` defaults to the bundled singleton (``None``) — passed through to
    ``check_preloaded_skill`` alone, since ``no_live_role`` never reads playbook data. A caller
    with the active/merged playbook in hand (``Service.playbook``) threads it explicitly so the
    always-on floor and type-implied kind reflect a project override's guidance changes.
    """
    return [
        *check_no_live_role(index, spec, active_backends),
        *check_preloaded_skill(index, spec, active_backends, playbook),
    ]
