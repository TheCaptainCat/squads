"""Whole-squad maintenance: sync managed files, repair/renumber the index, check, migrate."""

import contextlib
import dataclasses
import tomllib
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

from squads import _actor as actor
from squads import _aio
from squads import _clock as clock
from squads import _sections as sections
from squads import _view_tags as view_tags
from squads import _views as views
from squads._backends._base import AgentBackend, BackendContext
from squads._errors import IndexFullError, SquadsError
from squads._index._reconcile import (
    ReconcileResult,
    carry_forward_indexed_timestamps,
    fold_stem_into_floor,
    plan_reconcile,
)
from squads._index._reflog import append_line, reflog_path
from squads._index._resolver import item_file
from squads._interactions._loader import (
    playbook_override_command_lines,
    playbook_override_guide_pairs,
)
from squads._interactions._playbook import (
    orphaned_playbook_guide_message,
    orphaned_playbook_guides,
    unheld_capability_token_message,
    unheld_capability_tokens,
)
from squads._interactions._skills import (
    bundled_skill_slugs,
    custom_item_skill_description,
    custom_skill_slugs,
    orphaned_skill_item_type,
    skill_description,
    skill_origin,
)
from squads._itemfile import (
    frontmatter_skew,
    read_frontmatter,
    read_item_text,
    rewrite_ids,
    skew_message,
    write_text,
)
from squads._migrations._config_text import ConfigRewrite, plan_config_rewrite
from squads._migrations._context import MigrationContext
from squads._migrations._registry import MIGRATIONS, Migration, release_reading_schema
from squads._models import _attributes as attrs
from squads._models import _markers as markers
from squads._models._attributes import AttributeKey
from squads._models._config import CONFIG_FILENAME
from squads._models._index import SquadsDB
from squads._models._item import (
    DEFAULT_ID_PADDING,
    DISPLAY_ID_PADDING,
    MAX_ID_PADDING,
    Item,
    format_item_id,
    prefix_from_id,
)
from squads._models._metadata import RETIRED_ROLE_KEYS
from squads._models._schema import SCHEMA_VERSION, schema_tuple
from squads._models._vocab import prefix_for
from squads._paths import number_for_id
from squads._rendering._engine import creation_template_name, render
from squads._roles._loader import LEGACY_DEV_TABLE_MESSAGE, ROLES_OVERRIDE_FILENAME
from squads._roles._projection import RoleView
from squads._sections import join_frontmatter
from squads._services._base import ServiceCore
from squads._services._corpus_files import (
    LegacySkillBody,
    Parsed,
    Unparseable,
    Unreadable,
    Vanished,
    malformed_id_message,
    missing_dirent_message,
    read_corpus_file,
    seq_from_frontmatter_id,
    stem_digit_run,
)
from squads._services._corpus_fit import corpus_fit_refusal
from squads._services._duplicate_ids import (
    SHARED_NUMBER_REMEDY,
    MovedFile,
    RenumberScope,
    SameIdRenumber,
    duplicate_groups,
    normalized_id,
    renumber_same_id_groups,
    shared_number_groups,
)
from squads._services._results import (
    MigrationRun,
    ReflogEntry,
    RenumberResult,
    RepairResult,
    SelfRemedied,
    SyncSkips,
)
from squads._services._roster_projection import is_live_roster_entry
from squads._services._skill_files import (
    RESOLVE_CONFLICT_REMEDY,
    RESTAMP_BLOCKED_REMEDY,
    SkillScan,
    stamped_skill_parts,
)
from squads._workflow import ROSTER_ROLE, ROSTER_SKILL, bundled_spec
from squads._workflow._loader import WORKFLOW_OVERRIDE_FILENAME
from squads._workflow._models import WorkflowSpec

# (id, markdown path, type, slug, number) — one scanned item file, used by repair/renumber.
# ``type`` is a plain ``str`` — every type (built-in or custom) resolves from the spec.
type _FileRec = tuple[str, Path, str, str, int]

_ROOT_TMP_IGNORE_PATTERN = f"{CONFIG_FILENAME}.*.tmp"


