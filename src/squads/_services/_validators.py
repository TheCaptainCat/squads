"""Pluggable-validator dispatch engine: the sole source of ``sq check``'s per-item and squad-global
issues and of the create/update fail-closed gate. A type's effective set is ``COMMON_CORE`` plus its
category's ``CATEGORY_BUNDLES`` entry plus its own ``validators`` list (``_workflow/_models.py``),
and ``gate()`` runs only error-level members, aborting on the first finding.

The file checks (:meth:`CheckMixin._scan_for_check`) are not catalog members: they apply per file,
cannot be selected, and are reported even when the frontmatter is unreadable (rules in
``_services/_check_rules.py``).
"""

import dataclasses
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from squads import _clock as clock
from squads import _discussion as discussion
from squads import _sections as sections
from squads import _view_remedies as view_remedies
from squads import _view_tags as view_tags
from squads._backends._base import AgentBackend, BackendContext
from squads._errors import InvalidIdError, SquadsError
from squads._interactions._loader import (
    playbook_override_command_lines,
    playbook_override_guide_pairs,
)
from squads._interactions._models import PlaybookSpec
from squads._interactions._playbook import (
    orphaned_playbook_guide_message,
    orphaned_playbook_guides,
    unheld_capability_token_message,
    unheld_capability_tokens,
)
from squads._interactions._role_guidance import (
    CAPABILITY_SUBJECT_PREFIX,
    create_lanes,
    in_lane_owner,
)
from squads._interactions._skills import item_type_for_skill_slug
from squads._language import resolve_working_language
from squads._models import _attributes as attrs
from squads._models import _markers as markers
from squads._models._attributes import ORIGIN_VALUES, AttributeKey
from squads._models._config import CONFIG_FILENAME
from squads._models._index import SquadsDB
from squads._models._item import Item, split_ref
from squads._models._metadata import value_problem
from squads._models._participants import SlugBreach, roster_slug_breaches
from squads._paths import SquadPaths, number_for_id
from squads._pronouns import pronouns_problem
from squads._rendering._engine import scaffold_body
from squads._roles._catalog import get_catalog
from squads._roles._models import CatalogSource
from squads._roles._resolver import (
    base_problems,
    holds_default_designation,
    model_problem,
    override_file_keys,
    resolve_role_for_item,
    resolve_role_tolerantly,
)
from squads._services import _config_integrity as config_integrity
from squads._services._results import CheckIssue
from squads._services._roster_projection import is_live_roster_entry
from squads._specload import OverrideFiles
from squads._transform import check_view_transforms
from squads._views import ITEM_SKILL_VIEW_NAME
from squads._workflow._models import ROSTER_OPERATOR, ROSTER_ROLE, ROSTER_SKILL, WorkflowSpec
from squads._workflow._validator_names import (
    DEFAULT_SQUAD_GLOBAL_LEVEL,
    DEFAULT_VALIDATOR_LEVEL,
    SELECTABLE_SQUAD_GLOBAL_NAMES,
    SQUAD_GLOBAL_VALIDATOR_NAMES,
    VALIDATOR_NAMES,
    effective_validator_names,
    parse_validator_entry,
)

#: The on-disk scan map ``_scan_for_check`` builds: sequence number -> (frontmatter id, file
#: path, frontmatter dict). Same shape ``CheckMixin.check()``'s scan pass and its one
#: confirm pass both thread through — ``report()`` takes it for the same reason.
type OnDiskMap = dict[int, tuple[str, Path, dict[str, Any]]]

# A leading status/lifecycle banner: "STATUS:" / "**STATUS…**" opening a line, or a hand-written "##
# Status" heading, anchored to the start of the checked text. The only banner detector;
# `no_status_banner` is its sole consumer.
_STATUS_BANNER_RE = re.compile(r"^\*{0,2}status\*{0,2}\s*:", re.IGNORECASE)
_STATUS_HEADING_RE = re.compile(r"^#{2,3}\s*status\s*:?\s*$", re.IGNORECASE)


def _opens_with_status_banner(text: str | None) -> bool:
    """True when *text* opens with a self-declared status/lifecycle banner. Leading line only,
    which is what keeps prose that merely discusses lifecycle as a topic out of the finding —
    see the pattern comment above."""
    if not text:
        return False
    stripped = text.strip()
    if not stripped:
        return False
    first_line = stripped.splitlines()[0].strip()
    return bool(_STATUS_BANNER_RE.match(first_line) or _STATUS_HEADING_RE.match(first_line))


class ContextRequirement(StrEnum):
    """One piece of :class:`ValidatorContext` a caller may not supply, because its availability
    depends on the call path: ``report()`` supplies both, while ``gate()`` supplies neither, gating
    an in-memory ``Item`` with no file and paying no full-index scan per mutation. Naming them makes
    a member's non-participation on a path declared, and each value is the field's own name on
    :class:`ValidatorContext`.
    """

    RAW_TEXT = "raw_text"
    TYPE_PRESENT = "type_present"


@dataclass(frozen=True)
class ValidatorContext:
    """Everything one per-item validator reads: the item, the active spec, a read-only index handle,
    precomputed aggregates (registered slugs, incoming ``supersedes`` and dependency numbers, item
    types with a corpus member) and the item's on-disk text. ``type_present`` is empty on ``gate()``
    and ``raw_text`` is ``None`` when no file was found; :class:`ContextRequirement` members run
    only where the context carries them (:meth:`held_context`).
    """

    item: Item
    spec: WorkflowSpec
    index: SquadsDB | None = None
    registered_slugs: frozenset[str] = frozenset()
    supersedes_incoming: frozenset[int] = frozenset()
    dependency_incoming: frozenset[int] = frozenset()
    type_present: frozenset[str] = frozenset()
    raw_text: str | None = None
    #: The squad directory whose template overrides apply when a validator re-renders a scaffold;
    #: ``None`` is the bundled templates alone.
    squad_dir: Path | None = None

    def held_context(self) -> frozenset[ContextRequirement]:
        """Which :class:`ContextRequirement` fields this instance actually carries.

        Read off the values rather than declared by whoever built the context: a second
        declaration is a second thing to keep in step, and the one that drifts is always the
        one nothing reads. A caller that starts supplying a field therefore starts running the
        members that need it, with nothing else to update.
        """
        held: set[ContextRequirement] = set()
        if self.raw_text is not None:
            held.add(ContextRequirement.RAW_TEXT)
        if self.type_present:
            held.add(ContextRequirement.TYPE_PRESENT)
        return frozenset(held)


@dataclass(frozen=True)
class SquadGlobalContext:
    """Everything one squad-global validator reads: the whole index, the on-disk scan map, the
    active spec, the squad's paths (for ``backend_reconciled``'s ``BackendContext``) and
    ``playbook``, which ``roster_config_integrity`` and ``playbook_guide_role_live`` read. ``now``
    is the run's single clock instant, read once by ``report()``.
    """

    index: SquadsDB
    on_disk: OnDiskMap
    spec: WorkflowSpec
    paths: SquadPaths
    now: datetime
    playbook: PlaybookSpec
    catalog: CatalogSource
    files: OverrideFiles
    #: The service's own backends, so the managed-file rules judge the instances `sync` writes with.
    backends: Callable[[], list[AgentBackend]]


class Validator(Protocol):
    """One named per-item check in the closed catalog: given a :class:`ValidatorContext`,
    returns zero or more :class:`CheckIssue`. Validator *logic* is hard-coded in squads (no
    adopter-supplied code, no ``eval``) — a spec only ever names *which* validators run."""

    def __call__(self, ctx: ValidatorContext) -> list[CheckIssue]: ...


class SquadGlobalValidator(Protocol):
    """One named whole-squad check, run once per ``sq check`` regardless of any type's ``category``,
    in no bundle and not deselectable. A cross-source validator (on-disk scan versus index) must be
    a ``(single item, freshly observed pair) -> CheckIssue | None`` predicate that the scan and
    confirm passes both call, or ``check`` cannot confirm it; one reading only the disk
    (``backend_reconciled``) needs none of that.
    """

    def __call__(self, ctx: SquadGlobalContext) -> list[CheckIssue]: ...


def _resolved_level(ctx: ValidatorContext, name: str) -> str:
    """The effective level catalog member *name* reports for ``ctx.item``'s type: the type's own
    ``@<level>`` override in its ``validators`` list (already checked against any declared floor),
    else :data:`~squads._workflow._validator_names.DEFAULT_VALIDATOR_LEVEL`. Every member calls this
    rather than hardcoding a level, so the level lives in one table.
    """
    item_spec = ctx.spec.items.get(ctx.item.type)
    if item_spec is not None:
        for entry in item_spec.validators:
            bare, _param, level = parse_validator_entry(entry)
            if bare == name and level is not None:
                return level
    return DEFAULT_VALIDATOR_LEVEL[name]


def squad_global_selection(spec: WorkflowSpec, name: str) -> tuple[str | None, str | None]:
    """The ``(param, level)`` of the ``[squad] validators`` entry selecting *name*, or
    ``(None, None)`` when the squad does not select it."""
    for entry in spec.squad.validators:
        bare, param, level = parse_validator_entry(entry)
        if bare == name:
            return param, level
    return None, None


def squad_global_level(spec: WorkflowSpec, name: str) -> str:
    """The level a squad-global member reports at: its selection's ``@<level>``, else its
    declared default. Every squad-global member takes its level from here."""
    return squad_global_selection(spec, name)[1] or DEFAULT_SQUAD_GLOBAL_LEVEL[name]


# --------------------------------------------------------------------------- per-item catalog


def _parent_in(ctx: ValidatorContext) -> list[CheckIssue]:
    """Parent eligibility: a dangling parent, or one ``parent_allowed`` rejects.

    Reads the structured ``parents`` field via ``spec.parent_allowed`` — no duplicated param.
    An empty ``parents`` list (and no ``no_parent``) means "any parent or none".
    """
    item = ctx.item
    if not item.parent:
        return []
    level = _resolved_level(ctx, "parent_in")
    parent = ctx.index.get(item.parent) if ctx.index is not None else None
    if parent is None:
        return [CheckIssue(level, item.id, f"dangling parent {item.parent}", rule="parent_in")]
    if not ctx.spec.parent_allowed(item.type, parent.type):
        msg = f"{ctx.spec.parent_hint(item.type)} (got {parent.type})"
        return [CheckIssue(level, item.id, msg, rule="parent_in")]
    return []


def _no_parent(ctx: ValidatorContext) -> list[CheckIssue]:
    """Forbids any parent at all — the explicit opt-in that an empty ``parent_in`` allowlist
    deliberately does not imply. Selected by the ``records`` bundle and by ``epic``."""
    item = ctx.item
    if item.parent:
        level = _resolved_level(ctx, "no_parent")
        return [
            CheckIssue(
                level, item.id, f"{item.type} takes no parent (got {item.parent})", rule="no_parent"
            )
        ]
    return []


