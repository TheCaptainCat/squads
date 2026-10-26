"""The roster retirement gate: config-integrity clauses evaluated against a status transition's own
delta, plus its one escape, ``--unlink``. :func:`enforce` runs
:func:`~squads._services._config_integrity.check_all` before and after the transition on one
snapshot and raises only on a finding whose ``(clause, entry, kind)`` key is new, so a squad already
in a refusable state keeps every transition. ``force`` never reaches it.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from squads._errors import ConfigIntegrityError
from squads._interactions._models import PlaybookSpec
from squads._models._index import SquadsDB
from squads._models._item import Item, split_ref
from squads._roles._models import CatalogSource
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
    active spec; empty means not severable. ``preloaded_skill`` resolves to the declared ``preload``
    kind.
    """
    if clause == "preloaded_skill":
        return frozenset({spec.preload_ref_kind()})
    return frozenset()


#: A finding's condition identity for the before/after delta — never its rendering. See
#: :func:`_finding_key`.
type _FindingKey = tuple[Clause, str, Kind | None]


def _finding_key(finding: ConfigIntegrityFinding) -> _FindingKey:
    """The identity of the condition a finding represents, for :func:`enforce`'s before/after delta:
    ``message`` and ``severable_targets`` enumerate live roles and shrink as roles retire, so whole-
    finding equality would misread an improved violation as new.
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
    *kind*. Normally the retiring item's own outgoing edge (a skill's declared-``preload``
    ref to a role), though nothing here assumes that direction — a future clause's edge may
    point the other way, and would sever the same way on whichever item owns it."""

    referrer: str
    target: str
    kind: str


def _sever_declared_edges(
    item: Item, findings: Sequence[ConfigIntegrityFinding], spec: WorkflowSpec
) -> list[Severance]:
    """Remove exactly the edges *findings* enumerated for *item*: only a finding whose ``entry`` is
    *item* and whose clause is severable contributes, via its ``severable_targets``.
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


def enforce(  # noqa: PLR0913 — one keyword per input of the gate
    spec: WorkflowSpec,
    db: SquadsDB,
    item: Item,
    *,
    active_backends: Sequence[str],
    unlink: bool,
    old_status: str,
    playbook: PlaybookSpec,
    squad_dir: Path,
    catalog: CatalogSource,
    purge: bool = False,
) -> list[Severance]:
    """Evaluate the clauses against *item*'s prospective status on this transition's delta, inside
    the transaction snapshot and before any write. *old_status* defines a retirement. With *unlink*
    on a retirement, the edges the violated findings enumerated are severed first; *purge* evaluates
    the retirement a removal implies and never offers ``--unlink``. Returns the edges severed, or
    raises :class:`~squads._errors.ConfigIntegrityError` naming every newly introduced finding.
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
        # No clause names an operator, and retiring the last one is never refused. The exemption
        # comes before severance, so --unlink on an operator transition severs nothing.
        return []

    current_status = item.status
    item.status = old_status
    before_keys = frozenset(
        _finding_key(f) for f in check_all(db, spec, active_backends, playbook, squad_dir, catalog)
    )
    item.status = current_status

    severed: list[Severance] = []
    if unlink:
        prospective = _findings_new_since(
            check_all(db, spec, active_backends, playbook, squad_dir, catalog), before_keys
        )
        severed = _sever_declared_edges(item, prospective, spec)

    after = _findings_new_since(
        check_all(db, spec, active_backends, playbook, squad_dir, catalog), before_keys
    )
    if after:
        # --unlink is a real option only when retiring the finding's own entry; on a finding about
        # another item (a bystander skill a reactivation would preload) it would name a step the
        # tool refuses.
        offer_unlink = is_retirement and not purge
        lines = [
            f"{f.entry or item.id}: "
            + render_finding(f, unlink_available=offer_unlink and f.entry == item.id, removal=purge)
            for f in after
        ]
        header = (
            f"cannot remove {item.id}: other entries depend on it:"
            if purge
            else f"cannot move {item.id} to {item.status!r}: the resulting projection would be "
            "structurally invalid:"
        )
        raise ConfigIntegrityError(header + "\n- " + "\n- ".join(lines))
    return severed


def open_assigned_work(db: SquadsDB, spec: WorkflowSpec, slug: str) -> list[str]:
    """Every open item currently assigned to *slug*, sorted — board hygiene, never a
    config-integrity concern. The caller turns a non-empty result into a warning and proceeds
    regardless; this never raises."""
    return sorted(
        it.id for it in db.items.values() if it.assignee == slug and spec.is_open(it.status)
    )


def lost_default_designation_warning(
    db: SquadsDB,
    spec: WorkflowSpec,
    item: Item,
    squad_dir: Path | None,
    *,
    catalog: CatalogSource,
    purged: bool = False,
) -> str | None:
    """A warning (never a refusal) for a transition that takes the last live ``is_default``
    designation out of a live status, since the generated default-role line and orchestration prose
    lose the name. Returns ``None`` when *item* does not hold the designation or another live role
    does. Both questions go through :func:`~squads._roles._resolver.holds_default_designation`,
    because the catalog can designate a role with nothing stored.
    """
    if not holds_default_designation(item, squad_dir, catalog=catalog):
        return None
    live = spec.live_statuses(item.type)
    if any(
        it.type == item.type
        and it.id != item.id
        and it.status in live
        and holds_default_designation(it, squad_dir, catalog=catalog)
        for it in db.items.values()
    ):
        return None
    slug = item.slug
    message = (
        f"{item.id} ({slug}) carried the default-role designation; no live role carries it "
        "now — designate another live role with `sq role <addr> set-default`"
    )
    return message if purged else f"{message}, or reactivate {item.id}"
