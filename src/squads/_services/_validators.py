"""Pluggable-validator dispatch engine, per the accepted category/validator decision and the
architect's module-boundary pins on the category-axis feature.

Lives in ``_services/``, not ``_models/``/``_workflow/`` — it reads live item + index state
(parent lookups, incoming-supersedes edges, registered-slug set, on-disk body text), exactly
what ``_maintenance.py``'s ``_check_*`` methods hold today via
``self.store``/``self.paths``/``self.spec``. ``_workflow/_models.py`` stays pure value objects,
owning only the ``category`` field itself and the Plane-1 load-time spec-validity checks.

**Phase A (this module, as first landed): no behaviour change.** The engine exists and is wired
at both call sites (``sq check`` report mode, create/update gate mode), but :data:`CATALOG` and
:data:`SQUAD_GLOBAL_CATALOG` are empty — a deliberate no-op. Today's hardcoded ``_check_*``
methods remain the sole source of ``sq check`` output. A later phase lifts each ``_check_*``
into a named catalog entry and populates :data:`CATEGORY_BUNDLES`.

``ItemSpec`` carries only the bare ``category`` name — the effective per-item validator set
(common core + category default bundle + the type's own additions) is resolved here, at call
time, never pre-baked onto the spec.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from squads._errors import SquadsError
from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._services._results import CheckIssue
from squads._workflow._models import WorkflowSpec

#: The on-disk scan map ``_scan_for_check`` builds: sequence number -> (frontmatter id, file
#: path, frontmatter dict). Same shape ``MaintenanceMixin.check()`` already threads through
#: ``_check_reconciliation``/``_check_items`` — ``report()`` takes it for the same reason.
OnDiskMap = dict[int, tuple[str, Path, dict[str, Any]]]


@dataclass(frozen=True)
class ValidatorContext:
    """Everything one per-item validator reads: the item under test, the active spec, and
    precomputed squad-global inputs — mirrors what ``_check_items``/``_check_decisions``
    precompute today (registered-slug set, incoming-``supersedes`` edges, on-disk body text).
    Not yet populated with real data (Phase A has no validator to feed); Phase B's catalog
    entries read these fields instead of re-scanning the index/disk themselves.
    """

    item: Item
    spec: WorkflowSpec
    registered_slugs: frozenset[str] = frozenset()
    supersedes_incoming: frozenset[str] = frozenset()
    on_disk_bodies: dict[str, str] = field(default_factory=lambda: dict[str, str]())


class Validator(Protocol):
    """One named per-item check in the closed catalog: given a :class:`ValidatorContext`,
    returns zero or more :class:`CheckIssue`. Validator *logic* is hard-coded in squads (no
    adopter-supplied code, no ``eval``) — a spec only ever names *which* validators run."""

    def __call__(self, ctx: ValidatorContext) -> list[CheckIssue]: ...


class SquadGlobalValidator(Protocol):
    """One named whole-squad check: runs once per ``sq check``/gate invocation, independent
    of any type's ``category`` — its subject is the squad as a whole, not one item, so it
    attaches to no type's bundle and cannot be deselected."""

    def __call__(self, index: SquadsDB) -> list[CheckIssue]: ...


#: The closed per-item validator catalog — a CODE/definition constant, immutable and shared
#: across every request (fine under the ``_context.py`` CODE-vs-REQUEST split: it varies by
#: neither request nor squad). Phase A ships it empty; a later phase lifts each
#: ``_check_*`` method in as a named entry (e.g. ``"no_parent"``, ``"item_status_valid"``).
CATALOG: dict[str, Validator] = {}

#: The closed squad-global validator registry — same CODE-constant status as ``CATALOG``.
#: Phase A ships it empty; a later phase lifts ``_check_reconciliation``/``_check_backends``
#: in as ``"index_reconciled"``/``"backend_reconciled"``.
SQUAD_GLOBAL_CATALOG: dict[str, SquadGlobalValidator] = {}

#: Cross-cutting per-item hygiene shared by every category (the accepted decision's "common
#: core"): empty in Phase A pending the catalog above.
COMMON_CORE: tuple[str, ...] = ()

