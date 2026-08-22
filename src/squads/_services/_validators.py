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
the create/update fail-closed gate — ``COMMON_CORE``/``CATEGORY_BUNDLES`` (defined in
``_workflow/_models.py``, so the Plane-1 spec-validity pass can resolve the same effective set
this engine runs) are populated,
including ``no_parent`` on the ``records`` bundle and as ``epic``'s own ``validators`` addition,
and the hardcoded ``_check_*`` methods that used to compute this are retired from
``_maintenance.py``. One catalog member, ``parent_present``, sits in no bundle at all and is
reachable only through a type's own ``validators`` list — see its docstring for why that is the
decision and not an omission.
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
from squads._interactions import (
    TITLE_ADVISORY_MAX,
    is_live_roster_entry,
    orphaned_playbook_guide_message,
    orphaned_playbook_guides,
)
from squads._interactions._loader import playbook_override_guide_pairs
from squads._interactions._models import PlaybookSpec
from squads._models import _markers as markers
from squads._models._extras import ExtraKey as X
from squads._models._index import SquadsDB
from squads._models._item import VALID_REF_KINDS, Item, split_ref
from squads._paths import SquadPaths, number_for_id
from squads._services import _config_integrity as config_integrity
from squads._services._results import CheckIssue
from squads._workflow._models import (
    ROSTER_ROLE,
    ROSTER_SKILL,
    SQUAD_GLOBAL_VALIDATOR_NAMES,
    VALIDATOR_NAMES,
    WorkflowSpec,
    effective_validator_names,
)