def _parent_present(ctx: ValidatorContext) -> list[CheckIssue]:
    """Requires a parent, the mandatory half of the parent vocabulary: ``parents`` is only an
    eligibility allowlist, so ``parents = ["feature"]`` reads "a feature or nothing". It is in no
    :data:`CATEGORY_BUNDLES` entry and a type opts in via ``validators``, since ``gate()`` and
    ``report()`` share one effective set and a bundle entry would make every historical parentless
    item a ``sq check`` error no migration could fix.
    """
    item = ctx.item
    if item.parent:
        return []
    required = ctx.spec.item_parent_required(item.type)
    of_type = f" of type {required}" if required else ""
    level = _resolved_level(ctx, "parent_present")
    return [
        CheckIssue(level, item.id, f"{item.type} requires a parent{of_type}", rule="parent_present")
    ]


def _parent_acyclic(ctx: ValidatorContext) -> list[CheckIssue]:
    """Refuses a parent chain that revisits an item. It is in
    :data:`~squads._workflow._validator_names.COMMON_CORE`, so one member covers every parent-
    setting entry point through :meth:`ValidatorEngine.gate`. The visited set holds sequence numbers
    (a stored ``parent`` may differ in zero-pad width) and a dangling parent is left to
    ``parent_in``. An item in a cycle cannot be updated, but ``update --no-parent`` works because
    ``_update_model`` applies ``clear_parent`` before the gate reads the parent; the message names
    the closing edge's owner.
    """
    item = ctx.item
    if not item.parent or ctx.index is None:
        return []
    chain: list[str] = [item.id]
    seen: set[int] = {item.sequence_id}
    parent_id: str | None = item.parent
    while parent_id:
        node = ctx.index.get(parent_id)
        if node is None:
            return []  # dangling parent — `parent_in` owns that report
        chain.append(node.id)
        if node.sequence_id in seen:
            # The chain can close on the item under test while the index spells that item
            # differently (a reclassification gates the prospective id, the stored id closes it);
            # both ends are the same item and the message says so.
            restyled = node.sequence_id == item.sequence_id and node.id != item.id
            level = _resolved_level(ctx, "parent_acyclic")
            return [
                CheckIssue(
                    level,
                    item.id,
                    _parent_cycle_message(chain, ctx, restyled=restyled),
                    rule="parent_acyclic",
                )
            ]
        seen.add(node.sequence_id)
        parent_id = node.parent
    return []


def _parent_cycle_message(chain: list[str], ctx: ValidatorContext, *, restyled: bool) -> str:
    """The refusal message: the whole chain with the revisited item at both ends plus the command
    that breaks it. The remedy clears the parent of ``chain[-2]``, the item whose edge closes the
    loop, since clearing the item under test only detaches it from a cycle it may not be in.
    ``restyled`` means the closing endpoint is the head under an id it does not carry on disk, so it
    is named as the head with the stored spelling.
    """
    closer = ctx.index.get(chain[-2]) if ctx.index is not None else None
    remedy = (
        f"`sq {closer.type} {closer.sequence_id} update --no-parent`"
        if closer is not None
        else "`update --no-parent` on the item whose parent closes the loop"
    )
    rendered = list(chain)
    if restyled:
        rendered[-1] = f"{chain[0]} (stored as {chain[-1]})"
    return (
        f"{chain[0]}'s parent chain forms a cycle: {' -> '.join(rendered)}; break it with {remedy}"
    )


def _item_status_valid(ctx: ValidatorContext) -> list[CheckIssue]:
    """The item's status is not a state of its type's workflow."""
    item = ctx.item
    if item.status not in ctx.spec.workflow_for(item.type).states:
        level = _resolved_level(ctx, "item_status_valid")
        return [
            CheckIssue(
                level,
                item.id,
                f"status {item.status!r} invalid for {item.type}",
                rule="item_status_valid",
            )
        ]
    return []


def _dangling_ref(ctx: ValidatorContext) -> list[CheckIssue]:
    """A ref whose target is not in the index."""
    if ctx.index is None:
        return []
    level = _resolved_level(ctx, "dangling_ref")
    issues: list[CheckIssue] = []
    for r in ctx.item.refs:
        rid, _kind = split_ref(r)
        if ctx.index.get(rid) is None:
            issues.append(
                CheckIssue(level, ctx.item.id, f"dangling ref {rid}", rule="dangling_ref")
            )
    return issues


def _ref_kind_valid(ctx: ValidatorContext) -> list[CheckIssue]:
    """A ref whose spelled kind the spec does not declare.

    A bare/unspelled kind (``""``) is always valid by construction — it names whichever
    declared entry carries ``role = "default"`` — so only a *spelled* kind is checked against
    the merged spec's declared set."""
    level = _resolved_level(ctx, "ref_kind_valid")
    issues: list[CheckIssue] = []
    for r in ctx.item.refs:
        rid, kind = split_ref(r)
        if kind and kind not in ctx.spec.ref_kinds:
            issues.append(
                CheckIssue(
                    level,
                    ctx.item.id,
                    f"unknown ref kind {kind!r} on edge → {rid}",
                    rule="ref_kind_valid",
                )
            )
    return issues


def _agent_registered(ctx: ValidatorContext) -> list[CheckIssue]:
    """Author and assignee must both resolve to a registered
    role or operator slug (``ctx.registered_slugs``, precomputed by the engine). A skill
    authored by its own slug has no actor to check."""
    level = _resolved_level(ctx, "agent_registered")
    issues: list[CheckIssue] = []
    for attr in ("author", "assignee"):
        if attr == "author" and ctx.item.type == ROSTER_SKILL and ctx.item.author == ctx.item.slug:
            continue
        slug = getattr(ctx.item, attr)
        if slug and slug not in ctx.registered_slugs:
            issues.append(
                CheckIssue(
                    level,
                    ctx.item.id,
                    f"{attr} {slug!r} is not a registered role or operator",
                    rule="agent_registered",
                )
            )
    return issues


def _subentity_mapping(ctx: ValidatorContext) -> list[CheckIssue]:
    """A subtask maps to one of its parent's declared stories."""
    item = ctx.item
    kind = ctx.spec.item_subentity_kind(item.type)
    ks = ctx.spec.subentity_kinds.get(kind) if kind is not None else None
    if ks is None or not ks.maps_to_parent:
        return []
    refs = [(s.local_id, s.story) for s in item.subentities if s.story]
    if not refs:
        return []
    parent = ctx.index.get(item.parent) if (ctx.index is not None and item.parent) else None
    required_parent = ctx.spec.item_parent_required(item.type)
    host = required_parent or "parent"
    story_kind = ctx.spec.item_subentity_kind(host) or "story"
    level = _resolved_level(ctx, "subentity_mapping")
    if parent is None or (required_parent is not None and parent.type != required_parent):
        return [
            CheckIssue(
                level,
                item.id,
                f"{kind} maps to a {story_kind} but the {item.type} has no {host} parent",
                rule="subentity_mapping",
            )
        ]
    known = {s.local_id for s in parent.subentities}
    return [
        CheckIssue(
            level,
            item.id,
            f"{kind} {stn} → {us} missing from {parent.id}",
            rule="subentity_mapping",
        )
        for stn, us in refs
        if us not in known
    ]


def _subentity_status_valid(ctx: ValidatorContext) -> list[CheckIssue]:
    """A sub-entity's status is a state of its kind's own lifecycle."""
    item = ctx.item
    kind = ctx.spec.item_subentity_kind(item.type)
    if kind is None:
        return []
    valid = ctx.spec.subentity_workflow(kind).states
    level = _resolved_level(ctx, "subentity_status_valid")
    return [
        CheckIssue(
            level,
            item.id,
            f"{kind} {s.local_id} has invalid status {s.status!r}",
            rule="subentity_status_valid",
        )
        for s in item.subentities
        if s.status not in valid
    ]


def _subentity_deferral_resolved(ctx: ValidatorContext) -> list[CheckIssue]:
    """A sub-entity in a status whose role declares ``deferred`` names an indexed carrier that
    has not been retired, and no other sub-entity names a carrier at all.

    Roles are read by name, never a status spelling: a carrier in a ``superseded`` status is
    fine, its work continuing in the item that supersedes it.
    """
    item = ctx.item
    kind = ctx.spec.item_subentity_kind(item.type)
    if kind is None or ctx.index is None:
        return []
    level = _resolved_level(ctx, "subentity_deferral_resolved")
    issues: list[CheckIssue] = []
    for s in item.subentities:
        what = f"{kind} {s.local_id}"
        if not ctx.spec.role_for(s.status).deferred:
            if s.deferred_to:
                issues.append(
                    CheckIssue(
                        level,
                        item.id,
                        f"{what} is {s.status} yet names {s.deferred_to} as its carrier; "
                        "only a deferred status carries one",
                        rule="subentity_deferral_resolved",
                    )
                )
            continue
        if not s.deferred_to:
            issues.append(
                CheckIssue(
                    level,
                    item.id,
                    f"{what} is {s.status} but names no carrying item",
                    rule="subentity_deferral_resolved",
                )
            )
            continue
        carrier = ctx.index.get(s.deferred_to)
        if carrier is None:
            issues.append(
                CheckIssue(
                    level,
                    item.id,
                    f"{what} is {s.status} to {s.deferred_to}, not found",
                    rule="subentity_deferral_resolved",
                )
            )
        elif carrier.id == item.id:
            issues.append(
                CheckIssue(
                    level,
                    item.id,
                    f"{what} is {s.status} to its own item, which is no carrier",
                    rule="subentity_deferral_resolved",
                )
            )
        elif ctx.spec.status_role(carrier.status) == "retired":
            issues.append(
                CheckIssue(
                    level,
                    item.id,
                    f"{what} is {s.status} to {carrier.id}, which is {carrier.status} "
                    "and will not carry the work",
                    rule="subentity_deferral_resolved",
                )
            )
    return issues


def _subentities_settled_with_parent(ctx: ValidatorContext) -> list[CheckIssue]:
    """An item resting in a status whose role is ``settled`` while a sub-entity rests in a
    status whose role is not. Both sides are read by role, never by status name, so a deferred
    or noted sub-entity is settled and one awaiting verification is not."""
    item = ctx.item
    kind = ctx.spec.item_subentity_kind(item.type)
    if kind is None or not ctx.spec.role_for(item.status).settled:
        return []
    outstanding = [s for s in item.subentities if not ctx.spec.role_for(s.status).settled]
    if not outstanding:
        return []
    level = _resolved_level(ctx, "subentities_settled_with_parent")
    ids = ", ".join(s.local_id for s in outstanding)
    return [
        CheckIssue(
            level,
            item.id,
            f"status is {item.status} with {len(outstanding)} unsettled "
            f"{_plural(len(outstanding), kind)}: {ids}",
            rule="subentities_settled_with_parent",
        )
    ]


