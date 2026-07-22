"""Pluggable-validator dispatch engine, per the accepted category/validator decision and the
architect's module-boundary pins on the category-axis feature.

Lives in ``_services/``, not ``_models/``/``_workflow/`` — it reads live item + index state
(parent lookups, incoming-supersedes edges, registered-slug set, on-disk body text), exactly
what ``_maintenance.py``'s ``_check_*`` methods hold today via
``self.store``/``self.paths``/``self.spec``. ``_workflow/_models.py`` stays pure value objects,
owning only the ``category`` field itself, the closed validator-NAME registries
(``VALIDATOR_NAMES``/``SQUAD_GLOBAL_VALIDATOR_NAMES``), and the Plane-1 load-time spec-validity
checks that read them.

The engine is now the **sole** source of both ``sq check``'s per-item/squad-global issues and
the create/update fail-closed gate — :data:`COMMON_CORE`/:data:`CATEGORY_BUNDLES` are populated
(``no_parent`` on ``records``/``epic`` is withheld to a later, migration-sequenced task) and the
hardcoded ``_check_*`` methods that used to compute this are retired from ``_maintenance.py``.
``gate()`` only aborts on an **error**-level issue — a warn-level one (``agent_registered``,
``no_status_banner``, …) is advisory everywhere, mirroring ``sq check``'s own error-only exit
code; it is never a create/update blocker.

``ItemSpec`` carries only the bare ``category`` name — the effective per-item validator set
(common core + category default bundle + the type's own additions) is resolved here, at call
time, never pre-baked onto the spec.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from squads import _discussion as discussion
from squads import _sections as sections
from squads._backends._base import BackendContext
from squads._backends._registry import get_backend
from squads._interactions import TITLE_ADVISORY_MAX
from squads._models import _markers as markers
from squads._models._extras import ExtraKey as X
from squads._models._index import SquadsDB
from squads._models._item import VALID_REF_KINDS, Item, split_ref
from squads._paths import SquadPaths, number_for_id
from squads._services._results import CheckIssue
from squads._workflow._models import (
    SQUAD_GLOBAL_VALIDATOR_NAMES,
    VALIDATOR_NAMES,
    WorkflowSpec,
)

#: The on-disk scan map ``_scan_for_check`` builds: sequence number -> (frontmatter id, file
#: path, frontmatter dict). Same shape ``MaintenanceMixin.check()`` already threads through
#: ``_check_reconciliation``/``_check_items`` — ``report()`` takes it for the same reason.
type OnDiskMap = dict[int, tuple[str, Path, dict[str, Any]]]

# A leading status/lifecycle banner: "STATUS:" / "**STATUS…**" opening a line, or a
# hand-written "## Status" / "### Status" heading. Anchored so it only matches at the very
# start of the text being checked — never a bare keyword found anywhere in the middle.
# Mirrors ``_maintenance.py``'s detector (the routing task retires that copy once
# ``_check_status_banners`` is decomposed away).
_STATUS_BANNER_RE = re.compile(r"^\*{0,2}status\*{0,2}\s*:", re.IGNORECASE)
_STATUS_HEADING_RE = re.compile(r"^#{2,3}\s*status\s*:?\s*$", re.IGNORECASE)


def _opens_with_status_banner(text: str | None) -> bool:
    """True when *text* opens with a self-declared status/lifecycle banner (leading-line only
    — see ``_maintenance._opens_with_status_banner`` for the full false-positive rationale)."""
    if not text:
        return False
    stripped = text.strip()
    if not stripped:
        return False
    first_line = stripped.splitlines()[0].strip()
    return bool(_STATUS_BANNER_RE.match(first_line) or _STATUS_HEADING_RE.match(first_line))


@dataclass(frozen=True)
class ValidatorContext:
    """Everything one per-item validator reads: the item under test, the active spec, a
    read-only handle on the live index (parent/ref lookups — an O(1) ``.get()``, not a
    rescan), and precomputed squad-global aggregates (registered-slug set, incoming-
    ``supersedes`` sequence numbers) plus the item's own on-disk markdown text.

    ``raw_text`` replaces Phase A's placeholder ``on_disk_bodies: dict[str, str]`` shape now
    that a real validator reads it: a validator is already scoped to *one* item, so the single
    current item's full on-disk text (or ``None`` when its file wasn't found) is what's needed
    — the validator extracts whichever marker section it cares about via
    ``_sections.get_section``, exactly as the ``_check_*`` methods it replaces do.
    """

    item: Item
    spec: WorkflowSpec
    index: SquadsDB | None = None
    registered_slugs: frozenset[str] = frozenset()
    supersedes_incoming: frozenset[int] = frozenset()
    raw_text: str | None = None


@dataclass(frozen=True)
class SquadGlobalContext:
    """Everything one squad-global validator reads: the whole index, the on-disk scan map, the
    active spec, and the squad's resolved paths — the last two let ``backend_reconciled`` build
    the ``BackendContext`` its backend lookups need, mirroring what ``_check_backends`` holds
    via ``self._ctx``/``self._backends()`` today."""

    index: SquadsDB
    on_disk: OnDiskMap
    spec: WorkflowSpec
    paths: SquadPaths


class Validator(Protocol):
    """One named per-item check in the closed catalog: given a :class:`ValidatorContext`,
    returns zero or more :class:`CheckIssue`. Validator *logic* is hard-coded in squads (no
    adopter-supplied code, no ``eval``) — a spec only ever names *which* validators run."""

    def __call__(self, ctx: ValidatorContext) -> list[CheckIssue]: ...


class SquadGlobalValidator(Protocol):
    """One named whole-squad check: runs once per ``sq check``/gate invocation, independent
    of any type's ``category`` — its subject is the squad as a whole, not one item, so it
    attaches to no type's bundle and cannot be deselected."""

    def __call__(self, ctx: SquadGlobalContext) -> list[CheckIssue]: ...