#: The on-disk scan map ``_scan_for_check`` builds: sequence number -> (frontmatter id, file
#: path, frontmatter dict). Same shape ``MaintenanceMixin.check()``'s scan pass and its one
#: confirm pass both thread through — ``report()`` takes it for the same reason.
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
    via ``self._ctx``/``self._backends()`` today.

    ``playbook`` (defaulting to ``None``) is read by two validators:
    ``roster_config_integrity`` threads it to ``config_integrity.check_all`` so a project's
    merged playbook, not the bundled one, decides the always-on skill floor, and
    ``playbook_guide_role_live`` reads its per-type guides directly. ``report()``'s own
    construction always supplies ``Service.playbook``, so the ``None`` default only ever
    describes a caller that has no playbook to offer at all.
    """

    index: SquadsDB
    on_disk: OnDiskMap
    spec: WorkflowSpec
    paths: SquadPaths
    playbook: PlaybookSpec | None = None


class Validator(Protocol):
    """One named per-item check in the closed catalog: given a :class:`ValidatorContext`,
    returns zero or more :class:`CheckIssue`. Validator *logic* is hard-coded in squads (no
    adopter-supplied code, no ``eval``) — a spec only ever names *which* validators run."""

    def __call__(self, ctx: ValidatorContext) -> list[CheckIssue]: ...


class SquadGlobalValidator(Protocol):
    """One named whole-squad check: runs once per ``sq check``/gate invocation, independent
    of any type's ``category`` — its subject is the squad as a whole, not one item, so it
    attaches to no type's bundle and cannot be deselected.

    Standing requirement: a validator that is **cross-source** — any claim that compares the
    on-disk scan against the index snapshot, as ``index_reconciled`` does — must be evaluable
    for a single item id, or it cannot be confirmed by ``check``'s one-round confirm pass and
    does not belong in this catalog. Shape a new cross-source check as a
    small ``(single item, freshly observed pair) -> CheckIssue | None`` predicate (see
    ``on_disk_not_indexed``/``not_on_disk`` below) that the whole-scan pass and the confirm
    pass both call unchanged — never inline the comparison in the squad-global loop itself,
    or the two passes will have their own copies to drift apart. A validator that only reads
    the disk (``backend_reconciled``) carries no such requirement — nothing racing a
    concurrent item mutation can make it flicker.
    """

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
    """Forbids any parent at all — the explicit opt-in that an empty ``parent_in`` allowlist
    deliberately does not imply. Selected by the ``records`` bundle and by ``epic``."""
    item = ctx.item
    if item.parent:
        return [CheckIssue("error", item.id, f"{item.type} takes no parent (got {item.parent})")]
    return []


def _parent_present(ctx: ValidatorContext) -> list[CheckIssue]:
    """Requires a parent — the mandatory half of the parent vocabulary, which ``parents`` and
    ``no_parent`` between them could not express.

    ``parents`` is an *eligibility* allowlist: it says which type a parent may be, never that
    there must be one, so ``parents = ["feature"]`` reads as "a feature or nothing". This is the
    validator that closes that gap, and the only one defined over ``parent_required``'s
    requiredness: with it effective, an item created with no parent is refused, naming the
    declared type when the spec declares one.

    **In no** :data:`~squads._workflow._models.CATEGORY_BUNDLES` **entry, deliberately.** A type
    turns it on by naming it in its own ``validators`` — the same extend-only opt-in the
    sub-entity clause documents. The bundled spec does not, and that is a decision rather than an
    oversight: ``gate()`` and ``report()`` run one effective name set, so a validator that
    refuses a parentless item at create also errors on every parentless item already on disk.
    Putting this in the ``work`` bundle would therefore not be "new items must have a parent", it
    would be "every historical bare item is now a ``sq check`` error", with no migration able to
    invent a parent for them. Opt-in keeps the declaration honest for the adopter who wants it
    and leaves every existing corpus alone.
    """
    item = ctx.item
    if item.parent:
        return []
    required = ctx.spec.item_parent_required(item.type)
    of_type = f" of type {required}" if required else ""
    return [CheckIssue("error", item.id, f"{item.type} requires a parent{of_type}")]


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
    ks = ctx.spec.subentity_kinds.get(kind) if kind is not None else None
    if ks is None or not ks.maps_parent_story:
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


def _subentity_container_marker(ctx: ValidatorContext) -> list[CheckIssue]:
    """The item's on-disk container marker still matches the plural its kind declares.

    ``subentity_kinds.<kind>.plural`` is the persisted container-marker name, so it is a
    corpus-alignment field exactly like a type's ``prefix`` or ``folder`` — but unlike those
    two it leaves no witness in the index, so the loader's live-index cross-check cannot see
    it and ``sq workflow lint`` (which never opens an item file) has no way to. This is the
    only plane that can: ``sq check`` already holds each item's on-disk text.

    Renaming the plural against an existing corpus half-bricks it rather than breaking it,
    which is why it needs its own report. ``add-<kind>`` fails — it looks for a container the
    files do not carry — while sub-entity *body* writes keep succeeding, because those address
    their own per-block markers. So the corpus stays usable enough to look fine, and both
    gates said clean. Both directions are covered, because the plural can move either way:
    declaring one over an existing corpus, and removing the declaration afterwards.
    """
    item = ctx.item
    kind = ctx.spec.item_subentity_kind(item.type)
    if kind is None or ctx.raw_text is None:
        return []
    plural = ctx.spec.subentity_plural(kind)
    if sections.has_section(ctx.raw_text, plural):
        return []
    # Name the tag the file DOES carry: that is the difference between "your override renamed
    # this" and "this file is malformed", and it is the fact that tells the adopter which way
    # to fix it. A container is the only top-level marker in an item file that is not one of
    # the three fixed structural tags and not a sub-entity block tag (those are ``kind:LOCAL``,
    # so they carry a colon) — derived that way rather than matched against the *declared*
    # plurals, because the whole point is that the file carries an UNdeclared one, and the old
    # name it carries need not be declared anywhere any more.
    structural = {markers.BODY, markers.SUMMARY, markers.DISCUSSION, plural}
    tags = {
        tag.removeprefix(markers.PREFIX).removesuffix(":end")
        for tag in sections.find_markers(ctx.raw_text)
    }
    stale = sorted(tag for tag in tags if ":" not in tag and tag not in structural)
    found = f"; the file carries {stale[0]!r}" if stale else ""
    return [
        CheckIssue(
            "error",
            item.id,
            f"no {plural!r} container section{found} — {kind!r} declares plural {plural!r}, "
            f"so `sq {item.type} {item.sequence_id} add-{kind}` cannot write here. Revert "
            f"subentity_kinds.{kind}.plural in the workflow override, or change it only "
            f"while no {item.type} items exist",
        )
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
#: neither request nor squad). Every ``VALIDATOR_NAMES`` member resolves here (asserted below).
CATALOG: dict[str, Validator] = {
    "parent_in": _parent_in,
    "no_parent": _no_parent,
    "parent_present": _parent_present,
    "item_status_valid": _item_status_valid,
    "dangling_ref": _dangling_ref,
    "ref_kind_valid": _ref_kind_valid,
    "agent_registered": _agent_registered,
    "subtask_story_mapping": _subtask_story_mapping,
    "subentity_status_valid": _subentity_status_valid,
    "subentity_container_marker": _subentity_container_marker,
    "subentity_body_written": _subentity_body_written,
    "subentity_title_max": _subentity_title_max,
    "no_status_banner": _no_status_banner,
    "supersedes_incoming": _supersedes_incoming,
}
assert set(CATALOG) == VALIDATOR_NAMES, "CATALOG must implement exactly VALIDATOR_NAMES"


# --------------------------------------------------------------------------- squad-global catalog


def on_disk_not_indexed(seq: int, fid: str, *, indexed: bool) -> CheckIssue | None:
    """One direction of ``_index_reconciled``, factored to a single-item predicate so
    ``check``'s confirm round in ``_maintenance.py`` can re-run this exact comparison against
    a freshly loaded index's membership for just this candidate — never a second copy."""
    if indexed:
        return None
    return CheckIssue("error", fid, "on disk but not in index (run `sq repair`)")


