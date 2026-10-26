"""The ``sq check`` gate: the corpus scan, the cross-source confirm round and the report."""

import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from squads import _aio
from squads import _clock as clock
from squads import _sections as sections
from squads import _view_tags as view_tags
from squads import _views as views
from squads._backends._base import BackendContext
from squads._errors import SquadsError
from squads._index._resolver import item_file
from squads._interactions._models import PlaybookSpec
from squads._interactions._skills import (
    item_type_for_skill_slug,
    orphaned_skill_item_type,
)
from squads._itemfile import (
    SkewKey,
    frontmatter_skew,
    read_frontmatter,
    stale_encoding_clause,
)
from squads._models import _markers as markers
from squads._models._index import SquadsDB
from squads._models._item import (
    INVENTED_WHEN_ABSENT,
    Item,
    slug_from_stem,
)
from squads._services._base import ServiceCore
from squads._services._corpus_files import (
    LegacySkillBody,
    MissingId,
    Unparseable,
    Unreadable,
    Vanished,
    malformed_id_message,
    read_corpus_file,
    seq_from_frontmatter_id,
    stem_digit_run,
)
from squads._services._duplicate_ids import (
    confirmed_groups,
    confirmed_shared_numbers,
    duplicate_groups,
    normalized_id,
    shared_number_groups,
)
from squads._services._results import (
    CheckIssue,
    SelfRemedied,
)
from squads._services._skill_files import (
    ScanContext,
)
from squads._services._validators import (
    SQUAD_GLOBAL_CATALOG,
    SquadGlobalContext,
    ValidatorEngine,
    backend_entry_candidates,
    backend_entry_drift,
    backend_entry_missing,
    backend_entry_path,
    live_roster_slugs,
    not_on_disk,
    on_disk_not_indexed,
    squad_global_level,
)
from squads._view_remedies import clear_roster_body_cmd, view_placement_invocation
from squads._workflow import ROSTER_ROLE, ROSTER_SKILL
from squads._workflow._models import WorkflowSpec


def _missing_timestamp_issues(name: str, data: dict[str, Any]) -> list[CheckIssue]:
    """Report a frontmatter with no ``created_at``/``updated_at``, which load as an invented
    ``clock.now()`` that differs on every read (see
    :data:`~squads._models._item.INVENTED_WHEN_ABSENT`). It warns because any mutation heals the
    file. The message names the index as the heal's source without promising "the real value", which
    the index holds only while it still has it.
    """
    missing = sorted(k for k in INVENTED_WHEN_ABSENT if data.get(k) is None)
    if not missing:
        return []
    return [
        CheckIssue(
            "warn",
            name,
            f"frontmatter has no {', '.join(missing)} — a placeholder is invented on each read "
            "until any mutation writes the value the index holds back into the file",
            "timestamps_present",
        )
    ]


def _marker_issues(text: str) -> list[str]:
    """Detect unbalanced or duplicated sq markers in a file. The unpaired view-tag family
    (:func:`~squads._models._markers.view_tag_parts`, no ``close_marker``) is exempt from the
    pairing count, and its duplicates are left to :func:`_seeded_view_issues`, which can name the
    ``view add``/``view disable`` remedy; every other tag family reports its own duplicates here.
    """
    opens: Counter[str] = Counter()
    closes: Counter[str] = Counter()
    for raw in sections.find_markers(text):  # e.g. "sq:body", "sq:body:end"
        tag = raw[len(markers.PREFIX) :]
        if tag.endswith(":end"):
            closes[tag[: -len(":end")]] += 1
        else:
            opens[tag] += 1
    problems: list[str] = []
    for tag, n in opens.items():
        # A same-state view-tag duplicate is left to `_seeded_view_issues`, the one place that
        # names the `view add`/`view disable` remedy; reporting it here would double-report it with
        # no remedy.
        if n > 1 and markers.view_tag_parts(tag) is None:
            problems.append(f"duplicate marker <!-- sq:{tag} -->")
        if markers.view_tag_parts(tag) is None and closes[tag] < n:
            problems.append(f"unclosed marker <!-- sq:{tag} -->")
    for tag, n in closes.items():
        if opens[tag] < n:
            problems.append(f"close without open <!-- sq:{tag}:end -->")
    for tag, n in opens.items():
        paired = n == 1 and closes[tag] == 1 and markers.view_tag_parts(tag) is None
        if paired and text.find(markers.close_marker(tag)) < text.find(markers.open_marker(tag)):
            problems.append(f"close before open <!-- sq:{tag}:end -->")
    return problems


def _view_target_issues(
    text: str, item_type: str, spec: WorkflowSpec, playbook: PlaybookSpec, *, from_squad: Path
) -> list[str]:
    """Every **enabled** ``sq:view:<name>`` tag in *text* that cannot resolve for *item_type* —
    undeclared, template missing, or a source that cannot apply to this type — as report
    strings, once per name even if its tag repeats (a duplicate is :func:`_marker_issues`'s own
    signal). Reports only, through :func:`~squads._views.resolve_view_target`; never
    rewrites."""
    problems: list[str] = []
    seen: set[str] = set()
    for raw in sections.find_markers(text):
        parts = markers.view_tag_parts(raw)
        if parts is None or parts.disabled or parts.name in seen:
            continue
        seen.add(parts.name)
        reason = views.resolve_view_target(
            parts.name, item_type, spec, playbook, from_squad=from_squad
        )
        if reason is not None:
            problems.append(f"{reason} (<!-- {raw} -->)")
    return problems