# --------------------------------------------------------------------------- per-item catalog


def _parent_in(ctx: ValidatorContext) -> list[CheckIssue]:
    """Parent-eligibility ← ``_check_items``'s dangling-parent + ``parent_allowed`` branch.

    Reads the structured ``parents`` field via ``spec.parent_allowed`` — no duplicated param.
    An empty ``parents`` list (and no ``no_parent``) is today's lenient "any parent or none".
    """
    item = ctx.item
    if not item.parent:
        return []
    parent = ctx.index.get(item.parent) if ctx.index is not None else None
    if parent is None:
        return [CheckIssue("error", item.id, f"dangling parent {item.parent}")]
    if not ctx.spec.parent_allowed(item.type, parent.type):
        msg = f"{ctx.spec.parent_hint(item.type)} (got {parent.type})"
        return [CheckIssue("error", item.id, msg)]
    return []


def _no_parent(ctx: ValidatorContext) -> list[CheckIssue]:
    """Forbids any parent at all — the explicit opt-in a ``parent_in`` empty allowlist never
    spells (see the architect's pin on the feature). Not yet selected by any bundle."""
    item = ctx.item
    if item.parent:
        return [CheckIssue("error", item.id, f"{item.type} takes no parent (got {item.parent})")]
    return []


def _item_status_valid(ctx: ValidatorContext) -> list[CheckIssue]:
    """← ``_check_items``'s "status invalid for type" branch (named here for the first time —
    it was an unnamed inline check in the hardcoded set)."""
    item = ctx.item
    if item.status not in ctx.spec.workflow_for(item.type).states:
        return [CheckIssue("error", item.id, f"status {item.status!r} invalid for {item.type}")]
    return []


def _dangling_ref(ctx: ValidatorContext) -> list[CheckIssue]:
    """← ``_check_items``'s ref loop, dangling-target half."""
    if ctx.index is None:
        return []
    issues: list[CheckIssue] = []
    for r in ctx.item.refs:
        rid, _kind = split_ref(r)
        if ctx.index.get(rid) is None:
            issues.append(CheckIssue("warn", ctx.item.id, f"dangling ref {rid}"))
    return issues