def _subentity_container_marker(ctx: ValidatorContext) -> list[CheckIssue]:
    """The item's on-disk container marker still matches the plural its kind declares. The plural is
    a persisted corpus-alignment field like ``prefix`` or ``folder`` but leaves no witness in the
    index, so only ``sq check``, which holds each item's text, can see a mismatch. A rename half-
    bricks a corpus (``add-<kind>`` fails while body writes succeed), so both directions are
    reported; a file with no container is not, since the first ``add-<kind>`` writes one.
    """
    item = ctx.item
    kind = ctx.spec.item_subentity_kind(item.type)
    if kind is None or ctx.raw_text is None:
        return []
    plural = ctx.spec.subentity_plural(kind)
    if sections.has_section(ctx.raw_text, plural):
        return []
    # Name the tag the file does carry, which tells the adopter which way to fix it. A container is
    # the only top-level marker that is neither a structural tag nor a sub-entity block tag (those
    # have a colon), as the file may carry an undeclared old name.
    stale = discussion.stale_container_tags(ctx.raw_text, plural)
    if not stale:
        return []  # no container at all: `add-<kind>` writes one
    found = f"; the file carries {stale[0]!r}"
    level = _resolved_level(ctx, "subentity_container_marker")
    return [
        CheckIssue(
            level,
            item.id,
            f"no {plural!r} container section{found} — {kind!r} declares plural {plural!r}, "
            f"so `sq {item.type} {item.sequence_id} add-{kind}` cannot write here. Revert "
            f"subentity_kinds.{kind}.plural in the workflow override, or change it only "
            f"while no {item.type} items exist",
            rule="subentity_container_marker",
        )
    ]


def _subentity_body_written(ctx: ValidatorContext) -> list[CheckIssue]:
    """Flags a sub-entity body still at its
    kind's placeholder stub, read from ``ctx.raw_text``."""
    item = ctx.item
    kind = ctx.spec.item_subentity_kind(item.type)
    if kind is None or not item.subentities or ctx.raw_text is None:
        return []
    placeholder = discussion.body_placeholder(kind, ctx.spec)
    level = _resolved_level(ctx, "subentity_body_written")
    issues: list[CheckIssue] = []
    for sub in item.subentities:
        body = sections.get_section(ctx.raw_text, discussion.body_tag(kind, sub.local_id))
        if body is not None and body.strip() == placeholder:
            issues.append(
                CheckIssue(
                    level,
                    item.id,
                    f"{sub.local_id} body is unwritten (still the placeholder stub)",
                    rule="subentity_body_written",
                )
            )
    return issues


def _subentity_title_present(ctx: ValidatorContext) -> list[CheckIssue]:
    """A sub-entity with no title: the title is required on every write, so a file that carries an
    empty one was written by hand or by an older release."""
    item = ctx.item
    kind = ctx.spec.item_subentity_kind(item.type)
    if kind is None:
        return []
    level = _resolved_level(ctx, "subentity_title_present")
    return [
        CheckIssue(
            level,
            item.id,
            f"{kind} {sub.local_id} has no title"
            f" — set one with `sq {item.type} {item.sequence_id} {kind} {sub.local_id}"
            ' update --title "…"`',
            rule="subentity_title_present",
        )
        for sub in item.subentities
        if not sub.title.strip()
    ]


def _subentity_title_max(ctx: ValidatorContext) -> list[CheckIssue]:
    """A sub-entity title over the type's maximum. The threshold is resolved from the spec —
    ``WorkflowSpec.item_subentity_title_max`` — never a module constant, so a type's own
    ``subentity_title_max:<n>`` selection actually changes what fires. A type whose effective
    set does not hold the member has no threshold and reports nothing."""
    item = ctx.item
    kind = ctx.spec.item_subentity_kind(item.type)
    if kind is None:
        return []
    threshold = ctx.spec.item_subentity_title_max(item.type)
    if threshold is None:
        return []
    level = _resolved_level(ctx, "subentity_title_max")
    return [
        CheckIssue(
            level,
            item.id,
            f"advisory: {kind} {sub.local_id} title is {len(sub.title)} chars"
            f" (threshold: {threshold})"
            " — a sub-entity title is a one-line handle;"
            " put the detail in the body",
            rule="subentity_title_max",
        )
        for sub in item.subentities
        if len(sub.title) > threshold
    ]


def _item_title_max(ctx: ValidatorContext) -> list[CheckIssue]:
    """An item whose title is longer than the number its type's ``item_title_max:<n>`` entry
    names, counted in code points after NFC normalisation (so a decomposed and a composed
    spelling of one title agree; a grapheme cluster of several code points still counts as
    several). The number comes from the spec, so a type that does not select the check reports
    nothing."""
    item = ctx.item
    threshold = ctx.spec.item_title_max(item.type)
    length = len(unicodedata.normalize("NFC", item.title))
    if threshold is None or length <= threshold:
        return []
    level = _resolved_level(ctx, "item_title_max")
    return [
        CheckIssue(
            level,
            item.id,
            f"title is {length} chars (threshold: {threshold})"
            " — an item title is a one-line handle; put the detail in the body",
            rule="item_title_max",
        )
    ]


def _body_written(ctx: ValidatorContext) -> list[CheckIssue]:
    """An item whose ``sq:body`` is still the scaffold its creation template rendered: the item
    twin of ``subentity_body_written``. It reads the scaffold through the same derivation and
    the same "unwritten" predicate the body-overwrite guard uses, so it reports an item exactly
    when a plain body write would be accepted as a first write."""
    item = ctx.item
    body = sections.get_section(ctx.raw_text, markers.BODY) if ctx.raw_text is not None else None
    if body is None or not view_tags.body_is_unwritten(
        body, scaffold_body(item, ctx.spec, from_squad=ctx.squad_dir)
    ):
        return []
    level = _resolved_level(ctx, "body_written")
    return [
        CheckIssue(
            level,
            item.id,
            "body is unwritten (still the template scaffold)"
            f' — write it with `sq {item.type} {item.sequence_id} body -m "..."`',
            rule="body_written",
        )
    ]


def _description_present(ctx: ValidatorContext) -> list[CheckIssue]:
    """An item whose summary — the ``description`` line list views show — is empty or only
    whitespace."""
    item = ctx.item
    if item.description.strip():
        return []
    level = _resolved_level(ctx, "description_present")
    return [
        CheckIssue(
            level,
            item.id,
            "description is empty — set a summary: `--desc` on create, `update --desc` after",
            rule="description_present",
        )
    ]


def _assignee_present(ctx: ValidatorContext) -> list[CheckIssue]:
    """An item resting in a status whose role declares ``live`` while nobody is assigned. The
    reading is the role's flag, the engine's own definition of an active status, never a role
    or status name; a status with no declared role resolves to the fallback role, which is not
    live."""
    item = ctx.item
    if item.assignee or not ctx.spec.role_for(item.status).live:
        return []
    level = _resolved_level(ctx, "assignee_present")
    return [
        CheckIssue(
            level,
            item.id,
            f"status is {item.status} but nobody is assigned",
            rule="assignee_present",
        )
    ]


def _blocked_has_blocker(ctx: ValidatorContext) -> list[CheckIssue]:
    """An item resting in a status whose role declares ``blocked`` while no edge of a
    dependency-role ref kind touches it: none of its own refs has such a kind and no item's ref
    of such a kind points at it. Kinds are matched by their declared role, never by spelling,
    and an edge counts whether or not its other end exists or is settled."""
    item = ctx.item
    if not ctx.spec.role_for(item.status).blocked:
        return []
    kinds = ctx.spec.dependency_ref_kinds()
    if any(kind in kinds for _, kind in _outgoing_refs(item, ctx.spec)):
        return []
    if item.sequence_id in ctx.dependency_incoming:
        return []
    level = _resolved_level(ctx, "blocked_has_blocker")
    return [
        CheckIssue(
            level,
            item.id,
            f"status is {item.status} but no dependency edge is recorded "
            f"(kinds: {', '.join(sorted(kinds))}) "
            "— record a dependency edge (`--ref <id>:<kind>` on create, `ref add` after)",
            rule="blocked_has_blocker",
        )
    ]


def _settled_requires_discussion(ctx: ValidatorContext) -> list[CheckIssue]:
    """An item resting in a status whose role declares ``settled`` while its own discussion holds
    no comment. Comments are counted by the discussion parser, never by a pattern of this
    module's, and only the item's own discussion region counts: a comment on one of its stories,
    subtasks or findings does not. A file with no discussion region holds no comment."""
    item = ctx.item
    if ctx.raw_text is None or not ctx.spec.role_for(item.status).settled:
        return []
    region = sections.get_section(ctx.raw_text, markers.DISCUSSION) or ""
    if discussion.split_discussion(region, sequence_id=item.sequence_id):
        return []
    level = _resolved_level(ctx, "settled_requires_discussion")
    return [
        CheckIssue(
            level,
            item.id,
            f"status is {item.status} but its discussion holds no comment",
            rule="settled_requires_discussion",
        )
    ]


def _external_id_not_in_title(ctx: ValidatorContext) -> list[CheckIssue]:
    """An item whose title matches the regular expression its type's
    ``external_id_not_in_title:<regex>`` entry names, reporting the first match. The pattern is
    the adopter's own and is searched with no flags and no bound on its cost, a zero-width match
    (a bare lookahead) counting as no match; a type that does
    not select the check has no pattern and reports nothing."""
    item = ctx.item
    pattern = ctx.spec.item_external_id_pattern(item.type)
    if pattern is None:
        return []
    found = next((m for m in re.finditer(pattern, item.title) if m.group(0)), None)
    if found is None:
        return []
    level = _resolved_level(ctx, "external_id_not_in_title")
    return [
        CheckIssue(
            level,
            item.id,
            f"title holds `{found.group(0)}` (matches the external-id pattern `{pattern}`)"
            " — keep tracker ids out of the title",
            rule="external_id_not_in_title",
        )
    ]


def _no_status_banner(ctx: ValidatorContext) -> list[CheckIssue]:
    """An item whose body or description opens with a
    self-declared status/lifecycle banner. Body text comes from ``ctx.raw_text``;
    description comes straight from the item."""
    item = ctx.item
    level = _resolved_level(ctx, "no_status_banner")
    body = sections.get_section(ctx.raw_text, markers.BODY) if ctx.raw_text is not None else None
    if _opens_with_status_banner(body):
        return [
            CheckIssue(
                level,
                item.id,
                "body opens with a status/lifecycle banner"
                " — move state to frontmatter or a dated discussion comment",
                rule="no_status_banner",
            )
        ]
    if _opens_with_status_banner(item.description):
        return [
            CheckIssue(
                level,
                item.id,
                "description opens with a status/lifecycle banner"
                " — move state to frontmatter or a dated discussion comment",
                rule="no_status_banner",
            )
        ]
    return []