def _stem_slug(md: Path, item_type: str, spec: WorkflowSpec) -> str:
    """The filename's slug segment (``PREFIX-NNNNNN-<slug>.md`` -> ``<slug>``), resolved from
    *item_type*'s declared prefix. The fallback :func:`_check_slug` uses only when frontmatter
    cannot be read at all."""
    return slug_from_stem(md.stem, spec.items[item_type].prefix)


def _check_slug(md: Path, item_type: str, text: str, spec: WorkflowSpec) -> str:
    """The slug this check pass classifies *md* by, read from frontmatter whenever *text* parses
    and falling back to the filename segment (:func:`_stem_slug`) only when frontmatter can't be
    reached — matching the write path's own classification even for a hand-renamed skill file."""
    try:
        data = read_frontmatter(text=text, source=str(md))
    except SquadsError:
        return _stem_slug(md, item_type, spec)
    raw_slug = data.get("slug")
    return raw_slug if isinstance(raw_slug, str) and raw_slug else _stem_slug(md, item_type, spec)


def _disable_clause(item_type: str, addr: int | str, name: str, *, is_roster: bool) -> str:
    """The ``, or disable it with …`` tail of a missing-tag remedy; a roster host's generated
    view cannot be disabled, so it has none."""
    if is_roster:
        return ""
    disable = view_placement_invocation(item_type, addr, "disable", name)
    return f", or disable it with `{disable}`"


#: The opening of any sq tag, spaced the way the marker regex accepts.
_TAG_FRAGMENT_RE = re.compile(rf"<!--\s*{re.escape(markers.PREFIX)}")


def _seeded_view_issues(
    text: str, item_type: str, slug: str, n: int | None, spec: WorkflowSpec, *, from_squad: Path
) -> list[str]:
    """Every seeded view (:func:`~squads._views.seeded_view_names`) present exactly once and no view
    name duplicated, checked against *text* on disk, each violation with its runnable remedy. A role
    body with prose in place of its tag reports nothing; a skill with prose beside a missing tag is
    told to move the prose to a new skill first. An entirely absent region defers to
    :func:`_absent_body_region_issues`. It never repairs.
    """
    seeded = views.seeded_view_names(item_type, slug, spec, from_squad=from_squad)
    counts: Counter[str] = Counter()
    for raw in sections.find_markers(text):
        parts = markers.view_tag_parts(raw)
        if parts is not None:
            counts[parts.name] += 1
    is_roster = item_type in (ROSTER_ROLE, ROSTER_SKILL)
    addr: int | str = slug if is_roster else (n if n is not None else "<n>")
    region = sections.get_section(text, markers.BODY) if is_roster else None
    # A roster host with no `sq:body` marker pair is reported by `_absent_body_region_issues`: `view
    # add`/`view disable` need an existing region, so the remedies named here would fail and the two
    # findings would disagree.
    region_absent = (
        region is None
        if is_roster
        else markers.open_marker(markers.BODY) not in text
        and markers.close_marker(markers.BODY) not in text
    )
    prose_beside_missing_tag = is_roster and bool(view_tags.strip_view_tags(region or "").strip())
    # A role's prose is a supported state unless it holds a tag fragment: a truncated or
    # mistyped tag is damage, not prose, and stays reported.
    role_prose = prose_beside_missing_tag and not _TAG_FRAGMENT_RE.search(region or "")
    problems: list[str] = []
    for name in sorted(seeded - set(counts)):
        if region_absent or (role_prose and item_type == ROSTER_ROLE):
            continue
        tag = markers.open_marker(markers.view_tag(name))
        if prose_beside_missing_tag:
            clear_cmd = clear_roster_body_cmd(item_type, slug)
            add_cmd = view_placement_invocation(item_type, addr, "add", name)
            doc_type = item_type_for_skill_slug(slug, spec) if item_type == ROSTER_SKILL else None
            if doc_type is not None:
                # The same shape `_item_skill_shadowed` also reports: this prose may be an
                # author's own runbook (the reclaim never ran against it, e.g. an `sq adopt`
                # or a type declared later), so the remedy preserves it, never deletes outright.
                problems.append(
                    f"missing seeded view tag {tag} — the body already carries prose, and "
                    f"{slug!r} still documents the declared type {doc_type!r}, so this may be "
                    f"an author's own runbook rather than stale legacy text; the remedy that "
                    f"preserves it: (1) `sq skill add <new-slug>` and move the prose there; "
                    f"(2) drop {name!r} from [selected] in .overrides/workflow.toml; (3) clear "
                    f"{slug}'s own text with `{clear_cmd}`; (4) restore {name!r} to [selected]; "
                    f"(5) `{add_cmd}`"
                )
            else:
                problems.append(
                    f"missing seeded view tag {tag} — the body already carries "
                    f"prose; the remedy that converges to a single live rendering: (1) drop "
                    f"{name!r} from [selected] in .overrides/workflow.toml; (2) clear the text "
                    f"with `{clear_cmd}`; (3) restore {name!r} to [selected]; (4) `{add_cmd}`"
                )
        else:
            add_cmd = view_placement_invocation(item_type, addr, "add", name)
            # A roster host's generated view cannot be disabled; its remedy is to restore it.
            disable_clause = _disable_clause(item_type, addr, name, is_roster=is_roster)
            problems.append(
                f"missing seeded view tag {tag} — restore it with `{add_cmd}`{disable_clause}"
            )
    stray = {
        parts.name
        for tag in view_tags.out_of_region_view_tags(text)
        if (parts := markers.view_tag_parts(tag)) is not None
    }
    for name in sorted(n for n, c in counts.items() if c > 1):
        head = (
            f"duplicate {markers.PREFIX}{markers.view_tag(name)} tag "
            f"({counts[name]} copies, counting both states) — "
        )
        if name in stray:
            problems.append(
                head + "one copy sits outside sq:body, where `view add` and `view disable` "
                "refuse to act; remove or move that copy first, then collapse the rest with "
                f"`{view_placement_invocation(item_type, addr, 'add', name)}`"
            )
        else:
            collapse = f"`{view_placement_invocation(item_type, addr, 'add', name)}`"
            if not is_roster:
                collapse += f" or `{view_placement_invocation(item_type, addr, 'disable', name)}`"
            problems.append(head + "collapse to one with " + collapse)
    return problems


