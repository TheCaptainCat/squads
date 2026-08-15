"""Whole-squad maintenance: sync managed files, repair/renumber the index, check, migrate."""

from collections import Counter
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from squads import __version__, _aio
from squads import _actor as actor
from squads import _clock as clock
from squads import _sections as sections
from squads._backends._base import BackendContext
from squads._errors import RoleNotFoundError, SquadsError
from squads._index._reflog import append_line, reflog_path
from squads._index._resolver import item_file
from squads._interactions import (
    bundled_skill_slugs,
    custom_item_skill_description,
    custom_skill_slugs,
    orphaned_playbook_guide_message,
    orphaned_playbook_guides,
    orphaned_skill_item_type,
    skill_description,
)
from squads._interactions._loader import playbook_override_guide_pairs
from squads._itemfile import (
    INVENTED_WHEN_ABSENT,
    read_frontmatter,
    rewrite_ids,
    update_frontmatter,
    write_text,
)
from squads._migrations._registry import MIGRATIONS, Migration
from squads._models import _markers as markers
from squads._models._config import CONFIG_FILENAME
from squads._models._extras import ExtraKey as X
from squads._models._index import SquadsDB
from squads._models._item import (
    DEFAULT_ID_PADDING,
    DISPLAY_ID_PADDING,
    Item,
    format_item_id,
    prefix_from_id,
)
from squads._models._schema import SCHEMA_VERSION, schema_tuple
from squads._models._vocab import prefix_for
from squads._paths import number_for_id
from squads._roles._resolver import resolve_role
from squads._sections import join_frontmatter
from squads._services._base import ServiceCore
from squads._services._results import CheckIssue, ReflogEntry, RenumberResult, RepairResult
from squads._services._validators import (
    SQUAD_GLOBAL_CATALOG,
    ValidatorEngine,
    not_on_disk,
    on_disk_not_indexed,
)
from squads._workflow import ROSTER_ROLE, ROSTER_SKILL, bundled_spec
from squads._workflow._models import WorkflowSpec

# (id, markdown path, type, slug, number) — one scanned item file, used by repair/renumber.
# ``type`` is a plain ``str`` — every type (built-in or custom) resolves from the spec.
type _FileRec = tuple[str, Path, str, str, int]

_ROOT_TMP_IGNORE_PATTERN = f"{CONFIG_FILENAME}.*.tmp"


async def ensure_root_tmp_ignored(root: Path) -> None:
    """Make sure an interrupted ``.squads.toml`` write's temp sibling can never end up
    committed by accident.

    The atomic-replace primitive puts the temp file in the target's own directory (a
    cross-directory rename isn't atomic) — for ``.squads.toml`` that's the *project root*,
    outside the squad dir's own ``.gitignore``. Appends the pattern to a root ``.gitignore``
    if one exists, without touching any of its other (adopter-owned) content; creates a
    minimal one if none exists yet. A no-op once the pattern (or a covering ``*.tmp``) is
    already present.

    Called from ``init``/``adopt`` (a squad's first appearance) and from :meth:`sync
    <MaintenanceMixin.sync>` — the idempotent "bring this squad up to date" path, so a squad
    initialised before this pattern existed still picks it up on its next sync rather than
    carrying the hole forever.
    """
    gitignore = root / ".gitignore"
    if not await _aio.path_exists(gitignore):
        await _aio.atomic_write_text(gitignore, f"{_ROOT_TMP_IGNORE_PATTERN}\n")
        return
    text = await _aio.read_text(gitignore)
    lines = text.splitlines()
    if _ROOT_TMP_IGNORE_PATTERN in lines or "*.tmp" in lines:
        return
    sep = "" if text.endswith("\n") else "\n"
    await _aio.atomic_write_text(gitignore, f"{text}{sep}{_ROOT_TMP_IGNORE_PATTERN}\n")


def _missing_timestamp_issues(name: str, data: dict[str, Any]) -> list[CheckIssue]:
    """Report a frontmatter that carries no ``created_at``/``updated_at``.

    Absent, those load as an invented ``clock.now()`` that differs on every read (see
    :data:`~squads._itemfile.INVENTED_WHEN_ABSENT`) — so the file's own reported dates are
    fiction until something writes them, and every date-ordered view of it is wrong meanwhile.
    A warning rather than an error: the file is perfectly usable and any mutation heals it, but
    it is the one part of a loaded item that is not a function of what the file says, so it is
    reported rather than left to be silently re-invented per read.

    The message names the index as the source the heal will use, and says so in those words.
    It must not promise "the real value": what a mutation writes back is whatever the index
    currently holds for the key, which is the item's true original only for as long as the
    index still has it (:meth:`MaintenanceMixin._rebuild_index_from_disk` now carries it
    across a rebuild for exactly that reason). Over-promising here would make the warning read
    as reassurance in the one case where the operator most needs to act.
    """
    missing = sorted(k for k in INVENTED_WHEN_ABSENT if data.get(k) is None)
    if not missing:
        return []
    return [
        CheckIssue(
            "warning",
            name,
            f"frontmatter has no {', '.join(missing)} — a placeholder is invented on each read "
            "until any mutation writes the value the index holds back into the file",
        )
    ]


def _carry_forward_indexed_timestamps(
    item: Item, data: dict[str, Any], known_corpus: SquadsDB | None
) -> None:
    """Keep the previously-indexed timestamp for any key *data* — the file just scanned —
    carries no value for.

    Rebuilding the index from markdown means re-reading every field from the file, and for
    :data:`~squads._itemfile.INVENTED_WHEN_ABSENT` an absent field does not read as "absent":
    the loader substitutes ``clock.now()``. Committing that would write a placeholder *over* an
    entry the index already held correctly — and since a later mutation heals the markdown from
    the index, the fabricated instant then becomes the durable value in the source of truth,
    with nothing reporting it at any step. The item's real creation time would be unrecoverable
    from either artifact.

    So this is the same "carry the previous entry forward" posture the rebuild already takes
    for a whole unreadable *file* (:meth:`MaintenanceMixin._carry_forward_unreadable`), applied
    to an unreadable *field*: keep what was already indexed, fabricate nothing, and let the
    next rebuild pick up the real value once the file is fixed. ``check``'s warning keeps
    reporting the gap in the file itself, which is where it actually is.

    Gated on *known_corpus* — the caller's previous index snapshot — being present, which is
    also what makes it safe. ``repair`` supplies one; ``renumber`` deliberately does not,
    because a renumber shifts sequence numbers on purpose, so a lookup into the pre-renumber
    index would match a *different* item's entry. Carrying nothing there is correct, not a
    gap left open for convenience.
    """
    if known_corpus is None:
        return
    previous = known_corpus.get(item.id)
    if previous is None:
        return
    for key in INVENTED_WHEN_ABSENT:
        if data.get(key) is None:
            setattr(item, key, getattr(previous, key))


def _marker_issues(text: str) -> list[str]:
    """Detect unbalanced or duplicated sq markers in a file."""
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
        if n > 1:
            problems.append(f"duplicate marker <!-- sq:{tag} -->")
        if closes[tag] < n:
            problems.append(f"unclosed marker <!-- sq:{tag} -->")
    for tag, n in closes.items():
        if opens[tag] < n:
            problems.append(f"close without open <!-- sq:{tag}:end -->")
    return problems