def _supersedes_incoming(ctx: ValidatorContext) -> list[CheckIssue]:
    """A Superseded record with no incoming ``supersession``-semantic
    edge. Only types that declare a ref rule naming a declared ``supersession`` kind are
    checked — resolved through :meth:`WorkflowSpec.supersession_ref_kinds`, never a fixed
    ``"supersedes"`` spelling."""
    item = ctx.item
    supersession_kinds = ctx.spec.supersession_ref_kinds()
    if not any(rr.kind in supersession_kinds for rr in ctx.spec.item_ref_rules(item.type)):
        return []
    if (
        ctx.spec.status_role(item.status) == "superseded"
        and item.sequence_id not in ctx.supersedes_incoming
    ):
        level = _resolved_level(ctx, "supersedes_incoming")
        return [
            CheckIssue(
                level,
                item.id,
                f"status is {item.status} but no incoming supersedes edge found",
                rule="supersedes_incoming",
            )
        ]
    return []


def _outgoing_refs(item: Item, spec: WorkflowSpec) -> list[tuple[str, str]]:
    """*item*'s outgoing refs as ``(target id, kind)``, an unspelled kind resolved to the
    spec's default ref kind. The one reading both ref-rule checks use, so an edge written bare
    and the same edge with the default kind spelled out are one edge."""
    default = spec.default_ref_kind()
    return [(rid, kind or default) for rid, kind in map(split_ref, item.refs)]


def _ref_rule_target_present(ctx: ValidatorContext) -> list[CheckIssue]:
    """A settled item (status resolving to the ``done`` role) with no outgoing ref matching one of
    its type's ``target``-typed ``ref_rules`` whose edge points at an item of that target type. A
    ``ref_rule_target_present:<T>`` entry in ``validators`` selects ``<T>`` (read here, as dispatch
    strips the param) and the ``ref_rules`` entry types the edge; two rules for one ``<T>`` widen
    the kinds. Inert while the corpus has no item of the target type (``ctx.type_present``).
    """
    item = ctx.item
    if ctx.spec.status_role(item.status) != "done":
        return []
    item_spec = ctx.spec.items.get(item.type)
    if item_spec is None:
        return []
    targets = {
        param
        for entry in item_spec.validators
        for bare, param, _level in (parse_validator_entry(entry),)
        if bare == "ref_rule_target_present" and param is not None
    }
    active = targets & ctx.type_present
    if not active:
        return []
    accepted = {
        (rr.kind, rr.target) for rr in ctx.spec.item_ref_rules(item.type) if rr.target in active
    }
    if not accepted or ctx.index is None:
        return []
    for rid, kind in _outgoing_refs(item, ctx.spec):
        target_item = ctx.index.get(rid)
        if target_item is not None and (kind, target_item.type) in accepted:
            return []
    kinds = sorted({k for k, _ in accepted})
    level = _resolved_level(ctx, "ref_rule_target_present")
    return [
        CheckIssue(
            level,
            item.id,
            f"settled with no {'/'.join(kinds)} ref to a {'/'.join(sorted(active))} — its "
            "functional contract slice may be stale",
            rule="ref_rule_target_present",
        )
    ]


def _ref_rule_target_typed(ctx: ValidatorContext) -> list[CheckIssue]:
    """An outgoing edge whose kind has a typed ref rule on the item's type while the edge points
    at an item of another type. Only a rule that declares a ``target`` counts: an untyped rule
    neither makes its kind checked nor widens what a typed rule of the same kind accepts. A
    target the index does not hold is left to ``dangling_ref``."""
    item = ctx.item
    if ctx.index is None:
        return []
    allowed: dict[str, set[str]] = {}
    for rule in ctx.spec.item_ref_rules(item.type):
        if rule.target is not None:
            allowed.setdefault(rule.kind, set()).add(rule.target)
    if not allowed:
        return []
    level = _resolved_level(ctx, "ref_rule_target_typed")
    issues: list[CheckIssue] = []
    for rid, kind in _outgoing_refs(item, ctx.spec):
        targets = allowed.get(kind)
        target_item = ctx.index.get(rid)
        if not targets or target_item is None or target_item.type in targets:
            continue
        issues.append(
            CheckIssue(
                level,
                item.id,
                f"{kind} edge to {rid} points at a {target_item.type}, but a {item.type}'s "
                f"{kind} refs must point at a {'/'.join(sorted(targets))}",
                rule="ref_rule_target_typed",
            )
        )
    return issues


def _item_skill_shadowed(ctx: ValidatorContext) -> list[CheckIssue]:
    """A live ``sq-<slug>`` skill whose body carries authored prose while its slug still names a
    declared item type. Reports it rather than guessing whether the prose is a stale rendering
    or an author's real runbook — either way the type's generated guidance has nowhere
    supported to render, and the named remedy moves the prose to a new skill before clearing
    anything, never a clear-first sequence that could destroy it."""
    item = ctx.item
    slug = item.slug
    doc_type = item_type_for_skill_slug(slug, ctx.spec)
    if doc_type is None:
        return []
    body = sections.get_section(ctx.raw_text, markers.BODY) if ctx.raw_text is not None else None
    region = body or ""
    tag_present = any(
        (parts := markers.view_tag_parts(raw)) is not None and parts.name == ITEM_SKILL_VIEW_NAME
        for raw in sections.find_markers(region)
    )
    prose = view_tags.strip_view_tags(region).strip()
    if not prose:
        return []
    level = _resolved_level(ctx, "item_skill_shadowed")
    clear_cmd = view_remedies.clear_roster_body_cmd(ROSTER_SKILL, slug)
    remedy = (
        f"move the prose first (`sq skill add <new-slug>`); take the type out of the active "
        f"spec (drop it from `[selected]`, or remove a project type's own declaration); clear "
        f"{slug} with `{clear_cmd}`; then restore the type"
    )
    if tag_present:
        detail = (
            f"documents declared type {doc_type!r} and carries prose beside its item_skill "
            f"tag — {doc_type}'s generated guidance renders through the tag, but the prose "
            f"beside it has no supported way to be removed once this slug documents a "
            f"declared type; {remedy}"
        )
    else:
        detail = (
            f"documents declared type {doc_type!r} but carries authored content of its own "
            f"with no item_skill tag — {doc_type}'s generated skill guidance has nowhere to "
            f"render; {remedy}"
        )
    return [CheckIssue(level, item.id, detail, rule="item_skill_shadowed")]


def _attribute_valid(ctx: ValidatorContext) -> list[CheckIssue]:
    """Every attribute the item's type declares holds a value of its declared kind, and every
    required one is present.

    Judges the value as the file stores it. A failing value is reported and left as written: a
    typed accessor reads it as unset, and only a command that targets the key replaces it.
    """
    if ctx.raw_text is None:
        return []
    try:
        stored = sections.split_frontmatter(ctx.raw_text, source=ctx.item.path)[0]
    except SquadsError:
        return []
    level = _resolved_level(ctx, "attribute_valid")
    issues: list[CheckIssue] = []
    for name, spec in ctx.spec.item_attributes(ctx.item.type).items():
        value = stored.get(name)
        if value is None:
            if spec.required:
                issues.append(
                    CheckIssue(
                        level,
                        ctx.item.id,
                        f"missing required attribute {name!r}",
                        rule="attribute_valid",
                    )
                )
            continue
        problem = value_problem(spec, value)
        if problem is None and name == AttributeKey.ORIGIN and value not in ORIGIN_VALUES:
            problem = f"expected one of {', '.join(ORIGIN_VALUES)}, got {value!r}"
        if problem is None and name == AttributeKey.MODEL and ctx.item.type == ROSTER_ROLE:
            problem = model_problem(value)
        if problem is not None:
            issues.append(
                CheckIssue(
                    level, ctx.item.id, f"attribute {name!r}: {problem}", rule="attribute_valid"
                )
            )
    return issues


def _pronouns_valid(ctx: ValidatorContext) -> list[CheckIssue]:
    """A stored ``pronouns`` that fails the shape rule, on a type that declares the attribute.

    Judges the text as the file stores it and reports it, leaving it as written: renderers read
    such a value as unset. A value of another kind is ``attribute_valid``'s finding.
    """
    item = ctx.item
    if ctx.raw_text is None or AttributeKey.PRONOUNS not in ctx.spec.item_attributes(item.type):
        return []
    try:
        stored = sections.split_frontmatter(ctx.raw_text, source=item.path)[0]
    except SquadsError:
        return []
    value = stored.get(AttributeKey.PRONOUNS)
    problem = pronouns_problem(value) if isinstance(value, str) else None
    if problem is None:
        return []
    return [
        CheckIssue(
            _resolved_level(ctx, "pronouns_valid"),
            item.id,
            f"pronouns {problem} — replace it with "
            f"`sq {item.type} {item.slug} update --pronouns <text>`",
            rule="pronouns_valid",
        )
    ]


def _frontmatter_key_undeclared(ctx: ValidatorContext) -> list[CheckIssue]:
    """Every attribute no declaration on the item's type names, to catch a typo. Selected per
    project; it reports and never rewrites."""
    declared = set(ctx.spec.item_attributes(ctx.item.type)) | {
        f.code for f in ctx.spec.fields_for(ctx.item.type)
    }
    level = _resolved_level(ctx, "frontmatter_key_undeclared")
    return [
        CheckIssue(
            level,
            ctx.item.id,
            f"frontmatter key {key!r} is not declared on {ctx.item.type}",
            rule="frontmatter_key_undeclared",
        )
        for key in ctx.item.attributes
        if key not in declared
    ]


#: The closed per-item validator catalog — a CODE/definition constant, immutable and shared
#: across every request (fine under the ``_context.py`` CODE-vs-REQUEST split: it varies by
#: neither request nor squad). Every ``VALIDATOR_NAMES`` member resolves here (asserted below).
CATALOG: dict[str, Validator] = {
    "parent_in": _parent_in,
    "no_parent": _no_parent,
    "parent_present": _parent_present,
    "parent_acyclic": _parent_acyclic,
    "item_status_valid": _item_status_valid,
    "dangling_ref": _dangling_ref,
    "ref_kind_valid": _ref_kind_valid,
    "agent_registered": _agent_registered,
    "subentity_mapping": _subentity_mapping,
    "subentity_status_valid": _subentity_status_valid,
    "subentity_container_marker": _subentity_container_marker,
    "subentity_body_written": _subentity_body_written,
    "subentity_title_present": _subentity_title_present,
    "subentity_title_max": _subentity_title_max,
    "subentity_deferral_resolved": _subentity_deferral_resolved,
    "subentities_settled_with_parent": _subentities_settled_with_parent,
    "no_status_banner": _no_status_banner,
    "supersedes_incoming": _supersedes_incoming,
    "ref_rule_target_present": _ref_rule_target_present,
    "item_skill_shadowed": _item_skill_shadowed,
    "item_title_max": _item_title_max,
    "ref_rule_target_typed": _ref_rule_target_typed,
    "body_written": _body_written,
    "description_present": _description_present,
    "assignee_present": _assignee_present,
    "blocked_has_blocker": _blocked_has_blocker,
    "settled_requires_discussion": _settled_requires_discussion,
    "external_id_not_in_title": _external_id_not_in_title,
    "attribute_valid": _attribute_valid,
    "frontmatter_key_undeclared": _frontmatter_key_undeclared,
    "pronouns_valid": _pronouns_valid,
}
assert set(CATALOG) == VALIDATOR_NAMES, "CATALOG must implement exactly VALIDATOR_NAMES"

