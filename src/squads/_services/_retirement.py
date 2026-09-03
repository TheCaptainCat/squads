"""The roster retirement gate: config-integrity clauses evaluated against a status transition's
own delta, plus its one mechanised escape, ``--unlink``.

Reuses the pure predicates in ``_config_integrity.py`` unchanged (:func:`check_all`) rather than
re-deriving the clauses here — this module's whole job is enforcement (raise or proceed) and the
one escape that satisfies ``preloaded_skill`` by editing the snapshot before re-evaluating, never
a second detection pass.

**Delta-scoped, not whole-squad.** A clause answers whether *this* transition
breaks something that was not already broken, never "is this squad currently well-formed": a
squad already sitting in a state a clause would refuse keeps every transition available to it,
the repairing ones included. :func:`enforce` evaluates :func:`~squads._services._config_integrity
.check_all` twice against the same snapshot — once with *item*'s status reverted to what it was
before this call, once with the transition applied — and raises only on a finding whose
*condition* (its ``(clause, entry, kind)`` key) is absent from the first pass. That key, not
whole-object equality, is what the comparison has to use: ``message`` and ``severable_targets``
both enumerate the currently-live roles/types, so a pre-existing violation whose enumeration
merely *shrinks* is a different object under equality and would misread as newly introduced —
refusing a transition for a condition it strictly improved. Pre-existing invalidity stays the
report-mode validator's business alone (``_services/_validators.py``).

Called from ``_set_status_model``'s pure pre-write half, before any file is touched — the same
seam the bulk importer's pre-pass calls, so a replayed history is held to the same rule at each
step it replays. ``force`` (the lifecycle's own transition-edge override) never reaches this
module: the clauses are structural and unconditional, evaluated regardless of whether the caller
asked to force the lifecycle edge.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from squads._errors import ConfigIntegrityError
from squads._interactions._models import PlaybookSpec
from squads._models._extras import ExtraKey as X
from squads._models._index import SquadsDB
from squads._models._item import Item, split_ref
from squads._roles._resolver import holds_default_designation
from squads._services._config_integrity import (
    Clause,
    ConfigIntegrityFinding,
    Kind,
    check_all,
    render_finding,
)
from squads._workflow import ROSTER_OPERATOR
from squads._workflow._models import WorkflowSpec


def _clause_ref_kinds(clause: Clause, spec: WorkflowSpec) -> frozenset[str]:
    """The stored ref-kind edge(s) that constitute *clause*'s dependency, resolved through the
    active spec's declared semantics — empty means "not severable": ``no_live_role``'s
    dependency is a cardinality property of the projection, not a reference. ``preloaded_skill``
    resolves to the one declared ``preload``-role kind (:meth:`WorkflowSpec.preload_ref_kind`),
    never a fixed spelling. Declared here, next to this module's ``--unlink`` (its only
    consumer): a clause resolving a non-empty set inherits the flag with no code change here
    if it ever gains a severable formulation.
    """
    if clause == "preloaded_skill":
        return frozenset({spec.preload_ref_kind()})
    return frozenset()


#: A finding's condition identity for the before/after delta — never its rendering. See
#: :func:`_finding_key`.
type _FindingKey = tuple[Clause, str, Kind | None]


def _finding_key(finding: ConfigIntegrityFinding) -> _FindingKey:
    """The identity of the *condition* a finding represents, for the before/after delta in
    :func:`enforce` — deliberately not the finding object itself. ``message`` and
    ``severable_targets`` both enumerate the currently-live roles or types satisfying the
    condition, so comparing whole ``ConfigIntegrityFinding`` objects makes two findings over the
    exact same condition compare unequal the moment that enumeration merely shrinks — a
    pre-existing violation one live role's retirement strictly improves would then read as newly
    introduced. ``(clause, entry, kind)`` is already on the dataclass, identifies the condition
    rather than its rendering, and is stable across that enumeration changing size in either
    direction.
    """
    return (finding.clause, finding.entry, finding.kind)


def _findings_new_since(
    findings: Sequence[ConfigIntegrityFinding], before_keys: frozenset[_FindingKey]
) -> list[ConfigIntegrityFinding]:
    """*findings* whose condition key (:func:`_finding_key`) is absent from *before_keys* — the
    delta itself, factored out so the severance pass and the final refusal pass in
    :func:`enforce` compute it the same way."""
    return [f for f in findings if _finding_key(f) not in before_keys]


@dataclass(frozen=True)
class Severance:
    """One reference edge ``--unlink`` removed: *referrer* stopped referencing *target* via
    *kind*. Always the retiring item's own outgoing edge today (a skill's declared-``preload``
    ref to a role), though nothing here assumes that direction — a future clause's edge may
    point the other way, and would sever the same way on whichever item owns it."""

    referrer: str
    target: str
    kind: str


def _sever_declared_edges(
    item: Item, findings: Sequence[ConfigIntegrityFinding], spec: WorkflowSpec
) -> list[Severance]:
    """Remove exactly the edges *findings* enumerated for *item* — never every severable-kind
    ref on the item regardless of whether a finding named it.

    Only a finding whose own ``entry`` is *item* and whose clause resolves (via
    :func:`_clause_ref_kinds`) a non-empty kind set contributes targets, via that finding's own
    ``severable_targets`` — the specific ids its dependency was detected on, never the item's
    whole ref list matched against the clause's kind set alone.
    """
    to_sever: set[tuple[str, str]] = set()
    for f in findings:
        if f.entry != item.id:
            continue
        kinds = _clause_ref_kinds(f.clause, spec)
        if not kinds:
            continue
        to_sever.update((target, kind) for target in f.severable_targets for kind in kinds)

    kept: list[str] = []
    severed: list[Severance] = []
    for r in item.refs:
        rid, kind = split_ref(r)
        if (rid, kind) in to_sever:
            severed.append(Severance(referrer=item.id, target=rid, kind=kind))
        else:
            kept.append(r)
    item.refs = kept
    return severed


def enforce(
    spec: WorkflowSpec,
    db: SquadsDB,
    item: Item,
    *,
    active_backends: Sequence[str],
    unlink: bool,
    old_status: str,
    playbook: PlaybookSpec | None = None,
) -> list[Severance]:
    """Evaluate the clauses against *item*'s already-applied prospective status, scoped to this
    transition's own delta, inside the transaction's own snapshot and before any write.

    *old_status* is *item*'s status before this call's own change (already in hand at the call
    site, captured before :meth:`~squads._services._items.ItemsMixin._apply_status` mutates it)
    — needed both to define a retirement (a move *out of* a live status, never merely "the new
    status is not live") and to compute the pre-transition snapshot the delta is measured
    against.

    When *unlink* is set on a retirement, sever the edges the *violated* finding(s) actually
    enumerated for *item* first (in the same snapshot) and let the same unforced evaluation
    below run and pass on its own merits — the flag suppresses nothing, and it never severs an
    edge no finding named. A transition still refused raises before anything is written, so the
    caller's transaction never commits a partial severance.

    Returns the edges severed (possibly empty — a reported no-op is the caller's to print).
    Raises :class:`~squads._errors.ConfigIntegrityError`, naming every finding this transition
    newly introduces (via :func:`~squads._services._config_integrity.render_finding` — the one
    place condition and remedy are ever composed, so this line never duplicates a phrase the
    finding's own ``message`` already states), on any violation this transition introduces —
    including one ``--unlink`` did not fix.
    """
    live = spec.live_statuses(item.type)
    is_retirement = old_status in live and item.status not in live
    if unlink and not is_retirement:
        raise ConfigIntegrityError(
            f"--unlink is meaningless here: {item.id} is moving from {old_status!r} to "
            f"{item.status!r}, which is not a move out of a live status — the flag only "
            "applies to a retirement"
        )
    if item.type == ROSTER_OPERATOR:
        # No clause names an operator: an operator list may legitimately be empty, and
        # retiring the last one is never refused. The exemption comes before severance —
        # "no clause names an operator" is not "an operator transition severs unconditionally"
        # — so --unlink on an operator transition severs nothing.
        return []

    current_status = item.status
    item.status = old_status
    before_keys = frozenset(_finding_key(f) for f in check_all(db, spec, active_backends, playbook))
    item.status = current_status

    severed: list[Severance] = []
    if unlink:
        prospective = _findings_new_since(
            check_all(db, spec, active_backends, playbook), before_keys
        )
        severed = _sever_declared_edges(item, prospective, spec)

    after = _findings_new_since(check_all(db, spec, active_backends, playbook), before_keys)
    if after:
        # --unlink is only ever a real option on THIS command when it is a retirement of the
        # finding's own entry — never on a finding rendered here about some other item (e.g. a
        # bystander skill a reactivation would preload), where "pass --unlink" would name a
        # step the tool refuses.
        lines = [
            f"{f.entry or item.id}: "
            f"{render_finding(f, unlink_available=is_retirement and f.entry == item.id)}"
            for f in after
        ]
        raise ConfigIntegrityError(
            f"cannot move {item.id} to {item.status!r}: the resulting projection would be "
            "structurally invalid:\n- " + "\n- ".join(lines)
        )
    return severed


def open_assigned_work(db: SquadsDB, spec: WorkflowSpec, slug: str) -> list[str]:
    """Every open item currently assigned to *slug*, sorted — board hygiene, never a
    config-integrity concern. The caller turns a non-empty result into a warning and proceeds
    regardless; this never raises."""
    return sorted(
        it.id for it in db.items.values() if it.assignee == slug and spec.is_open(it.status)
    )


def lost_default_designation_warning(
    db: SquadsDB, spec: WorkflowSpec, item: Item, squad_dir: Path | None
) -> str | None:
    """A warning (never a refusal — the withdrawn ``no_default_role`` clause) for a transition
    that takes the last live ``is_default`` designation out of a live status: the generated
    config's default-role line and orchestration prose both lose the name they read off it.
    ``sq role <addr> set-default`` (:meth:`~squads._services._roster.RosterMixin
    .set_default_role`) moves the designation to another live role; reactivating *item* is the
    other way back.

    Same shape as :func:`open_assigned_work`'s board-hygiene warning: never blocks, only
    informs. Returns ``None`` when *item* does not hold the designation, or another live role
    already does.

    Both questions go through :func:`~squads._roles._resolver.holds_default_designation`,
    never a raw ``extra.is_default`` read: the stored key is an override on a designation the
    role catalog also answers, so the catalog's own designated role holds it with nothing
    stored — and a raw read would stay silent on exactly the retirement that costs the
    generated config its default-role line.
    """
    if not holds_default_designation(item, squad_dir):
        return None
    live = spec.live_statuses(item.type)
    if any(
        it.type == item.type
        and it.id != item.id
        and it.status in live
        and holds_default_designation(it, squad_dir)
        for it in db.items.values()
    ):
        return None
    slug = item.extra.get(X.SLUG, item.slug)
    return (
        f"{item.id} ({slug}) carried the default-role designation; no live role carries it "
        "now — designate another live role with `sq role <addr> set-default`, or reactivate "
        f"{item.id}"
    )