def _ref_kind_valid(ctx: ValidatorContext) -> list[CheckIssue]:
    """← ``_check_items``'s ref loop, unknown-kind half."""
    issues: list[CheckIssue] = []
    for r in ctx.item.refs:
        rid, kind = split_ref(r)
        if kind not in VALID_REF_KINDS:
            issues.append(
                CheckIssue("warn", ctx.item.id, f"unknown ref kind {kind!r} on edge → {rid}")
            )
    return issues


def _agent_registered(ctx: ValidatorContext) -> list[CheckIssue]:
    """← ``_check_items``'s author/assignee branch: both must resolve to a registered
    roster slug (``ctx.registered_slugs``, precomputed by the engine)."""
    issues: list[CheckIssue] = []
    for attr in ("author", "assignee"):
        slug = getattr(ctx.item, attr)
        if slug and slug not in ctx.registered_slugs:
            issues.append(
                CheckIssue(
                    "warn", ctx.item.id, f"{attr} {slug!r} is not a registered agent or operator"
                )
            )
    return issues


def _subtask_story_mapping(ctx: ValidatorContext) -> list[CheckIssue]:
    """← ``_check_subtask_stories``: a subtask maps to one of its parent's declared stories."""
    item = ctx.item
    kind = ctx.spec.item_subentity_kind(item.type)
    if kind != "subtask":
        return []
    refs = [(s.local_id, s.story) for s in item.subentities if s.story]
    if not refs:
        return []
    parent = ctx.index.get(item.parent) if (ctx.index is not None and item.parent) else None
    required_parent = ctx.spec.item_parent_required(item.type)
    host = required_parent or "parent"
    story_kind = ctx.spec.item_subentity_kind(host) or "story"
    if parent is None or (required_parent is not None and parent.type != required_parent):
        return [
            CheckIssue(
                "error",
                item.id,
                f"{kind} maps to a {story_kind} but the {item.type} has no {host} parent",
            )
        ]
    known = {s.local_id for s in parent.subentities}
    return [
        CheckIssue("error", item.id, f"{kind} {stn} → {us} missing from {parent.id}")
        for stn, us in refs
        if us not in known
    ]


def _subentity_status_valid(ctx: ValidatorContext) -> list[CheckIssue]:
    """← ``_check_subentity_status``."""
    item = ctx.item
    kind = ctx.spec.item_subentity_kind(item.type)
    if kind is None:
        return []
    valid = ctx.spec.subentity_workflow(kind).states
    return [
        CheckIssue("error", item.id, f"{kind} {s.local_id} has invalid status {s.status!r}")
        for s in item.subentities
        if s.status not in valid
    ]


def _subentity_body_written(ctx: ValidatorContext) -> list[CheckIssue]:
    """← ``_check_unwritten_subentity_bodies``: flags a sub-entity body still at its
    kind's placeholder stub, read from ``ctx.raw_text``."""
    item = ctx.item
    kind = ctx.spec.item_subentity_kind(item.type)
    if kind is None or not item.subentities or ctx.raw_text is None:
        return []
    placeholder = discussion.body_placeholder(kind, ctx.spec)
    issues: list[CheckIssue] = []
    for sub in item.subentities:
        body = sections.get_section(ctx.raw_text, discussion.body_tag(kind, sub.local_id))
        if body is not None and body.strip() == placeholder:
            issues.append(
                CheckIssue(
                    "warn",
                    item.id,
                    f"{sub.local_id} body is unwritten (still the placeholder stub)",
                )
            )
    return issues