def not_on_disk(item: Item, *, on_disk: bool) -> CheckIssue | None:
    """The other direction of ``_index_reconciled`` — same reuse rationale as
    ``on_disk_not_indexed``."""
    if on_disk:
        return None
    return CheckIssue("error", item.id, "in index but no markdown file found")


def _index_reconciled(ctx: SquadGlobalContext) -> list[CheckIssue]:
    """← ``_check_reconciliation``: index and on-disk files agree, compared by sequence
    number (width-tolerant across a repad). The whole-scan pass over the pair; ``check``'s
    confirm pass re-runs ``on_disk_not_indexed``/``not_on_disk`` directly, one candidate at
    a time, rather than calling this function again — a full rescan would reintroduce the
    cost the lock-free design exists to avoid."""
    index_seqs = {it.sequence_id for it in ctx.index.items.values()}
    on_disk_seqs = set(ctx.on_disk)
    issues = [
        issue
        for seq, (fid, _md, _data) in ctx.on_disk.items()
        if (issue := on_disk_not_indexed(seq, fid, indexed=seq in index_seqs)) is not None
    ]
    issues += [
        issue
        for it in ctx.index.items.values()
        if (issue := not_on_disk(it, on_disk=it.sequence_id in on_disk_seqs)) is not None
    ]
    return issues


def live_roster_slugs(ctx: SquadGlobalContext) -> tuple[frozenset[str], frozenset[str]]:
    """The roster-scoped ``(live role slugs, live skill slugs)`` pair
    :func:`backend_entry_candidates` hands to each backend's ``managed_entry_paths`` — derived
    from ``ctx.index`` via :func:`~squads._interactions.is_live_roster_entry`, the exact
    predicate ``ServiceCore._project_roster_item`` uses to materialise/withdraw. Never a fixed
    or historical slug list, so a retire/reactivate cycle can never leave a false positive (the
    retired side) or a false negative (the reactivated side) on either backend.

    Not underscored: :meth:`MaintenanceMixin._confirm_cross_source` calls this a second time,
    against a freshly reloaded index, to recompute the live set a per-entry candidate is
    confirmed against — see :func:`backend_entry_missing`.
    """
    roles = frozenset(
        slug
        for it in ctx.index.items.values()
        if it.type == ROSTER_ROLE
        and is_live_roster_entry(it, ctx.spec)
        and (slug := it.extra.get(X.SLUG))
    )
    skills = frozenset(
        slug
        for it in ctx.index.items.values()
        if it.type == ROSTER_SKILL
        and is_live_roster_entry(it, ctx.spec)
        and (slug := it.extra.get(X.SLUG))
    )
    return roles, skills


def _backend_reconciled(ctx: SquadGlobalContext) -> list[CheckIssue]:
    """← ``_check_backends``: each active backend's fixed top-level managed files exist on
    disk — reported at **error**, since nothing short of ``sq sync`` explains their absence
    away. Reads only ``ctx.paths.config.active_backends`` and the disk, never ``ctx.index``,
    so — unlike the per-entry roster pointer check below — nothing racing a concurrent item
    mutation can make this one flicker; it needs no confirm round.

    A per-entry roster pointer (``managed_entry_paths``) is a *different* claim, reported at
    **warn** for reasons stated where it now lives: :func:`backend_entry_candidates` and
    :func:`backend_entry_missing`, confirmed through ``check``'s one confirm round exactly like
    ``index_reconciled``'s two directions (see :meth:`MaintenanceMixin._confirm_cross_source`).
    It used to be computed here, unconfirmed, until making it roster- (and therefore
    index-) derived turned it cross-source.
    """
    bctx = BackendContext(paths=ctx.paths, spec=ctx.spec)
    issues: list[CheckIssue] = []
    for name in ctx.paths.config.active_backends:
        backend = get_backend(name)
        issues.extend(
            CheckIssue(
                "error",
                rel_path,
                f"managed file missing — run `sq sync` (backend: {backend.name})",
            )
            for rel_path in backend.managed_paths(bctx)
            if not (bctx.root / rel_path).exists()
        )
    return issues