def _absent_body_region_issues(
    text: str, item_type: str, slug: str, spec: WorkflowSpec
) -> list[str]:
    """One error when a file's ``sq:body`` marker pair is entirely absent (one missing is
    :func:`_marker_issues`'s job). Any other type is told to restore the pair; a role or skill is
    told ``view add``/``view disable`` when :func:`~squads._view_tags.reinstate_absent_body_region`
    says the region can be reinstated safely, else manual recovery because real prose is in the way.
    """
    if markers.open_marker(markers.BODY) in text or markers.close_marker(markers.BODY) in text:
        return []
    generic = [
        f"missing {markers.PREFIX}{markers.BODY} region (no "
        f"`{markers.open_marker(markers.BODY)}`/`{markers.close_marker(markers.BODY)}` "
        "pair at all) — restore the marker pair in this file, for example from git"
    ]
    if item_type not in (ROSTER_ROLE, ROSTER_SKILL):
        return generic
    view_name = views.roster_body_view_name(item_type, slug, spec)
    if view_name is None:
        return generic
    if view_tags.reinstate_absent_body_region(text) is None:
        return [
            "missing sq:body region (no `<!-- sq:body -->`/`<!-- sq:body:end -->` pair at "
            "all) with something other than the seeded view tag in the way — no `view "
            "add`/`view disable` can restore this without guessing which lines are authored; "
            "recover the file by hand or from a backup"
        ]
    add_cmd = view_placement_invocation(item_type, slug, "add", view_name)
    return [
        "missing sq:body region (no `<!-- sq:body -->`/`<!-- sq:body:end -->` pair at all) — "
        f"restore it with `{add_cmd}`"
    ]


def _blocks_outside_container_issues(text: str, item_type: str, spec: WorkflowSpec) -> list[str]:
    """One warning per sub-entity block whose opening marker sits outside the item's container
    (or in a file with no container at all). A half-present container is left to
    :func:`_marker_issues`."""
    kind = spec.item_subentity_kind(item_type)
    if kind is None:
        return []
    plural = spec.subentity_plural(kind)
    opened, closed = markers.open_marker(plural), markers.close_marker(plural)
    start, end = text.find(opened), text.find(closed)
    if (start == -1) != (end == -1):
        return []
    prefix = f"{markers.PREFIX}{kind}:"
    return [
        f"{kind} block {tag.removeprefix(prefix)} sits outside its {plural!r} container "
        f"-- move it between `{opened}` and `{closed}`"
        for tag, at, _ in sections.iter_marker_spans(text)
        if tag.startswith(prefix) and tag.count(":") == 2 and not (start != -1 and start < at < end)
    ]


def _drift_direction(item: Item, fdata: dict[str, Any]) -> str | None:
    """Which side is ahead when the two ``updated_at`` values order the pair: ``"markdown"`` is the
    expected, repairable skew; ``"index"`` means the ordering rule or the crash model was violated.
    ``None`` when whole-second truncation or a missing/unparseable value leaves them unordered, and
    nothing is said about direction then.
    """
    raw = fdata.get("updated_at")
    if isinstance(raw, datetime):
        disk_dt = raw if raw.tzinfo else raw.replace(tzinfo=UTC)
    elif isinstance(raw, str):
        try:
            disk_dt = clock.parse_iso(raw)
        except ValueError:
            return None
    else:
        return None
    if disk_dt > item.updated_at:
        return "markdown"
    if item.updated_at > disk_dt:
        return "index"
    return None