def _subentity_title_max(ctx: ValidatorContext) -> list[CheckIssue]:
    """← ``_check_subentity_title_lengths``. The one seed validator with a genuine param: the
    ``TITLE_ADVISORY_MAX`` threshold is a module constant, not a structured spec field."""
    item = ctx.item
    kind = ctx.spec.item_subentity_kind(item.type)
    if kind is None:
        return []
    return [
        CheckIssue(
            "warn",
            item.id,
            f"advisory: {kind} {sub.local_id} title is {len(sub.title)} chars"
            f" (threshold: {TITLE_ADVISORY_MAX})"
            " — a sub-entity title is a one-line handle;"
            " put the detail in the body",
        )
        for sub in item.subentities
        if len(sub.title) > TITLE_ADVISORY_MAX
    ]


def _no_status_banner(ctx: ValidatorContext) -> list[CheckIssue]:
    """← ``_check_status_banners``: an item whose body or description opens with a
    self-declared status/lifecycle banner. Body text comes from ``ctx.raw_text``;
    description comes straight from the item."""
    item = ctx.item
    body = sections.get_section(ctx.raw_text, markers.BODY) if ctx.raw_text is not None else None
    if _opens_with_status_banner(body):
        return [
            CheckIssue(
                "warn",
                item.id,
                "body opens with a status/lifecycle banner"
                " — move state to frontmatter or a dated discussion comment",
            )
        ]
    if _opens_with_status_banner(item.description):
        return [
            CheckIssue(
                "warn",
                item.id,
                "description opens with a status/lifecycle banner"
                " — move state to frontmatter or a dated discussion comment",
            )
        ]
    return []


def _supersedes_incoming(ctx: ValidatorContext) -> list[CheckIssue]:
    """← ``_check_decisions``: a Superseded record with no incoming ``supersedes`` edge.
    Only types that declare a ``supersedes`` ref rule are checked."""
    item = ctx.item
    if not any(rr.kind == "supersedes" for rr in ctx.spec.item_ref_rules(item.type)):
        return []
    if (
        ctx.spec.status_role(item.status) == "superseded"
        and item.sequence_id not in ctx.supersedes_incoming
    ):
        return [
            CheckIssue(
                "warn", item.id, f"status is {item.status} but no incoming supersedes edge found"
            )
        ]
    return []


#: The closed per-item validator catalog — a CODE/definition constant, immutable and shared
#: across every request (fine under the ``_context.py`` CODE-vs-REQUEST split: it varies by
#: neither request nor squad). Every ``VALIDATOR_NAMES`` member resolves here (asserted below);
#: no bundle selects any of them yet — that's the routing task.
CATALOG: dict[str, Validator] = {
    "parent_in": _parent_in,
    "no_parent": _no_parent,
    "item_status_valid": _item_status_valid,
    "dangling_ref": _dangling_ref,
    "ref_kind_valid": _ref_kind_valid,
    "agent_registered": _agent_registered,
    "subtask_story_mapping": _subtask_story_mapping,
    "subentity_status_valid": _subentity_status_valid,
    "subentity_body_written": _subentity_body_written,
    "subentity_title_max": _subentity_title_max,
    "no_status_banner": _no_status_banner,
    "supersedes_incoming": _supersedes_incoming,
}
assert set(CATALOG) == VALIDATOR_NAMES, "CATALOG must implement exactly VALIDATOR_NAMES"


# --------------------------------------------------------------------------- squad-global catalog


def _index_reconciled(ctx: SquadGlobalContext) -> list[CheckIssue]:
    """← ``_check_reconciliation``: index and on-disk files agree, compared by sequence
    number (width-tolerant across a repad)."""
    index_seqs = {it.sequence_id for it in ctx.index.items.values()}
    issues = [
        CheckIssue("error", fid, "on disk but not in index (run `sq repair`)")
        for seq, (fid, _md, _data) in ctx.on_disk.items()
        if seq not in index_seqs
    ]
    issues += [
        CheckIssue("error", it.id, "in index but no markdown file found")
        for it in ctx.index.items.values()
        if it.sequence_id not in ctx.on_disk
    ]
    return issues