def backend_entry_candidates(ctx: SquadGlobalContext) -> list[tuple[str, str]]:
    """Per-entry backend pointers absent right now, against *ctx.index* — the scan-time
    candidate set for ``check``'s confirm round, never reported directly.

    This reads ``ctx.index`` (via :func:`live_roster_slugs`) as well as the disk, so — unlike
    :func:`_backend_reconciled`'s top-level check — it is cross-source: a mutation racing the
    scan (concretely, a retirement withdrawing the very pointer a candidate names) can make a
    path here transiently absent for a reason that is not a defect. Each ``(backend name,
    rel_path)`` pair is confirmed by :func:`backend_entry_missing` against a freshly reloaded
    index before ever becoming a :class:`CheckIssue` — see
    :meth:`MaintenanceMixin._confirm_cross_source`.

    Reported at **warn**, not error, but not for the reason once written here: an adopter who
    gitignores this backend's whole directory does *not* escape ``sq check`` over that choice —
    ``_backend_reconciled``'s top-level ``managed_paths`` entry for the same backend (e.g.
    ``claude_code``'s ``.claude/settings.json``) is already **error** and already fails a fully
    gitignored directory, before and after this rule existed. The honest reason: before this
    widening, a per-entry pointer going untracked while the top-level files stayed tracked was
    invisible to ``sq check`` altogether — not error, not warn, nothing. Warn keeps that
    previously-silent shape's exit code unchanged rather than adding a new error to a patch
    release; it is not protecting a "supported choice" that was already failing the gate.
    """
    live_role_slugs, live_skill_slugs = live_roster_slugs(ctx)
    bctx = BackendContext(
        paths=ctx.paths,
        spec=ctx.spec,
        live_role_slugs=live_role_slugs,
        live_skill_slugs=live_skill_slugs,
    )
    candidates: list[tuple[str, str]] = []
    for name in ctx.paths.config.active_backends:
        backend = get_backend(name)
        candidates.extend(
            (backend.name, rel_path)
            for rel_path in backend.managed_entry_paths(bctx)
            if not (bctx.root / rel_path).exists()
        )
    return candidates


def backend_entry_missing(
    backend_name: str, rel_path: str, *, root: Path, fresh_live_paths: frozenset[str]
) -> CheckIssue | None:
    """Re-observe one per-entry-pointer candidate (see :func:`backend_entry_candidates`)
    against a freshly reloaded index's own recomputed live-roster set and the disk right now —
    the single-candidate confirm predicate, same shape as :func:`on_disk_not_indexed`/
    :func:`not_on_disk`.

    *fresh_live_paths* is this one backend's ``managed_entry_paths`` recomputed from the fresh
    index (never the stale scan-time one) — if the slug behind *rel_path* was retired between
    the scan and this confirm, the fresh set no longer names it and the candidate resolves
    (``None``) rather than being reported; likewise if the file has since been created.
    """
    if rel_path not in fresh_live_paths:
        return None
    if (root / rel_path).exists():
        return None
    return CheckIssue(
        "warn", rel_path, f"managed pointer missing — run `sq sync` (backend: {backend_name})"
    )


def _roster_config_integrity(ctx: SquadGlobalContext) -> list[CheckIssue]:
    """The config-integrity clauses (``no_live_role``/``preloaded_skill``), evaluated against
    state already on disk rather than gating a transition: the roster status verb shipped
    before any clause refused these
    transitions, so a squad already sitting in a state a fresh retirement would refuse (or one
    reached some other way) keeps it silently, and `sq sync` faithfully projects the breakage.
    Delegates to ``_config_integrity.check_all``, the module the retirement gate also calls, so
    neither restates the clauses. Reads the index and the config only — never the on-disk scan
    — so it carries none of ``SquadGlobalValidator``'s cross-source single-item-evaluability
    obligation.

    Renders each finding's condition plus its remedy when one exists, via
    ``config_integrity.render_finding`` — the one place condition and remedy are ever composed,
    so this line never duplicates a phrase the finding's own ``message`` already states."""
    findings = config_integrity.check_all(
        ctx.index, ctx.spec, ctx.paths.config.active_backends, ctx.playbook
    )
    return [
        CheckIssue("error", f.entry, f"config integrity: {config_integrity.render_finding(f)}")
        for f in findings
    ]