#: What each catalog member needs from the context beyond the item and spec, so a member that
#: cannot run on a path is skipped by name. Listed members sit the gate out; error-level
#: ``subentity_container_marker`` does because no edit causes or cures its corpus/spec mismatch,
#: so gating would block every edit on the type.
VALIDATOR_CONTEXT: dict[str, frozenset[ContextRequirement]] = {
    "subentity_container_marker": frozenset({ContextRequirement.RAW_TEXT}),
    "subentity_body_written": frozenset({ContextRequirement.RAW_TEXT}),
    "body_written": frozenset({ContextRequirement.RAW_TEXT}),
    "settled_requires_discussion": frozenset({ContextRequirement.RAW_TEXT}),
    "no_status_banner": frozenset({ContextRequirement.RAW_TEXT}),
    "ref_rule_target_present": frozenset({ContextRequirement.TYPE_PRESENT}),
    "item_skill_shadowed": frozenset({ContextRequirement.RAW_TEXT}),
    "attribute_valid": frozenset({ContextRequirement.RAW_TEXT}),
    "pronouns_valid": frozenset({ContextRequirement.RAW_TEXT}),
}
assert set(VALIDATOR_CONTEXT) <= set(CATALOG), (
    "VALIDATOR_CONTEXT must only declare requirements for members CATALOG implements"
)
assert {r.value for r in ContextRequirement} <= {
    f.name for f in dataclasses.fields(ValidatorContext)
}, "every ContextRequirement must name a real ValidatorContext field"


# --------------------------------------------------------------------------- squad-global catalog


def on_disk_not_indexed(seq: int, fid: str, *, indexed: bool, level: str) -> CheckIssue | None:
    """One direction of ``_index_reconciled``, factored to a single-item predicate so
    ``check``'s confirm round in ``_check.py`` can re-run this exact comparison against
    a freshly loaded index's membership for just this candidate — never a second copy."""
    if indexed:
        return None
    return CheckIssue(level, fid, "on disk but not in index (run `sq repair`)", "index_reconciled")


def not_on_disk(item: Item, *, on_disk: bool, level: str) -> CheckIssue | None:
    """The other direction of ``_index_reconciled`` — same reuse rationale as
    ``on_disk_not_indexed``."""
    if on_disk:
        return None
    return CheckIssue(level, item.id, "in index but no markdown file found", "index_reconciled")


def _index_reconciled(ctx: SquadGlobalContext) -> list[CheckIssue]:
    """Index and on-disk files agree, compared by sequence
    number (width-tolerant across a repad). The whole-scan pass over the pair; ``check``'s
    confirm pass re-runs ``on_disk_not_indexed``/``not_on_disk`` directly, one candidate at
    a time, rather than calling this function again — a full rescan would reintroduce the
    cost the lock-free design exists to avoid."""
    level = squad_global_level(ctx.spec, "index_reconciled")
    index_seqs = {it.sequence_id for it in ctx.index.items.values()}
    on_disk_seqs = set(ctx.on_disk)
    issues = [
        issue
        for seq, (fid, _md, _data) in ctx.on_disk.items()
        if (issue := on_disk_not_indexed(seq, fid, indexed=seq in index_seqs, level=level))
        is not None
    ]
    issues += [
        issue
        for it in ctx.index.items.values()
        if (issue := not_on_disk(it, on_disk=it.sequence_id in on_disk_seqs, level=level))
        is not None
    ]
    return issues


def live_roster_slugs(ctx: SquadGlobalContext) -> tuple[frozenset[str], frozenset[str]]:
    """The ``(live role slugs, live skill slugs)`` pair :func:`backend_entry_candidates` hands to
    each backend's ``managed_entry_paths``, derived from ``ctx.index`` via
    :func:`is_live_roster_entry`, the predicate ``RosterProjection.project_item`` uses. It is public
    because :meth:`CheckMixin._confirm_cross_source` calls it again on a freshly reloaded index (see
    :func:`backend_entry_missing`).
    """
    roles = frozenset(
        slug
        for it in ctx.index.items.values()
        if it.type == ROSTER_ROLE and is_live_roster_entry(it, ctx.spec) and (slug := it.slug)
    )
    skills = frozenset(
        slug
        for it in ctx.index.items.values()
        if it.type == ROSTER_SKILL and is_live_roster_entry(it, ctx.spec) and (slug := it.slug)
    )
    return roles, skills


def _backend_reconciled(ctx: SquadGlobalContext) -> list[CheckIssue]:
    """Each active backend's fixed top-level managed files exist on disk, at **error**, since only
    ``sq sync`` explains their absence. It reads only the config and the disk, never ``ctx.index``,
    so it is not cross-source and needs no confirm round, unlike the per-entry pointer claim
    (:func:`backend_entry_candidates`, :func:`backend_entry_missing`), which is index-derived.
    """
    bctx = BackendContext(
        paths=ctx.paths, spec=ctx.spec, playbook=ctx.playbook, catalog=ctx.catalog
    )
    level = squad_global_level(ctx.spec, "backend_reconciled")
    issues: list[CheckIssue] = []
    for backend in ctx.backends():
        issues.extend(
            CheckIssue(
                level,
                rel_path,
                f"managed file missing — run `sq sync` (backend: {backend.name})",
                rule="backend_reconciled",
            )
            for rel_path in backend.managed_paths(bctx)
            if not (bctx.root / rel_path).exists()
        )
    return issues


def backend_entry_candidates(ctx: SquadGlobalContext) -> list[tuple[str, str]]:
    """Per-entry backend pointers absent right now against *ctx.index*: scan-time candidates for
    ``check``'s confirm round, never reported directly. Each ``(backend, rel_path)`` is confirmed by
    :func:`backend_entry_missing` against a fresh index. It reports at **warn**, as a gitignored
    backend directory already fails on :func:`_backend_reconciled`'s error-level top-level entry.
    """
    live_role_slugs, live_skill_slugs = live_roster_slugs(ctx)
    bctx = BackendContext(
        paths=ctx.paths,
        spec=ctx.spec,
        playbook=ctx.playbook,
        catalog=ctx.catalog,
        live_role_slugs=live_role_slugs,
        live_skill_slugs=live_skill_slugs,
    )
    candidates: list[tuple[str, str]] = []
    for backend in ctx.backends():
        candidates.extend(
            (backend.name, rel_path)
            for rel_path in backend.managed_entry_paths(bctx)
            if not (bctx.root / rel_path).exists()
        )
    return candidates


def backend_entry_missing(
    backend_name: str, rel_path: str, *, root: Path, fresh_live_paths: frozenset[str]
) -> CheckIssue | None:
    """Re-observe one per-entry-pointer candidate (see :func:`backend_entry_candidates`) against the
    fresh index's recomputed live set and the disk. *fresh_live_paths* is one backend's
    ``managed_entry_paths`` from the fresh index; if the slug was retired or the file created since
    the scan, the candidate resolves to ``None``.
    """
    if rel_path not in fresh_live_paths:
        return None
    if (root / rel_path).exists():
        return None
    return CheckIssue(
        "warn",
        rel_path,
        f"managed pointer missing — run `sq sync` (backend: {backend_name})",
        "backend_reconciled",
    )


def backend_entry_path(
    backend: AgentBackend,
    paths: SquadPaths,
    spec: WorkflowSpec,
    playbook: PlaybookSpec,
    catalog: CatalogSource,
    kind: str,
    slug: str,
) -> str | None:
    """The one declared path for a single live role/skill *slug*, via
    :meth:`~squads._backends._base.AgentBackend.managed_entry_paths` scoped to that slug (an empty
    ``BackendContext`` otherwise), so there is no second path rule. ``None`` when *backend* declares
    none for that *kind* (e.g. ``agents_md``). Shared by :func:`backend_entry_drift_candidates` and
    the currency confirm round, so both compare the same path.
    """
    ctx = (
        BackendContext(
            paths=paths,
            spec=spec,
            playbook=playbook,
            catalog=catalog,
            live_role_slugs=frozenset({slug}),
        )
        if kind == "role"
        else BackendContext(
            paths=paths,
            spec=spec,
            playbook=playbook,
            catalog=catalog,
            live_skill_slugs=frozenset({slug}),
        )
    )
    found = backend.managed_entry_paths(ctx)
    return found[0] if found else None


def backend_entry_drift(  # noqa: PLR0913 — one keyword per input of the re-render
    backend: AgentBackend,
    kind: str,
    item: Item,
    *,
    paths: SquadPaths,
    spec: WorkflowSpec,
    playbook: PlaybookSpec,
    catalog: CatalogSource,
    role_skills: dict[str, list[str]],
    rel_path: str,
) -> CheckIssue | None:
    """Re-observe one currency candidate: render *item* fresh and compare it with *rel_path* on
    disk. The render is the expectation, never recovered from the file. ``None`` when the file is
    gone, the render matches, or the resolver refuses the role override (reported elsewhere).
    Otherwise **error** when the drift is in the containment fragment
    :meth:`~squads._backends._base.AgentBackend.restriction_fragment` requires (a stale pointer
    still granting revoked authority), else **warn**.

    *role_skills* must carry the role's freshly resolved preload list, or a ``scopes``-preloaded
    skill reads as drift, and a role's expectation is resolved through
    :func:`~squads._roles._resolver.resolve_role_for_item`, not stored attributes.
    """
    disk_path = paths.root / rel_path
    try:
        disk_text = disk_path.read_text(encoding="utf-8")
    except OSError:
        return None
    bctx = BackendContext(
        paths=paths, spec=spec, playbook=playbook, catalog=catalog, role_skills=role_skills
    )
    if kind == "role":
        from squads._errors import SquadsError

        try:
            role = resolve_role_for_item(item, paths.squad_dir, catalog=catalog)
        except SquadsError:
            return None
    else:
        role = None
    fresh = (
        backend.render_role_entry(bctx, item, role)
        if role is not None
        else backend.render_skill_entry(bctx, item)
    )
    if fresh is None or fresh == disk_text:
        return None
    level = "warn"
    if role is not None:
        expected = backend.restriction_fragment(role)
        if expected is not None and expected not in disk_text:
            level = "error"
    verb = (
        "capability restriction had drifted"
        if level == "error"
        else "is out of date or edited by hand"
    )
    return CheckIssue(
        level,
        rel_path,
        f"managed pointer {verb} — run `sq sync` (backend: {backend.name})",
        "backend_reconciled",
    )