def _drift_message(fields: list[SkewKey], item: Item, fdata: dict[str, Any]) -> str:
    """The ``sq check`` finding text for a confirmed skew, the same two-clause split as
    :func:`~squads._itemfile.skew_message`: a real divergence keeps the write seam's wording (with
    its direction suffix), a stale index encoding gets
    :func:`~squads._itemfile.stale_encoding_clause` instead, in the same words as the write
    seam's own refusal. A mixed item reports both clauses."""
    diverged = [k.name for k in fields if not k.stale_encoding]
    stale = [k.name for k in fields if k.stale_encoding]
    clauses: list[str] = []
    if diverged:
        direction = _drift_direction(item, fdata)
        if direction == "markdown":
            suffix = " — markdown is ahead"
        elif direction == "index":
            suffix = " — index is ahead of markdown, which should not happen"
        else:
            suffix = ""
        clauses.append(f"{', '.join(diverged)} drift between frontmatter and index{suffix}")
    if stale:
        clauses.append(stale_encoding_clause(stale))
    return (
        f"{'; '.join(clauses)}; "
        "run `sq repair` before this item is mutated again, or the fix is lost silently"
    )


def _value_skew_issue(
    item: Item, text: str, fdata: dict[str, Any], *, default_kind: str
) -> CheckIssue | None:
    """The frontmatter/index value-divergence candidate: every top-level field where *text*'s
    frontmatter diverges from *item*. It is confirmable from a freshly re-observed ``(item, text,
    fdata)``, so the scan and confirm passes share it, and it reuses
    :func:`~squads._itemfile.frontmatter_skew` so it flags what the write seam would refuse
    (:func:`~squads._itemfile.ensure_no_skew`), at ``warn``.
    """
    diverging = frontmatter_skew(text, item, default_kind=default_kind)
    if not diverging:
        return None
    return CheckIssue(
        "warn", item.id, _drift_message(diverging, item, fdata), "frontmatter_matches_index"
    )


def _stem_seq(md: Path, item_type: str, spec: WorkflowSpec) -> int | None:
    """The sequence number recovered from *md*'s **filename** stem alone — see
    :func:`stem_digit_run`, whose ``None`` case (the stem doesn't even parse) propagates."""
    digit_run = stem_digit_run(md, item_type, spec)
    return int(digit_run) if digit_run is not None else None


def _unparseable_seq_or_suppress(
    md: Path, item_type: str, spec: WorkflowSpec, unparseable_seqs: set[int]
) -> bool:
    """Record *md*'s filename-derived sequence number into *unparseable_seqs* (mutated in
    place), for :meth:`CheckMixin._scan_for_check` to subtract from its missing-direction
    reconciliation candidates. Returns ``True`` when even the filename stem doesn't parse, in
    which case there is no safe seq to subtract and the caller should set ``suppress_missing``
    instead — see :meth:`CheckMixin._scan_for_check`'s docstring."""
    stem_seq = _stem_seq(md, item_type, spec)
    if stem_seq is None:
        return True
    unparseable_seqs.add(stem_seq)
    return False


def _report_and_third_state(
    issues: list[CheckIssue],
    unparseable_seqs: set[int],
    md: Path,
    item_type: str,
    spec: WorkflowSpec,
    issue: CheckIssue,
) -> bool:
    """Report *issue* against *md* and third-state the file: the shared body of every "present but
    cannot be evaluated" branch in :meth:`CheckMixin._scan_for_check`. Both lists are mutated in
    place. Returns ``True`` when even the filename stem does not parse, so the caller must set
    ``suppress_missing``; callers fold it in with ``|=`` so one branch never clears another's
    decision.
    """
    issues.append(issue)
    return _unparseable_seq_or_suppress(md, item_type, spec, unparseable_seqs)


# (live role slugs, live skill slugs, role slug -> Item, skill slug -> Item, role slug -> resolved
# preload list): one index's roster-currency state from ``CheckMixin._roster_drift_state``, shared
# by the scan and confirm halves.
type _RosterDriftState = tuple[
    frozenset[str], frozenset[str], dict[str, Item], dict[str, Item], dict[str, list[str]]
]