def _backend_reconciled(ctx: SquadGlobalContext) -> list[CheckIssue]:
    """← ``_check_backends``: each active backend's managed files exist on disk."""
    bctx = BackendContext(paths=ctx.paths, spec=ctx.spec)
    issues: list[CheckIssue] = []
    for name in ctx.paths.config.active_backends:
        backend = get_backend(name)
        for rel_path in backend.managed_paths(bctx):
            full = bctx.root / rel_path
            if not full.exists():
                issues.append(
                    CheckIssue(
                        "error",
                        rel_path,
                        f"managed file missing — run `sq sync` (backend: {backend.name})",
                    )
                )
    return issues


#: The closed squad-global validator registry — same CODE-constant status as ``CATALOG``.
SQUAD_GLOBAL_CATALOG: dict[str, SquadGlobalValidator] = {
    "index_reconciled": _index_reconciled,
    "backend_reconciled": _backend_reconciled,
}
assert set(SQUAD_GLOBAL_CATALOG) == SQUAD_GLOBAL_VALIDATOR_NAMES, (
    "SQUAD_GLOBAL_CATALOG must implement exactly SQUAD_GLOBAL_VALIDATOR_NAMES"
)


# --------------------------------------------------------------------------- context builders


def registered_slugs(index: SquadsDB, spec: WorkflowSpec) -> frozenset[str]:
    """The set of slugs a roster item (role/skill/operator) declares — what
    ``agent_registered`` checks an item's author/assignee against."""
    return frozenset(
        slug
        for r in index.items.values()
        if spec.item_is_roster(r.type)
        for slug in (r.extra.get(X.SLUG),)
        if slug
    )


def supersedes_incoming_seqs(index: SquadsDB) -> frozenset[int]:
    """Sequence numbers of every item with an incoming ``supersedes`` edge — what
    ``supersedes_incoming`` checks a Superseded record's own sequence number against."""
    seqs: set[int] = set()
    for it in index.items.values():
        for r in it.refs:
            rid, kind = split_ref(r)
            if kind == "supersedes":
                seqs.add(number_for_id(rid))
    return frozenset(seqs)


# --------------------------------------------------------------------------- composition + engine

#: Cross-cutting per-item hygiene shared by every category (the accepted decision's "common
#: core"): item status validity, ref resolution/kind, no self-declared status prose, and
#: author/assignee registration.
COMMON_CORE: tuple[str, ...] = (
    "item_status_valid",
    "dangling_ref",
    "ref_kind_valid",
    "no_status_banner",
    "agent_registered",
)