def _roster_config_integrity(ctx: SquadGlobalContext) -> list[CheckIssue]:
    """The config-integrity clauses (``no_live_role``/``preloaded_skill``) evaluated against state
    already on disk rather than gating a transition, so a squad already in a state a retirement
    would refuse is reported. It delegates to ``_config_integrity.check_all``, which the retirement
    gate also calls, and renders each finding through ``render_finding``. It reads the index and
    config only, so it has no cross-source obligation.
    """
    findings = config_integrity.check_all(
        ctx.index,
        ctx.spec,
        ctx.paths.config.active_backends,
        ctx.playbook,
        ctx.paths.squad_dir,
        ctx.catalog,
    )
    level = squad_global_level(ctx.spec, "roster_config_integrity")
    return [
        CheckIssue(
            level,
            f.entry,
            f"config integrity: {config_integrity.render_finding(f)}",
            rule="roster_config_integrity",
        )
        for f in findings
    ]


def _default_designation_duplicated(ctx: SquadGlobalContext) -> list[CheckIssue]:
    """More than one live ``role`` item holding the default-role designation: an error naming the
    holders, with ``sq role <addr> set-default`` as the remedy, found through
    :func:`~squads._roles._resolver.holds_default_designation`, not the stored key. It is report-
    only and outside ``config_integrity.check_all``, as on a reactivation it would fire with no
    available remedy.
    """
    live = ctx.spec.live_statuses(ROSTER_ROLE)
    holders = sorted(
        it.id
        for it in ctx.index.items.values()
        if it.type == ROSTER_ROLE
        and it.status in live
        and holds_default_designation(it, ctx.paths.squad_dir, catalog=ctx.catalog)
    )
    if len(holders) <= 1:
        return []
    return [
        CheckIssue(
            squad_global_level(ctx.spec, "default_designation_duplicated"),
            "",
            "more than one live role carries the default-role designation: "
            f"{', '.join(holders)} — remedy: `sq role <addr> set-default`",
            rule="default_designation_duplicated",
        )
    ]


def _slug_breach_remedy(
    breach: SlugBreach, breaching_ids: frozenset[str], live: frozenset[str]
) -> str:
    """The commands that replace a breaching roster entry, addressed by id because a slug that
    matches a group verb cannot be addressed by slug. An entry that breaks no rule of its own
    points at the other holders that do; a retired operator is retired again after the re-add."""
    if breach.problem is None:
        culprits = [i for i in breach.held_by if i in breaching_ids]
        if culprits:
            if len(culprits) == 1:
                return f"replace {culprits[0]}, which breaks a rule of its own"
            return f"replace {', '.join(culprits)}, which break a rule of their own"
    if breach.kind == "operator":
        name = breach.item.title
        text = (
            f'sq operator {breach.item.id} remove --purge, then sq operator add "{name}" '
            "--slug <compliant slug>"
        )
        if breach.item.status not in live:
            text += f", then sq operator <compliant slug> status {breach.item.status}"
        return text
    if breach.kind == "skill":
        return (
            "add the skill again under another name with sq skill add, "
            f"then sq skill {breach.item.id} remove --purge"
        )
    return (
        "create the role again under a compliant slug with sq role add <slug>, "
        f"then sq role {breach.item.id} remove --purge"
    )


def _roster_slug_valid(ctx: SquadGlobalContext) -> list[CheckIssue]:
    """Each role or operator, live or retired, whose slug is outside its grammar or shared inside
    the author namespace, one error per entry with the replacing commands as the remedy.

    Report-only, like ``default_designation_duplicated``: the remedy removes and recreates the
    entry, so a write gate on this would lock the squad out of it.
    """
    items = ctx.index.items.values()
    breaches = roster_slug_breaches(
        [it for it in items if it.type == ROSTER_ROLE],
        [it for it in items if it.type == ROSTER_OPERATOR],
        [it for it in items if it.type == ROSTER_SKILL],
        group_verbs=True,
    )
    breaching = frozenset(b.item.id for b in breaches if b.problem is not None)
    live = ctx.spec.live_statuses(ROSTER_OPERATOR)
    level = squad_global_level(ctx.spec, "roster_slug_valid")
    return [
        CheckIssue(
            level,
            b.item.id,
            f"{b.text('it is also held by')} — remedy: {_slug_breach_remedy(b, breaching, live)}",
            rule="roster_slug_valid",
        )
        for b in breaches
    ]


def _display_config_valid(ctx: SquadGlobalContext) -> list[CheckIssue]:
    """Each part of the ``[display]`` table in ``.squads.toml`` that is not usable and fell back
    to its default: an unknown key, a value that is not ``true`` or ``false``, or a non-table.

    The squad has no item to attach this to, so the finding names the config file.
    """
    level = squad_global_level(ctx.spec, "display_config_valid")
    return [
        CheckIssue(
            level, CONFIG_FILENAME, f"{problem}; the default applies", rule="display_config_valid"
        )
        for problem in ctx.paths.config.display_problems
    ]


def _working_language_valid(ctx: SquadGlobalContext) -> list[CheckIssue]:
    """A ``working_language`` in ``.squads.toml`` that is not a BCP 47 tag Babel knows; English
    applies. An absent key is valid. The finding names the config file."""
    level = squad_global_level(ctx.spec, "working_language_valid")
    _, problem = resolve_working_language(ctx.paths.config.working_language)
    return (
        []
        if problem is None
        else [CheckIssue(level, CONFIG_FILENAME, problem, rule="working_language_valid")]
    )


def _view_transform_resolves(ctx: SquadGlobalContext) -> list[CheckIssue]:
    """Each override view transform that cannot be called: its file is missing, escapes
    ``.overrides/``, fails to import, or lacks a function sq can call. Imports the file, so its
    top-level code runs; the function is never called."""
    level = squad_global_level(ctx.spec, "view_transform_resolves")
    return [
        CheckIssue(level, f"views.{name}.transform", message, rule="view_transform_resolves")
        for name, message in check_view_transforms(ctx.spec, ctx.paths.squad_dir)
    ]


def _role_base_resolves(ctx: SquadGlobalContext) -> list[CheckIssue]:
    """A live role whose base does not resolve: a catalog role the catalog no longer declares, a
    template role naming an undeclared template or missing (or carrying) the `tech` it takes, a
    self-defining role without its job title or description, or a role storing both a template and a
    mission. `sq sync` keeps materialising such a role from what it stores, and this reports it.
    """
    try:
        catalog = ctx.catalog()
    except SquadsError:  # the broken catalog override is its own finding
        return []
    level = squad_global_level(ctx.spec, "role_base_resolves")
    live = ctx.spec.live_statuses(ROSTER_ROLE)
    return [
        CheckIssue(level, it.id, f"role {it.slug!r} {problem}", rule="role_base_resolves")
        for it in sorted(ctx.index.items.values(), key=lambda i: i.sequence_id)
        if it.type == ROSTER_ROLE and it.status in live and it.slug
        for problem in base_problems(it, catalog)
    ]


#: A per-slug file key -> where a role that defines itself stores that field: an attribute, or the
#: item's own ``description``.
_FILE_KEY_STORED_AS: tuple[tuple[str, str], ...] = (
    ("title", AttributeKey.JOB_TITLE),
    ("description", "description"),
    ("mission", AttributeKey.MISSION),
    ("responsibilities", AttributeKey.RESPONSIBILITIES),
    ("agreements", AttributeKey.AGREEMENTS),
    ("color", AttributeKey.COLOR),
    ("can_spawn", AttributeKey.CAN_SPAWN),
    ("capabilities", AttributeKey.CAPABILITIES),
)


def _role_definition_shadowed(ctx: SquadGlobalContext) -> list[CheckIssue]:
    """A per-slug file that sets a field a role defining itself stores in its item: the file wins,
    so `sq role <slug> update` of that field has no effect. Names the file and the fields."""
    level = squad_global_level(ctx.spec, "role_definition_shadowed")
    issues: list[CheckIssue] = []
    for it in sorted(ctx.index.items.values(), key=lambda i: i.sequence_id):
        if it.type != ROSTER_ROLE or not it.slug or attrs.mission(it) is None:
            continue
        keys = override_file_keys(it.slug, ctx.paths.squad_dir)
        fields = sorted(
            key
            for key in keys
            if (stored := dict(_FILE_KEY_STORED_AS).get(key)) is not None
            and (it.description.strip() if stored == "description" else it.attribute(stored))
        )
        if fields:
            issues.append(
                CheckIssue(
                    level,
                    it.id,
                    f".overrides/roles/{it.slug}.toml sets {', '.join(fields)}, which role "
                    f"{it.slug!r} stores in its item: the file wins, so `sq role {it.slug} "
                    "update` of those fields has no effect — delete the file or those keys",
                    rule="role_definition_shadowed",
                )
            )
    return issues


def _playbook_guide_role_live(ctx: SquadGlobalContext) -> list[CheckIssue]:
    """A playbook guide whose role slug names no live role, a warning per dropped guide: the
    override accepts a project role slug by filename and the generated skill drops it unless the
    role is live. It is never a gate clause, since both remedies are outside a transition, and it
    reads the raw override (:func:`~squads._interactions._loader.playbook_override_guide_pairs`) to
    scope to guides the adopter wrote.
    """
    live = ctx.spec.live_statuses(ROSTER_ROLE)
    roles = [it for it in ctx.index.items.values() if it.type == ROSTER_ROLE]
    known = frozenset(slug for it in roles if (slug := it.slug))
    live_initial = ctx.spec.live_initial(ROSTER_ROLE)
    level = squad_global_level(ctx.spec, "playbook_guide_role_live")
    live_roles = [
        resolve_role_tolerantly(it, ctx.paths.squad_dir, catalog=ctx.catalog)
        for it in roles
        if it.status in live and it.slug
    ]
    override_guides = playbook_override_guide_pairs(ctx.paths.squad_dir, ctx.files)
    try:
        catalog_slugs = {r.slug for r in ctx.catalog().roles}
    except SquadsError:  # the broken catalog override is its own finding
        catalog_slugs = set[str]()
    messages = [
        orphaned_playbook_guide_message(
            item_type,
            slug,
            retired=slug in known,
            live_status=live_initial,
            in_catalog=slug in catalog_slugs,
        )
        for item_type, slug in orphaned_playbook_guides(
            ctx.playbook,
            ctx.spec,
            live_roles=live_roles,
            override_guides=override_guides,
        )
    ]
    messages += [
        unheld_capability_token_message(item_type, capability)
        for item_type, capability in unheld_capability_tokens(
            ctx.playbook,
            ctx.spec,
            live_roles=live_roles,
            override_guides=override_guides,
            override_commands=playbook_override_command_lines(ctx.paths.squad_dir, ctx.files),
        )
    ]
    return [CheckIssue(level, "", message, rule="playbook_guide_role_live") for message in messages]