def _drift_direction(item: Item, fdata: dict[str, Any]) -> str | None:
    """Which side is ahead when the two ``updated_at`` values order the pair:
    ``"markdown"`` is the expected, repairable skew; ``"index"`` means the ordering rule was
    violated, or the failure was out of the stated crash model. ``None`` when the clock's
    whole-second truncation (or a missing/unparseable frontmatter value) leaves the pair
    unordered — say nothing about direction then, rather than reaching for a second input to
    force an answer.
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


def _drift_message(field: str, item: Item, fdata: dict[str, Any]) -> str:
    direction = _drift_direction(item, fdata)
    if direction == "markdown":
        suffix = " — markdown is ahead"
    elif direction == "index":
        suffix = " — index is ahead of markdown, which should not happen"
    else:
        suffix = ""
    return (
        f"{field} drift between frontmatter and index{suffix}; "
        "run `sq repair` before this item is mutated again, or the fix is lost silently"
    )


def _status_drift(item: Item, fdata: dict[str, Any]) -> CheckIssue | None:
    """One of the two drift candidates: confirmable for a single item id, so
    ``check``'s scan pass (to detect the candidate) and its one confirm pass (to decide
    whether it still holds) both call this same function against their own ``(item, fdata)``
    pair — never two copies of the comparison to drift apart. Level stays ``warn`` regardless
    of direction: forged clocks (``sq --at``) make direction an informative detail, not a
    gate signal.
    """
    if fdata.get("status") == item.status:
        return None
    return CheckIssue("warn", item.id, _drift_message("status", item, fdata))


def _parent_drift(item: Item, fdata: dict[str, Any]) -> CheckIssue | None:
    """The other drift candidate — see :func:`_status_drift`."""
    if (fdata.get("parent") or None) == item.parent:
        return None
    return CheckIssue("warn", item.id, _drift_message("parent", item, fdata))


def _drift_issues(item: Item, fdata: dict[str, Any]) -> list[CheckIssue]:
    """Both drift candidates for one ``(item, fdata)`` pair."""
    return [i for i in (_status_drift(item, fdata), _parent_drift(item, fdata)) if i is not None]


def _stem_digit_run(md: Path, item_type: str, spec: WorkflowSpec) -> str | None:
    """The zero-padded digit run recovered from *md*'s **filename** stem alone (e.g.
    ``"000011"``), ``None`` when even that does not parse.

    The fallback source for a file whose frontmatter cannot be read at all — the same
    prefix-stripped digit-run parse :meth:`MaintenanceMixin.repad` already relies on for the
    identical reason (a filename is a weaker source of truth than frontmatter, but it is the
    only one left once frontmatter is unreadable). A hyphenated prefix (e.g. ``"RUN-BOOK"``) is
    stripped whole rather than split on the stem's first hyphen. Kept as the raw digit-run
    *string* (not just the parsed int) so a caller that also needs the filename's padding
    width — :meth:`MaintenanceMixin._rebuild_index_from_disk`'s counter/padding floor — never
    has to re-parse the stem a second time to get it.
    """
    prefix = spec.items[item_type].prefix
    digits_slug = md.stem.removeprefix(f"{prefix}-")
    digit_run, _, _slug = digits_slug.partition("-")
    return digit_run if digit_run.isdigit() else None


def _stem_seq(md: Path, item_type: str, spec: WorkflowSpec) -> int | None:
    """The sequence number recovered from *md*'s **filename** stem alone — see
    :func:`_stem_digit_run`, whose ``None`` case (the stem doesn't even parse) propagates."""
    digit_run = _stem_digit_run(md, item_type, spec)
    return int(digit_run) if digit_run is not None else None


def _unparseable_seq_or_suppress(
    md: Path, item_type: str, spec: WorkflowSpec, unparseable_seqs: set[int]
) -> bool:
    """Record *md*'s filename-derived sequence number into *unparseable_seqs* (mutated in
    place), for :meth:`MaintenanceMixin._scan_for_check` to subtract from its missing-direction
    reconciliation candidates. Returns ``True`` when even the filename stem doesn't parse, in
    which case there is no safe seq to subtract and the caller should set ``suppress_missing``
    instead — see :meth:`MaintenanceMixin._scan_for_check`'s docstring."""
    stem_seq = _stem_seq(md, item_type, spec)
    if stem_seq is None:
        return True
    unparseable_seqs.add(stem_seq)
    return False


def _seq_from_frontmatter_id(fid: object) -> int | None:
    """The sequence number carried by a frontmatter ``id:`` value, or ``None`` when that value
    is not a well-formed id at all.

    Two shapes give ``None``: a non-string (``id: 5``, ``id: [a, b]`` — where ``number_for_id``
    raises ``AttributeError``) and a trailing segment that is not an integer (``id: TASK-abc``
    — where it raises ``InvalidIdError``). Both are corrupt *file data*, and every call site is
    inside a per-file scan loop that must never abort the whole scan for one bad file, so the
    parse is funnelled through here and the failure reported per file like any other defect.
    """
    if not isinstance(fid, str):
        return None
    try:
        return number_for_id(fid)
    except SquadsError:
        return None


def _report_and_third_state(
    issues: list[CheckIssue],
    unparseable_seqs: set[int],
    md: Path,
    item_type: str,
    spec: WorkflowSpec,
    message: str,
) -> bool:
    """Report *message* as an error against *md* and third-state the file — the shared body of
    every "this file is present but cannot be evaluated" branch in
    :meth:`MaintenanceMixin._scan_for_check`.

    Both lists are mutated in place. Returns ``True`` when even the filename stem does not parse,
    so there is no safe sequence number to subtract and the caller must set ``suppress_missing``;
    callers fold it in with ``|=`` so one branch can never clear another's decision.
    """
    issues.append(CheckIssue("error", md.name, message))
    return _unparseable_seq_or_suppress(md, item_type, spec, unparseable_seqs)


def _missing_dirent_message(md: Path, *, is_symlink: bool) -> str:
    """The one wording for a ``FileNotFoundError`` raised on a dirent the caller's own glob just
    saw — shared by every command that can hit one (``check``, ``repair``, ``repad``/``renumber``)
    so the same dirent cannot be given two different diagnoses depending on which command found
    it.

    The distinction is the whole point of the ``is_symlink`` test each caller performs: a broken
    symlink is a **present** dirent whose *target* is missing, so "No such file or directory" —
    what the raw ``OSError`` says, and what the ``repad``/``renumber`` preflight used to report —
    sends an operator looking for a file that is sitting right there. Only a dirent that genuinely
    vanished between the scan and the read is absent.

    Names the path exactly once and never interpolates the errno: the raw ``str(exc)`` repeats the
    path a second time inside its own text, which is how the two-paths-in-one-message shape got in.
    """
    if is_symlink:
        return f"{md} is a broken symlink (its target does not exist)"
    return f"{md} vanished between the directory scan and the read"


def _malformed_id_message(fid: object) -> str:
    """The report for a frontmatter ``id:`` that :func:`_seq_from_frontmatter_id` could not read.

    Describes the **file**, and deliberately says nothing about what another command will then do
    with it. Two reasons, both load-bearing.

    *No repair outcome is claimed.* ``repair``'s behaviour is not one behaviour across the shapes
    that reach here, all driven: ``id: TASK-abc`` rebuilds the entry cleanly (prefix from the id's
    own prefix segment, number from ``sequence_id``); a non-string ``id: 5`` is refused by the load
    boundary, so ``repair`` reports the file and leaves the previous index entry in place; and a
    hyphen-less ``id: TASK`` rebuilds an entry whose id degrades to the ``UNRESOLVED`` sentinel.
    No single sentence is true of all three — and this same message is reused verbatim by
    ``renumber``, which refuses outright, where any repair claim is doubly wrong. So each command
    reports its own outcome and this states only what is wrong with the line.

    *The remedy is the one that works.* The wording this replaced also offered "or delete it".
    Driven: a file with no ``id:`` at all is reported by ``check`` ("file has no `id` in
    frontmatter") and third-stated by ``repair``, so deleting the line swaps one error for
    another. Correcting the line is the only action that clears it, and the message says so
    rather than letting an operator discover it the slow way.
    """
    return (
        f"frontmatter `id` {fid!r} is malformed -- an `id:` must read `<PREFIX>-<number>`, and "
        "the prefix half of the item's identity is read from this line, with nothing else in the "
        "file supplying it. Correct the `id:` line to match this file's `sequence_id` and its "
        "type's prefix; removing the line is reported too, so it is not a fix."
    )


def _is_legacy_skill_body(md: Path, item_type: str, spec: WorkflowSpec) -> bool:
    """True for a pre-stamping, slug-named skill body file (e.g. ``squads.md``) that has
    legitimately never carried a frontmatter ``id`` — the one shape where a missing ``id`` is
    not an error, since these files pre-date the id-stamping migration entirely (see
    :meth:`MaintenanceMixin._iter_item_files`). An ID-prefixed skill file (``SKILL-*.md``)
    missing its ``id`` is a real error, same as any other type — only the legacy, unstamped
    shape is exempt. Shared by both :meth:`MaintenanceMixin._scan_for_check` and
    :meth:`MaintenanceMixin._rebuild_index_from_disk`'s "no id" branch so the exemption can
    never drift between the two.

    **This is wider than "pre-migration", and deliberately stays that way.** It matches any
    skill file whose name lacks the type prefix, whenever it was written — including an
    unstamped body produced *today* by a seeding gap, which is a real defect (a generated,
    pointer-referenced file no ``SKILL`` item indexes) wearing the same shape. Narrowing it
    was tried and is not available: the two states are indistinguishable on disk *and* in the
    index, because ``init``'s internal ``_skip_skill_seed`` hook manufactures exactly the
    defect shape on purpose — bodies written, ids deliberately not stamped, to hold the global
    counter still. Every discriminator that reports the defect also reports that hook's output.

    So the report for an unindexed skill body lives where the file is *produced* rather than
    where it is later found: :meth:`MaintenanceMixin.sync` seeds every managed skill slug and
    then reports, by name, any slug-named body still left unindexed
    (:meth:`MaintenanceMixin._unindexed_skill_bodies`). That covers the variant this exemption
    cannot — a body whose slug no seeding vocabulary claims — at the one surface that knows it
    just wrote the file, and leaves check free to keep tolerating a corpus that has genuinely
    never been stamped.
    """
    if item_type != ROSTER_SKILL:
        return False
    skill_prefix = prefix_for(ROSTER_SKILL, spec) + "-"
    return not md.name.startswith(skill_prefix)


def _fold_stem_into_floor(
    max_n: int, max_filename_width: int, stem_seq: int | None, digit_run: str | None
) -> tuple[int, int]:
    """Fold one unreadable file's filename-derived sequence number/digit-run width into the
    rebuild's running counter/padding floor — the same ``max()`` a successfully-parsed file's
    own ``item.id``/filename would contribute, so an unreadable file (with or without a
    previous index entry to carry forward) can never let its own number regress the counter
    or its own width regress the padding floor."""
    if stem_seq is not None:
        max_n = max(max_n, stem_seq)
    if digit_run:
        max_filename_width = max(max_filename_width, len(digit_run))
    return max_n, max_filename_width


class MaintenanceMixin(ServiceCore):
    # ------------------------------------------------------------------ sync
    async def sync(self) -> list[str]:
        """Regenerate all tool-owned managed files to the current version; stamp the config.

        Returns one skip-report message per drifted roster item whose frontmatter was left
        untouched (see :meth:`_refresh_catalog_extra`/:meth:`_refresh_role_skills_extra`),
        one notice per live ``SKILL`` item this run just withdrew because its type is no
        longer declared (:func:`~squads._interactions.orphaned_skill_item_type`), and one per
        playbook guide **the adopter wrote** that this run just dropped from a generated
        ``sq-<type>`` skill because its role slug names no live role
        (:func:`~squads._interactions.orphaned_playbook_guides` — the guide-level sibling of that
        same withdrawal, reported here for the same reason: this run is what silently removed it;
        a guide that exists only in the bundled playbook is squads' own degradation and stays
        silent, since no adopter can edit it), and one per WARN-only notice a per-entry backend
        write surfaced (``Artifact.warning`` via :meth:`_project_roster_item` — today that is a
        declared ``model`` the host's own agent frontmatter cannot express, which the generated
        pointer drops), and one per skill body left on disk that no ``SKILL`` item indexes once
        this run's own seeding is done (:meth:`_unindexed_skill_bodies`) — empty for a clean
        roster, exactly today's
        silent behaviour. Never raises for any of them: this is bulk
        regeneration of derived state, and is itself what an operator reaches for when
        generated files are wrong, so a drifted or withdrawn item is reported and the rest of
        the squad still syncs (exit stays 0 — ``sq check`` is the dedicated reporter that
        gates).
        """
        # Idempotent: a squad initialised before this pattern existed picks it up here
        # instead of carrying the hole for the rest of its life.
        await ensure_root_tmp_ignored(self.paths.root)

        # Ensure that every type folder declared in the active spec exists on disk.
        # Built-in type folders are created by init/adopt; custom type folders may not
        # yet exist if the type was added to the spec after the squad was initialised.
        for ts in self.spec.items.values():
            folder = self.paths.squad_dir / ts.folder
            await _aio.mkdir(folder, parents=True, exist_ok=True)

        backends = self._backends()
        ctx = self._ctx
        for backend in backends:
            await backend.ensure_scaffold(ctx)
        # Recompute every role's resolved preload-skill set (system membership + scope
        # edges) once, up front — shared by the projection ctx below and the extra.skills
        # cache write, so a full sync is the single recomputation point for both surfaces.
        role_skills = await self._role_skills_map()
        proj_ctx = BackendContext(
            paths=self.paths, spec=self.spec, playbook=self.playbook, role_skills=role_skills
        )
        skipped: list[str] = []
        # sq sync is the convergence point for the live/withdrawn projection:
        # every roster item's status is re-applied against the predicate on every run,
        # materialising a live entry and withdrawing every other one — including an entry
        # already retired before this landed, with no migration owed. The item's own
        # sq-managed state (the catalog-extra merge, the resolved-skills cache, the rendered
        # body) refreshes unconditionally regardless of liveness: only the *backend*
        # projection — via ``_project_roster_item``, the same helper the single-item
        # transition path uses — is gated.
        for it in await self.list_items(item_type=ROSTER_ROLE):
            msgs = (
                await self._refresh_catalog_extra(it),
                await self._refresh_role_skills_extra(it, role_skills),
            )
            skipped.extend(msg for msg in msgs if msg is not None)
            skipped += await self._project_roster_item(it, proj_ctx)
            await self._regen_role_body(it)
        for it in await self.list_items(item_type=ROSTER_SKILL):
            stale_type = orphaned_skill_item_type(it.extra.get(X.SLUG, ""), self.spec)
            if stale_type is not None and it.status in self.spec.live_statuses(ROSTER_SKILL):
                skipped.append(
                    f"{it.id} ({it.extra.get(X.SLUG)}): type {stale_type!r} no longer "
                    "declared — generated files withdrawn; restore the type to "
                    "re-materialise, or retire this skill to close it out"
                )
            skipped += await self._project_roster_item(it, proj_ctx)
        skill_map = await self._skill_paths()
        ctx_with_skills = BackendContext(
            paths=self.paths,
            skill_paths=skill_map,
            role_skills=role_skills,
            spec=self.spec,
            playbook=self.playbook,
        )
        roster = await self.roster()
        ops = await self.operators()
        for backend in backends:
            await backend.write_managed(ctx_with_skills, roster, ops)
        # Reported after write_managed, not before: this is a statement about what the files
        # just written do NOT contain. `roster` is the live set write_managed itself gated on,
        # so the two can never disagree about which guides were dropped.
        known_slugs = {r.slug for r in await self.roster_all()}
        live_initial = self.spec.live_initial(ROSTER_ROLE)
        skipped += [
            orphaned_playbook_guide_message(
                item_type, slug, retired=slug in known_slugs, live_status=live_initial
            )
            for item_type, slug in orphaned_playbook_guides(
                self.playbook,
                self.spec,
                live_role_slugs={r.slug for r in roster},
                override_guides=playbook_override_guide_pairs(self.paths.squad_dir),
            )
        ]
        # Seed SKILL ids for every managed skill body ``write_managed`` just wrote, bundled
        # and custom alike, in the same order ``init``/``adopt`` use (idempotent; a slug whose
        # convention-named file already exists is skipped without touching it).
        #
        # Seeding only the custom half here — which is what this did — left a hole exactly the
        # width of "a bundled-playbook type whose body file first appears after init": the
        # backend writes ``agents/skills/sq-<type>.md`` with no frontmatter, nothing ever
        # stamps it, and neither a repeated sync nor `sq repair` heals it, because repair
        # rebuilds the index from frontmatter and this file has none. The type is real, its
        # `.claude` pointer is generated against the unindexed body, and live roles preload
        # the skill — but `sq skill sq-<type> show` exits 1 and `sq check` says nothing. That
        # is reachable today (a workflow override that dropped the type, then removed) and
        # would otherwise be reachable by construction on every future release that adds a
        # bundled type: each would need its own hand-written migration to stamp the new
        # skill. Seeding both halves on every sync is what makes that migration unnecessary.
        await self.seed_bundled_skills()
        await self.seed_custom_skills()
        # ... and report anything the two seeders could not claim. Seeding both halves closes
        # the gap for every slug a seeding vocabulary names; this closes the *class*, by asking
        # the only question that generalises to the next variant — is there a skill body on
        # disk that no `SKILL` item indexes — at the one moment the answer is unambiguous,
        # right after this run both wrote the bodies and seeded them.
        skipped += self._unindexed_skill_bodies()
        await self._stamp_version(__version__)
        return skipped

    def _unindexed_skill_bodies(self) -> list[str]:
        """One report line per slug-named skill body file left with no ``SKILL`` item after
        seeding — empty in the normal case.

        A skill body under the skills folder that does not carry the type's id prefix has no
        frontmatter, so nothing indexes it: ``sq skill <slug> show`` cannot find it, it is
        absent from ``sq list --type skill``, and ``sq repair`` cannot recover it either, since
        repair rebuilds the index *from* frontmatter. It is nonetheless a live file — the
        backends' generated pointers reference it and roles preload its slug.

        ``sq check`` deliberately tolerates this shape (see :func:`_is_legacy_skill_body`: it
        cannot tell it apart from a genuinely never-stamped corpus, nor from the state
        ``init``'s ``_skip_skill_seed`` hook manufactures). Sync can, because sync is what
        wrote the file: by this point it has run both seeders over every slug either
        vocabulary names, so anything still bare is a body no seeding path claims — the shape
        a future generated-skill slug outside those vocabularies would take. Reported, never
        raised: the rest of the sync stands, exactly like every other line this method returns.
        """
        folder = self.paths.squad_dir / self.spec.items[ROSTER_SKILL].folder
        if not folder.is_dir():
            return []
        prefix = prefix_for(ROSTER_SKILL, self.spec) + "-"
        return [
            f"{md.name}: skill body written under the skills folder but no {ROSTER_SKILL} item "
            "indexes it — generated pointers reference it and roles may preload its slug, but "
            f"`sq {ROSTER_SKILL} {md.stem} show` cannot find it and `sq repair` cannot recover "
            "it (it has no frontmatter to rebuild from). It names no slug this squad seeds; "
            "remove the file, or declare the type whose skill it is"
            for md in sorted(folder.glob("*.md"))
            if not md.name.startswith(prefix)
        ]

    async def _refresh_catalog_extra(self, item: Item) -> str | None:
        """Merge current catalog fields into a predefined role's item extra.

        When a new field is added to :class:`RoleDef` (e.g. ``agreements``), existing items
        created before that field existed will lack it in their frontmatter.  Sync is the
        reconciliation point: for every predefined role we pull the authoritative definition
        from the catalog and merge its ``to_extra()`` output into the live item, then persist
        the updated frontmatter so subsequent reads see the new fields.

        Developer roles (``is_dev=True``) and custom items without a catalog entry are skipped —
        their extra is fully owned by the ``add_dev`` / ``create`` call-site.

        This is a roster-regen path, not a single mutation: an unrepaired skew is skipped and
        reported (the returned message) rather than refused, and the in-memory merge is rolled
        back on skip so *item* stays truthful to what is actually on disk. Returns ``None``
        when nothing changed or the write went through.

        **The merge is mirrored into the index, in the same transaction.** The values this
        merges are read from ``resolve_role``, which layers a project's
        ``.overrides/roles/<slug>.toml`` over the bundled catalog — so this is the write that
        carries an adopter's renamed role title (or model, or mission) onto the item. Every
        consumer of that title reads the *index*, not the frontmatter: :meth:`roster` builds
        its ``RoleView`` list from ``extra``-on-index, and that list is what both backends
        compile ``CLAUDE.md``/``AGENTS.md`` from. Writing the frontmatter alone left the
        override's title durable but invisible — the generated roster kept rendering the
        bundled value until an unrelated ``sq repair`` happened to rebuild the index, with
        ``sq check`` clean the whole time. Markdown first, index commit last (invariant 8), so
        an interrupted refresh leaves the sanctioned one-sided skew ``sq repair`` heals.

        The catalog keys this call writes stay exempt from the skew guard everywhere — see
        ``_itemfile.PERMITTED_EXTRA_SKEW``. That exemption no longer describes *this* writer's
        steady state (the mirror above is what removed the permanent lag) but is still what
        lets a squad synced by an older release, whose index already lags on those keys,
        converge on its next sync instead of being refused by the guard first.
        """
        slug = item.extra.get(X.SLUG, "")
        try:
            catalog_role = resolve_role(slug, self.paths.squad_dir)
        except RoleNotFoundError:
            return None  # dev role or unknown slug — not catalog-managed
        catalog_extra = catalog_role.to_extra()
        base = item.model_copy(deep=True)
        previous: dict[str, Any] = {}
        for key, value in catalog_extra.items():
            if item.extra.get(key) != value:
                previous[key] = item.extra.get(key)
                item.extra[key] = value
        if not previous:
            return None
        try:
            async with self.store.transaction() as db:
                await update_frontmatter(item_file(self.paths, item), item, base)
                db.add(item)
        except SquadsError as exc:
            for key, old_value in previous.items():
                if old_value is None:
                    item.extra.pop(key, None)
                else:
                    item.extra[key] = old_value
            return str(exc)
        return None

    async def _stamp_version(self, version: str) -> None:
        cfg = self.paths.config.model_copy(update={"squads_version": version})
        await _aio.atomic_write_text(self.paths.config_path, cfg.to_toml())

    async def _stamp_schema(self, version: str) -> None:
        cfg = self.paths.config.model_copy(update={"schema_version": version})
        await _aio.atomic_write_text(self.paths.config_path, cfg.to_toml())

    # ------------------------------------------------------------------ migrations
    async def run_pending_migrations(self) -> list[Migration]:
        """Apply each migration whose target schema exceeds the on-disk one, in order.

        Rebuilds the index from the migrated frontmatter and stamps the new schema version.
        Returns the applied :class:`Migration` records (empty when already current).
        """
        disk = self.paths.config.schema_version
        applied = [m for m in MIGRATIONS if schema_tuple(m.to_schema) > schema_tuple(disk)]
        for m in applied:
            await m.run(self.paths)
        if applied:
            await self.repair()
            await self._stamp_schema(SCHEMA_VERSION)
            # Reflog: log the migration batch after repair has completed.
            sid, psid = actor.current_session()
            await append_line(
                reflog_path(self.paths.squad_dir),
                ts=clock.iso(clock.now()),
                actor=actor.current_actor(),
                op="migrate",
                target="",
                delta={
                    "from_schema": disk,
                    "to_schema": SCHEMA_VERSION,
                    "applied": [m.to_schema for m in applied],
                },
                session_id=sid,
                parent_session_id=psid,
            )
        return applied

    # ------------------------------------------------------------------ skill seeding
    async def seed_bundled_skills(self) -> list[Item]:
        """Stamp SKILL-… ids onto the bundled managed skill body files (idempotent).

        Called by ``sq init`` after ``refresh_managed()`` has written the skill body files.
        Each bundled skill receives a full ``Item`` of the ``skill`` roster type with the
        roster-type profile (status ``Active``, no sub-entities), allocated through
        ``IndexStore.transaction()`` in lexical-by-slug order.

        Files are written with the convention-correct name
        ``agents/skills/SKILL-<NNNNNN>-<slug>.md``. The legacy slug-named file written by
        ``write_managed`` (``<slug>.md``) is renamed to the convention name at this step;
        the ``sq init`` flow always ends with convention-named files on disk.

        Idempotent: if a convention-named file ``SKILL-*-<slug>.md`` already exists for a
        slug, it is left completely untouched.

        Returns the list of ``Item``s that were stamped (not including already-stamped ones).
        """
        now = clock.now()
        seeded: list[Item] = []
        skill_prefix = prefix_for(ROSTER_SKILL, self.spec)
        skills_folder = self.paths.squad_dir / self.spec.items[ROSTER_SKILL].folder
        for slug in bundled_skill_slugs():
            desc = skill_description(slug)

            # Check if a convention-named file already exists — idempotent skip.
            existing_convention = list(skills_folder.glob(f"{skill_prefix}-*-{slug}.md"))
            if existing_convention:
                continue  # already at convention name — leave id/sequence_id untouched

            # Look for the legacy slug-named body file written by write_managed.
            legacy_path = skills_folder / f"{slug}.md"
            if not legacy_path.is_file():
                continue  # body file not written yet (shouldn't happen after refresh_managed)
            existing_text = await _aio.read_text(legacy_path)

            # Allocate a new SKILL id through the single global counter.
            sid, _psid = actor.current_session()
            async with self.store.transaction() as db:
                item_id = db.allocate_id(ROSTER_SKILL, prefix=skill_prefix)
                # Convention-correct filename from the allocated id.
                seq = number_for_id(item_id)
                # Padded filename stem — deliberately NOT the displayed item.id.
                new_name = f"{skill_prefix}-{seq:0{db.padding}d}-{slug}.md"
                squad_rel = self.paths.squad_relative(ROSTER_SKILL, new_name, spec=self.spec)
                item = Item(
                    sequence_id=db.counter,
                    type=ROSTER_SKILL,
                    prefix=skill_prefix,
                    title=slug,
                    slug=slug,
                    # Scaffolding creates LIVE, not merely at `initial`: a generated role
                    # entry preloads a skill by slug and never consults that skill item's
                    # status, so seeding at a non-live `initial` would leave a clean `sq
                    # init` with every role entry preloading skills that were never
                    # materialised — a config-invalid state manufactured by squads itself.
                    status=self.spec.live_initial(ROSTER_SKILL),
                    description=desc,
                    author=slug,
                    path=squad_rel,
                    created_at=now,
                    updated_at=now,
                    created_session=sid,
                    modified_session=sid,
                    extra={X.SLUG: slug},
                )
                # Stamp frontmatter and write to the convention-named file.
                stamped = join_frontmatter(item.to_frontmatter_dict(), existing_text)
                convention_path = skills_folder / new_name
                await write_text(convention_path, stamped)
                # Remove the legacy slug-named file inside the SAME transaction: the item's
                # own convention-named file is already written above, so this costs nothing
                # and keeps the skew one-sided (a crash here leaves the legacy file gone and
                # the index not-yet-committed — markdown ahead, exactly the sanctioned skew —
                # rather than a permanent orphan the idempotent-skip logic can never revisit).
                await _aio.path_unlink(legacy_path)
                db.add(item)
                self.store.log(
                    "create",
                    item_id,
                    {
                        "title": slug,
                        "type": ROSTER_SKILL,
                        "status": self.spec.live_initial(ROSTER_SKILL),
                    },
                )
            # Rewrite each backend's .claude pointer to reference the convention-named body.
            # write_managed ran before seeding and wrote the pointer to the old slug path;
            # generate_skill_entry rewrites it to item.path (= SKILL-NNNNNN-slug.md). Stays
            # outside the transaction: a backend pointer is a regenerable artifact.
            ctx = self._ctx
            for backend in self._backends():
                await backend.generate_skill_entry(ctx, item)
            seeded.append(item)
        return seeded

    # ------------------------------------------------------------------ custom skill seeding
    async def seed_custom_skills(self) -> list[Item]:
        """Stamp SKILL-… ids onto custom-type managed skill body files (idempotent).

        Mirrors :meth:`seed_bundled_skills` but operates on custom types declared in the
        active spec (beyond the built-in types).  SKILL ids are allocated in
        the same lexical-by-slug order as :func:`bundled_skill_slugs`, so there's no
        SKILL-id churn for existing bundled skills — custom slugs sort independently into the
        full sorted slug space.

        Called from :meth:`sync` (so a custom type declared or renamed after the squad
        already exists gets seeded on the next sync) AND from ``init``/``adopt`` (which both
        resolve the merged, possibly-overridden spec via ``_init_time_spec`` and so see custom
        types from the very start — a fresh squad with a custom type no longer sits with
        unindexed skill body files until someone happens to run `sq sync`).
        """
        now = clock.now()
        seeded: list[Item] = []
        skill_prefix = prefix_for(ROSTER_SKILL, self.spec)
        skills_folder = self.paths.squad_dir / self.spec.items[ROSTER_SKILL].folder
        for slug in custom_skill_slugs(self.spec):
            desc = custom_item_skill_description(slug.removeprefix("sq-"))

            # Check if a convention-named file already exists — idempotent skip.
            existing_convention = list(skills_folder.glob(f"{skill_prefix}-*-{slug}.md"))
            if existing_convention:
                continue  # already at convention name — leave id/sequence_id untouched

            # Look for the legacy slug-named body file written by write_managed.
            legacy_path = skills_folder / f"{slug}.md"
            if not legacy_path.is_file():
                continue  # body file not written yet (write_managed must run first)
            existing_text = await _aio.read_text(legacy_path)

            # Allocate a new SKILL id through the single global counter.
            sid, _psid = actor.current_session()
            async with self.store.transaction() as db:
                item_id = db.allocate_id(ROSTER_SKILL, prefix=skill_prefix)
                seq = number_for_id(item_id)
                # Padded filename stem — deliberately NOT the displayed item.id.
                new_name = f"{skill_prefix}-{seq:0{db.padding}d}-{slug}.md"
                squad_rel = self.paths.squad_relative(ROSTER_SKILL, new_name, spec=self.spec)
                item = Item(
                    sequence_id=db.counter,
                    type=ROSTER_SKILL,
                    prefix=skill_prefix,
                    title=slug,
                    slug=slug,
                    # Scaffolding creates LIVE, not merely at `initial`: a generated role
                    # entry preloads a skill by slug and never consults that skill item's
                    # status, so seeding at a non-live `initial` would leave a clean `sq
                    # init` with every role entry preloading skills that were never
                    # materialised — a config-invalid state manufactured by squads itself.
                    status=self.spec.live_initial(ROSTER_SKILL),
                    description=desc,
                    author=slug,
                    path=squad_rel,
                    created_at=now,
                    updated_at=now,
                    created_session=sid,
                    modified_session=sid,
                    extra={X.SLUG: slug},
                )
                stamped = join_frontmatter(item.to_frontmatter_dict(), existing_text)
                convention_path = skills_folder / new_name
                await write_text(convention_path, stamped)
                # See seed_bundled_skills for why the legacy unlink moves inside the
                # transaction, alongside the write it now always follows.
                await _aio.path_unlink(legacy_path)
                db.add(item)
                self.store.log(
                    "create",
                    item_id,
                    {
                        "title": slug,
                        "type": ROSTER_SKILL,
                        "status": self.spec.live_initial(ROSTER_SKILL),
                    },
                )
            # Rewrite each backend's .claude pointer to the convention-named body.
            ctx = self._ctx
            for backend in self._backends():
                await backend.generate_skill_entry(ctx, item)
            seeded.append(item)
        return seeded

    # ------------------------------------------------------------------ scan helpers
    def _iter_item_files(self) -> Iterator[tuple[str, Path]]:
        """Yield (item_type, markdown path) for every item file across the type folders.

        Every type declared in the active spec — built-in or custom — is scanned uniformly
        (one generic path, no static/dynamic split), ordered by each type's
        ``ItemSpec.order`` (the same deterministic-not-alphabetical axis the CLI/playbook
        registration already uses), tie-broken by type name. This reproduces the exact
        historical built-in scan order (epic, feature, task, bug, decision, review, guide,
        role, skill, operator) byte-for-byte, which matters for collision resolution when
        two items share a sequence number pre-renumber (`sq repair --renumber`).

        Skill files follow the ``SKILL-<NNNNNN>-<slug>.md`` convention so they are scanned
        with the same ``PREFIX-*.md`` glob as every other type.  Legacy slug-named files
        (pre-migration) are also yielded so callers can detect them; files without an ``id``
        in their frontmatter are silently skipped by the repair/check callers.
        """
        for item_type, ts in sorted(self.spec.items.items(), key=lambda kv: (kv[1].order, kv[0])):
            folder = self.paths.squad_dir / ts.folder
            if not folder.is_dir():
                continue
            prefix = ts.prefix
            if item_type == ROSTER_SKILL:
                # Convention files follow SKILL-*.md (post-migration / fresh init).
                # Also include legacy <slug>.md files so pre-migration squads can still be
                # repaired/checked (they will be silently skipped by callers that require an id).
                convention = sorted(folder.glob(f"{prefix}-*.md"))
                legacy = sorted(md for md in folder.glob("*.md") if not md.name.startswith(prefix))
                yield from ((item_type, md) for md in convention + legacy)
            else:
                yield from ((item_type, md) for md in sorted(folder.glob(f"{prefix}-*.md")))

    # ------------------------------------------------------------------ scan helpers (cont.)
    async def _corpus_alignment_refusals(
        self, known_corpus: SquadsDB | None, rebuilt: SquadsDB
    ) -> list[str]:
        """Human-readable refusal messages for a rebuild-from-disk that would otherwise glob
        only the *active* spec's declared ``folder``/``prefix`` and silently treat a
        re-foldered or re-prefixed type's pre-existing corpus as deleted. Empty when nothing
        is misaligned.

        Two sources, combined:

        - **Precise, when a previous index is available** (``known_corpus`` — repair's own
          last-loaded snapshot): any item present in ``known_corpus`` but missing from
          ``rebuilt`` (the fresh disk scan just produced), whose own last-recorded ``path`` is
          still an actual file on disk. This asks only the one question that matters — is the
          file this index entry pointed at still really there — never a comparison of the
          item's own ``prefix``/``id`` metadata (which a hand-built ``Item`` in a test, or any
          other legitimately-reconstructible-but-stale record, can carry without the file
          having moved at all). It is also right even after more than one rename generation:
          the previous index reflects wherever the corpus actually was last aligned, not just
          the bundled default.
        - **Disk fallback, for any type with no prior knowledge** (``known_corpus`` is
          ``None`` — a fresh ``sq adopt`` with no index yet — or a type the previous index had
          zero items for): the bundled location is the one other place a pre-existing corpus
          can legitimately be, so it is the one extra place worth a direct disk check before
          concluding a type truly has nothing left behind.

        A wholly custom type (no bundled counterpart, and never previously indexed) has no
        reference point either way and is silently skipped — there is nothing to compare
        against, the same way an always-empty type is.
        """
        errors: list[str] = []
        known_types: set[str] = set()
        if known_corpus is not None:
            known_types = {it.type for it in known_corpus.items.values()}
            missing_seqs = sorted(known_corpus.items.keys() - set(rebuilt.items))
            stranded_by_type: dict[str, list[str]] = {}
            for seq in missing_seqs:
                old_item = known_corpus.items[seq]
                if await _aio.path_exists(self.paths.squad_dir / old_item.path):
                    stranded_by_type.setdefault(old_item.type, []).append(old_item.id)
            for t, ids in sorted(stranded_by_type.items()):
                errors.append(
                    f"type {t!r} has {len(ids)} item(s) still on disk at their previously "
                    f"recorded location, invisible to the active workflow spec's current "
                    f"folder/prefix for {t!r}: {sorted(ids)} — revert the change in "
                    ".overrides/workflow.toml, or make it only while the type has no items "
                    "(no command realigns an existing corpus)"
                )

        bundled = bundled_spec()
        for item_type, ts in self.spec.items.items():
            if item_type in known_types:
                continue  # already covered precisely above, from the item's own recorded path
            bundled_ts = bundled.items.get(item_type)
            if bundled_ts is None:
                continue  # a project-declared type has no bundled fallback location
            if (bundled_ts.folder, bundled_ts.prefix) == (ts.folder, ts.prefix):
                continue  # nothing changed for this type — already covered by the normal scan
            legacy_folder = self.paths.squad_dir / bundled_ts.folder
            if not legacy_folder.is_dir():
                continue
            found = sorted(legacy_folder.glob(f"{bundled_ts.prefix}-*.md"))
            if not found:
                continue
            ids: list[str] = []
            for md in found:
                data = read_frontmatter(text=await _aio.read_text(md), source=str(md))
                ids.append(str(data.get("id") or md.name))
            errors.append(
                f"type {item_type!r} has {len(ids)} item(s) still on disk at the bundled "
                f"prefix/folder ({bundled_ts.prefix!r} / {bundled_ts.folder!r}), invisible to "
                f"the active workflow spec's re-prefixed/re-foldered location "
                f"({ts.prefix!r} / {ts.folder!r}): {ids} — revert the change in "
                ".overrides/workflow.toml, or make it only while the type has no items "
                "(no command realigns an existing corpus)"
            )
        return errors

    # ------------------------------------------------------------------ repair / renumber
    def _carry_forward_unreadable(
        self,
        db: SquadsDB,
        unreadable: list[str],
        known_corpus: SquadsDB | None,
        md: Path,
        item_type: str,
        message: str,
    ) -> tuple[int | None, str | None]:
        """One file's third-state handling, shared by every branch of
        :meth:`_rebuild_index_from_disk` that cannot produce an ``Item`` from *md* (unreadable
        bytes, unparseable YAML, valid YAML with no ``id``, or a type-invalid field): report
        *message* under *md*'s name, and carry *md*'s previous entry from ``known_corpus``
        forward into *db* unchanged when one exists — recovered by the sequence number parsed
        from the filename stem alone, since the frontmatter is exactly what this file cannot
        supply. Returns that stem's ``(seq, digit_run)`` so the caller can fold it into its own
        running counter/padding floor via :func:`_fold_stem_into_floor` — this method only
        touches ``db``/``unreadable``, never the floor, which is a whole-rebuild value no
        single file owns.
        """
        unreadable.append(f"{md.name}: {message}")
        digit_run = _stem_digit_run(md, item_type, self.spec)
        stem_seq = int(digit_run) if digit_run is not None else None
        carried = (
            known_corpus.items.get(stem_seq)
            if known_corpus is not None and stem_seq is not None
            else None
        )
        if carried is not None:
            db.add(carried)
        return stem_seq, digit_run

    async def _report_third_state(
        self,
        db: SquadsDB,
        unreadable: list[str],
        known_corpus: SquadsDB | None,
        md: Path,
        item_type: str,
        message: str,
        max_n: int,
        max_filename_width: int,
    ) -> tuple[int, int]:
        """The one call every branch of :meth:`_rebuild_index_from_disk` that cannot produce
        an ``Item`` from *md* reaches for: report + carry-forward
        (:meth:`_carry_forward_unreadable`), then fold the recovered filename stem into the
        running counter/padding floor (:func:`_fold_stem_into_floor`) in one step, so no call
        site has to thread the intermediate ``(stem_seq, digit_run)`` pair itself."""
        stem_seq, digit_run = self._carry_forward_unreadable(
            db, unreadable, known_corpus, md, item_type, message
        )
        return _fold_stem_into_floor(max_n, max_filename_width, stem_seq, digit_run)

    async def _handle_missing_dirent(
        self,
        db: SquadsDB,
        unreadable: list[str],
        known_corpus: SquadsDB | None,
        md: Path,
        item_type: str,
        max_n: int,
        max_filename_width: int,
    ) -> tuple[int, int]:
        """A ``FileNotFoundError`` on a dirent this rebuild's own glob just saw — the
        absent-vs-unreadable split: a broken symlink is a *present* dirent (the read failed on
        its target, not on whether it's there), so it gets :meth:`_report_third_state`'s
        treatment; a dirent that has genuinely vanished between the glob and the read is not
        this rebuild's file to report on, so the floor passes through unchanged and nothing is
        added to ``unreadable`` — a real deletion is `repair`'s missing-direction report to
        make, from ``known_corpus``, not this scan's.
        """
        if not await _aio.path_is_symlink(md):
            return max_n, max_filename_width
        return await self._report_third_state(
            db,
            unreadable,
            known_corpus,
            md,
            item_type,
            _missing_dirent_message(md, is_symlink=True),
            max_n,
            max_filename_width,
        )

    async def _handle_missing_id(
        self,
        db: SquadsDB,
        unreadable: list[str],
        known_corpus: SquadsDB | None,
        md: Path,
        item_type: str,
        max_n: int,
        max_filename_width: int,
    ) -> tuple[int, int]:
        """A file whose frontmatter parsed but carries no ``id`` — the third-state treatment
        (:meth:`_report_third_state`), except for a pre-migration skill body file, which
        legitimately has never had one (:func:`_is_legacy_skill_body`) and passes through with
        the floor unchanged."""
        if _is_legacy_skill_body(md, item_type, self.spec):
            return max_n, max_filename_width
        return await self._report_third_state(
            db,
            unreadable,
            known_corpus,
            md,
            item_type,
            "file has no `id` in frontmatter",
            max_n,
            max_filename_width,
        )

    async def _rebuild_index_from_disk(
        self,
        *,
        previous_counter: int,
        previous_padding: int,
        known_corpus: SquadsDB | None = None,
    ) -> tuple[SquadsDB, list[str]]:
        """Scan every item file fresh and commit a rebuilt index — the core of :meth:`repair`,
        factored out so :meth:`renumber` can reuse it *without* repair's previous-snapshot /
        missing-file / reflog bookkeeping, which is specific to the ``sq repair`` verb (a
        renumber shift makes old sequence numbers vanish on purpose; repair's missing-file
        detector has no way to tell that apart from a genuine deletion, so `renumber` must not
        route through it — see :meth:`renumber`).

        ``previous_counter``/``previous_padding`` are the floors the rebuilt counter/padding
        must never regress below: the caller's most recent index read. ``known_corpus`` is
        the caller's last-loaded index snapshot, when it has one (``repair`` does;
        ``renumber`` passes ``None``) — see :meth:`_corpus_alignment_refusals`.

        Refuses (``SquadsError``, nothing written) rather than committing the freshly-scanned
        result when :meth:`_corpus_alignment_refusals` finds a type's pre-existing corpus
        sitting somewhere the active spec's declared ``folder``/``prefix`` can no longer see: a
        commit that proceeded anyway would glob only the active location, find nothing, and
        report those items as deleted when their files are sitting right there — exactly the
        corpus-alignment refusal the ordinary load path already makes for this same
        situation, made here too since this path can otherwise walk straight past it. The
        check runs on the freshly-scanned result (not the spec in the abstract), so it fires
        only when something a previous index actually knew about truly stopped resolving —
        never on a merely-reconstructed metadata quirk that doesn't affect where the file is.

        Returns ``(db, unreadable)`` — ``unreadable`` names every file whose content could not
        be read or parsed, **or** that parsed but cannot become an item (no ``id``, or a
        type-invalid field — :meth:`Item.from_frontmatter` is the load boundary for the
        latter, raising :class:`SquadsError` for both). Each is reported, never silently
        dropped: caught here per file so one bad file never aborts the rebuild for the rest of
        the corpus. Its *previous* index entry — recovered from ``known_corpus`` via the
        sequence number parsed from the filename stem alone, since the frontmatter ``id`` is
        exactly what may be unreadable or absent — is carried forward into ``db`` unchanged
        rather than dropped: skipping it would make the item unresolvable and its file an
        orphan, the exact disappearance this release's durability work closed. A carried entry
        is exactly what was already indexed — nothing fabricated — so the next repair after the
        file is fixed picks up the real values. Nothing is carried when there is no previous
        entry to carry (never indexed, or no previous index at all): the item is left
        unindexed, and it is reported here as unreadable, full stop — ``check`` does not
        additionally claim it is on-disk-but-not-indexed, since that would mean guessing the
        file's id from its filename and reporting the guess as fact.
        Either way, the filename-derived sequence number/digit-run width is folded into the
        rebuild's counter/padding floor (:func:`_fold_stem_into_floor`) — an unreadable file's
        own number must never be free for reissue just because its frontmatter couldn't
        contribute to the ordinary ``max_n``/``max_filename_width`` scan below.

        A timestamp the markdown does not carry is *not* re-read as an invented ``now`` and
        committed over the entry the index already holds: it is carried forward from
        ``known_corpus`` (:func:`_carry_forward_indexed_timestamps`) — the same carry-the-
        previous-entry posture above, at field granularity rather than file granularity. The
        rebuild rebuilds from what the corpus says; it must not manufacture what the corpus
        omitted, least of all over a value it already had.

        A ``FileNotFoundError`` on a dirent this same call's own glob just saw is a fourth,
        narrower case: a *broken symlink* is a present-but-unreadable dirent (the read failed
        on its target, not on its own presence) and gets the third-state treatment above; a
        dirent that has genuinely vanished between the glob and the read is skipped outright,
        with nothing reported here — it is not this rebuild's file to report, and the
        missing-direction reconciliation this same call's caller (:meth:`repair`) already
        computes from ``known_corpus`` is the honest place for a real deletion to surface.
        """
        db = SquadsDB(squads_version=__version__, counter=0)
        max_n = 0
        max_filename_width = 0
        unreadable: list[str] = []
        for item_type, md in self._iter_item_files():
            try:
                text = await _aio.read_text(md)
                data = read_frontmatter(text=text, source=str(md))
            except FileNotFoundError:
                max_n, max_filename_width = await self._handle_missing_dirent(
                    db, unreadable, known_corpus, md, item_type, max_n, max_filename_width
                )
                continue
            except SquadsError as exc:
                max_n, max_filename_width = await self._report_third_state(
                    db, unreadable, known_corpus, md, item_type, str(exc), max_n, max_filename_width
                )
                continue
            if not data.get("id"):
                max_n, max_filename_width = await self._handle_missing_id(
                    db, unreadable, known_corpus, md, item_type, max_n, max_filename_width
                )
                continue
            squad_rel = self.paths.squad_relative(item_type, md.name, spec=self.spec)
            try:
                item = Item.from_frontmatter(data, path=squad_rel)
            except SquadsError as exc:
                max_n, max_filename_width = await self._report_third_state(
                    db, unreadable, known_corpus, md, item_type, str(exc), max_n, max_filename_width
                )
                continue
            _carry_forward_indexed_timestamps(item, data, known_corpus)
            # Load-boundary vocab validation: reject items with an unknown type, status, or
            # sub-entity status before they enter the rebuilt index.  Use self.spec — the
            # Service-owned spec (possibly an override) — so repair respects the active
            # workflow spec.
            if item.type not in self.spec.items:
                raise SquadsError(
                    f"item {item.id} has unknown type {item.type!r} in {md.name}; "
                    f"fix the frontmatter before running `sq repair`"
                )
            if item.status not in self.spec.statuses:
                raise SquadsError(
                    f"item {item.id} has unknown status {item.status!r} in {md.name}; "
                    f"fix the frontmatter before running `sq repair`"
                )
            # Sub-entity statuses share the same vocabulary.
            for sub in item.subentities:
                if sub.status not in self.spec.statuses:
                    raise SquadsError(
                        f"item {item.id} sub-entity {sub.local_id} has unknown status "
                        f"{sub.status!r} in {md.name}; fix the frontmatter before "
                        f"running `sq repair`"
                    )
            db.add(item)
            max_n = max(max_n, number_for_id(item.id))
            # Derive the filename digit-run width (PREFIX-<digits>-<slug>.md).
            # The filename, not the frontmatter id, is the in-corpus record of a repad.
            # Strip the *known* prefix (from the item just parsed, hyphens and all) rather
            # than splitting the stem on its first/second hyphen — a hyphenated prefix (e.g.
            # "RUN-BOOK") would otherwise be mis-split and the digit run missed entirely.
            stem = md.stem  # e.g. "RUN-BOOK-000042-fix-login"
            digits_slug = stem.removeprefix(f"{item.prefix}-")  # "000042-fix-login"
            digit_run, _, _slug = digits_slug.partition("-")  # "000042", "fix-login"
            if digit_run.isdigit():
                max_filename_width = max(max_filename_width, len(digit_run))

        # Never let the counter regress: keep whichever is higher — the previous high-water mark
        # or the maximum sequence number found on disk.
        db.counter = max(previous_counter, max_n)
        # Padding: max(stored_floor, corpus_max_filename_width).
        # The stored value is the floor; the filename scan is the recompute. previous_padding
        # defaults to DEFAULT_ID_PADDING (6) for pre-existing squads, so a single max() with
        # the corpus width always yields a correct, never-regressing result.
        db.padding = max(previous_padding, max_filename_width)

        refusals = await self._corpus_alignment_refusals(known_corpus, db)
        if refusals:
            bullet_list = "\n".join(f"  - {msg}" for msg in refusals)
            raise SquadsError(
                "refusing to rebuild the index: the active workflow spec has re-foldered or "
                "re-prefixed a type against a corpus that still has files where it used to "
                "be — rebuilding would report them as deleted rather than reconcile "
                f"them:\n{bullet_list}"
            )

        await self.store.overwrite(db)
        return db, unreadable

    async def repair(self, *, renumber: bool = False) -> RepairResult:
        # Snapshot the previous index (if any) before rebuilding, so we can:
        #  (a) preserve the high-water mark of the counter,
        #  (b) preserve the padding floor, and
        #  (c) report items that were indexed but whose files have gone missing.
        previous_counter = 0
        previous_padding = DEFAULT_ID_PADDING
        # Keyed by sequence_id (int) so the comparison is width-tolerant: _propagate_padding
        # widens item.id strings when loading from an already-repadded index, while
        # from_frontmatter below rebuilds at the default width.  Comparing by the integer
        # sequence number avoids the cross-width mismatch (mirrors _check_reconciliation).
        previous_seq_to_id: dict[int, str] = {}
        known_corpus: SquadsDB | None = None
        if self.store.exists():
            try:
                # validate_vocab=False: repair's whole point is recovering from vocab drift
                # (e.g. a type/status/badge-code dropped via an override) — the ordinary
                # fail-closed load() would raise SquadsError for precisely that case, which
                # is NOT a corrupt index (it parsed fine) and must not be treated as absent:
                # doing so would lose the counter high-water mark and let a freed sequence
                # number be reissued. A genuinely unreadable index (missing file, bad JSON,
                # schema violation) still raises here and falls into the except below.
                prev = await self.store.load(validate_vocab=False)
                previous_counter = prev.counter
                previous_padding = prev.padding
                previous_seq_to_id = {it.sequence_id: it.id for it in prev.items.values()}
                known_corpus = prev
            except SquadsError:  # genuinely corrupt/missing index — treat as empty
                pass

        if renumber:
            await self._renumber()

        db, unreadable = await self._rebuild_index_from_disk(
            previous_counter=previous_counter,
            previous_padding=previous_padding,
            known_corpus=known_corpus,
        )

        # An unreadable file whose previous entry was carried forward is still in db.items,
        # so it never lands here — "missing" stays reserved for a genuine deletion (the file
        # is gone), never confused with "present but unreadable" (the file is right there).
        missing_seqs = sorted(previous_seq_to_id.keys() - set(db.items))
        missing_ids = [previous_seq_to_id[s] for s in missing_seqs]

        # Reflog: append after overwrite (repair uses overwrite, not transaction).
        sid, psid = actor.current_session()
        await append_line(
            reflog_path(self.paths.squad_dir),
            ts=clock.iso(clock.now()),
            actor=actor.current_actor(),
            op="repair",
            target="",
            delta={"items": len(db.items), "missing": missing_ids, "unreadable": unreadable},
            session_id=sid,
            parent_session_id=psid,
        )

        return RepairResult(db=db, missing_ids=missing_ids, unreadable=unreadable)

    # ------------------------------------------------------------------ repad
    async def repad(self, new_padding: int) -> int:
        """Raise the squad's ID padding to ``new_padding`` and rename every item file.

        One-way, irreversible format bump:

        - Refuses if ``new_padding`` <= the current stored padding (padding never shrinks).
        - Renames every item file across all type folders to
          ``PREFIX-<seq zero-padded to new_padding>-<slug>.md``.
        - File *contents* are left byte-untouched — only filenames change.
        - Calls :meth:`repair` afterwards to rebuild the index with the new padding stored and
          all ``path`` fields updated.

        Returns the number of files renamed.
        """
        db = await self.store.load()
        current = db.padding
        if new_padding <= current:
            raise SquadsError(
                f"new padding {new_padding} must be greater than the current padding {current}; "
                "padding can only increase (one-way format bump)"
            )

        # Refuse before touching anything if any file's frontmatter cannot be read — unlike
        # `sq check`/`sq repair`, repad rewrites identity (the filename, then the frontmatter
        # id it encodes) across the *whole* corpus, and a file whose id cannot be read cannot
        # be correctly repadded. `_scan_records()` reads every file unguarded for exactly this
        # reason: any parse failure raises here, before the first rename below, leaving the
        # tree untouched. (`self.repair()` at the end of this method would otherwise degrade
        # past the same failure instead of refusing — that leniency is right for `repair` on
        # its own, but not for a bulk identity rewrite riding on top of it.)
        await self._scan_records()

        renamed = 0
        for item_type, md in self._iter_item_files():
            stem = md.stem  # e.g. "RUN-BOOK-XXXXXX-fix-login"
            # Prefix comes from the active spec for this item's type — not by splitting the
            # stem on a hyphen, which mis-parses a hyphenated prefix (e.g. "RUN-BOOK") and
            # corrupts the filename. Strip that known prefix, then the remainder is
            # <digits>[-<slug>].
            prefix = self.spec.items[item_type].prefix
            digits_slug = stem.removeprefix(f"{prefix}-")  # "000042-fix-login"
            digit_run, _, slug_part = digits_slug.partition("-")  # "000042", "fix-login"
            if not digit_run.isdigit():
                continue  # malformed filename — skip
            seq = int(digit_run)
            # Build the new filename via the canonical formatter — no hand-rolled :0Nd here.
            # Padded filename stem — deliberately NOT item.id, which is unpadded;
            # formatted from the sequence number at new_padding instead.
            base = format_item_id(prefix, seq, new_padding)
            new_name = f"{base}-{slug_part}.md" if slug_part else f"{base}.md"
            new_path = md.parent / new_name
            if new_path != md:
                await _aio.path_rename(md, new_path)
                renamed += 1

        # Write the new padding into the index before calling repair, so repair's stored-floor
        # logic picks it up and writes it back out.
        async with self.store.transaction() as _db:
            old_padding = _db.padding
            _db.padding = new_padding
            self.store.log(
                "migrate",
                "",
                {
                    "op": "repad",
                    "old_padding": old_padding,
                    "new_padding": new_padding,
                    "renamed": renamed,
                },
            )

        # Rebuild the index so path fields and all item IDs reflect the new width.
        await self.repair()
        return renamed

    async def _scan_records(self) -> list[_FileRec]:
        records: list[_FileRec] = []
        for item_type, md in self._iter_item_files():
            try:
                text = await _aio.read_text(md)
            except FileNotFoundError as exc:
                # Same "cannot correctly rewrite an identity it cannot read" refusal as any
                # other unreadable file below — just a dirent this scan's own glob saw but
                # whose read then failed (a broken symlink, most plausibly). Converted to a
                # clean SquadsError here rather than left to propagate raw: repad/renumber
                # refuse either way, but the caller should never see a bare traceback for it.
                #
                # Refusing for both shapes does not mean *diagnosing* both the same way: this
                # goes through the message every other command uses (see
                # `_missing_dirent_message`), so one dirent cannot be a "broken symlink" to
                # `check` and a "No such file or directory" to `repad`.
                raise SquadsError(
                    f"{_missing_dirent_message(md, is_symlink=await _aio.path_is_symlink(md))}"
                    " — refusing to rewrite ids while a file in the corpus cannot be read"
                ) from exc
            fid = read_frontmatter(text=text, source=str(md)).get("id")
            if not fid:
                continue
            seq = _seq_from_frontmatter_id(fid)
            if seq is None:
                # Same "cannot correctly rewrite an identity it cannot read" refusal as the
                # unreadable-file branch above, for a file whose `id:` itself is corrupt
                # (`id: 5`, `id: TASK-abc`). Repad/renumber rewrite identity across the whole
                # corpus, so refusing is right -- but as a clean SquadsError, never the raw
                # AttributeError/InvalidIdError the parse would otherwise throw.
                raise SquadsError(f"{md} cannot be renumbered: {_malformed_id_message(fid)}")
            stem = md.name.removesuffix(".md")
            # Strip the id's own (possibly hyphenated) prefix + digit run rather than
            # splitting the stem on its first two hyphens, which mis-parses a hyphenated
            # prefix (e.g. "RUN-BOOK") and mistakes part of the prefix for the slug.
            remainder = stem.removeprefix(f"{prefix_from_id(fid)}-")
            _digit_run, _, slug = remainder.partition("-")
            records.append((fid, md, item_type, slug, seq))
        return records

    @staticmethod
    def _renumber_plan(
        records: list[_FileRec],
        padding: int = DEFAULT_ID_PADDING,
    ) -> tuple[dict[str, str], list[tuple[Path, str, str, str]]]:
        """Assign fresh numbers to ID-number collisions. Returns (id remap, files to rename).

        ``padding`` is the squad's current (filename) padding (from ``db.padding``); the
        **rename** target is minted at this width so renumber on a width-7 squad does not
        produce width-6 filenames. The **remap** target — fed to ``rewrite_ids`` to rewrite
        frontmatter ``id:``/refs/prose everywhere — is minted unpadded instead
        (``DISPLAY_ID_PADDING``): those two must diverge exactly like the create/rename/retype
        seams, or the textual substitution would stamp a padded string into content that is
        supposed to read unpadded.
        """
        by_number: dict[int, list[_FileRec]] = {}
        for rec in records:
            by_number.setdefault(rec[4], []).append(rec)
        next_free = max(by_number, default=0) + 1
        remap: dict[str, str] = {}
        renames: list[tuple[Path, str, str, str]] = []
        for number in sorted(by_number):
            for fid, md, _item_type, slug, _ in sorted(by_number[number], key=lambda r: r[0])[1:]:
                # Extract prefix from the existing ID (works for both built-in and custom
                # types, hyphenated prefixes included — this is the shared rpartition-based
                # primitive, not a hand-rolled split).
                fid_prefix = prefix_from_id(fid)
                new_padded = format_item_id(fid_prefix, next_free, padding)
                new_display = format_item_id(fid_prefix, next_free, DISPLAY_ID_PADDING)
                next_free += 1
                remap[fid] = new_display
                renames.append((md, _item_type, slug, new_padded))
        return remap, renames

    async def _apply_remap(
        self,
        paths: Iterable[Path],
        remap: dict[str, str],
        renames: list[tuple[Path, str, str, str]],
    ) -> None:
        """Shared renumber apply-path: rewrite refs -> rename -> resync.

        Both ``repair --renumber`` (post-merge collision fixer, via :meth:`_renumber`) and
        ``sq renumber`` (pre-merge block-shift, via :meth:`renumber`) drive this identical
        sequence so the machinery does not fork:

        1. ``rewrite_ids`` over every file in ``paths`` — whole-word substitution of each old
           id in ``remap`` to its new **unpadded** display id (content, not filenames)
           across frontmatter ``id:``/refs, body prose, and inline mentions.
        2. Rename the files whose own id changed to the **padded** filename stem in
           ``renames`` (already minted by the caller's planner at the squad's filename
           padding — deliberately not the unpadded id written into content above).
        3. Resync the renamed file's stored ``sequence_id`` frontmatter field to match.

        Counter-neutral by design: this executor never touches ``SquadsDB.counter``. The
        accepted pre-merge block-shift design's shared-apply-path description lists "counter
        bump" alongside this sequence but then assigns the bump to ``sq renumber``
        specifically — the ratified reading (tech-lead) is that the executor stays
        counter-neutral and each caller reconciles the counter its own way (``repair``'s
        full-index rebuild vs. ``sq renumber``'s explicit bump-to-new-max). A no-op when
        ``remap`` is empty (nothing to shift/reassign).
        """
        if not remap:
            return
        await rewrite_ids(list(paths), remap)
        for old_path, _item_type, slug, new_id in renames:
            new_name = f"{new_id}-{slug}.md" if slug else f"{new_id}.md"
            # Use the parent directory of the existing file — avoids resolving the type
            # through folder_for and works for both built-in and custom types.
            new_path = old_path.parent / new_name
            await _aio.path_rename(old_path, new_path)
            text = await _aio.read_text(new_path)
            fm, _ = sections.split_frontmatter(text, source=str(new_path))
            if fm:
                fm["sequence_id"] = number_for_id(new_id)
                await write_text(
                    new_path, sections.replace_frontmatter(text, fm, source=str(new_path))
                )

    async def _renumber(self) -> dict[str, str]:
        """Resolve duplicate global ID numbers from a merge: reassign + rewrite references."""
        records = await self._scan_records()
        padding = (await self.store.load()).padding if self.store.exists() else DEFAULT_ID_PADDING
        remap, renames = self._renumber_plan(records, padding)
        if not remap:
            return {}
        await self._apply_remap((md for _, md, *_ in records), remap, renames)
        return remap

    # ------------------------------------------------------------------ renumber pre-merge
    @staticmethod
    def _offset_plan(
        records: list[_FileRec],
        *,
        from_seq: int,
        counter: int,
        onto: int | None,
        by: int | None,
        padding: int,
    ) -> tuple[dict[str, str], list[tuple[Path, str, str, str]], str | None]:
        """Plan a disjoint block-shift of every local item numbered ``>= from_seq``:
        operator-supplied integers in, a ``{old -> new}`` remap + padded renames out. sq stays
        git-agnostic here — no subprocess, no git, no merge-base; ``counter``/``onto``/
        ``by`` cross in as plain integers the caller already resolved.

        Exactly one of ``onto``/``by`` must be supplied:

        - ``onto=M`` (the other branch's counter): the minimal safe offset is auto-computed —
          ``delta = max(M, counter) + 1 - from_seq`` — landing the shifted block strictly above
          both this branch's own maximum (``counter``) and the other branch's counter. Always
          computable, always safe; this path never emits an unsafe offset or a warning.
        - ``by=n`` (explicit escape-hatch offset): validated as ``from_seq + n > counter``. An
          unsafe value **refuses** with :class:`SquadsError` — no records/paths are touched,
          the minimum safe offset is reported, and the message notes that without ``onto`` sq
          cannot certify the shift also clears the *other* branch's counter (the operator's
          guarantee to make on this path). Never silently auto-corrected. A *safe* ``by`` still
          returns a non-``None`` warning string for the same reason — the missing-``onto``
          certification gap applies whether or not the value happened to be safe.

        Because the new range sits strictly above the old local range, no new id string in the
        remap ever equals an old one, so the single-pass whole-word ``rewrite_ids`` substitution
        is order-independent — no high-to-low ordering machinery is needed here, unlike an
        in-place/overlapping shift would require.

        Returns ``(remap, renames, warning)``. ``remap``/``renames`` are the same shape
        :meth:`_renumber_plan` produces for the collision path — empty when no local item has
        ``sequence_id >= from_seq``. ``remap`` targets are unpadded display ids (content);
        ``renames`` targets are minted at filename ``padding`` (on-disk), preserving relative
        order and gaps among the shifted items. ``warning`` is non-``None`` exactly on the
        ``by`` path.
        """
        if (onto is None) == (by is None):
            raise SquadsError("sq renumber: exactly one of --onto or --by is required")
        no_onto_certification = (
            "sq cannot certify this offset clears the OTHER branch's counter without "
            "--onto — that guarantee is yours to make on this path."
        )
        warning: str | None = None
        if onto is not None:
            delta = max(onto, counter) + 1 - from_seq
        else:
            assert by is not None  # exclusivity enforced above
            delta = by
            if from_seq + delta <= counter:
                min_safe = counter + 1 - from_seq
                raise SquadsError(
                    f"--by {by} is unsafe: {from_seq} + {by} = {from_seq + delta} does not "
                    f"clear this branch's own counter ({counter}); minimum safe offset is "
                    f"{min_safe}. {no_onto_certification}"
                )
            warning = no_onto_certification
        selected = sorted((rec for rec in records if rec[4] >= from_seq), key=lambda r: r[4])
        remap: dict[str, str] = {}
        renames: list[tuple[Path, str, str, str]] = []
        for fid, md, item_type, slug, seq in selected:
            new_seq = seq + delta
            fid_prefix = prefix_from_id(fid)
            new_display = format_item_id(fid_prefix, new_seq, DISPLAY_ID_PADDING)
            new_padded = format_item_id(fid_prefix, new_seq, padding)
            remap[fid] = new_display
            renames.append((md, item_type, slug, new_padded))
        return remap, renames, warning

    async def renumber(
        self, *, from_seq: int, onto: int | None = None, by: int | None = None
    ) -> RenumberResult:
        """Pre-merge block-shift renumber: the new top-level ``sq renumber`` verb.

        Shifts every local item with ``sequence_id >= from_seq`` into a disjoint range,
        preserving referential intent — every reference is rewritten while it is still
        unambiguous (contrast the post-merge ``repair(renumber=True)`` fallback, whose remap
        is keyed by the collided id string and so cannot tell which reference meant which
        item). This is a distinct verb from ``repair --renumber``: an intentional,
        operator-parameterized identity transform with a required boundary, not an idempotent
        argument-free reconstruction.

        Validation happens strictly before any file is touched: :meth:`_offset_plan` raises
        :class:`SquadsError` for an unsafe ``--by`` (or a bad ``onto``/``by`` combination)
        before the executor or the index rebuild runs, so the tree is left completely
        untouched on the refuse path.

        The shift reuses the shared apply-path executor (:meth:`_apply_remap`) and then
        commits via :meth:`_rebuild_index_from_disk` — the same disk-rescan :meth:`repair`
        uses internally, so the counter bump to the true post-shift maximum falls out for
        free — but **not** ``repair`` itself: `repair`'s missing-file detector would
        otherwise see every shifted item's old sequence number vanish and misreport it as a
        deletion, when it in fact just moved.

        Exactly one reflog line is appended, strictly after the index commit above, carrying
        a compact summary of the shift (the boundary, whichever of ``onto``/``by`` the
        operator actually supplied, and the full remap) — never a replayable diff. Every
        prior reflog line is left completely untouched: this is a pure append, no in-place
        rewrite of any historical ``target``/``delta``. A forensic reader walking the log
        forward from an old, now-superseded id finds this one line and can follow it to the
        item's current id; the old lines stay a truthful record of what was true when they
        were written. Nothing is appended on the no-op path (nothing shifted).
        """
        if self.store.exists():
            idx = await self.store.load()
            counter, padding = idx.counter, idx.padding
        else:
            counter, padding = 0, DEFAULT_ID_PADDING
        records = await self._scan_records()
        remap, renames, warning = self._offset_plan(
            records, from_seq=from_seq, counter=counter, onto=onto, by=by, padding=padding
        )
        if remap:
            await self._apply_remap((md for _, md, *_ in records), remap, renames)
            # _scan_records() above already read every file's frontmatter unguarded, so an
            # unreadable file would have aborted this verb before any rename ever ran —
            # nothing unreadable survives to reach the rebuild below.
            db, _unreadable = await self._rebuild_index_from_disk(
                previous_counter=counter, previous_padding=padding
            )
            # Reflog: appended after the index commit above (never in-place rewriting a
            # historical line) — a single summary event, not a replayable diff.
            sid, psid = actor.current_session()
            await append_line(
                reflog_path(self.paths.squad_dir),
                ts=clock.iso(clock.now()),
                actor=actor.current_actor(),
                op="renumber",
                target="",
                delta={"from": from_seq, "onto": onto, "by": by, "remap": remap},
                session_id=sid,
                parent_session_id=psid,
            )
        elif self.store.exists():
            db = await self.store.load()
        else:
            db = SquadsDB(squads_version=__version__, counter=counter, padding=padding)
        return RenumberResult(remap=remap, db=db, warning=warning)

    # ------------------------------------------------------------------ reflog read
    async def read_reflog(
        self,
        *,
        item: str | None = None,
        actor_filter: str | None = None,
        op_filter: str | None = None,
        since: str | None = None,
        tail: int | None = None,
    ) -> list[ReflogEntry]:
        """Read and filter the reflog.

        - A missing or empty reflog returns an empty list (back-compat).
        - A trailing partial line is skipped silently; interior malformed lines are warn-skipped.
        - No lock is acquired — reads are lock-free, like ``store.load()``.

        Filters are applied in order (AND semantics):
        - ``item``: match ``target`` exactly.
        - ``actor_filter``: match ``actor`` exactly.
        - ``op_filter``: match ``op`` exactly.
        - ``since``: only entries whose ``ts >= since`` (lexicographic ISO-8601 comparison).
        - ``tail``: keep only the last N entries (applied after filtering).
        """
        from squads._index._reflog import read_lines

        raw = await read_lines(reflog_path(self.paths.squad_dir))

        out: list[ReflogEntry] = []
        for line in raw:
            if item and line.target != item:
                continue
            if actor_filter and line.actor != actor_filter:
                continue
            if op_filter and line.op != op_filter:
                continue
            if since and line.ts < since:
                continue
            out.append(
                ReflogEntry(
                    v=line.v,
                    ts=line.ts,
                    actor=line.actor,
                    op=line.op,
                    target=line.target,
                    delta=line.delta,
                    session_id=line.session_id,
                    parent_session_id=line.parent_session_id,
                )
            )

        if tail is not None:
            out = out[-tail:]
        return out

    # ------------------------------------------------------------------ check
    async def check(self) -> list[CheckIssue]:
        """Report the squad board as of one point in time.

        ``check`` takes no lock: it never blocks a mutation, is never blocked by one, and
        never writes. Its per-item/squad-global catalog issues and single-source scan issues
        (marker damage, a missing frontmatter ``id``, the two override checks) are each as
        true as the one read that produced them, and are reported as-is. Its **cross-source**
        issues — status/parent drift and both directions of index/disk reconciliation, each a
        claim comparing the on-disk scan against the index snapshot loaded above — are
        candidates, not findings: they are confirmed by exactly one cheap re-read
        (:meth:`_confirm_cross_source`) before being reported, so a mutation racing the scan
        can no longer produce a false drift warning or a false reconciliation error (and can
        no longer make ``sq check`` exit 3 for a board that was never actually wrong).

        A reported drift or reconciliation issue therefore means a **real, durable**
        inconsistency that ``sq repair`` heals. What this may **not** claim is quiescence —
        an empty/warn-only result means "no confirmed inconsistency was observed", not "the
        board is consistent now"; another transaction may commit the instant after this
        returns.
        """
        from squads._overrides._service import check_override_issues

        index = await self.store.load()
        issues, on_disk, bodies, unparseable_seqs, suppress_missing = await self._scan_for_check()
        # Two override checks — version-drift warn + missing-marker error.
        issues += [
            CheckIssue(level, item, msg)
            for level, item, msg in check_override_issues(self.paths.squad_dir)
        ]
        issues += self._orphaned_skill_issues(index)
        # ``index_reconciled`` is excluded here — it is cross-source, so its two directions
        # are confirmed below instead of reported straight from the scan pair.
        squad_global = {k: v for k, v in SQUAD_GLOBAL_CATALOG.items() if k != "index_reconciled"}
        engine = ValidatorEngine(
            spec=self.spec, paths=self.paths, playbook=self.playbook, squad_global=squad_global
        )
        issues += engine.report(index, on_disk, bodies=bodies)
        issues += await self._confirm_cross_source(
            index,
            on_disk,
            unparseable_seqs=unparseable_seqs,
            suppress_missing=suppress_missing,
        )
        return issues

    def _orphaned_skill_issues(self, index: SquadsDB) -> list[CheckIssue]:
        """A live ``SKILL`` item whose ``sq-<type>`` slug names a type the active spec no
        longer declares — the drop or rename left its generated pointer/body withdrawn
        (:meth:`ServiceCore._project_roster_item`), but the item itself is still sitting at a
        live status, which would otherwise read as a going concern with no ``sq check``
        complaint at all. ``warn``, not ``error``: nothing is broken (the withdrawal already
        happened), and the fix is reversible either way — restore the type, or retire the
        skill by hand.
        """
        issues: list[CheckIssue] = []
        for item in index.items.values():
            if item.type != ROSTER_SKILL or item.status not in self.spec.live_statuses(
                ROSTER_SKILL
            ):
                continue
            stale_type = orphaned_skill_item_type(item.extra.get(X.SLUG, ""), self.spec)
            if stale_type is None:
                continue
            issues.append(
                CheckIssue(
                    "warn",
                    item.id,
                    f"skill {item.extra.get(X.SLUG, item.id)!r} is {item.status} but type "
                    f"{stale_type!r} is no longer declared — its generated files have "
                    "been withdrawn; restore the type to bring it back, or retire this "
                    "skill (update its status) to close it out",
                )
            )
        return issues

    async def _confirm_one_drift_candidate(
        self,
        seq: int,
        fresh_index: SquadsDB,
        on_disk: dict[int, tuple[str, Path, dict[str, Any]]],
    ) -> list[CheckIssue]:
        """Re-observe one drift candidate at the freshly-loaded index's path (falling back to
        the scan's own path when that one's gone — see the inline comment below) and re-run
        the drift predicate; factored out of :meth:`_confirm_cross_source` so that function's
        own branch count stays readable. Empty when the candidate cannot be confirmed at all:
        removed from the index since the scan, gone from disk entirely, or unparseable on this
        read (a race between the scan and this confirm, or a file that only became unparseable
        since — either way the run already reports the parse failure once it is next seen at
        scan time, and stacking a speculative drift claim on top of it helps nobody).
        """
        fresh_item = fresh_index.items.get(seq)
        if fresh_item is None:
            return []  # removed since the scan — no index side left to confirm against
        confirm_path = item_file(self.paths, fresh_item)
        try:
            text = await _aio.read_text(confirm_path)
        except FileNotFoundError:
            # The fresh index's own path field can itself be the stale side: an interrupted
            # rename leaves the file at its new path while the index still holds the old one.
            # Fall back to the path the scan actually found this sequence at before giving up
            # on the candidate — only skip when neither path has the file, the genuine
            # "gone since the scan" case.
            confirm_path = on_disk[seq][1]
            try:
                text = await _aio.read_text(confirm_path)
            except FileNotFoundError:
                return []  # gone from both paths — no frontmatter side left to confirm
        try:
            fdata = read_frontmatter(text=text, source=str(confirm_path))
        except SquadsError:
            return []  # unparseable on this read — not confirmed, see the docstring above
        return _drift_issues(fresh_item, fdata)

    async def _confirm_cross_source(
        self,
        index: SquadsDB,
        on_disk: dict[int, tuple[str, Path, dict[str, Any]]],
        *,
        unparseable_seqs: frozenset[int] = frozenset(),
        suppress_missing: bool = False,
    ) -> list[CheckIssue]:
        """The one confirm round for cross-source claims.

        Partitions status/parent drift and both index/disk reconciliation directions into
        *candidates* from the ``(index, on_disk)`` scan pair, then — only when the candidate
        set is non-empty — re-loads the index exactly once and re-observes exactly those
        candidates (never a full rescan, which would reintroduce the cost the lock-free
        design exists to avoid) at the path the freshly loaded index gives for each one,
        before re-running the same predicate against that fresh pair. A candidate produced by
        a transaction that commits between the scan and this reload resolves here and is
        never reported; a durable inconsistency reproduces on the fresh pair and is reported
        below, still naming its skew direction when the two ``updated_at`` values order it.

        A clean board pays nothing: no candidates, no second index load, no second file read.

        ``unparseable_seqs``/``suppress_missing`` come from :meth:`_scan_for_check`'s
        present-but-unparseable third state: a file that exists but could not be parsed is
        never a *missing* candidate (the file is right there — see the module's durability
        contract), and when even its filename stem could not be resolved to a sequence number,
        ``suppress_missing`` drops the missing-direction claim for the whole run rather than
        risk reporting one that might be false.
        """
        drift_seqs = {
            item.sequence_id
            for item in index.items.values()
            if (entry := on_disk.get(item.sequence_id)) is not None
            and _drift_issues(item, entry[2])
        }
        orphan_seqs = set(on_disk) - set(index.items)
        missing_seqs: set[int] = set(index.items) - set(on_disk) - unparseable_seqs
        if suppress_missing:
            missing_seqs = set()
        if not (drift_seqs or orphan_seqs or missing_seqs):
            return []

        fresh_index = await self.store.load()
        issues: list[CheckIssue] = []

        for seq in sorted(drift_seqs):
            issues += await self._confirm_one_drift_candidate(seq, fresh_index, on_disk)

        for seq in sorted(orphan_seqs):
            fid, path, _data = on_disk[seq]
            if not await _aio.path_exists(path):
                continue  # the file itself is gone since the scan — nothing left to claim
            issue = on_disk_not_indexed(seq, fid, indexed=seq in fresh_index.items)
            if issue is not None:
                issues.append(issue)

        for seq in sorted(missing_seqs):
            fresh_item = fresh_index.items.get(seq)
            if fresh_item is None:
                continue  # removed from the index since the scan — no claim to confirm
            exists = await _aio.path_exists(item_file(self.paths, fresh_item))
            issue = not_on_disk(fresh_item, on_disk=exists)
            if issue is not None:
                issues.append(issue)

        return issues

    async def _scan_for_check(
        self,
    ) -> tuple[
        list[CheckIssue],
        dict[int, tuple[str, Path, dict[str, Any]]],
        dict[int, str],
        frozenset[int],
        bool,
    ]:
        """Scan every item file for marker issues, frontmatter, and raw body text.

        Returns ``(issues, on_disk, bodies, unparseable_seqs, suppress_missing)``.
        ``on_disk``/``bodies`` are keyed by the item's **sequence number** (int) so
        reconciliation comparisons are width-tolerant — frontmatter ``id`` fields keep their
        old width after ``sq migrate repad`` while the index reports the new width. ``on_disk``'s
        stored tuple is ``(fid, path, frontmatter_data)`` so error messages can still name the
        original frontmatter ID; ``bodies`` is the file's full raw text, read once here and
        threaded straight into :meth:`ValidatorEngine.report` so no validator re-reads the file
        itself.

        Skill files with no ``id`` in their frontmatter are silently skipped (pre-migration
        body files that have not yet been stamped as SKILL items).  Only ID-prefixed skill
        files (``SKILL-*.md``) without a valid frontmatter id are reported as errors.

        **A file that cannot be read, parsed, or built into an item is a third state, not a
        skip.** Reading or parsing it raises :class:`SquadsError` (the read-path guards this
        module depends on turn a raw decode/permission/YAML failure into one), and so does
        :meth:`Item.from_frontmatter` for frontmatter that parses as YAML but carries a
        type-invalid field — that is the load boundary check must cross too, or a file
        ``repair`` cannot rebuild passes here as clean. Every one of those is caught per file
        so one bad file never aborts the scan for the other hundreds. The failing file is
        reported as an error-level issue and goes into neither ``on_disk`` nor ``bodies``
        (there is no usable content to compare), but it is **present on disk**, so treating it
        as "missing" would be a phantom claim (see :meth:`_confirm_cross_source`). It is
        instead keyed into ``unparseable_seqs`` — by the frontmatter ``id`` itself when that
        parsed (the type-invalid-field case), or otherwise best-effort by the sequence number
        recovered from its **filename** stem alone (the same stem-parsing :meth:`repad` already
        relies on) — which the caller subtracts from the missing-direction reconciliation
        candidates. When even the stem does not parse, ``suppress_missing`` is set instead:
        there is no safe seq to subtract, so the caller drops the whole missing-direction claim
        for this run rather than risk reporting one that might be false.

        A ``FileNotFoundError`` on a dirent this same call's own glob just saw gets the same
        absent-vs-unreadable split as :meth:`_rebuild_index_from_disk`: a broken symlink is
        present-but-unreadable (reported, third-stated), a genuinely vanished dirent is skipped
        outright with nothing reported.
        """
        issues: list[CheckIssue] = []
        on_disk: dict[int, tuple[str, Path, dict[str, Any]]] = {}
        bodies: dict[int, str] = {}
        unparseable_seqs: set[int] = set()
        suppress_missing = False
        for item_type, md in self._iter_item_files():
            try:
                text = await _aio.read_text(md)
            except FileNotFoundError:
                if not await _aio.path_is_symlink(md):
                    continue  # vanished between glob and read -- genuinely absent
                suppress_missing |= _report_and_third_state(
                    issues,
                    unparseable_seqs,
                    md,
                    item_type,
                    self.spec,
                    _missing_dirent_message(md, is_symlink=True),
                )
                continue
            except SquadsError as exc:
                suppress_missing |= _report_and_third_state(
                    issues, unparseable_seqs, md, item_type, self.spec, str(exc)
                )
                continue
            issues += [CheckIssue("error", md.name, msg) for msg in _marker_issues(text)]
            try:
                data = read_frontmatter(text=text, source=str(md))
            except SquadsError as exc:
                suppress_missing |= _report_and_third_state(
                    issues, unparseable_seqs, md, item_type, self.spec, str(exc)
                )
                continue
            fid = data.get("id")
            if not fid:
                if _is_legacy_skill_body(md, item_type, self.spec):
                    continue  # pre-migration skill body -- never had an id, not an error
                issues.append(CheckIssue("error", md.name, "file has no `id` in frontmatter"))
                continue
            seq = _seq_from_frontmatter_id(fid)
            if seq is None:
                suppress_missing |= _report_and_third_state(
                    issues, unparseable_seqs, md, item_type, self.spec, _malformed_id_message(fid)
                )
                continue
            squad_rel = self.paths.squad_relative(item_type, md.name, spec=self.spec)
            try:
                Item.from_frontmatter(data, path=squad_rel)
            except SquadsError as exc:
                issues.append(CheckIssue("error", md.name, str(exc)))
                unparseable_seqs.add(seq)
                continue
            issues += _missing_timestamp_issues(md.name, data)
            on_disk[seq] = (fid, md, data)
            bodies[seq] = text
        return issues, on_disk, bodies, frozenset(unparseable_seqs), suppress_missing