#: Per-category default per-item validator-name bundle (per the accepted decision: "a category
#: supplies a default validator bundle"). Every bundle is empty in Phase A — a later phase
#: points each at real catalog entries (e.g. ``records`` gains ``"no_parent"``).
CATEGORY_BUNDLES: dict[str, tuple[str, ...]] = {
    "roster": (),
    "work": (),
    "records": (),
}


def effective_validator_names(
    category: str,
    *,
    common_core: tuple[str, ...] = COMMON_CORE,
    category_bundles: dict[str, tuple[str, ...]] | None = None,
    extra: tuple[str, ...] = (),
) -> tuple[str, ...]:
    """A type's effective per-item validator-name set: common core + its category's default
    bundle + its own additions (the "extend-only floor" — a type may add to a bundle, never
    subtract from it).

    *extra* stands in for a future ``ItemSpec.validators`` field (Phase B); Phase A always
    calls this with none, so today every type's effective set is exactly ``common_core +
    category_bundles[category]`` (both empty, so always ``()``).

    Parameterised on *common_core*/*category_bundles* — not hardcoded to the module
    constants — so a caller (or a test) can exercise the composition against a stub bundle
    before Phase B populates the real one. *category_bundles* defaults to ``None`` (resolved
    to the module-level :data:`CATEGORY_BUNDLES` below) rather than binding the mutable dict
    itself as a parameter default.
    """
    bundles = category_bundles if category_bundles is not None else CATEGORY_BUNDLES
    return common_core + bundles.get(category, ()) + extra


@dataclass(frozen=True)
class ValidatorEngine:
    """Runs the catalog over live item + index state — one engine, two call sites, per the
    accepted category/validator decision. Constructed with the active, per-request ``spec``
    (never a module singleton — rides the same seam as ``Service.spec``).

    ``report()`` collects every issue across both validator classes, for ``sq check``.
    ``gate()`` runs only the one item's per-item set and stops at the first violation, for
    create/update. Squad-global validators never run in gate mode — they are a report-only,
    once-per-invocation check, not a create/update gate.
    """

    spec: WorkflowSpec
    catalog: dict[str, Validator] = field(default_factory=lambda: CATALOG)
    squad_global: dict[str, SquadGlobalValidator] = field(
        default_factory=lambda: SQUAD_GLOBAL_CATALOG
    )

    def _context_for(self, item: Item) -> ValidatorContext:
        return ValidatorContext(item=item, spec=self.spec)

    def _run_per_item(self, item: Item) -> list[CheckIssue]:
        item_spec = self.spec.items.get(item.type)
        if item_spec is None:
            return []  # a dropped/renamed type — not this engine's concern (index cross-check)
        names = effective_validator_names(item_spec.category)
        ctx = self._context_for(item)
        issues: list[CheckIssue] = []
        for name in names:
            issues += self.catalog[name](ctx)
        return issues

    def report(self, index: SquadsDB, on_disk: OnDiskMap) -> list[CheckIssue]:
        """Collect every issue: every item's effective per-item set, plus every squad-global
        validator (run once). An empty catalog contributes nothing — Phase A is a no-op.

        *on_disk* is not yet read by any validator (Phase A's catalog is empty); it is part
        of the surface now so Phase B's on-disk-body validators need no signature change.
        """
        del on_disk  # unused in Phase A — see docstring
        issues: list[CheckIssue] = []
        for item in index.items.values():
            issues += self._run_per_item(item)
        for validator in self.squad_global.values():
            issues += validator(index)
        return issues

    def gate(self, item: Item, index: SquadsDB) -> None:
        """Abort on the first violation of *item*'s own effective per-item set. A no-op when
        the catalog is empty (Phase A) — raises ``SquadsError`` naming the violation once
        Phase B populates real validators. *index* is not yet read (no validator needs
        cross-item lookups yet); kept on the surface for the same forward-compat reason as
        ``report()``'s *on_disk*.
        """
        del index  # unused in Phase A — see docstring
        issues = self._run_per_item(item)
        if issues:
            raise SquadsError(issues[0].message)