@dataclass(frozen=True)
class _AuthorPool:
    """The roles that could author a type: every catalog role, every roster entry (with the
    status it rests in), and the capabilities each holds."""

    spec: WorkflowSpec
    statuses: dict[str, str]
    capabilities: dict[str, frozenset[str]]
    developer_capabilities: frozenset[str]

    def remedy(self, slug: str) -> str | None:
        """The command that brings role *slug* back, or ``None`` for a slug the catalog does not
        carry and the roster has no entry for. A roster entry whose status has no edge to the
        live status is revived with ``--force``, which the remedy says."""
        status = self.statuses.get(slug)
        if status is None:
            return (
                f"activate `{slug}` (`sq role activate {slug}`)"
                if slug in self.capabilities
                else None
            )
        live = self.spec.live_initial(ROSTER_ROLE)
        command = f"sq role {slug} status {live}"
        if self.spec.can_transition(ROSTER_ROLE, status, live):
            return f"reactivate `{slug}` (`{command}`)"
        return f"reactivate `{slug}` (`{command} --force`; {status} has no edge to {live})"

    def remedies(self, subjects: set[str]) -> list[str]:
        """What brings an author of the lane back: for a slug its own remedy, for a capability
        each role holding it, or a developer to add when a developer lane has no holder."""
        slugs: set[str] = set()
        add_developer = False
        for subject in subjects:
            if not subject.startswith(CAPABILITY_SUBJECT_PREFIX):
                slugs.add(subject)
                continue
            name = subject[len(CAPABILITY_SUBJECT_PREFIX) :]
            holders = {slug for slug, caps in self.capabilities.items() if name in caps}
            slugs |= holders
            add_developer |= not holders and name in self.developer_capabilities
        found = [self.remedy(slug) for slug in sorted(slugs)]
        remedies = [r for r in found if r is not None]
        return (
            [*remedies, "add a developer (`sq dev add --tech <tech>`)"]
            if add_developer
            else remedies
        )


def _type_has_live_author(ctx: SquadGlobalContext) -> list[CheckIssue]:
    """A non-roster type holding an item at a status that is not settled while no live role is
    an in-lane author of it, naming the catalog roles whose activation would fix it. A type
    whose items are all settled is not reported: a role retired on purpose leaves history, not
    debt."""
    roles = [it for it in ctx.index.items.values() if it.type == ROSTER_ROLE and it.slug]
    live = ctx.spec.live_statuses(ROSTER_ROLE)
    live_roles = [
        resolve_role_tolerantly(it, ctx.paths.squad_dir, catalog=ctx.catalog)
        for it in roles
        if it.status in live
    ]
    live_slugs = {role.slug for role in live_roles}
    try:
        catalog = ctx.catalog()
    except SquadsError:  # the broken catalog override is its own finding
        catalog = get_catalog()
    pool = _AuthorPool(
        spec=ctx.spec,
        statuses={it.slug: it.status for it in roles if it.slug},
        capabilities={
            **{r.slug: frozenset(r.capabilities) for r in catalog.roles},
            **{
                it.slug: frozenset(
                    resolve_role_tolerantly(
                        it, ctx.paths.squad_dir, catalog=ctx.catalog
                    ).capabilities
                )
                for it in roles
                if it.slug
            },
        },
        developer_capabilities=catalog.developer_capabilities(),
    )
    level = squad_global_level(ctx.spec, "type_has_live_author")
    issues: list[CheckIssue] = []
    for item_type in sorted(ctx.spec.non_roster_types()):
        open_count = sum(
            1
            for it in ctx.index.items.values()
            if it.type == item_type and not ctx.spec.role_for(it.status).settled
        )
        if not open_count or in_lane_owner(item_type, ctx.playbook, live_roles) & live_slugs:
            continue
        remedies = pool.remedies(
            {subject for subject, types in create_lanes(ctx.playbook).items() if item_type in types}
        )
        issues.append(
            CheckIssue(
                level,
                "",
                f"type {item_type!r} has {open_count} open {_plural(open_count, 'item')} but no "
                "live role authors it" + (f" — {' or '.join(remedies)}" if remedies else ""),
                rule="type_has_live_author",
            )
        )
    return issues


def active_items(index: SquadsDB, spec: WorkflowSpec) -> list[Item]:
    """The active items in sequence order: work-category items resting at a status whose role
    declares ``live = true``."""
    return sorted(
        (
            it
            for it in index.items.values()
            if (ts := spec.items.get(it.type)) is not None
            and ts.category == "work"
            and it.status in spec.live_statuses(it.type)
        ),
        key=lambda it: it.sequence_id,
    )


def _plural(count: int, noun: str) -> str:
    """*noun*, pluralised with ``s`` unless *count* is one."""
    return noun if count == 1 else f"{noun}s"


def _ids(items: list[Item], limit: int = 5) -> str:
    """The ids of *items* for a message: the first *limit*, then a count of the rest."""
    shown = ", ".join(it.id for it in items[:limit])
    return shown if len(items) <= limit else f"{shown} and {len(items) - limit} more"


def _squad_global_param(ctx: SquadGlobalContext, name: str) -> int | None:
    """The integer parameter of the selection of *name*, or ``None`` when it is not selected."""
    param = squad_global_selection(ctx.spec, name)[0]
    return int(param) if param is not None else None


def _children_settled_with_parent(ctx: SquadGlobalContext) -> list[CheckIssue]:
    """One finding per parent at a settled status that still has a child at a status that is not
    settled. Sub-entities are not children."""
    open_children: dict[int, list[Item]] = {}
    for it in ctx.index.items.values():
        parent = ctx.index.get(it.parent) if it.parent else None
        if parent is not None and not ctx.spec.role_for(it.status).settled:
            open_children.setdefault(parent.sequence_id, []).append(it)
    level = squad_global_level(ctx.spec, "children_settled_with_parent")
    issues: list[CheckIssue] = []
    for seq in sorted(open_children):
        parent = ctx.index.items[seq]
        if not ctx.spec.role_for(parent.status).settled:
            continue
        kids = sorted(open_children[seq], key=lambda it: it.sequence_id)
        issues.append(
            CheckIssue(
                level,
                parent.id,
                f"{parent.id} is {parent.status} with {len(kids)} open "
                f"{'child' if len(kids) == 1 else 'children'}: {_ids(kids)}",
                rule="children_settled_with_parent",
            )
        )
    return issues


def _dependency_edges(index: SquadsDB, spec: WorkflowSpec) -> dict[int, list[int]]:
    """Each item's sequence number -> the sequence numbers it depends on, from every ref whose
    kind declares the dependency role, oriented by the kind's declared direction."""
    blocker_kind = spec.dependency_ref_kind("blocker")
    dependent_kind = spec.dependency_ref_kind("dependent")
    edges: dict[int, list[int]] = {}
    for it in index.items.values():
        for r in it.refs:
            rid, kind = split_ref(r)
            target = index.get(rid)
            if target is None:
                continue
            if kind == blocker_kind:
                edges.setdefault(target.sequence_id, []).append(it.sequence_id)
            elif kind == dependent_kind:
                edges.setdefault(it.sequence_id, []).append(target.sequence_id)
    return edges


class _Tarjan:
    """Iterative strongly-connected-components pass over *edges*, so a long chain cannot overflow
    the stack."""

    def __init__(self, edges: dict[int, list[int]]) -> None:
        self.edges = edges
        self.number: dict[int, int] = {}
        self.low: dict[int, int] = {}
        self.stack: list[int] = []
        self.on_stack: set[int] = set()
        self.cycles: list[list[int]] = []

    def run(self) -> list[list[int]]:
        for root in sorted(self.edges):
            if root not in self.number:
                self._walk(root)
        return sorted(self.cycles)

    def _walk(self, root: int) -> None:
        work: list[tuple[int, int]] = [(root, 0)]
        while work:
            node, pos = work.pop()
            if pos == 0:
                self.number[node] = self.low[node] = len(self.number)
                self.stack.append(node)
                self.on_stack.add(node)
            child = self._next_unvisited(node, pos)
            if child is not None:
                work.append((node, child[1]))
                work.append((child[0], 0))
                continue
            if self.low[node] == self.number[node]:
                self._close(node)
            if work:
                parent = work[-1][0]
                self.low[parent] = min(self.low[parent], self.low[node])

    def _next_unvisited(self, node: int, pos: int) -> tuple[int, int] | None:
        """The next target of *node* from *pos* not yet numbered, with the position after it;
        lowers ``low`` over the targets on the stack passed on the way."""
        targets = self.edges.get(node, [])
        for i in range(pos, len(targets)):
            target = targets[i]
            if target not in self.number:
                return target, i + 1
            if target in self.on_stack:
                self.low[node] = min(self.low[node], self.number[target])
        return None

    def _close(self, node: int) -> None:
        component: list[int] = []
        while (member := self.stack.pop()) != node:
            self.on_stack.discard(member)
            component.append(member)
        self.on_stack.discard(node)
        component.append(node)
        if len(component) > 1 or node in self.edges.get(node, []):
            self.cycles.append(sorted(component))


def _cycles(edges: dict[int, list[int]]) -> list[list[int]]:
    """Every strongly connected component with a cycle (two or more nodes, or a self-edge), each
    sorted, in order of its least member."""
    return _Tarjan(edges).run()


def _cycle_path(edges: dict[int, list[int]], component: list[int]) -> list[int]:
    """The shortest way back to the component's least member along its dependency edges,
    starting and ending on that member."""
    start = component[0]
    members = set(component)
    came_from: dict[int, int] = {}
    queue = [start]
    for node in queue:
        for nxt in edges.get(node, []):
            if nxt == start:
                path = [node]
                while path[-1] != start:
                    path.append(came_from[path[-1]])
                return [*reversed(path), start]
            if nxt in members and nxt not in came_from and nxt != start:
                came_from[nxt] = node
                queue.append(nxt)
    return [start, start]


def _dependency_acyclic(ctx: SquadGlobalContext) -> list[CheckIssue]:
    """One finding per strongly connected group of dependency edges, settled or not, giving a
    path around it (each item depends on the next) and any further items in the group."""
    level = squad_global_level(ctx.spec, "dependency_acyclic")
    edges = _dependency_edges(ctx.index, ctx.spec)
    issues: list[CheckIssue] = []
    for component in _cycles(edges):
        path = _cycle_path(edges, component)
        text = "dependency cycle: " + " -> ".join(ctx.index.items[seq].id for seq in path)
        rest = [seq for seq in component if seq not in path]
        if rest:
            text += " (also involving " + ", ".join(ctx.index.items[s].id for s in rest) + ")"
        issues.append(CheckIssue(level, "", text, rule="dependency_acyclic"))
    return issues


def _wip_limit(ctx: SquadGlobalContext) -> list[CheckIssue]:
    """One finding per assignee holding more active items than the selected limit."""
    limit = _squad_global_param(ctx, "wip_limit")
    if limit is None:
        return []
    held: dict[str, list[Item]] = {}
    for it in active_items(ctx.index, ctx.spec):
        if it.assignee:
            held.setdefault(it.assignee, []).append(it)
    level = squad_global_level(ctx.spec, "wip_limit")
    return [
        CheckIssue(
            level,
            "",
            f"{slug} holds {len(items)} active {_plural(len(items), 'item')} "
            f"(limit {limit}): {_ids(items)}",
            rule="wip_limit",
        )
        for slug, items in sorted(held.items())
        if len(items) > limit
    ]