#: Per-category default per-item validator-name bundle (per the accepted decision: "a category
#: supplies a default validator bundle"). Neither ``records``' ``no_parent`` nor ``epic``'s own
#: addition is wired yet — the two deliberate new enforcements are a separate, sequenced task
#: (coordinated with the ADR-migration feature so this repo's own ``sq check`` stays clean).
CATEGORY_BUNDLES: dict[str, tuple[str, ...]] = {
    "roster": (),
    "work": (
        "parent_in",
        "subentity_status_valid",
        "subentity_body_written",
        "subentity_title_max",
        "subtask_story_mapping",
    ),
    "records": ("supersedes_incoming",),
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

    *extra* stands in for the per-type ``ItemSpec.validators`` field (the assignment-surface
    task); until then every caller passes none, so today every type's effective set is exactly
    ``common_core + category_bundles[category]`` (both empty, so always ``()``).

    Parameterised on *common_core*/*category_bundles* — not hardcoded to the module
    constants — so a caller (or a test) can exercise the composition against a stub bundle
    before the routing task populates the real one. *category_bundles* defaults to ``None``
    (resolved to the module-level :data:`CATEGORY_BUNDLES` below) rather than binding the
    mutable dict itself as a parameter default.
    """
    bundles = category_bundles if category_bundles is not None else CATEGORY_BUNDLES
    return common_core + bundles.get(category, ()) + extra


@dataclass(frozen=True)
class ValidatorEngine:
    """Runs the catalog over live item + index state — one engine, two call sites, per the
    accepted category/validator decision. Constructed with the active, per-request ``spec``
    (never a module singleton — rides the same seam as ``Service.spec``).

    ``report()`` collects every issue across both validator classes, for ``sq check``.
    ``gate()`` runs only the one item's own effective per-item set and stops at the first
    **error-level** violation, for create/update — a warn-level catalog issue (e.g.
    ``agent_registered``, ``no_status_banner``) is advisory everywhere, exactly like ``sq
    check``'s exit code (error-only): it never aborts a mutation, only ever gets reported.
    Squad-global validators never run in gate mode — they are a report-only, once-per-
    invocation check, not a create/update gate.

    ``paths`` is required once ``squad_global`` is non-empty (``backend_reconciled`` needs it
    to build a ``BackendContext``); ``report()``'s default construction
    (``ValidatorEngine(spec=..., paths=...)``) always supplies it.
    """

    spec: WorkflowSpec
    paths: SquadPaths | None = None
    catalog: dict[str, Validator] = field(default_factory=lambda: CATALOG)
    squad_global: dict[str, SquadGlobalValidator] = field(
        default_factory=lambda: SQUAD_GLOBAL_CATALOG
    )

    def _run_per_item(
        self,
        item: Item,
        index: SquadsDB,
        *,
        registered: frozenset[str],
        supersedes: frozenset[int],
        raw_text: str | None,
    ) -> list[CheckIssue]:
        item_spec = self.spec.items.get(item.type)
        if item_spec is None:
            return []  # a dropped/renamed type — not this engine's concern (index cross-check)
        names = effective_validator_names(item_spec.category, extra=tuple(item_spec.validators))
        ctx = ValidatorContext(
            item=item,
            spec=self.spec,
            index=index,
            registered_slugs=registered,
            supersedes_incoming=supersedes,
            raw_text=raw_text,
        )
        issues: list[CheckIssue] = []
        for name in names:
            # Strip a documentary `:<param>` suffix before the catalog lookup — every CATALOG
            # key is bare (Plane-1 already rejected a param on a name that doesn't take one).
            issues += self.catalog[name.partition(":")[0]](ctx)
        return issues

    def report(
        self, index: SquadsDB, on_disk: OnDiskMap, *, bodies: dict[int, str] | None = None
    ) -> list[CheckIssue]:
        """Collect every issue: every item's effective per-item set, plus every squad-global
        validator (run once). *bodies* maps sequence number -> the item's on-disk markdown
        text (the caller already read it scanning ``on_disk``); absent/``None`` entries mean
        body-reading validators (``subentity_body_written``, ``no_status_banner``) see no text
        for that item and stay silent, same as when the file could not be resolved.
        """
        registered = registered_slugs(index, self.spec)
        supersedes = supersedes_incoming_seqs(index)
        bodies = bodies or {}
        issues: list[CheckIssue] = []
        for item in index.items.values():
            issues += self._run_per_item(
                item,
                index,
                registered=registered,
                supersedes=supersedes,
                raw_text=bodies.get(item.sequence_id),
            )
        if self.squad_global:
            from squads._errors import SquadsError

            if self.paths is None:
                raise SquadsError("ValidatorEngine.report(): squad-global validators need paths")
            g_ctx = SquadGlobalContext(
                index=index, on_disk=on_disk, spec=self.spec, paths=self.paths
            )
            for validator in self.squad_global.values():
                issues += validator(g_ctx)
        return issues

    def gate(self, item: Item, index: SquadsDB) -> None:
        """Abort on *item*'s first **error-level** violation of its own effective per-item
        set (warn-level issues are report-only, never a gate — see the class docstring).
        ``raw_text`` is never threaded in here: every catalog validator that reads it is
        warn-level, so its absence cannot change a gate decision.
        """
        registered = registered_slugs(index, self.spec)
        supersedes = supersedes_incoming_seqs(index)
        issues = [
            i
            for i in self._run_per_item(
                item, index, registered=registered, supersedes=supersedes, raw_text=None
            )
            if i.level == "error"
        ]
        if issues:
            from squads._errors import SquadsError

            raise SquadsError(issues[0].message)