class CheckMixin(ServiceCore):
    async def check(self) -> list[CheckIssue]:
        """Report the squad board as of one point in time, without a lock or a write. Cross-source
        claims (drift, reconciliation, a missing per-entry pointer) are candidates confirmed by one
        re-read (:meth:`_confirm_cross_source`), so a racing mutation cannot cause a false finding;
        a reported drift is durable and ``sq repair`` heals it. A clean result means no confirmed
        inconsistency was observed, not that the board is consistent now.
        """
        from squads._overrides._service import check_override_issues

        index = await self.store.load()
        ctx = ScanContext()
        ctx.skills.items = [it for it in index.items.values() if it.type == ROSTER_SKILL]
        ctx.skills.texts = await self._read_skill_texts(ctx.skills)
        issues, on_disk, bodies, unparseable_seqs, suppress_missing = await self._scan_for_check(
            ctx
        )
        # Two override checks — version-drift warn + missing-marker error. Role items keyed by
        # slug so a role override resolves against its own live identity, exactly like
        # `sq sync` and `sq role <slug> show` do — see `role_base_from_item`.
        role_items_by_slug = {it.slug: it for it in index.items.values() if it.type == ROSTER_ROLE}
        issues += [
            CheckIssue(level, item, msg, rule)
            for level, item, msg, rule in check_override_issues(
                self.paths.squad_dir, role_items_by_slug, catalog=self.catalog, files=self.files
            )
        ]
        issues += self._orphaned_skill_issues(index)
        carriers = await self._id_carriers(ctx.carriers)
        listing = self._all_item_files()
        dup_groups = await confirmed_groups(duplicate_groups(carriers), listing)
        issues += [
            CheckIssue("error", key, self._duplicate_id_message(files), "ids_unique")
            for key, files in dup_groups.items()
        ]
        shared = await confirmed_shared_numbers(shared_number_groups(carriers), listing)
        issues += [
            CheckIssue(
                "error", f"#{number}", self._shared_number_message(number, files), "numbers_unique"
            )
            for number, files in shared.items()
        ]
        # The scan keys files by number, so under a shared number it holds only one of the
        # files, and a per-item check would read it for the wrong item. The shared-number error
        # names every file; the number is still present on disk.
        for number in shared:
            on_disk.pop(number, None)
            bodies.pop(number, None)
            unparseable_seqs = unparseable_seqs | {number}

        # ``index_reconciled`` is excluded here — it is cross-source, so its two directions
        # are confirmed below instead of reported straight from the scan pair.
        squad_global = {k: v for k, v in SQUAD_GLOBAL_CATALOG.items() if k != "index_reconciled"}
        engine = ValidatorEngine(
            spec=self.spec,
            paths=self.paths,
            playbook=self.playbook,
            squad_global=squad_global,
            role_catalog=self.catalog,
            override_files=self.files,
            backends=self._backends,
        )
        issues += engine.report(index, on_disk, bodies=bodies)
        g_ctx = SquadGlobalContext(
            now=clock.now(),
            index=index,
            on_disk=on_disk,
            spec=self.spec,
            paths=self.paths,
            playbook=self.playbook,
            catalog=self.catalog,
            files=self.files,
            backends=self._backends,
        )
        issues += await self._confirm_cross_source(
            index,
            on_disk,
            bodies,
            unparseable_seqs=unparseable_seqs,
            suppress_missing=suppress_missing,
            backend_entry_candidates=backend_entry_candidates(g_ctx),
            backend_entry_drift_candidates=self._scan_backend_entry_drift(index, on_disk),
        )
        # A repair that refuses a duplicated id is no remedy for its absence from the index.
        issues = [
            i
            for i in issues
            if not (i.rule == "index_reconciled" and normalized_id(i.item) in dup_groups)
        ]
        return issues

    def _orphaned_skill_issues(self, index: SquadsDB) -> list[CheckIssue]:
        """A live ``SKILL`` item whose ``sq-<type>`` slug names a type the active spec no longer
        declares: its pointer and body were withdrawn (:meth:`RosterProjection.project_item`) but
        the item still reads as live. ``warn``, because nothing is broken and the fix is reversible:
        restore the type or retire the skill.
        """
        issues: list[CheckIssue] = []
        for item in index.items.values():
            if item.type != ROSTER_SKILL or item.status not in self.spec.live_statuses(
                ROSTER_SKILL
            ):
                continue
            stale_type = orphaned_skill_item_type(item.slug, self.spec)
            if stale_type is None:
                continue
            issues.append(
                CheckIssue(
                    "warn",
                    item.id,
                    f"skill {item.slug!r} is {item.status} but type "
                    f"{stale_type!r} is no longer declared — its generated files have "
                    "been withdrawn; restore the type to bring it back, or retire this "
                    "skill (update its status) to close it out",
                    "skill_type_declared",
                )
            )
        return issues

    async def _confirm_one_drift_candidate(
        self,
        seq: int,
        fresh_index: SquadsDB,
        on_disk: dict[int, tuple[str, Path, dict[str, Any]]],
        *,
        default_kind: str,
    ) -> list[CheckIssue]:
        """Re-observe one drift candidate at the fresh index's path (falling back to the scan's
        path, see the inline comment) and re-run the drift predicate; split out of
        :meth:`_confirm_cross_source` for readability. Empty when the candidate cannot be confirmed:
        removed from the index, gone from disk, or unparseable on this read (the parse failure is
        reported at scan time).
        """
        fresh_item = fresh_index.items.get(seq)
        if fresh_item is None:
            return []  # removed since the scan — no index side left to confirm against
        confirm_path = item_file(self.paths, fresh_item)
        try:
            text = await _aio.read_text(confirm_path)
        except FileNotFoundError:
            # The fresh index's path can itself be stale (an interrupted rename leaves the file at
            # its new path, the index at the old one), so fall back to the scan's path; skip only
            # when neither has the file.
            confirm_path = on_disk[seq][1]
            try:
                text = await _aio.read_text(confirm_path)
            except FileNotFoundError:
                return []  # gone from both paths — no frontmatter side left to confirm
        try:
            fdata = read_frontmatter(text=text, source=str(confirm_path))
        except SquadsError:
            return []  # unparseable on this read — not confirmed, see the docstring above
        issue = _value_skew_issue(fresh_item, text, fdata, default_kind=default_kind)
        return [issue] if issue is not None else []

    async def _confirm_cross_source(
        self,
        index: SquadsDB,
        on_disk: dict[int, tuple[str, Path, dict[str, Any]]],
        bodies: dict[int, str],
        *,
        unparseable_seqs: frozenset[int] = frozenset(),
        suppress_missing: bool = False,
        backend_entry_candidates: list[tuple[str, str]] | None = None,
        backend_entry_drift_candidates: list[tuple[str, str, str]] | None = None,
    ) -> list[CheckIssue]:
        """The one confirm round for cross-source claims: from the scan triple ``(index, on_disk,
        bodies)`` it takes the value-skew, reconciliation and backend-entry candidates and, only if
        any exist, reloads the index once with ``store.load(fresh=True)`` (bypassing the request-
        scoped snapshot), re-running each predicate on those alone.
        ``unparseable_seqs``/``suppress_missing`` keep an unparseable file from being *missing*.
        """
        # Resolved once for the whole confirm round — before any scan or confirm — rather
        # than per candidate: a spec declaring the wrong number of default ref kinds must
        # fail as one clean refusal naming the spec, not partway through the round.
        default_kind = self.spec.default_ref_kind()
        drift_seqs = {
            item.sequence_id
            for item in index.items.values()
            if (text := bodies.get(item.sequence_id)) is not None
            and frontmatter_skew(text, item, default_kind=default_kind)
        }
        orphan_seqs = set(on_disk) - set(index.items)
        missing_seqs: set[int] = set(index.items) - set(on_disk) - unparseable_seqs
        if suppress_missing:
            missing_seqs = set()
        entry_candidates = backend_entry_candidates or []
        entry_drift_candidates = backend_entry_drift_candidates or []
        anything_to_confirm = (
            drift_seqs or orphan_seqs or missing_seqs or entry_candidates or entry_drift_candidates
        )
        if not anything_to_confirm:
            return []

        # fresh=True: this round exists to re-read the index now; a request-scoped snapshot
        # (``squads._index._store.read_scope``) would reopen the false-positive window.
        fresh_index = await self.store.load(fresh=True)
        issues: list[CheckIssue] = []
        reconciled_level = squad_global_level(self.spec, "index_reconciled")

        for seq in sorted(drift_seqs):
            issues += await self._confirm_one_drift_candidate(
                seq, fresh_index, on_disk, default_kind=default_kind
            )

        for seq in sorted(orphan_seqs):
            fid, path, _data = on_disk[seq]
            if not await _aio.path_exists(path):
                continue  # the file itself is gone since the scan — nothing left to claim
            issue = on_disk_not_indexed(
                seq, fid, indexed=seq in fresh_index.items, level=reconciled_level
            )
            if issue is not None:
                issues.append(issue)

        for seq in sorted(missing_seqs):
            fresh_item = fresh_index.items.get(seq)
            if fresh_item is None:
                continue  # removed from the index since the scan — no claim to confirm
            exists = await _aio.path_exists(item_file(self.paths, fresh_item))
            issue = not_on_disk(fresh_item, on_disk=exists, level=reconciled_level)
            if issue is not None:
                issues.append(issue)

        issues += self._confirm_backend_entry_candidates(entry_candidates, fresh_index, on_disk)
        issues += self._confirm_backend_entry_drift_candidates(
            entry_drift_candidates, fresh_index, on_disk
        )

        return issues

    def _roster_drift_state(
        self, index: SquadsDB, on_disk: dict[int, tuple[str, Path, dict[str, Any]]]
    ) -> _RosterDriftState:
        """Everything a per-entry currency comparison needs from one loaded *index*: live role/skill
        slug sets, each slug's ``Item``, and every live role's freshly resolved preload list
        (:meth:`RosterProjection.resolve_role_skills`, since the system-membership fallback would
        misread a ``scopes``-preloaded role as drifted). Both :meth:`_scan_backend_entry_drift` and
        :meth:`_confirm_backend_entry_drift_candidates` build it, off their own index.
        """
        g_ctx = SquadGlobalContext(
            now=clock.now(),
            index=index,
            on_disk=on_disk,
            spec=self.spec,
            paths=self.paths,
            playbook=self.playbook,
            catalog=self.catalog,
            files=self.files,
            backends=self._backends,
        )
        live_role_slugs, live_skill_slugs = live_roster_slugs(g_ctx)
        role_items = {it.slug: it for it in index.items.values() if it.type == ROSTER_ROLE}
        skill_items = {it.slug: it for it in index.items.values() if it.type == ROSTER_SKILL}
        role_skills = {
            slug: self.roster_projection.resolve_role_skills(slug, role_items.get(slug), index)
            for slug in live_role_slugs
        }
        return live_role_slugs, live_skill_slugs, role_items, skill_items, role_skills

    def _scan_backend_entry_drift(
        self, index: SquadsDB, on_disk: dict[int, tuple[str, Path, dict[str, Any]]]
    ) -> list[tuple[str, str, str]]:
        """The scan-time half of currency detection: render-and-compare
        (:func:`~squads._services._validators.backend_entry_drift`) against the *index* ``check()``
        loaded, never a second ``store.load()``, for each live per-entry pointer. Only a mismatch
        becomes a ``(backend, kind, slug)`` candidate; a slug with no path or an absent file is
        skipped, absence being :func:`~squads._services._validators.backend_entry_candidates`'s.
        """
        live_role_slugs, live_skill_slugs, role_items, skill_items, role_skills = (
            self._roster_drift_state(index, on_disk)
        )
        candidates: list[tuple[str, str, str]] = []
        for backend in self._backends():
            for kind, slugs, items in (
                ("role", live_role_slugs, role_items),
                ("skill", live_skill_slugs, skill_items),
            ):
                for slug in sorted(slugs):
                    item = items.get(slug)
                    if item is None:
                        continue
                    rel_path = backend_entry_path(
                        backend, self.paths, self.spec, self.playbook, self.catalog, kind, slug
                    )
                    if rel_path is None:
                        continue
                    issue = backend_entry_drift(
                        backend,
                        kind,
                        item,
                        paths=self.paths,
                        spec=self.spec,
                        playbook=self.playbook,
                        role_skills=role_skills,
                        rel_path=rel_path,
                        catalog=self.catalog,
                    )
                    if issue is not None:
                        candidates.append((backend.name, kind, slug))
        return candidates

    def _confirm_backend_entry_drift_candidates(
        self,
        candidates: list[tuple[str, str, str]],
        fresh_index: SquadsDB,
        on_disk: dict[int, tuple[str, Path, dict[str, Any]]],
    ) -> list[CheckIssue]:
        """The currency half of :meth:`_confirm_cross_source`'s confirm round: re-resolves each
        candidate's live status, item and preload-skill list against *fresh_index*, never the scan-
        time state, then calls :func:`~squads._services._validators.backend_entry_drift` again. A
        candidate whose slug was retired or removed since the scan resolves silently. Empty
        *candidates* costs only the roster-state build.
        """
        if not candidates:
            return []
        fresh_role_slugs, fresh_skill_slugs, role_items, skill_items, role_skills = (
            self._roster_drift_state(fresh_index, on_disk)
        )
        issues: list[CheckIssue] = []
        for backend_name, kind, slug in candidates:
            live = fresh_role_slugs if kind == "role" else fresh_skill_slugs
            if slug not in live:
                continue  # retired since the scan — the same resolution presence's confirm uses
            item = (role_items if kind == "role" else skill_items).get(slug)
            if item is None:
                continue  # removed from the index entirely since the scan
            backend = next(b for b in self._backends() if b.name == backend_name)
            rel_path = backend_entry_path(
                backend, self.paths, self.spec, self.playbook, self.catalog, kind, slug
            )
            if rel_path is None or not (self.paths.root / rel_path).exists():
                continue  # gone since the scan — presence's finding, not this one's
            issue = backend_entry_drift(
                backend,
                kind,
                item,
                paths=self.paths,
                spec=self.spec,
                playbook=self.playbook,
                role_skills=role_skills,
                rel_path=rel_path,
                catalog=self.catalog,
            )
            if issue is not None:
                issues.append(issue)
        return issues

    def _confirm_backend_entry_candidates(
        self,
        candidates: list[tuple[str, str]],
        fresh_index: SquadsDB,
        on_disk: dict[int, tuple[str, Path, dict[str, Any]]],
    ) -> list[CheckIssue]:
        """The per-entry-pointer half of :meth:`_confirm_cross_source`'s confirm round: recomputes
        each backend's ``managed_entry_paths`` from *fresh_index*'s live roster and re-checks every
        candidate via :func:`~squads._services._validators.backend_entry_missing`.
        """
        if not candidates:
            return []
        fresh_g_ctx = SquadGlobalContext(
            now=clock.now(),
            index=fresh_index,
            on_disk=on_disk,
            spec=self.spec,
            paths=self.paths,
            playbook=self.playbook,
            catalog=self.catalog,
            files=self.files,
            backends=self._backends,
        )
        fresh_role_slugs, fresh_skill_slugs = live_roster_slugs(fresh_g_ctx)
        fresh_bctx = BackendContext(
            paths=self.paths,
            spec=self.spec,
            playbook=self.playbook,
            live_role_slugs=fresh_role_slugs,
            live_skill_slugs=fresh_skill_slugs,
            catalog=self.catalog,
        )
        fresh_paths_by_backend = {
            backend.name: frozenset(backend.managed_entry_paths(fresh_bctx))
            for backend in self._backends()
        }
        issues: list[CheckIssue] = []
        for backend_name, rel_path in candidates:
            issue = backend_entry_missing(
                backend_name,
                rel_path,
                root=self.paths.root,
                fresh_live_paths=fresh_paths_by_backend.get(backend_name, frozenset()),
            )
            if issue is not None:
                issues.append(issue)
        return issues

    async def _scan_for_check(
        self, ctx: ScanContext
    ) -> tuple[
        list[CheckIssue],
        dict[int, tuple[str, Path, dict[str, Any]]],
        dict[int, str],
        frozenset[int],
        bool,
    ]:
        """Scan every item file for marker issues, frontmatter and raw text, returning ``(issues,
        on_disk, bodies, unparseable_seqs, suppress_missing)`` keyed by sequence number. The file
        checks are errors outside the validator catalog, and a skill file with no ``id`` is legacy
        and skipped unless it is ``SKILL-*.md``.

        A file that cannot be read, parsed or built into an item is a third state: its
        :class:`SquadsError` is caught per file and reported, and it is keyed into
        ``unparseable_seqs`` (by ``id`` or filename stem) so it is never a phantom missing claim; an
        unparseable stem sets ``suppress_missing``.
        """
        issues: list[CheckIssue] = []
        on_disk: dict[int, tuple[str, Path, dict[str, Any]]] = {}
        bodies: dict[int, str] = {}
        unparseable_seqs: set[int] = set()
        suppress_missing = False
        # Resolved once for the whole scan, before the per-file loop and its own per-file
        # SquadsError handling below — for the same reason as `_rebuild_index_from_disk`.
        default_kind = self.spec.default_ref_kind()
        for item_type, md in self._iter_item_files():
            record = await read_corpus_file(
                item_type, md, self.spec, read=lambda path: self._scan_text(path, ctx.skills)
            )
            if isinstance(record, Vanished):
                continue
            if isinstance(record, Unreadable):
                suppress_missing |= _report_and_third_state(
                    issues,
                    unparseable_seqs,
                    md,
                    item_type,
                    self.spec,
                    CheckIssue("error", md.name, record.message, "file_readable"),
                )
                continue
            text = record.text
            issues += [
                CheckIssue("error", md.name, msg, "markers_balanced")
                for msg in _marker_issues(text)
            ]
            issues += [
                CheckIssue("error", md.name, msg, "view_target_resolves")
                for msg in _view_target_issues(
                    text, item_type, self.spec, self.playbook, from_squad=self.paths.squad_dir
                )
            ]
            issues += [
                CheckIssue(
                    "warn", md.name, view_tags.out_of_region_view_warning(tag), "view_tag_in_region"
                )
                for tag in view_tags.out_of_region_view_tags(text)
            ]
            check_slug = _check_slug(md, item_type, text, self.spec)
            issues += [
                CheckIssue("error", md.name, msg, "seeded_view_resolves")
                for msg in _seeded_view_issues(
                    text,
                    item_type,
                    check_slug,
                    _stem_seq(md, item_type, self.spec),
                    self.spec,
                    from_squad=self.paths.squad_dir,
                )
            ]
            issues += [
                CheckIssue("error", md.name, msg, "body_regions_present")
                for msg in _absent_body_region_issues(text, item_type, check_slug, self.spec)
            ]
            issues += [
                CheckIssue("warn", md.name, msg, "block_in_container")
                for msg in _blocks_outside_container_issues(text, item_type, self.spec)
            ]
            if isinstance(record, Unparseable):
                remedy = await self._skill_remedy(md, item_type, ctx.skills)
                suppress_missing |= _report_and_third_state(
                    issues,
                    unparseable_seqs,
                    md,
                    item_type,
                    self.spec,
                    CheckIssue(
                        "error",
                        md.name,
                        SelfRemedied(f"{record.message}; {remedy}") if remedy else record.message,
                        "frontmatter_parses",
                    ),
                )
                continue
            fid = ctx.carriers.record(md, record.data.get("id"))
            if isinstance(record, LegacySkillBody):
                continue  # pre-migration skill body -- never had an id, not an error
            if isinstance(record, MissingId):
                issues.append(
                    CheckIssue(
                        "error",
                        md.name,
                        await self._missing_id_message(md, item_type, ctx.skills),
                        "id_present",
                    )
                )
                continue
            data = record.data
            seq = seq_from_frontmatter_id(fid)
            if seq is None:
                suppress_missing |= _report_and_third_state(
                    issues,
                    unparseable_seqs,
                    md,
                    item_type,
                    self.spec,
                    CheckIssue("error", md.name, malformed_id_message(fid), "id_well_formed"),
                )
                continue
            squad_rel = self.paths.squad_relative(item_type, md.name, spec=self.spec)
            try:
                Item.from_frontmatter(data, path=squad_rel, default_kind=default_kind)
            except SquadsError as exc:
                issues.append(CheckIssue("error", md.name, str(exc), "fields_valid"))
                unparseable_seqs.add(seq)
                continue
            issues += _missing_timestamp_issues(md.name, data)
            on_disk[seq] = (fid, md, data)
            bodies[seq] = text
        return issues, on_disk, bodies, frozenset(unparseable_seqs), suppress_missing