def _default_designation_duplicated(ctx: SquadGlobalContext) -> list[CheckIssue]:
    """More than one **live** ``role`` item carrying ``is_default`` — an error naming the
    holders, with ``sq role <addr> set-default`` as the remedy.

    Report-only, deliberately: this predicate is never folded into
    ``config_integrity.check_all``, so the retirement gate (``_retirement.py::enforce``) never
    evaluates it. Delta scoping would fire it on *reactivating* a non-live role that still
    carries the key while a live role also carries it — and no remedy exists in that direction:
    ``Service.set_default_role`` refuses a non-live target, and no interactive command clears
    the key off a non-live role. That is exactly the lock-out the withdrawn ``no_default_role``
    clause was withdrawn for, so this stays a reporter-only fact about state already reached
    (today, only through the bulk importer's ``update`` event — the one path outside
    ``set_default_role`` that writes the key), never a gate clause.
    """
    live = ctx.spec.live_statuses(ROSTER_ROLE)
    holders = sorted(
        it.id
        for it in ctx.index.items.values()
        if it.type == ROSTER_ROLE and it.status in live and it.extra.get(X.IS_DEFAULT)
    )
    if len(holders) <= 1:
        return []
    return [
        CheckIssue(
            "error",
            "",
            "more than one live role carries the default-role designation: "
            f"{', '.join(holders)} — remedy: `sq role <addr> set-default`",
        )
    ]


def _playbook_guide_role_live(ctx: SquadGlobalContext) -> list[CheckIssue]:
    """A playbook guide whose role slug names no live role — a warning per dropped guide.

    The gap the playbook override's permissive slug authority leaves open: the loader accepts a
    project role slug by filename (it must, being readable before the index), the generated
    skill drops it unless the role is live, and nothing in between says so. This is the same
    event as the orphaned ``sq-<type>`` skill the reporter already flags, one level down — a
    guide the renderer will drop must never validate silently.

    Warning, not error, and never a gate clause: both remedies (activate the role, or edit
    ``.overrides/playbook.toml``) are outside any single transition, and a squad mid-scaffold is
    legitimately in this state for as long as the adopter takes to run ``sq role activate``.
    Refusing the retirement instead — the shape the *skill* side uses, where ``--unlink`` is a
    performable step — would offer no equivalent escape here, since sq never rewrites an
    adopter's override file. See :func:`~squads._interactions.orphaned_playbook_guides` for the
    predicate and its two deliberate exemptions.

    Scoped to guides the adopter actually wrote, which is why the raw override document is read
    here (:func:`~squads._interactions._loader.playbook_override_guide_pairs`) rather than only
    the merged playbook the context carries: the merged document holds no provenance, and a
    report an adopter cannot act on is worse than silence for a squad whose only "fault" is
    having retired a bundled role.
    """
    if ctx.playbook is None:
        return []  # no playbook resolved for this context — nothing to strip guides from
    live = ctx.spec.live_statuses(ROSTER_ROLE)
    roles = [it for it in ctx.index.items.values() if it.type == ROSTER_ROLE]
    known = frozenset(slug for it in roles if (slug := it.extra.get(X.SLUG)))
    live_slugs = frozenset(
        slug for it in roles if it.status in live and (slug := it.extra.get(X.SLUG))
    )
    live_initial = ctx.spec.live_initial(ROSTER_ROLE)
    return [
        CheckIssue(
            "warn",
            "",
            orphaned_playbook_guide_message(
                item_type, slug, retired=slug in known, live_status=live_initial
            ),
        )
        for item_type, slug in orphaned_playbook_guides(
            ctx.playbook,
            ctx.spec,
            live_role_slugs=live_slugs,
            override_guides=playbook_override_guide_pairs(ctx.paths.squad_dir),
        )
    ]


#: The closed squad-global validator registry — same CODE-constant status as ``CATALOG``.
SQUAD_GLOBAL_CATALOG: dict[str, SquadGlobalValidator] = {
    "index_reconciled": _index_reconciled,
    "backend_reconciled": _backend_reconciled,
    "roster_config_integrity": _roster_config_integrity,
    "default_designation_duplicated": _default_designation_duplicated,
    "playbook_guide_role_live": _playbook_guide_role_live,
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
    playbook: PlaybookSpec | None = None
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
                index=index,
                on_disk=on_disk,
                spec=self.spec,
                paths=self.paths,
                playbook=self.playbook,
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