async def ensure_root_tmp_ignored(root: Path) -> None:
    """Ensure an interrupted ``.squads.toml`` write's temp sibling cannot be committed: the atomic-
    replace temp file sits in the project root, outside the squad dir's ``.gitignore``. It appends
    the pattern to a root ``.gitignore`` (creating a minimal one if absent) without touching adopter
    content, and is a no-op once a covering pattern exists. ``init``, ``adopt`` and :meth:`sync
    <MaintenanceMixin.sync>` call it.
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


def _ref_encoding_is_stale(data: dict[str, Any], item: Item) -> bool:
    """Whether *data*, the raw frontmatter just parsed for *item*, holds a ref encoding other than
    the canonical one *item* carries after folding. The only shape the fold changes is an edge
    spelled with the default kind (folded to bare), so comparing ``refs`` alone is exact; *item*
    exists, so ``data["refs"]`` was already accepted as absent or a list of ``str``.
    """
    raw_refs = cast("list[str]", data.get("refs") or [])
    return list(item.refs) != raw_refs


#: Suffix of a retired sub-entity badge region's tag (``<kind>:<local-id>:head``), undeclared in
#: ``_models/_markers.py``. Suffix matching is vocabulary-blind, so a dropped kind's region is
#: recognised, and a local id is free-form and uppercase.
_RETIRED_HEAD_SUFFIX = ":head"


def _retired_region_tags(text: str) -> list[str]:
    """Every retired marker region in *text*, as section tags in file order, matched by shape: the
    fixed :data:`~squads._models._markers.SUMMARY` region and every tag ending in
    :data:`_RETIRED_HEAD_SUFFIX`. Close markers are skipped so each region is named once, and an
    unbalanced region is left for ``check`` to report rather than cut through.
    """
    seen: list[str] = []
    for raw in sections.find_markers(text):
        tag = raw[len(markers.PREFIX) :]
        if tag.endswith(":end") or tag in seen:
            continue
        if tag != markers.SUMMARY and not tag.endswith(_RETIRED_HEAD_SUFFIX):
            continue
        if sections.has_section(text, tag):
            seen.append(tag)
    return seen


def _converge_body_tag(
    text: str, view_name: str, spec: WorkflowSpec, item_type: str, addr: int | str
) -> str:
    """Converge *text*'s ``sq:body`` region onto *view_name*'s placement tag only when the
    region is empty or already just that tag — anything else is left untouched, since it might
    be an author's real prose rather than a stale rendering. A missing region is reinstated
    first when that is safe; otherwise *text* comes back unchanged, never raising."""
    if sections.get_section(text, markers.BODY) is None:
        reinstated = view_tags.reinstate_absent_body_region(text)
        if reinstated is None:
            return text
        text = reinstated
    current = (sections.get_section(text, markers.BODY) or "").strip()
    tag_line = markers.open_marker(markers.view_tag(view_name))
    if current not in ("", tag_line):
        return text
    new_inner = view_tags.place_view_tags(
        sections.get_section(text, markers.BODY) or "",
        None,
        seeded=frozenset({view_name}),
        spec=spec,
        item_type=item_type,
        addr=addr,
    )
    return sections.replace_section(text, markers.BODY, new_inner)


def _strip_retired_regions(
    text: str, *, body_tag: str | None, spec: WorkflowSpec, item_type: str, addr: int | str
) -> str:
    """*text* with every retired region removed (marker-safe, via
    :func:`~squads._sections.remove_section`) and its ``sq:body`` region converged onto
    *body_tag*'s placement tag when given. A file with none of these regions, or an
    already-converged body, is a no-op; :func:`_converge_body_tag` never raises, so this
    function has no skip channel of its own."""
    for tag in _retired_region_tags(text):
        text = sections.remove_section(text, tag)
    if body_tag is not None:
        text = _converge_body_tag(text, body_tag, spec, item_type, addr)
    return text


def _retired_role_keys(item: Item, spec: WorkflowSpec) -> frozenset[str]:
    """The retired mirror keys *item* still carries as attributes, empty for a non-role item. The
    candidates are the closed set :data:`~squads._models._metadata.RETIRED_ROLE_KEYS`, never every
    unrecognised key, so a sweep never deletes another tool's key; a name the spec declares on role
    is the adopter's attribute.
    """
    if item.type != ROSTER_ROLE:
        return frozenset()
    declared = frozenset(spec.item_attributes(ROSTER_ROLE))
    return (RETIRED_ROLE_KEYS - declared) & frozenset(item.attributes)


@dataclasses.dataclass
class _PendingRewrites:
    """The file rewrites :meth:`MaintenanceMixin._rebuild_index_from_disk` has decided on but not
    performed, deferred past the corpus-alignment refusal check so a refusal never leaves a
    rewritten file without an index commit. ``files`` holds one ``(path, new_text)`` per path, the
    transformations composed by :func:`_record_pending_rewrite` so neither edit discards the other.
    ``canonicalized`` and ``stripped`` name the items each applied to; an item can be in both.
    """

    files: list[tuple[Path, str]] = dataclasses.field(default_factory=list[tuple[Path, str]])
    canonicalized: list[str] = dataclasses.field(default_factory=list[str])
    stripped: list[str] = dataclasses.field(default_factory=list[str])


def _frontmatter_without(data: dict[str, Any], keys: frozenset[str]) -> dict[str, Any]:
    """*data* — the file's own parsed frontmatter — with the top-level *keys* removed and
    **everything else left exactly as the file had it**, other keys and their order included.

    Deliberately not ``item.to_frontmatter_dict()``, which is what the ref canonicalisation
    writes: that mapping is the model's canonical projection, and a sweep that rewrites
    anything beyond its frozen list of removed keys is the defect the list exists to prevent.
    """
    return {k: v for k, v in data.items() if k not in keys}


def _record_pending_rewrite(
    pending: _PendingRewrites,
    md: Path,
    text: str,
    data: dict[str, Any],
    item: Item,
    *,
    body_tag: str | None,
    spec: WorkflowSpec,
) -> None:
    """Queue *item*'s write-back onto *pending* when its file needs one, composing every reason
    (stale ref encoding, retired region or body convergence, retired role mirror keys) into one
    replacement text: regions first, then one frontmatter rewrite (``item.to_frontmatter_dict()``
    when canonicalising, else :func:`_frontmatter_without`). The mirror keys leave the ``Item`` too,
    so ``db.add(item)`` agrees with the file; nothing is queued when the text is unchanged.
    """
    slug = item.slug
    addr: int | str = slug if item.type in (ROSTER_ROLE, ROSTER_SKILL) else number_for_id(item.id)
    new_text = _strip_retired_regions(
        text, body_tag=body_tag, spec=spec, item_type=item.type, addr=addr
    )
    stripped = new_text != text
    retired_keys = _retired_role_keys(item, spec)
    for key in retired_keys:
        del item.attributes[key]
    canonicalized = _ref_encoding_is_stale(data, item)
    if canonicalized:
        new_text = sections.replace_frontmatter(
            new_text, item.to_frontmatter_dict(), source=str(md)
        )
    elif retired_keys:
        new_text = sections.replace_frontmatter(
            new_text, _frontmatter_without(data, retired_keys), source=str(md)
        )
    if new_text == text:
        return
    stripped = stripped or bool(retired_keys)
    pending.files.append((md, new_text))
    if canonicalized:
        pending.canonicalized.append(item.id)
    if stripped:
        pending.stripped.append(item.id)


def _reader_phrase(schema: str) -> str:
    """The release that can read a squad stamped *schema*, as the refusals name it."""
    release = release_reading_schema(schema)
    return f"a squads release that reads schema v{schema}" + (
        f" (v{release} is one)" if release else ""
    )


def _earlier_steps_note(running: Migration | None, applied: list[Migration]) -> str:
    """What a refusal by a step says about who can change the roster: the release the squad is
    stamped for, and, when earlier steps ran, that they did."""
    if running is None:
        return ""
    if running is applied[0]:
        return f"Change the roster with {_reader_phrase(running.from_schema)}.\n"
    return (
        "Earlier steps of this run have already been applied, so running again is safe, and "
        f"the files are now in the shape of schema v{running.from_schema}: change the roster "
        f"with {_reader_phrase(running.from_schema)}.\n"
    )


def _index_full_refusal(exc: IndexFullError, schema: str) -> str:
    """The refusal for a pending runner that needs an id the index has none left to give: the
    way out is a release that can widen the padding, then this command again."""
    reader = _reader_phrase(schema)
    return (
        f"the index is full: all {exc.capacity:,} ids at padding {exc.padding} are used up, "
        f"and a pending migration needs another. Widen the padding with {reader}, then "
        "upgrade and re-run `sq migrate up`. The schema is unchanged."
    )


def _unindexable_refusal(result: ReconcileResult, reader: str) -> str:
    """The refusal for files at the squad's item locations that cannot be given an index entry
    of their own: each file with its cause, and the remedy there is."""
    lines = [f"  - {u.path}: {' '.join(u.cause.split())}" for u in result.unindexable]
    done: list[str] = []
    if result.indexed:
        done.append(f"indexed {', '.join(result.indexed)}")
    if result.missing:
        done.append(f"dropped {', '.join(result.missing)} (no file backs it)")
    index_note = (
        f" The index was rebuilt first ({'; '.join(done)})." if done and result.had_index else ""
    )
    remedy = (
        "\ncorrect each file, or, when it is not one of the squad's items, move it out of the "
        "folder it sits in, then re-run `sq migrate up`."
    )
    if not result.had_index:
        remedy = (
            "\nthere was no readable index, so every item-shaped file under the squad directory "
            "was taken for an item: restore the index (from version control, or with the index "
            f"rebuild of {reader}), or "
            "correct each file, or move it out of the squad directory, then re-run "
            "`sq migrate up`."
        )
    renumber = ""
    if any(u.shared_number for u in result.unindexable):
        renumber = (
            "\nto renumber one of the files that share a number, by hand: give it "
            f"number {result.counter + 1}, which is above the counter, in its file name, in "
            "its `id` and in its `sequence_id`, and change every reference that names its old "
            f"id. {reader[0].upper()}{reader[1:]} can also "
            "renumber it, references included."
        )
    return (
        "no migration has run: "
        f"{len(result.unindexable)} item file(s) cannot be given an index entry, and the "
        "schema is unchanged:\n" + "\n".join(lines) + renumber + remedy + index_note
    )


class MaintenanceMixin(ServiceCore):
    # ------------------------------------------------------------------ sync
    async def sync(self) -> SyncSkips:
        """Regenerate all tool-owned managed files (never ``.squads.toml``) and return a
        :class:`~squads._services._results.SyncSkips`, a plain ``list[str]`` of exact-text-
        deduplicated notices (drifted roster role left untouched, withdrawn ``SKILL`` item, dropped
        adopter-written playbook guide, per-entry backend WARN, regenerated pointer, unindexed skill
        body). It never raises for these, being what an operator runs when generated files are
        wrong; ``sq check`` gates.
        """
        skipped = list(await self._prepare_sync_surface())
        backends = self._backends()
        ctx = self._ctx
        for backend in backends:
            await backend.ensure_scaffold(ctx)
        # Recompute every role's resolved preload-skill set (system membership + scope
        # edges) once, up front, for the projection ctx below — a full sync is the single
        # recomputation point that every per-entry backend pointer's list is built from.
        role_skills = await self.roster_projection.role_skills_map()
        proj_ctx = BackendContext(
            paths=self.paths,
            spec=self.spec,
            playbook=self.playbook,
            role_skills=role_skills,
            catalog=self.catalog,
        )
        # Copied out of the snapshot: ``list_items`` returns the read scope's own aliases with no
        # copy, and the loop below hands these items to the projection.
        roster_roles = [
            item.model_copy(deep=True) for item in await self.list_items(item_type=ROSTER_ROLE)
        ]
        roster_skills = await self.list_items(item_type=ROSTER_SKILL)

        # The role/system-skill/per-item-type-skill body-tag convergence step
        # (:meth:`_repair_body_tag`/:func:`_converge_body_tag`), scoped to the roster: no index
        # rebuild, no retired-region strip, no ref-encoding canonicalisation.
        await self._backfill_roster_body_tags(roster_roles, roster_skills)

        entry_ctx = self._live_entry_context(roster_roles, roster_skills)
        missing_before = {
            (backend.name, rel_path)
            for backend in backends
            for rel_path in backend.managed_entry_paths(entry_ctx)
            if not (self.paths.root / rel_path).exists()
        }
        # Currency sibling of `missing_before`: the content of every existing per-entry pointer,
        # captured before the roster loops rewrite it, so the report can tell "out of date or edited
        # by hand" from "was missing". A path in `missing_before` is never a member here.
        content_before = await self._entry_content_snapshot(backends, entry_ctx, missing_before)

        skipped += await self._project_roster_entries(roster_roles, roster_skills, proj_ctx)
        skipped += self._regenerated_pointer_notices(backends, entry_ctx, missing_before)
        roster = await self._write_managed_files(backends, role_skills)
        # Currency's report, sibling of the "was missing" one: a pointer whose content this run just
        # changed relative to `content_before`, worded apart from a missing one. A path in
        # `missing_before` was never captured, so the two never overlap.
        skipped += await self._entry_drift_report(backends, entry_ctx, content_before)
        skipped += await self._dropped_guidance_notices(roster)
        # Seed SKILL ids for every managed skill file ``write_managed`` just ensured, bundled and
        # custom, in ``init``/``adopt`` order and idempotently; a bare file has no frontmatter, so
        # repair could never index one that first appears after init.
        await self.seed_bundled_skills()
        await self.seed_custom_skills()
        skipped += await self._skill_body_notices()
        # Collapse exact duplicates only (order-preserving) — see the docstring above. A
        # second, textually different message about the same item is never touched by this.
        return SyncSkips(dict.fromkeys(skipped))

    async def _prepare_sync_surface(self) -> list[str]:
        """The folders and files ``sync`` needs in place before it reads the index; returns the
        notices from restoring a managed skill file that lost its frontmatter."""
        # Idempotent: a squad initialised before this pattern existed picks it up here
        # instead of carrying the hole for the rest of its life.
        await ensure_root_tmp_ignored(self.paths.root)

        # Ensure that every type folder declared in the active spec exists on disk.
        # Built-in type folders are created by init/adopt; custom type folders may not
        # yet exist if the type was added to the spec after the squad was initialised.
        for ts in self.spec.items.values():
            folder = self.paths.squad_dir / ts.folder
            await _aio.mkdir(folder, parents=True, exist_ok=True)

        # A managed skill file that lost its frontmatter is restored before anything reads the
        # index; when the index does not know it yet, rebuild the index from the restored file.
        return await self._restore_skill_files_ahead_of_sync()

    def _live_entry_context(
        self, roster_roles: list[Item], roster_skills: list[Item]
    ) -> BackendContext:
        """The roster-scoped set of per-entry pointers that should exist after this run, by the same
        live predicate and ``managed_entry_paths`` declaration `sq check`'s `backend_reconciled`
        uses, so the two agree. Snapshotting the absent ones before the roster loops write lets the
        report say "regenerated" for them alone.
        """
        live_role_slugs = frozenset(
            slug for it in roster_roles if is_live_roster_entry(it, self.spec) and (slug := it.slug)
        )
        live_skill_slugs = frozenset(
            slug
            for it in roster_skills
            if is_live_roster_entry(it, self.spec) and (slug := it.slug)
        )
        return BackendContext(
            paths=self.paths,
            spec=self.spec,
            playbook=self.playbook,
            live_role_slugs=live_role_slugs,
            live_skill_slugs=live_skill_slugs,
            catalog=self.catalog,
        )

    async def _project_roster_entries(
        self, roster_roles: list[Item], roster_skills: list[Item], proj_ctx: BackendContext
    ) -> list[str]:
        """Re-apply every roster item's status against the live predicate, materialising live
        entries and withdrawing every other, including ones retired earlier. Only the backend
        projection (``project_item``, shared with the single-item transition) is gated here; a
        role's definition renders at read time off its ``sq:view:role_definition`` tag, which the
        body-tag backfill writes ahead of these loops.
        """
        skipped: list[str] = []
        # Resolved once for the whole sync sweep, not per role.
        default_kind = self.spec.default_ref_kind()
        for it in roster_roles:
            skew_msg = await self._detect_roster_item_skew(it, default_kind=default_kind)
            if skew_msg is not None:
                skipped.append(skew_msg)
            skipped += await self.roster_projection.project_item(it, proj_ctx)
        for it in roster_skills:
            stale_type = orphaned_skill_item_type(it.slug, self.spec)
            if stale_type is not None and it.status in self.spec.live_statuses(ROSTER_SKILL):
                skipped.append(
                    f"{it.id} ({it.slug}): type {stale_type!r} no longer "
                    "declared — generated files withdrawn; restore the type to "
                    "re-materialise, or retire this skill to close it out"
                )
            skipped += await self.roster_projection.project_item(it, proj_ctx)
        return skipped

    def _regenerated_pointer_notices(
        self,
        backends: list[AgentBackend],
        entry_ctx: BackendContext,
        missing_before: set[tuple[str, str]],
    ) -> list[str]:
        """Report, per file and per backend, only the per-entry pointers that were actually
        absent before this run and that this run's own loops just wrote — a retirement
        withdraws a pointer by removing its slug from the live set itself, so it is never a
        member of `missing_before` and is never reported here."""
        if not missing_before:
            return []
        return [
            f"{rel_path}: was missing — regenerated by this sync (backend: {backend.name})"
            for backend in backends
            for rel_path in backend.managed_entry_paths(entry_ctx)
            if (backend.name, rel_path) in missing_before and (self.paths.root / rel_path).exists()
        ]

    async def _write_managed_files(
        self, backends: list[AgentBackend], role_skills: dict[str, list[str]]
    ) -> list[RoleView]:
        """Compile every backend's managed regions and files; returns the live roster they were
        compiled from."""
        skill_map = await self.roster_projection.skill_paths()
        ctx_with_skills = BackendContext(
            paths=self.paths,
            skill_paths=skill_map,
            skill_invocable=await self.roster_projection.skill_invocable(),
            role_skills=role_skills,
            spec=self.spec,
            playbook=self.playbook,
            catalog=self.catalog,
        )
        roster = await self.roster()
        ops = await self.operators()
        for backend in backends:
            await backend.write_managed(ctx_with_skills, roster, ops)
        return roster

    async def _dropped_guidance_notices(self, roster: list[RoleView]) -> list[str]:
        """What the generated skills just written do NOT contain: reported after
        ``write_managed``, not before. `roster` is the live set ``write_managed`` itself gated
        on, so the two can never disagree about which guides were dropped."""
        known_slugs = {r.slug for r in await self.roster_all()}
        live_initial = self.spec.live_initial(ROSTER_ROLE)
        override_guides = playbook_override_guide_pairs(self.paths.squad_dir, self.files)
        try:
            catalog_slugs = {r.slug for r in self.catalog().roles}
        except SquadsError:  # the broken catalog override is its own finding
            catalog_slugs = set[str]()
        return [
            *(
                orphaned_playbook_guide_message(
                    item_type,
                    slug,
                    retired=slug in known_slugs,
                    live_status=live_initial,
                    in_catalog=slug in catalog_slugs,
                )
                for item_type, slug in orphaned_playbook_guides(
                    self.playbook,
                    self.spec,
                    live_roles=roster,
                    override_guides=override_guides,
                )
            ),
            *(
                unheld_capability_token_message(item_type, capability)
                for item_type, capability in unheld_capability_tokens(
                    self.playbook,
                    self.spec,
                    live_roles=roster,
                    override_guides=override_guides,
                    override_commands=playbook_override_command_lines(
                        self.paths.squad_dir, self.files
                    ),
                )
            ),
        ]

    async def _skill_body_notices(self) -> list[str]:
        """The notices from restamping managed skill frontmatter, then one per skill body that no
        `SKILL` item indexes: the question that generalises to every variant of the seeding gap,
        asked at the one moment the answer is unambiguous, right after this run both wrote the
        bodies and seeded them."""
        _restamped, restamp_skips = await self._restamp_managed_skill_frontmatter()
        return [*restamp_skips, *self._unindexed_skill_bodies()]

    def _catalog_skill_item(
        self, slug: str, number: int, filename: str, known: Item | None = None
    ) -> Item:
        """A managed skill's item as the seeders would create it, built from the file name's
        number and slug and the skill catalog alone. When the index already knows *number*,
        its timestamps and sessions are carried over so the restored file agrees with it."""
        desc = (
            skill_description(slug)
            if slug in bundled_skill_slugs()
            else custom_item_skill_description(slug.removeprefix("sq-"))
        )
        now = clock.now()
        sid, _psid = actor.current_session()
        return Item(
            sequence_id=number,
            type=ROSTER_SKILL,
            prefix=prefix_for(ROSTER_SKILL, self.spec),
            title=slug,
            slug=slug,
            status=self.spec.live_initial(ROSTER_SKILL),
            description=desc,
            author=slug,
            path=self.paths.squad_relative(ROSTER_SKILL, filename, spec=self.spec),
            created_at=known.created_at if known else now,
            updated_at=known.updated_at if known else now,
            created_session=known.created_session if known else sid,
            modified_session=known.modified_session if known else sid,
            slug_in_file=True,
            attributes={
                AttributeKey.ORIGIN: (attrs.origin(known) if known else None)
                or skill_origin(slug, self.spec)
            },
        )

    async def _restore_skill_files_ahead_of_sync(self) -> list[str]:
        """Restamp managed skill files before anything reads them, and rebuild the index from
        them when it does not know a restored file yet. Returns the restamp's report lines."""
        restored, skips = await self._restamp_managed_skill_frontmatter()
        if restored:
            known = {it.sequence_id for it in await self._indexed_skills()}
            if any(n not in known for n in restored):
                await self.repair()
        return skips

    async def _restamp_managed_skill_frontmatter(self) -> tuple[list[int], list[str]]:
        """Rewrite the frontmatter of every managed skill file that has none, has no ``id`` or has
        unreadable YAML, keeping its body. It comes from the file name and skill catalog, never the
        index, and an authored item is untouched. A file another file's id or slug already claims is
        reported, not written, and a merge conflict past the frontmatter refuses the sync. Returns
        the number restamped and a report line per file left alone.
        """
        state = await self._skill_folder_state(SkillScan())
        folder = self.paths.squad_dir / self.spec.items[ROSTER_SKILL].folder
        restamped: list[int] = []
        skipped: list[str] = []
        for name, text in state.texts.items():
            verdict = state.verdict(name, self.spec)
            if verdict is None:
                continue
            if verdict.kind == "conflict":
                raise SquadsError(
                    f"malformed frontmatter in {folder / name}: {verdict.reason}; "
                    f"{RESOLVE_CONFLICT_REMEDY}"
                )
            if verdict.kind == "blocked":
                skipped.append(
                    f"{name}: not restamped -- {verdict.reason}; {RESTAMP_BLOCKED_REMEDY}"
                )
                continue
            number, slug = stamped_skill_parts(folder / name, self.spec) or (0, "")
            item = self._catalog_skill_item(slug, number, name, state.known.get(number))
            body = sections.strip_frontmatter(text)
            await write_text(folder / name, join_frontmatter(item.to_frontmatter_dict(), body))
            restamped.append(number)
        return restamped, skipped

    async def _entry_content_snapshot(
        self,
        backends: list[AgentBackend],
        entry_ctx: BackendContext,
        missing_before: set[tuple[str, str]],
    ) -> dict[tuple[str, str], str]:
        """The pre-write half of ``sync``'s currency report, factored out to keep that
        method's own branch/statement count readable: the content of every live per-entry
        pointer that already exists (never one in *missing_before* — that path belongs to the
        presence report instead), read once before this run's roster loops write anything.
        """
        snapshot: dict[tuple[str, str], str] = {}
        for backend in backends:
            for rel_path in backend.managed_entry_paths(entry_ctx):
                key = (backend.name, rel_path)
                if key in missing_before:
                    continue
                with contextlib.suppress(OSError):
                    snapshot[key] = await _aio.read_text(self.paths.root / rel_path)
        return snapshot

    async def _entry_drift_report(
        self,
        backends: list[AgentBackend],
        entry_ctx: BackendContext,
        content_before: dict[tuple[str, str], str],
    ) -> list[str]:
        """The post-write half of ``sync``'s currency report: compares each snapshotted path's
        content now against *content_before*, and a changed one is reported "out of date or edited
        by hand" (never "was missing", since a path in ``missing_before`` was never captured).
        Factored out like :meth:`_entry_content_snapshot`.
        """
        if not content_before:
            return []
        report: list[str] = []
        for backend in backends:
            for rel_path in backend.managed_entry_paths(entry_ctx):
                before = content_before.get((backend.name, rel_path))
                if before is None:
                    continue
                after: str | None = None
                with contextlib.suppress(OSError):
                    after = await _aio.read_text(self.paths.root / rel_path)
                if after is not None and after != before:
                    report.append(
                        f"{rel_path}: out of date or edited by hand — regenerated by this sync "
                        f"(backend: {backend.name})"
                    )
        return report

    def _unindexed_skill_bodies(self) -> list[str]:
        """One report line per slug-named skill body left with no ``SKILL`` item after seeding. Such
        a body has no frontmatter, so ``sq skill <slug> show`` cannot find it and ``sq repair``
        cannot index it, yet backend pointers reference it. ``sq check`` tolerates the shape
        (:func:`is_legacy_skill_body`), but sync wrote the file and ran both seeders over every
        known slug, so a leftover is one no seeding path claims. Reported, never raised.
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

    async def _detect_roster_item_skew(self, item: Item, *, default_kind: str) -> str | None:
        """Read *item*'s on-disk frontmatter and report, never write, a real divergence from the
        index-loaded copy, for every roster item this pass touches
        (:func:`~squads._itemfile.skew_message`'s sync reuse). It is unconditional because a role is
        otherwise not read during a sync, so a drift would go unnoticed. A missing or unreadable
        file returns ``None``, being another pass's report.
        """
        path = item_file(self.paths, item)
        try:
            text = await read_item_text(path, item.id)
        except SquadsError:
            return None
        diverging = frontmatter_skew(text, item, default_kind=default_kind)
        if not diverging:
            return None
        return skew_message(item, diverging)

    # ------------------------------------------------------------------ migrations
    async def run_pending_migrations(self) -> MigrationRun:
        """Apply each migration whose target schema exceeds the on-disk one, in order, then rebuild
        the index and stamp the new schema. It returns the applied :class:`Migration` records and
        the rebuild's :class:`~squads._services._results.RepairResult`, the corpus sweep a behind-
        schema squad only gets here. The :meth:`repair` call sits after every runner (see its
        ordering rule), and its result is ``None`` exactly when nothing applied.
        """
        disk = self.paths.config.schema_version
        applied = [m for m in MIGRATIONS if schema_tuple(m.to_schema) > schema_tuple(disk)]
        changed: dict[str, int] = {}
        skipped: dict[str, list[str]] = {}
        reports: dict[str, tuple[str, ...]] = {}
        ctx = MigrationContext(
            paths=self.paths, spec=self.spec, playbook=self.playbook, catalog=self.catalog
        )
        reconciled: ReconcileResult | None = None
        original_index: str | None = None
        config_rewrite: ConfigRewrite | None = None
        if applied:
            await self._refuse_legacy_dev_table()
            # Computed and checked before any file changes, written last.
            config_rewrite = plan_config_rewrite(
                await self._config_text(),
                SCHEMA_VERSION,
                self.paths.config_path.name,
            )
            built, reconciled = await plan_reconcile(self.paths.squad_dir, self.store, disk)
            # With a readable index the rebuilt one is kept even when the run stops; with none,
            # a run refused before its first runner leaves the squad as it found it.
            if reconciled.had_index:
                original_index = await _aio.read_text(self.paths.index_path)
                await self._keep_reconciled(built, reconciled, disk)
            refusal = self._pre_runner_refusal(built, reconciled)
            if refusal is not None:
                raise SquadsError(refusal)
            if not reconciled.had_index:
                await self._keep_reconciled(built, reconciled, disk)
        repaired: RepairResult | None = None
        running: Migration | None = None
        try:
            for m in applied:
                running = m
                outcome = await m.run(ctx)
                changed[m.to_schema] = outcome.count
                if outcome.skipped:
                    skipped[m.to_schema] = list(outcome.skipped)
                if outcome.report:
                    reports[m.to_schema] = outcome.report
            running = None
            if applied:
                repaired = await self.repair(rerun="`sq migrate up`")
        except IndexFullError as exc:
            raise SquadsError(_index_full_refusal(exc, disk)) from exc
        except SquadsError as exc:
            raise await self._refusal_after_runner(
                exc, running, applied, disk, original_index
            ) from exc
        if config_rewrite is not None:
            await _aio.atomic_write_text(self.paths.config_path, config_rewrite.text)
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
        return MigrationRun(
            applied=applied,
            changed=changed,
            skipped=skipped,
            reports=reports,
            repair=repaired,
            reconcile=reconciled,
            config_dropped=config_rewrite.dropped if config_rewrite else (),
        )

    async def _refuse_legacy_dev_table(self) -> None:
        """Stop the run, changing nothing, when the role catalog override carries a ``[dev]``
        table, which is not a key of the catalog document. The table is never renamed here:
        ``sq migrate`` does not rewrite overrides."""
        path = self.paths.squad_dir / ROLES_OVERRIDE_FILENAME
        if not await _aio.path_exists(path):
            return
        try:
            declared = tomllib.loads(await _aio.read_text(path))
        except (tomllib.TOMLDecodeError, OSError, UnicodeDecodeError):  # fmt: skip
            return  # the catalog loader reports an unreadable document
        if "dev" in declared:
            raise SquadsError(
                f"{LEGACY_DEV_TABLE_MESSAGE}\nNothing was changed: rename the table, then run "
                "`sq migrate up` again."
            )

    async def _config_text(self) -> str:
        """``.squads.toml`` as written, line endings included."""
        raw = await _aio.read_bytes(self.paths.config_path)
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SquadsError(f"{self.paths.config_path.name} is not valid UTF-8: {exc}") from exc

    async def _refusal_after_runner(
        self,
        exc: SquadsError,
        running: Migration | None,
        applied: list[Migration],
        disk: str,
        original_index: str | None,
    ) -> SquadsError:
        """The refusal a failing runner becomes. A first step that fails has changed no file, so
        the index the earlier release wrote is put back; after earlier steps the run says to
        repair with that release first."""
        text = str(exc)
        if original_index is not None and running is not None:
            if running is applied[0]:
                await _aio.atomic_write_text(self.paths.index_path, original_index)
            else:
                text += (
                    f"\nRebuild the index with the repair command of {_reader_phrase(disk)} first."
                )
        return SquadsError(
            f"{text}\n{_earlier_steps_note(running, applied)}"
            f"The squad is still at schema v{disk}: fix the cause, then re-run "
            "`sq migrate up`, which rebuilds the index from the files first."
        )

    async def _keep_reconciled(self, built: SquadsDB, result: ReconcileResult, schema: str) -> None:
        """Write the rebuilt index and record what it indexed and dropped."""
        await self.store.overwrite(built)
        if result.indexed or result.missing:
            await self._log_reconcile(schema, result)

    def _pre_runner_refusal(self, built: SquadsDB, result: ReconcileResult) -> str | None:
        """Why the run must stop before its first runner, or ``None``: an item file that cannot
        be indexed, or a corpus that does not fit the vocabulary the run resolved."""
        schema = self.paths.config.schema_version
        reader = _reader_phrase(schema)
        if result.unindexable:
            return _unindexable_refusal(result, reader)
        override = self.paths.squad_dir / WORKFLOW_OVERRIDE_FILENAME
        done: list[str] = []
        if result.indexed:
            done.append(f"indexed {', '.join(result.indexed)}")
        if result.missing:
            done.append(f"dropped {', '.join(result.missing)} (no file backs it)")
        rebuilt = (
            f" The index was rebuilt first ({'; '.join(done)})."
            if done and result.had_index
            else ""
        )
        return corpus_fit_refusal(
            built,
            self.spec,
            self.paths.squad_dir,
            had_index=result.had_index,
            override_path=override if override.is_file() else None,
            reader=reader,
            rebuilt=rebuilt,
        )

    async def _log_reconcile(self, schema: str, result: ReconcileResult) -> None:
        """Record what the index rebuild indexed and dropped as soon as it is written, so a run
        that stops afterwards still leaves it on record."""
        sid, psid = actor.current_session()
        await append_line(
            reflog_path(self.paths.squad_dir),
            ts=clock.iso(clock.now()),
            actor=actor.current_actor(),
            op="migrate",
            target="",
            delta={
                "from_schema": schema,
                "reconcile": {"indexed": list(result.indexed), "missing": list(result.missing)},
            },
            session_id=sid,
            parent_session_id=psid,
        )

    # ------------------------------------------------------------------ skill seeding
    async def seed_bundled_skills(self) -> list[Item]:
        """Stamp SKILL-… ids onto the bundled managed skill bodies (idempotent), after
        ``refresh_managed()`` creates them. Each gets a roster-profile ``skill`` ``Item`` (status
        ``Active``) allocated through ``IndexStore.transaction()`` in lexical-by-slug order, and the
        legacy ``<slug>.md`` is renamed to ``agents/skills/SKILL-<NNNNNN>-<slug>.md``; a slug
        already convention-named is untouched. Returns the ``Item``s stamped.
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

            # Look for the legacy slug-named body file write_managed created.
            legacy_path = skills_folder / f"{slug}.md"
            if not legacy_path.is_file():
                continue  # body file not created yet (shouldn't happen after refresh_managed)
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
                    # Scaffolding creates LIVE, not at `initial`: a role entry preloads a skill by
                    # slug without consulting its status, so a non-live skill would leave a clean
                    # `sq init` with roles preloading unmaterialised skills.
                    status=self.spec.live_initial(ROSTER_SKILL),
                    description=desc,
                    author=slug,
                    path=squad_rel,
                    created_at=now,
                    updated_at=now,
                    created_session=sid,
                    modified_session=sid,
                    slug_in_file=True,
                    attributes={AttributeKey.ORIGIN: skill_origin(slug, self.spec)},
                )
                # Stamp frontmatter and write to the convention-named file.
                stamped = join_frontmatter(item.to_frontmatter_dict(), existing_text)
                convention_path = skills_folder / new_name
                await write_text(convention_path, stamped)
                # Remove the legacy slug-named file in the same transaction, after the convention-
                # named file is written: a crash leaves markdown ahead (the sanctioned skew) rather
                # than an orphan the idempotent skip never revisits.
                await _aio.path_unlink(legacy_path)
                db.add(item)
                self.store.log(
                    "create",
                    item.id,
                    {
                        "title": slug,
                        "type": ROSTER_SKILL,
                        "status": self.spec.live_initial(ROSTER_SKILL),
                    },
                )
            # Rewrite each backend's pointer to reference the convention-named body (write_managed
            # wrote the old slug path). It stays outside the transaction, a backend pointer being
            # regenerable.
            ctx = self._ctx
            for backend in self._backends():
                await backend.generate_skill_entry(ctx, item)
            seeded.append(item)
        return seeded

    # ------------------------------------------------------------------ custom skill seeding
    async def seed_custom_skills(self) -> list[Item]:
        """Stamp SKILL-… ids onto custom-type managed skill body files (idempotent), mirroring
        :meth:`seed_bundled_skills` for custom types in the active spec. Ids follow
        :func:`bundled_skill_slugs`'s lexical-by-slug order, so bundled ids do not churn. It runs
        from :meth:`sync` (a type declared or renamed later) and from ``init``/``adopt`` (via
        ``_init_time_spec``), so a fresh squad has no unindexed skill bodies.
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

            # Look for the legacy slug-named body file write_managed created.
            legacy_path = skills_folder / f"{slug}.md"
            if not legacy_path.is_file():
                continue  # body file not created yet (write_managed must run first)
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
                    # Scaffolding creates LIVE, not at `initial`: a role entry preloads a skill by
                    # slug without consulting its status, so a non-live skill would leave a clean
                    # `sq init` with roles preloading unmaterialised skills.
                    status=self.spec.live_initial(ROSTER_SKILL),
                    description=desc,
                    author=slug,
                    path=squad_rel,
                    created_at=now,
                    updated_at=now,
                    created_session=sid,
                    modified_session=sid,
                    slug_in_file=True,
                    attributes={AttributeKey.ORIGIN: skill_origin(slug, self.spec)},
                )
                stamped = join_frontmatter(item.to_frontmatter_dict(), existing_text)
                convention_path = skills_folder / new_name
                await write_text(convention_path, stamped)
                # See seed_bundled_skills for why the legacy unlink moves inside the
                # transaction, alongside the write it always follows.
                await _aio.path_unlink(legacy_path)
                db.add(item)
                self.store.log(
                    "create",
                    item.id,
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

    # ------------------------------------------------------------------ scan helpers (cont.)
    async def _corpus_alignment_refusals(
        self, known_corpus: SquadsDB | None, rebuilt: SquadsDB
    ) -> list[str]:
        """Refusal messages for a rebuild that would glob only the active spec's
        ``folder``/``prefix`` and treat a re-foldered or re-prefixed type's corpus as deleted; empty
        when aligned. With ``known_corpus``, an item missing from ``rebuilt`` whose recorded
        ``path`` is still a file is refused, and every type absent from it has its bundled location
        checked on disk. A wholly custom, never-indexed type is skipped.
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
        *,
        report: bool = True,
    ) -> tuple[int | None, str | None]:
        """One file's third-state handling, shared by every branch of
        :meth:`_rebuild_index_from_disk` that cannot build an ``Item`` from *md*: report *message*
        under its name and carry its previous entry from ``known_corpus`` into *db* unchanged, found
        by the sequence number in the filename stem. Returns the stem's ``(seq, digit_run)`` for the
        caller's floor via :func:`fold_stem_into_floor`, which no single file owns.
        """
        if report:
            line = f"{md.name}: {message}"
            unreadable.append(SelfRemedied(line) if isinstance(message, SelfRemedied) else line)
        digit_run = stem_digit_run(md, item_type, self.spec)
        stem_seq = int(digit_run) if digit_run is not None else None
        carried = (
            known_corpus.items.get(stem_seq)
            if known_corpus is not None and stem_seq is not None
            else None
        )
        if carried is not None:
            db.add(carried)
        return stem_seq, digit_run

    async def _duplicated_files(self) -> dict[Path, SelfRemedied]:
        """Each file whose id another file also carries, with its group's report line."""
        duplicated: dict[Path, SelfRemedied] = {}
        for key, files in duplicate_groups(await self._id_carriers()).items():
            note = SelfRemedied(f"{key}: {self._duplicate_id_message(files)}")
            duplicated.update(dict.fromkeys(files, note))
        return duplicated

    def _carry_duplicate(
        self,
        db: SquadsDB,
        unreadable: list[str],
        known_corpus: SquadsDB | None,
        md: Path,
        item_type: str,
        entry: SelfRemedied,
        floor: tuple[int, int],
    ) -> tuple[int, int]:
        """Two truths for one id: neither file is taken. The previous entry (if any) is carried
        forward, and the group is reported once, naming every file."""
        note = entry
        stem_seq, digit_run = self._carry_forward_unreadable(
            db,
            unreadable,
            known_corpus,
            md,
            item_type,
            note,
            report=not any(line.endswith(note) for line in unreadable),
        )
        return fold_stem_into_floor(floor[0], floor[1], stem_seq, digit_run)

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
        running counter/padding floor (:func:`fold_stem_into_floor`) in one step, so no call
        site has to thread the intermediate ``(stem_seq, digit_run)`` pair itself."""
        stem_seq, digit_run = self._carry_forward_unreadable(
            db, unreadable, known_corpus, md, item_type, message
        )
        return fold_stem_into_floor(max_n, max_filename_width, stem_seq, digit_run)

    def _raise_unless_vocab_valid(self, item: Item, md: Path, rerun: str) -> None:
        """Load-boundary vocab validation for :meth:`_rebuild_index_from_disk`: reject an item
        with an unknown type, status, or sub-entity status before it enters the rebuilt index.
        Uses ``self.spec`` — the Service-owned spec (possibly an override) — so repair respects
        the active workflow spec. Split out of the rebuild loop purely to keep that
        already-long method under the complexity ceiling."""
        if item.type not in self.spec.items:
            raise SquadsError(
                f"item {item.id} has unknown type {item.type!r} in {md.name}; "
                f"fix the frontmatter before running {rerun}"
            )
        if item.status not in self.spec.statuses:
            raise SquadsError(
                f"item {item.id} has unknown status {item.status!r} in {md.name}; "
                f"fix the frontmatter before running {rerun}"
            )
        # Sub-entity statuses share the same vocabulary.
        for sub in item.subentities:
            if sub.status not in self.spec.statuses:
                raise SquadsError(
                    f"item {item.id} sub-entity {sub.local_id} has unknown status "
                    f"{sub.status!r} in {md.name}; fix the frontmatter before "
                    f"running {rerun}"
                )

    async def _backfill_roster_body_tags(
        self, roster_roles: list[Item], roster_skills: list[Item]
    ) -> None:
        """Converge every role's and skill's ``sq:body`` region onto its placement tag in place: the
        part of :meth:`repair`'s sweep :meth:`sync` needs, without the index rebuild, retired-region
        strip or ref canonicalisation. It uses :meth:`_repair_body_tag` to classify and the strict
        :func:`_converge_body_tag` to mutate (a genuinely empty region only), touching only
        ``sq:body`` and needing no reflog entry since no indexed field changes.
        """
        for item in (*roster_roles, *roster_skills):
            view_name = self._repair_body_tag(item)
            if view_name is None:
                continue
            md = item_file(self.paths, item)
            try:
                text = await _aio.read_text(md)
            except FileNotFoundError:
                # Indexed but the file is gone — not this call's problem to report; the next
                # `sq check`/`sq repair` surfaces a missing file its own, dedicated way.
                continue
            slug = item.slug
            new_text = _converge_body_tag(text, view_name, self.spec, item.type, slug)
            if new_text != text:
                await write_text(md, new_text)

    def _repair_body_tag(self, item: Item) -> str | None:
        """The placement tag the repair sweep converges *item*'s ``sq:body`` onto, or ``None`` to
        leave it alone; :func:`_converge_body_tag` acts only on a genuinely empty region. It is
        :func:`~squads._views.roster_body_view_name`, which the roster write refusal and ``sq
        check`` also read (:func:`~squads._views.seeded_view_names`), so they cannot disagree; a
        view dropped via ``[selected]`` leaves its region alone.
        """
        slug = item.slug
        if item.type not in (ROSTER_ROLE, ROSTER_SKILL):
            return None
        return views.roster_body_view_name(item.type, slug, self.spec)

    async def _rebuild_index_from_disk(
        self,
        *,
        previous_counter: int,
        previous_padding: int,
        known_corpus: SquadsDB | None = None,
        rerun: str = "`sq repair`",
    ) -> tuple[SquadsDB, list[str], list[str], list[str]]:
        """Scan every item file fresh and commit a rebuilt index: the core of :meth:`repair`,
        factored out so :meth:`renumber` reuses it without repair's missing-file bookkeeping, which
        would misread a shift as deletions. ``previous_counter``/``previous_padding`` are floors the
        result never regresses below and ``known_corpus`` is the caller's last-loaded snapshot. It
        refuses (nothing written) when :meth:`_corpus_alignment_refusals` finds a corpus the active
        spec cannot see. Returns ``(db, unreadable, canonicalized, stripped)``.

        ``unreadable`` names every file that could not be read, parsed or built into an item, caught
        per file. Its previous entry is carried forward from ``known_corpus`` by filename-stem
        sequence number (else it stays unindexed, as guessing an id would report a guess as fact),
        and the stem folds into the counter/padding floor (:func:`fold_stem_into_floor`) so its
        number is never reissued. A timestamp the markdown lacks is carried forward, not invented.

        The file is made canonical too: a stale ref encoding, a retired region or role mirror key
        (also dropped from the parsed ``Item``) and a role's body-tag convergence compose into one
        queued write per path (:func:`_record_pending_rewrite`), written before the index commit;
        ``canonicalized`` and ``stripped`` name those items. The strip list is frozen: a name needs
        no live writer, no authoritative reader and derived content, or this sweep and its writer
        would undo each other.
        """
        db = SquadsDB(counter=0)
        max_n = 0
        max_filename_width = 0
        unreadable: list[str] = []
        # Every file to rewrite, one entry per path composing both transformations, collected here
        # and written only after the corpus-alignment refusal check passes, so a refusal never
        # leaves a rewritten file without an index commit (see _PendingRewrites).
        pending = _PendingRewrites()
        # Resolved once before the per-file loop and its SquadsError handling: a spec declaring the
        # wrong number of default ref kinds must fail as one refusal naming the spec, not N
        # "unreadable file" issues.
        default_kind = self.spec.default_ref_kind()
        skills = SkillScan()
        duplicated = await self._duplicated_files()
        for item_type, md in self._iter_item_files():
            if md in duplicated:
                max_n, max_filename_width = self._carry_duplicate(
                    db,
                    unreadable,
                    known_corpus,
                    md,
                    item_type,
                    duplicated[md],
                    (max_n, max_filename_width),
                )
                continue
            record = await read_corpus_file(item_type, md, self.spec)
            if isinstance(record, Vanished | LegacySkillBody):
                continue
            if not isinstance(record, Parsed):
                message = (
                    record.message
                    if isinstance(record, Unreadable | Unparseable)
                    else await self._missing_id_message(md, item_type, skills)
                )
                max_n, max_filename_width = await self._report_third_state(
                    db, unreadable, known_corpus, md, item_type, message, max_n, max_filename_width
                )
                continue
            text, data = record.text, record.data
            squad_rel = self.paths.squad_relative(item_type, md.name, spec=self.spec)
            try:
                item = Item.from_frontmatter(data, path=squad_rel, default_kind=default_kind)
            except SquadsError as exc:
                max_n, max_filename_width = await self._report_third_state(
                    db, unreadable, known_corpus, md, item_type, str(exc), max_n, max_filename_width
                )
                continue
            carry_forward_indexed_timestamps(item, data, known_corpus)
            self._raise_unless_vocab_valid(item, md, rerun)
            _record_pending_rewrite(
                pending, md, text, data, item, body_tag=self._repair_body_tag(item), spec=self.spec
            )
            db.add(item)
            max_n = max(max_n, number_for_id(item.id))
            # The filename digit-run width (PREFIX-<digits>-<slug>.md) is the in-corpus record of a
            # repad. Strip the known prefix (from the parsed item) rather than splitting on a
            # hyphen, which would mis-split a hyphenated prefix like "RUN-BOOK".
            stem = md.stem  # e.g. "RUN-BOOK-000042-fix-login"
            digits_slug = stem.removeprefix(f"{item.prefix}-")  # "000042-fix-login"
            digit_run, _, _slug = digits_slug.partition("-")  # "000042", "fix-login"
            if digit_run.isdigit():
                max_filename_width = max(max_filename_width, len(digit_run))

        # Never let the counter regress: keep whichever is higher — the previous high-water mark
        # or the maximum sequence number found on disk.
        db.counter = max(previous_counter, max_n)
        # Padding is max(stored floor, corpus max filename width): the stored value is the floor and
        # the filename scan the recompute, so the result never regresses.
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

        # Markdown before the index, as everywhere else: every rewritten file is written
        # here, once the rebuild is known to proceed, strictly before the index commit
        # below.
        for md, new_text in pending.files:
            await write_text(md, new_text)

        await self.store.overwrite(db)
        return db, unreadable, pending.canonicalized, pending.stripped

    async def repair(self, *, renumber: bool = False, rerun: str = "`sq repair`") -> RepairResult:
        """Rebuild the index from the markdown frontmatter (see :meth:`_repair_held`), holding the
        index lock from the first file read to the index commit so no writer interleaves."""
        async with self.store.exclusive():
            return await self._repair_held(renumber=renumber, rerun=rerun)

    async def _repair_held(
        self, *, renumber: bool = False, rerun: str = "`sq repair`"
    ) -> RepairResult:
        """Rebuild the index from the markdown frontmatter, sweeping the corpus while walking it
        (:meth:`_rebuild_index_from_disk`). A strip must never run ahead of a surface regeneration
        that reads what it removes, nor regenerate anything itself. That holds here by construction:
        the schema gate limits ``sq repair`` to a current-schema corpus, and the one behind-schema
        call is the tail of :meth:`run_pending_migrations`, after every runner.
        """
        # Snapshot the previous index (if any) before rebuilding, to preserve the counter high-water
        # mark and padding floor and to report indexed items whose files have gone missing.
        previous_counter = 0
        previous_padding = DEFAULT_ID_PADDING
        # Keyed by sequence_id (int) so the comparison is width-tolerant: a repadded index widens id
        # strings while from_frontmatter rebuilds at the default width (as `index_reconciled` does).
        previous_seq_to_id: dict[int, str] = {}
        known_corpus: SquadsDB | None = None
        if self.store.exists():
            try:
                # validate_vocab=False: repair recovers from vocab drift that load() rejects; an
                # absent-index fallback would lose the counter mark and let a freed number be
                # reissued. A genuinely unreadable index is caught below and treated as empty.
                prev = await self.store.load(validate_vocab=False)
                previous_counter = prev.counter
                previous_padding = prev.padding
                previous_seq_to_id = {it.sequence_id: it.id for it in prev.items.values()}
                known_corpus = prev
            except SquadsError:  # genuinely corrupt/missing index — treat as empty
                pass

        renumbered = SameIdRenumber()
        if renumber:
            renumbered = await self._renumber_same_id(
                previous_counter, previous_padding, known_corpus
            )
            renumbered.moved += await self._renumber()
        await self.refuse_shared_numbers()

        db, unreadable, canonicalized, stripped = await self._rebuild_index_from_disk(
            rerun=rerun,
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
            delta={
                "items": len(db.items),
                "missing": missing_ids,
                "unreadable": unreadable,
                "canonicalized": canonicalized,
                "stripped": stripped,
            },
            session_id=sid,
            parent_session_id=psid,
        )

        return RepairResult(
            db=db,
            missing_ids=missing_ids,
            unreadable=unreadable,
            canonicalized=canonicalized,
            stripped=stripped,
            renumbered=renumbered.moved,
            references=renumbered.references,
        )

    async def refuse_shared_numbers(self, remedy: str = SHARED_NUMBER_REMEDY) -> None:
        """Refuse, before the index is rebuilt, a number carried by files of different ids: the
        index is keyed by number, so the rebuild would keep one file and hide the other. *remedy*
        is the command the message names."""
        groups = shared_number_groups(await self._id_carriers())
        if not groups:
            return
        lines = "\n".join(
            f"  - {self._shared_number_message(number, files, remedy)}"
            for number, files in sorted(groups.items())
        )
        raise SquadsError(f"refusing to rebuild the index: it keys items by number:\n{lines}")

    async def _renumber_same_id(
        self, previous_counter: int, padding: int, known_corpus: SquadsDB | None
    ) -> SameIdRenumber:
        """``repair --renumber`` for ids carried by several files: see
        :func:`~squads._services._duplicate_ids.renumber_same_id_groups`."""
        groups = duplicate_groups(await self._id_carriers())
        if not groups:
            return SameIdRenumber()
        numbers = [previous_counter]
        for item_type, md in self._iter_item_files():
            run = stem_digit_run(md, item_type, self.spec)
            if run is not None:
                numbers.append(int(run))
        previous: list[Item] = list(known_corpus.items.values()) if known_corpus else []
        indexed: dict[str, Path] = {}
        for it in previous:
            key = normalized_id(it.id)
            if key is not None:
                indexed[key] = self.paths.abspath(it.path)
        scope = RenumberScope(
            folder_for_prefix={
                ts.prefix: self.paths.squad_dir / ts.folder for ts in self.spec.items.values()
            },
            indexed_paths=indexed,
            list_files=self._all_item_files,
            rehint=lambda text, fm, path, old: self._rehint(text, fm, path, old_number=old),
        )
        return await renumber_same_id_groups(
            squad_dir=self.paths.squad_dir,
            groups=groups,
            scope=scope,
            padding=padding,
            first_free=max(numbers) + 1,
        )

    # ------------------------------------------------------------------ repad
    async def repad(self, new_padding: int) -> int:
        """Raise the squad's ID padding (see :meth:`_repad_held`), holding the index lock from
        the first file read to the index commit so no writer interleaves."""
        async with self.store.exclusive():
            return await self._repad_held(new_padding)

    async def _repad_held(self, new_padding: int) -> int:
        """Raise the squad's ID padding to ``new_padding`` and rename every item file to
        ``PREFIX-<seq zero-padded>-<slug>.md``. It is a one-way bump: it refuses ``new_padding`` not
        above the stored padding, leaves file contents byte-untouched, and calls :meth:`repair`
        afterwards to rebuild the index with the new padding and paths. Returns the number of files
        renamed.
        """
        if new_padding > MAX_ID_PADDING:
            raise SquadsError(
                f"new padding {new_padding} is above the maximum of {MAX_ID_PADDING} digits; "
                "padding can only increase, so a width that wide could not be taken back"
            )
        db = await self.store.load(fresh=True)
        current = db.padding
        if new_padding <= current:
            raise SquadsError(
                f"new padding {new_padding} must be greater than the current padding {current}; "
                "padding can only increase (one-way format bump)"
            )

        # Refuse before touching anything if any frontmatter cannot be read: repad rewrites identity
        # across the whole corpus, so `_scan_records()` reads every file unguarded and a parse
        # failure raises before the first rename.
        await self._scan_records()

        renamed = 0
        for item_type, md in self._iter_item_files():
            stem = md.stem  # e.g. "RUN-BOOK-XXXXXX-fix-login"
            # The prefix comes from the active spec for this item's type, not a hyphen split, which
            # would mis-parse a hyphenated prefix like "RUN-BOOK"; the remainder is
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

        # Write the new padding into the index before the rebuild, so its stored-floor logic
        # picks it up and writes it back out. The lock is already held, so the index is
        # replaced directly rather than through a transaction.
        stored = await self.store.load(fresh=True)
        old_padding = stored.padding
        stored.padding = new_padding
        await self.store.overwrite(stored)
        sid, psid = actor.current_session()
        await append_line(
            reflog_path(self.paths.squad_dir),
            ts=clock.iso(clock.now()),
            actor=actor.current_actor(),
            op="migrate",
            target="",
            delta={
                "op": "repad",
                "old_padding": old_padding,
                "new_padding": new_padding,
                "renamed": renamed,
            },
            session_id=sid,
            parent_session_id=psid,
        )

        # Rebuild the index so path fields and all item IDs reflect the new width.
        await self._repair_held()
        return renamed

    async def _scan_records(self) -> list[_FileRec]:
        records: list[_FileRec] = []
        for item_type, md in list(self._iter_item_files()):
            try:
                text = await _aio.read_text(md)
            except FileNotFoundError as exc:
                if not await _aio.path_is_symlink(md):
                    continue  # moved or removed since the listing: the file is no longer here
                # A dirent this scan's glob saw but whose read failed (likely a broken symlink) gets
                # the same refusal as any unreadable file, as a clean SquadsError, worded by
                # `missing_dirent_message` so `check` and `repad` diagnose it identically.
                raise SquadsError(
                    f"{missing_dirent_message(md, is_symlink=await _aio.path_is_symlink(md))}"
                    " — refusing to rewrite ids while a file in the corpus cannot be read"
                ) from exc
            fid = read_frontmatter(text=text, source=str(md)).get("id")
            if not fid:
                continue
            seq = seq_from_frontmatter_id(fid)
            if seq is None:
                # A file whose `id:` is corrupt (`id: 5`, `id: TASK-abc`) is refused as a clean
                # SquadsError, never the raw AttributeError/InvalidIdError, since repad/renumber
                # cannot rewrite an identity they cannot read.
                raise SquadsError(f"{md} cannot be renumbered: {malformed_id_message(fid)}")
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
        """Assign fresh numbers to ID-number collisions. Returns (id remap, files to rename). The
        rename target is minted at the squad's filename ``padding`` (``db.padding``), but the remap
        target fed to ``rewrite_ids`` is unpadded (``DISPLAY_ID_PADDING``), as in the
        create/rename/retype seams, or the substitution would stamp a padded string into content
        that reads unpadded.
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
    ) -> dict[Path, Path]:
        """Shared renumber apply path, driven by ``repair --renumber`` (:meth:`_renumber`) and ``sq
        renumber`` (:meth:`renumber`): ``rewrite_ids`` substitutes each old id in ``remap`` with its
        unpadded display id across *paths*, the files in ``renames`` get the padded filename stem,
        and each renamed file's ``sequence_id`` is resynced. It never touches ``SquadsDB.counter``,
        each caller reconciling it its own way, and is a no-op for an empty ``remap``. Returns each
        renamed file's old and new path.
        """
        moved: dict[Path, Path] = {}
        if not remap:
            return moved
        await rewrite_ids(list(paths), remap)
        for old_path, item_type, slug, new_id in renames:
            new_name = f"{new_id}-{slug}.md" if slug else f"{new_id}.md"
            # Use the parent directory of the existing file — avoids resolving the type
            # through folder_for and works for both built-in and custom types.
            new_path = old_path.parent / new_name
            await _aio.path_rename(old_path, new_path)
            moved[old_path] = new_path
            text = await _aio.read_text(new_path)
            fm, _ = sections.split_frontmatter(text, source=str(new_path))
            if fm:
                fm["sequence_id"] = number_for_id(new_id)
                text = sections.replace_frontmatter(text, fm, source=str(new_path))
                text = self._rehint(
                    text, fm, new_path, old_number=stem_digit_run(old_path, item_type, self.spec)
                )
                await write_text(new_path, text)
        return moved

    def _rehint(self, text: str, fm: dict[str, Any], path: Path, *, old_number: str | None) -> str:
        """*text* with the lines its creation template renders from the item's number moved from
        the old number to the new one. A line the author has since edited no longer matches and is
        left alone."""
        if old_number is None:
            return text
        try:
            item = Item.from_frontmatter(
                fm, path=path.name, default_kind=self.spec.default_ref_kind()
            )
            template = creation_template_name(item.type, self.spec, from_squad=self.paths.squad_dir)
            stale = item.model_copy(update={"sequence_id": int(old_number)})
            old_lines, new_lines = (
                render(
                    template,
                    from_squad=self.paths.squad_dir,
                    item=it,
                    description=it.description,
                    spec=self.spec,
                ).splitlines()
                for it in (stale, item)
            )
        except SquadsError:
            return text
        if len(old_lines) != len(new_lines):
            return text
        lines = text.split("\n")
        for old, new in zip(old_lines, new_lines, strict=True):
            if old != new and old in lines:
                lines[lines.index(old)] = new
        return "\n".join(lines)

    async def _renumber(self) -> list[MovedFile]:
        """Resolve duplicate global ID numbers from a merge: reassign + rewrite references. Returns
        each file given a new number."""
        records = await self._scan_records()
        # An id carried by several files is not a number collision: no reference to it can be
        # attributed to one copy, so those files are left to the same-id handling.
        shared = {
            md for files in duplicate_groups((r[0], r[1]) for r in records).values() for md in files
        }
        records = [r for r in records if r[1] not in shared]
        padding = (
            (await self.store.load(fresh=True)).padding
            if self.store.exists()
            else DEFAULT_ID_PADDING
        )
        remap, renames = self._renumber_plan(records, padding)
        if not remap:
            return []
        paths = await self._apply_remap((md for _, md, *_ in records), remap, renames)
        squad = self.paths.squad_dir
        return [
            MovedFile(
                fid,
                remap[fid],
                md.relative_to(squad).as_posix(),
                paths[md].relative_to(squad).as_posix(),
            )
            for fid, md, *_ in records
            if md in paths
        ]

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
        """Plan a disjoint block-shift of every item numbered ``>= from_seq``, returning ``(remap,
        renames, warning)``. Exactly one of ``onto``/``by`` is required: ``onto=M`` computes the
        minimal safe ``delta = max(M, counter) + 1 - from_seq``, while ``by=n`` refuses (naming the
        minimum) unless ``from_seq + n > counter`` and always warns, as sq cannot certify the other
        branch's counter. The new range sits strictly above the old, so no new id equals an old one
        and the single-pass ``rewrite_ids`` is order-independent.
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
        """Pre-merge block-shift renumber (see :meth:`_renumber_held`), holding the index lock
        from the first file read to the index commit so no writer interleaves."""
        async with self.store.exclusive():
            return await self._renumber_held(from_seq=from_seq, onto=onto, by=by)

    async def _renumber_held(
        self, *, from_seq: int, onto: int | None = None, by: int | None = None
    ) -> RenumberResult:
        """Pre-merge block-shift renumber (``sq renumber``): shift every item with ``sequence_id >=
        from_seq`` into a disjoint range, rewriting each reference while it is unambiguous.
        :meth:`_offset_plan` validates before any file is touched, and the commit goes through
        :meth:`_rebuild_index_from_disk`, not ``repair``, whose missing-file detector would
        misreport the moves as deletions. One reflog line is appended after the commit, and none
        when nothing shifted.
        """
        if self.store.exists():
            idx = await self.store.load(fresh=True)
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
            (
                db,
                _unreadable,
                _canonicalized,
                stripped,
            ) = await self._rebuild_index_from_disk(
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
                delta={
                    "from": from_seq,
                    "onto": onto,
                    "by": by,
                    "remap": remap,
                    "stripped": stripped,
                },
                session_id=sid,
                parent_session_id=psid,
            )
        elif self.store.exists():
            db = await self.store.load(fresh=True)
            stripped = []
        else:
            db = SquadsDB(counter=counter, padding=padding)
            stripped = []
        return RenumberResult(remap=remap, db=db, warning=warning, stripped=stripped)

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
        """Read and filter the reflog: a missing or empty reflog returns an empty list, a trailing
        partial line is skipped silently and an interior malformed line is warn-skipped, and no lock
        is taken. Filters are ANDed: ``item`` matches ``target``, ``actor_filter`` ``actor`` and
        ``op_filter`` ``op`` exactly; ``since`` keeps ``ts >= since`` (ISO-8601 string order);
        ``tail`` keeps the last N after filtering.
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