def _unassigned_active(ctx: SquadGlobalContext) -> list[CheckIssue]:
    """One finding when more active items than the selected number have no assignee."""
    limit = _squad_global_param(ctx, "unassigned_active")
    if limit is None:
        return []
    unassigned = [it for it in active_items(ctx.index, ctx.spec) if not it.assignee]
    if len(unassigned) <= limit:
        return []
    return [
        CheckIssue(
            squad_global_level(ctx.spec, "unassigned_active"),
            "",
            f"{len(unassigned)} active {_plural(len(unassigned), 'item')} "
            f"{'has' if len(unassigned) == 1 else 'have'} no assignee (limit {limit}): "
            f"{_ids(unassigned)}",
            rule="unassigned_active",
        )
    ]


def _stale_active(ctx: SquadGlobalContext) -> list[CheckIssue]:
    """One finding per active item last updated more than the selected number of days before the
    run's clock instant."""
    days = _squad_global_param(ctx, "stale_active")
    if days is None:
        return []
    cutoff = ctx.now - timedelta(days=days)
    level = squad_global_level(ctx.spec, "stale_active")
    return [
        CheckIssue(
            level,
            it.id,
            f"{it.id} is {it.status} and untouched since {clock.iso(it.updated_at)} "
            f"(more than {days} {_plural(days, 'day')})",
            rule="stale_active",
        )
        for it in active_items(ctx.index, ctx.spec)
        if it.updated_at < cutoff
    ]


#: The closed squad-global validator registry — same CODE-constant status as ``CATALOG``.
SQUAD_GLOBAL_CATALOG: dict[str, SquadGlobalValidator] = {
    "index_reconciled": _index_reconciled,
    "backend_reconciled": _backend_reconciled,
    "roster_config_integrity": _roster_config_integrity,
    "default_designation_duplicated": _default_designation_duplicated,
    "roster_slug_valid": _roster_slug_valid,
    "role_base_resolves": _role_base_resolves,
    "role_definition_shadowed": _role_definition_shadowed,
    "playbook_guide_role_live": _playbook_guide_role_live,
    "display_config_valid": _display_config_valid,
    "working_language_valid": _working_language_valid,
    "view_transform_resolves": _view_transform_resolves,
    "type_has_live_author": _type_has_live_author,
    "children_settled_with_parent": _children_settled_with_parent,
    "dependency_acyclic": _dependency_acyclic,
    "wip_limit": _wip_limit,
    "unassigned_active": _unassigned_active,
    "stale_active": _stale_active,
}
assert set(SQUAD_GLOBAL_CATALOG) == SQUAD_GLOBAL_VALIDATOR_NAMES, (
    "SQUAD_GLOBAL_CATALOG must implement exactly SQUAD_GLOBAL_VALIDATOR_NAMES"
)


# --------------------------------------------------------------------------- context builders


def registered_slugs(index: SquadsDB, spec: WorkflowSpec) -> frozenset[str]:
    """The set of slugs a role or operator declares — what ``agent_registered`` checks an item's
    author/assignee against. A skill never authors, so it is outside the set."""
    return frozenset(
        slug
        for r in index.items.values()
        if r.type in (ROSTER_ROLE, ROSTER_OPERATOR)
        for slug in (r.slug,)
        if slug
    )


@dataclass(frozen=True)
class IncomingEdges:
    """The sequence numbers of every item some ref points at, by edge role: through a declared
    ``supersession`` kind, and through a declared ``dependency`` kind of either direction."""

    supersedes: frozenset[int]
    dependency: frozenset[int]


def incoming_edges(index: SquadsDB, spec: WorkflowSpec) -> IncomingEdges:
    """Both incoming-edge sets from one pass over every ref. Kinds are resolved through
    :meth:`WorkflowSpec.supersession_ref_kinds` and :meth:`WorkflowSpec.dependency_ref_kinds`
    (zero or more declared), never a fixed spelling, and a target is keyed by sequence number so
    a ref stored at another id width still matches."""
    supersession = spec.supersession_ref_kinds()
    dependency = spec.dependency_ref_kinds()
    supersedes: set[int] = set()
    depended: set[int] = set()
    for it in index.items.values():
        for r in it.refs:
            rid, kind = split_ref(r)
            if kind not in supersession and kind not in dependency:
                continue
            try:
                number = number_for_id(rid)
            except InvalidIdError:
                continue  # `dangling_ref` reports an id that does not parse
            if kind in supersession:
                supersedes.add(number)
            if kind in dependency:
                depended.add(number)
    return IncomingEdges(frozenset(supersedes), frozenset(depended))


def supersedes_incoming_seqs(index: SquadsDB, spec: WorkflowSpec) -> frozenset[int]:
    """Sequence numbers of every item with an incoming edge of a declared ``supersession``
    kind — what ``supersedes_incoming`` checks a Superseded record's own sequence number
    against."""
    return incoming_edges(index, spec).supersedes


def types_present(index: SquadsDB) -> frozenset[str]:
    """Every item type with at least one corpus member — what ``ref_rule_target_present``
    checks its selected target type(s) against for its inertness precondition: before the
    target type's first item exists, the finding's remedy does not exist either, so the check
    is inert rather than warning on the whole pre-existing corpus at once."""
    return frozenset(it.type for it in index.items.values())


# --------------------------------------------------------------------------- composition + engine


# Cross-cutting per-item hygiene shared by every category (the accepted decision's "common
# core") is declared as `_workflow/_models.py::COMMON_CORE`, not here — see that constant for
# why the vocabulary half lives low and this module only supplies the behaviour.
@dataclass(frozen=True)
class ValidatorEngine:
    """Runs the catalog over live item and index state: one engine, two call sites, built with the
    request's ``spec``. ``report()`` collects every issue for ``sq check``; ``gate()`` runs the one
    item's error-level members whose context it holds and aborts on the first finding. Warn-level
    members are never evaluated on a write and squad-global validators never run in gate mode.
    ``paths`` and ``role_catalog`` are required once ``squad_global`` is non-empty.
    """

    spec: WorkflowSpec
    playbook: PlaybookSpec
    paths: SquadPaths | None = None
    role_catalog: CatalogSource | None = None
    override_files: OverrideFiles | None = None
    backends: Callable[[], list[AgentBackend]] | None = None
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
        incoming: IncomingEdges,
        type_present: frozenset[str],
        raw_text: str | None,
        error_level_only: bool = False,
    ) -> list[CheckIssue]:
        """Run *item*'s effective members. *error_level_only* (set by ``gate()``) also skips a
        member whose resolved level for the item's type is not ``error``: it cannot refuse a
        write, so evaluating it would only cost time under the index lock."""
        item_spec = self.spec.items.get(item.type)
        if item_spec is None:
            return []  # a dropped/renamed type — not this engine's concern (index cross-check)
        names = effective_validator_names(item_spec.category, extra=tuple(item_spec.validators))
        ctx = ValidatorContext(
            item=item,
            spec=self.spec,
            index=index,
            registered_slugs=registered,
            supersedes_incoming=incoming.supersedes,
            dependency_incoming=incoming.dependency,
            type_present=type_present,
            raw_text=raw_text,
            squad_dir=self.paths.squad_dir if self.paths is not None else None,
        )
        held = ctx.held_context()
        issues: list[CheckIssue] = []
        run: set[str] = set()
        for name in names:
            # Strip a `:<param>`/`@<level>` suffix before the catalog lookup — every CATALOG
            # key is bare (Plane-1 already validated both suffixes on entry, and each member
            # resolves its own effective level/param straight off `ctx.spec`, not off `name`).
            bare = parse_validator_entry(name)[0]
            # `names` can hold several selections of one bare member (e.g.
            # `ref_rule_target_present:contract` and `:milestone`); the member reads every matching
            # entry from `ctx.spec` itself, so run each bare member once.
            if bare in run:
                continue
            run.add(bare)
            # A member runs only where the caller carries what it declared it needs: skipping by
            # name is the same outcome as running against a context it cannot read, but by decision
            # rather than coincidence.
            if not VALIDATOR_CONTEXT.get(bare, frozenset()) <= held:
                continue
            if error_level_only and _resolved_level(ctx, bare) != "error":
                continue
            issues += self.catalog[bare](ctx)
        return issues

    def report(
        self,
        index: SquadsDB,
        on_disk: OnDiskMap,
        *,
        bodies: dict[int, str] | None = None,
        only: frozenset[str] | None = None,
    ) -> list[CheckIssue]:
        """Collect every issue: every item's effective per-item set plus every squad-global
        validator (once). *bodies* maps sequence number to the item's on-disk text; a missing entry
        leaves body-reading validators silent for that item. *only*, when given, limits the per-item
        members to those item ids.
        """
        registered = registered_slugs(index, self.spec)
        incoming = incoming_edges(index, self.spec)
        present = types_present(index)
        bodies = bodies or {}
        issues: list[CheckIssue] = []
        for item in index.items.values():
            if only is not None and item.id not in only:
                continue
            issues += self._run_per_item(
                item,
                index,
                registered=registered,
                incoming=incoming,
                type_present=present,
                raw_text=bodies.get(item.sequence_id),
            )
        if self.squad_global:
            from squads._errors import SquadsError

            if (
                self.paths is None
                or self.role_catalog is None
                or self.override_files is None
                or self.backends is None
            ):
                raise SquadsError(
                    "ValidatorEngine.report(): squad-global validators need paths and a catalog"
                )
            g_ctx = SquadGlobalContext(
                index=index,
                on_disk=on_disk,
                spec=self.spec,
                paths=self.paths,
                playbook=self.playbook,
                catalog=self.role_catalog,
                files=self.override_files,
                backends=self.backends,
                now=clock.now(),
            )
            for name, validator in self.squad_global.items():
                if name not in SELECTABLE_SQUAD_GLOBAL_NAMES:
                    issues += validator(g_ctx)
            for entry in self.spec.squad.validators:
                selected = self.squad_global.get(parse_validator_entry(entry)[0])
                if selected is not None:
                    issues += selected(g_ctx)
        return issues

    def gate(self, item: Item, index: SquadsDB) -> None:
        """Abort on the first finding of an error-level per-item member for *item*'s type; warn-
        level members are not evaluated. This path holds neither :class:`ContextRequirement`, since
        a create gates an in-memory ``Item`` before any file exists and ``type_present`` is a full
        index scan per write; :meth:`_run_per_item` skips members requiring them
        (:data:`VALIDATOR_CONTEXT`).
        """
        registered = registered_slugs(index, self.spec)
        incoming = incoming_edges(index, self.spec)
        issues = [
            i
            for i in self._run_per_item(
                item,
                index,
                registered=registered,
                incoming=incoming,
                type_present=frozenset(),
                raw_text=None,
                error_level_only=True,
            )
            if i.level == "error"
        ]
        if issues:
            from squads._errors import SquadsError

            raise SquadsError(issues[0].message)
