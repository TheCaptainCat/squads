"""Whole-squad maintenance: sync managed files, repair/renumber the index, check, migrate."""

import contextlib
import dataclasses
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
from squads._errors import IndexFullError, RoleNotFoundError, SquadsError
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
    update_frontmatter,
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
    Item,
    format_item_id,
    prefix_from_id,
)
from squads._models._metadata import RETIRED_ROLE_KEYS
from squads._models._schema import SCHEMA_VERSION, schema_tuple
from squads._models._vocab import prefix_for
from squads._paths import number_for_id
from squads._roles._catalog import RoleDef
from squads._roles._projection import RoleView
from squads._roles._resolver import pinned_name_of, resolve_role_with_base, role_base_from_item
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
    RenumberScope,
    SameIdRenumber,
    duplicate_groups,
    normalized_id,
    renumber_same_id_groups,
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


def _ref_encoding_is_stale(data: dict[str, Any], item: Item) -> bool:
    """Whether *data* — the raw, unfolded frontmatter :meth:`_rebuild_index_from_disk` just
    parsed for *item* — holds a ref encoding other than the canonical one *item* (already
    folded through :meth:`Item.from_frontmatter`) carries.

    A spelled ref folds to a different literal than what is written on disk when an edge is
    spelled with the live default kind (never emitted, always folded back to bare). That is
    the only shape the fold changes; every other frontmatter field round-trips unchanged when
    *item* was built from *data* directly, so comparing ``refs`` alone is exact.

    ``data["refs"]`` is safe to compare as a plain list here without re-validating its shape:
    *item* already exists, which means ``Item.from_frontmatter`` already accepted this same
    *data* — so ``refs`` was already either absent/empty or a list of ``str``.
    """
    raw_refs = cast("list[str]", data.get("refs") or [])
    return list(item.refs) != raw_refs


#: Suffix of a retired sub-entity badge region's tag. The tag itself
#: (``<kind>:<local-id>:head``) is composed at write time and is **not** declared in
#: ``_models/_markers.py``, so there is no constant to compare against and an absent one
#: proves nothing about what a corpus holds. Matching on the suffix is deliberate: it is
#: vocabulary-blind, so a badge region belonging to a sub-entity kind a project declared and
#: later dropped is recognised too, without this sweep having to read the live spec's kind
#: list. A local id is a declared ``local_prefix`` plus a number, free-form and uppercase for
#: every bundled kind, which is why nothing here may assume its spelling — a scan whose
#: character class assumes lowercase matches none of them and reports an empty corpus.
_RETIRED_HEAD_SUFFIX = ":head"


def _retired_region_tags(text: str) -> list[str]:
    """Every retired marker region present in *text*, as section tags in file order.

    Two families, matched by tag **shape** rather than by any declared vocabulary: the fixed
    :data:`~squads._models._markers.SUMMARY` region, and every tag ending in
    :data:`_RETIRED_HEAD_SUFFIX`. Both are derived renderings whose writers have retired and
    whose replacements are computed on every read, so what is on disk can only disagree with
    the frontmatter that is the sole source.

    Close markers are skipped (their tag carries a trailing ``:end``) so each region is named
    once, and a tag whose region is not balanced in *text* is skipped outright — an unclosed
    region is a marker defect for ``check`` to report, never something to cut through.
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
    """The retired mirror keys *item* still carries as attributes — empty for anything that is
    not a role item, and empty for a role that carries none of them.

    The set is a difference between two declarations, never a list written out here: the
    candidates are :data:`~squads._models._metadata.RETIRED_ROLE_KEYS` widened by
    :meth:`RoleDef.attribute_keys`, and what is taken back out is
    :meth:`RoleDef.stored_attribute_keys` for *this* role's shape. That subtraction is why a
    developer's ``model`` survives while a non-dev role's is removed, and why the answer cannot
    drift from the writer. Getting it wrong in the other direction is unrecoverable: a
    developer's ``model`` is an operator setting with no catalog answer, so a stripped one is
    re-rolled from the dev pool as a different value.

    A role is identified by its item type and its shape by the stored ``tech`` attribute, never
    by the slug's spelling. An operator item is kept off this sweep by the type check.
    """
    if item.type != ROSTER_ROLE:
        return frozenset()
    stored = RoleDef.stored_attribute_keys(templated=attrs.is_templated(item))
    retired = (RETIRED_ROLE_KEYS | RoleDef.attribute_keys()) - stored
    # A name the squad's spec declares on role is the adopter's attribute, not a mirror key; the
    # one declared name the mirror also used (the stored model) is still swept.
    declared = frozenset(spec.item_attributes(ROSTER_ROLE)) - RoleDef.attribute_keys()
    return (retired - declared) & frozenset(item.attributes)


@dataclasses.dataclass
class _PendingRewrites:
    """The file rewrites :meth:`MaintenanceMixin._rebuild_index_from_disk`'s per-file loop has
    decided on but not yet performed — deferred to after the corpus-alignment refusal check,
    so a refusal that aborts the whole rebuild never leaves a rewritten file behind with no
    matching index commit.

    ``files`` holds one ``(path, new_text)`` entry **per path**, never two. Both
    transformations a file can need — the ref-encoding canonicalisation and the retired-region
    strip — are composed into that single replacement text by :func:`_record_pending_rewrite`.
    Queuing them as two independent entries, each built from the file's original text, would
    mean whichever was written last silently discarded the other's edit.

    ``canonicalized`` and ``stripped`` name the items each transformation actually applied to,
    kept apart because they are different facts about a corpus and are reported separately.
    An item can appear in both.
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
    """Queue *item*'s write-back onto *pending* when its file needs one.

    Two independent reasons a file is rewritten, composed here into **one** replacement text
    and **one** queued entry (see :class:`_PendingRewrites`):

    - its on-disk ref encoding is stale (:func:`_ref_encoding_is_stale`), so the frontmatter is
      rewritten to the canonical encoding the fold already produced;
    - it carries a retired region, or a body this sweep converges onto a placement tag
      (:func:`_strip_retired_regions`, licensed per-item by *body_tag* — see
      :meth:`MaintenanceMixin._repair_body_tag`);
    - it is a role item that still carries retired mirror keys (:func:`_retired_role_keys`).

    The regions go first and the frontmatter rewrite last, over the stripped text:
    :func:`~squads._sections.replace_frontmatter` preserves the body verbatim, so the order
    only decides which text the later transformation reads, never what any of them produces.

    There is exactly **one** frontmatter rewrite, never two, and the two reasons pick
    different mappings for it. Canonicalisation writes ``item.to_frontmatter_dict()``, the
    model's own projection — it has to, since the canonical ref encoding exists only on the
    parsed ``Item``; the mirror keys are already gone from that ``Item`` by then, so the one
    rewrite serves both. A file needing only the key removal is rewritten from its own parsed
    frontmatter instead (:func:`_frontmatter_without`), which is the narrower edit: the model's
    projection would also drop a key the model derives rather than stores, and this sweep
    removes only what is on its list.

    **The mirror keys leave the** :class:`~squads._models._item.Item` **as well as the file**,
    and that is the coupling this vehicle introduces which a migration step did not have: the
    caller's very next statement is ``db.add(item)``, so an ``Item`` still carrying a key the
    file no longer does would put the index and the markdown into disagreement on exactly the
    key just removed. Those keys are not in ``PERMITTED_EXTRA_SKEW`` either, so the
    disagreement would not be forgiven — it would refuse every later read of that item.

    Nothing is queued when the composed text equals the original — the identity that makes a
    second rebuild over an already-corrected corpus write no file at all.

    Split out of the per-file loop purely to keep that already-long method under the
    complexity ceiling; the writes themselves are the caller's, after the refusal check.
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
        """Regenerate all tool-owned managed files to the current version. The body-tag backfill
        (:meth:`_backfill_roster_body_tags`) never declines (convergence is strict, so it either
        fills a genuinely empty region or leaves a non-empty one untouched, silently). Never
        writes ``.squads.toml``.

        **Deduplicated by exact text before returning.** A generic safety net over the
        per-writer skip-report messages below, not tied to any one of them — collapsing exact
        duplicates (not de-duplicating by item id, or by any other looser key) is what keeps a
        second, genuinely different message about the *same* item — a different field set, a
        different reason — passing through untouched.

        Returns a :class:`~squads._services._results.SyncSkips` — every existing caller can
        keep treating it as the plain ``list[str]`` of skip/notice messages below.

        Returns one skip-report message per drifted roster role whose
        frontmatter was left untouched (see :meth:`_detect_roster_item_skew`, and
        :meth:`_refresh_catalog_attributes`
        for the narrower catalog-merge case that can raise the same way), one notice per live
        ``SKILL`` item this run just withdrew because its type is no
        longer declared (:func:`orphaned_skill_item_type`), and one per
        playbook guide **the adopter wrote** that this run just dropped from a generated
        ``sq-<type>`` skill because its role slug names no live role
        (:func:`orphaned_playbook_guides` — the guide-level sibling of that
        same withdrawal, reported here for the same reason: this run is what silently removed it;
        a guide that exists only in the bundled playbook is squads' own degradation and stays
        silent, since no adopter can edit it), and one per WARN-only notice a per-entry backend
        write surfaced (``Artifact.warning`` via :meth:`project_item` — today that is a
        declared ``model`` the host's own agent frontmatter cannot express, which the generated
        pointer drops), one per per-entry backend pointer this run found absent and had to
        regenerate (naming the file and the backend — see the loop below; empty on a healthy
        squad, byte-identical to before this reporting existed), one per per-entry backend
        pointer this run found present but whose content differed from a fresh render and
        had to regenerate (the same shape, worded "out of date or edited by hand" rather than
        "was missing" so an operator can tell the two facts apart), and one per skill body
        left on disk that no ``SKILL`` item indexes once this run's own seeding is done
        (:meth:`_unindexed_skill_bodies`) — empty for a clean roster, exactly today's
        silent behaviour. Never raises for any of them: this is bulk
        regeneration of derived state, and is itself what an operator reaches for when
        generated files are wrong, so a drifted or withdrawn item is reported and the rest of
        the squad still syncs (exit stays 0 — ``sq check`` is the dedicated reporter that
        gates).
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
        # Copied out of the snapshot before any mutation: ``list_items`` returns the read
        # scope's own aliases with no copy, and ``_refresh_catalog_attributes`` below mutates
        # ``item.attributes`` in place and then grafts that same object into a fresh
        # ``transaction()`` db via ``db.add`` — a pre-transaction object landing in a db it
        # did not come from. The commit path is safe regardless (``ensure_no_skew`` gates the
        # graft, and the excluded-key set is exactly what the graft reasserts), but a private
        # copy here makes that local to this loop rather than something a reader has to trace
        # across three files.
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
        # The currency sibling of `missing_before` (the render-and-compare half of pointer
        # detection): the content of every per-entry pointer that DOES already exist,
        # captured before the roster loops below (re)write it — so the report after them can
        # tell "out of date or edited by hand"
        # (content changed) apart from "was missing" (`missing_before`, above) rather than
        # conflating the two under one message. A path in `missing_before` is never a member
        # here, so the two reports stay mutually exclusive by construction.
        content_before = await self._entry_content_snapshot(backends, entry_ctx, missing_before)

        skipped += await self._project_roster_entries(roster_roles, roster_skills, proj_ctx)
        skipped += self._regenerated_pointer_notices(backends, entry_ctx, missing_before)
        roster = await self._write_managed_files(backends, role_skills)
        # Currency's own report, the sibling of the "was missing" one above: a per-entry
        # pointer whose content this run's own writes above just changed relative to
        # `content_before`'s snapshot — distinguishable wording ("out of date or edited by
        # hand") because "was missing" and a changed pointer are different facts about a
        # repository. Never doubles up with the presence report: a path in `missing_before`
        # was never captured into `content_before` in the first place.
        skipped += await self._entry_drift_report(backends, entry_ctx, content_before)
        skipped += await self._dropped_guidance_notices(roster)
        # Seed SKILL ids for every managed skill file ``write_managed`` just ensured, bundled
        # and custom alike, in the same order ``init``/``adopt`` use (idempotent; a slug whose
        # convention-named file already exists is skipped without touching it). Both halves are
        # seeded because a bundled-playbook type whose body file first appears after init would
        # otherwise never be stamped: repair rebuilds the index from frontmatter, and the bare
        # file has none.
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
        """The roster-scoped set of per-entry pointers that *should* exist after this run —
        the same live predicate and the same backend declaration `sq check`'s
        `backend_reconciled` rule uses (`managed_entry_paths`), so the two can never
        disagree about which pointer belongs to which state. Snapshotting which of them are
        absent *before* the roster loops write anything is what lets the report after
        them say "regenerated" rather than treating an ordinary, already-there file the same
        way — a second, independent probe would risk drifting from this one."""
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
        """Re-apply every roster item's status against the live predicate, materialising a live
        entry and withdrawing every other one — including an entry already retired before this
        landed, with no migration owed. The item's own sq-managed state (the catalog-attribute
        merge) refreshes unconditionally regardless of liveness: only the *backend* projection —
        via ``project_item``, the same helper the single-item transition path uses — is gated.
        The role's own definition renders at read time off the ``sq:view:role_definition`` tag
        its ``sq:body`` carries (``squads._view_tags.expand_view_tags``, via
        ``ItemsMixin.read_body``); these loops don't write that tag either — the body-tag
        backfill does, once, ahead of them (see ``_backfill_roster_body_tags``)."""
        skipped: list[str] = []
        # Resolved once for the whole sync sweep, not per role.
        default_kind = self.spec.default_ref_kind()
        for it in roster_roles:
            skew_msg = await self._detect_roster_item_skew(it, default_kind=default_kind)
            if skew_msg is not None:
                skipped.append(skew_msg)
            msg = await self._refresh_catalog_attributes(it, default_kind=default_kind)
            if msg is not None:
                skipped.append(msg)
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
        return [
            *(
                orphaned_playbook_guide_message(
                    item_type, slug, retired=slug in known_slugs, live_status=live_initial
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
        """Rewrite the frontmatter of every managed skill file that has none, has no ``id`` or
        has unreadable YAML, keeping its body. The frontmatter comes from the file name and the
        skill catalog, never from the index, and an authored item is never touched. A file that
        another file's id or slug already claims is reported, not written; a merge conflict
        that reaches past the frontmatter refuses the sync. Returns the numbers restamped and
        one report line per file left alone."""
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
            await _aio.atomic_write_text(
                folder / name, join_frontmatter(item.to_frontmatter_dict(), body)
            )
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
        """The post-write half of ``sync``'s currency report — the sibling of the "was missing"
        block, factored out for the same readability reason as
        :meth:`_entry_content_snapshot`. Compares each snapshotted path's content right now
        against *content_before*; a changed one means this run's own writes above just replaced
        content that no longer matched a fresh render, so it is reported "out of date or edited
        by hand" rather than "was missing" — the two never overlap, since a path in
        ``missing_before`` was never captured into *content_before* to begin with.
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
        """One report line per slug-named skill body file left with no ``SKILL`` item after
        seeding — empty in the normal case.

        A skill body under the skills folder that does not carry the type's id prefix has no
        frontmatter, so nothing indexes it: ``sq skill <slug> show`` cannot find it, it is
        absent from ``sq list --type skill``, and ``sq repair`` cannot recover it either, since
        repair rebuilds the index *from* frontmatter. It is nonetheless a live file — the
        backends' generated pointers reference it and roles preload its slug.

        ``sq check`` deliberately tolerates this shape (see :func:`is_legacy_skill_body`: it
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

    async def _detect_roster_item_skew(self, item: Item, *, default_kind: str) -> str | None:
        """Read *item*'s on-disk frontmatter and report -- never write -- a real divergence
        from the index-loaded copy, unconditionally, for every roster item this pass touches.

        :func:`~squads._itemfile.skew_message`'s own docstring names three reusers: the
        refusal a single-mutation write seam raises, the ``ImportIssue`` the bulk importer's
        pre-pass collects, and "the skip-and-report line ``sq sync`` emits for a drifted
        roster item" -- the third one, and this is that check's home. Unconditionally is the
        load-bearing word: a role whose catalog fields already agree with the index
        (:meth:`_refresh_catalog_attributes` finds nothing to merge) would otherwise never have its
        frontmatter read again during a sync, so a drift on an ordinary field -- unrelated to
        any catalog-merged value, e.g. an interrupted ``description`` edit -- would go
        unnoticed until some unrelated seam happened to touch the same item.

        Deliberately independent of :meth:`_refresh_catalog_attributes`: both run unconditionally
        over the same roster loop, so a real skew is reported the same way regardless of
        whether the catalog merge also has something to say about the same item -- ``sync``'s
        own dedup collapses the identical message if both happen to raise it.

        A missing or unreadable file is not this check's business -- some other pass reports
        that -- so it returns ``None`` rather than raising.
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

    async def _refresh_catalog_attributes(self, item: Item, *, default_kind: str) -> str | None:
        """Reconcile a role item against its resolved definition: merge
        :meth:`RoleDef.to_attributes`'s keys into the item's attributes, and project the
        resolved name/mission onto the item's own ``title``/``description``.

        **What this merges is deliberately small.** A role's title, mission, responsibilities,
        agreements, colour and spawn authority resolve from the catalog on every read, so there
        is nothing about them left to reconcile here. What the merge converges is the stored
        residue (:data:`~squads._roles._catalog.RoleDef._ATTRIBUTE_FIELDS`) and, through
        :meth:`RoleDef.to_item_fields`, the resolved ``full_name``/``mission`` onto
        ``item.title``/``item.description`` — the fields read by every surface that does not
        know the item is a role and so cannot resolve a role catalog.

        Every role, dev or bundled, resolves through
        :func:`~squads._roles._resolver.resolve_role_with_base` with a base built by
        :func:`~squads._roles._resolver.role_base_from_item` (passed this squad's own
        ``squad_dir``, so a bundled role's base already carries a project's catalog-document
        override — ``.overrides/roles.toml`` — the same way an unactivated slug's does), which
        reads *this item's own* stored operator-settable fields rather than re-rolling a dev
        name from the pool. Every other field comes from the current catalog fresh. With no
        override file present the merged definition equals the base equals the item's own
        values, so both diff loops below find nothing and this returns ``None``. Only a
        genuinely orphaned custom item — no catalog entry, no dev shape, no override file — is
        skipped outright, via the ``RoleNotFoundError`` catch just below.

        **A change through this writer is not silent.** When the merge actually changes
        something, ``item.updated_at`` moves, ``item.modified_session`` is set to the acting
        session, and one ``"update"`` reflog entry is appended (after the index commit,
        alongside every other mutation) — so a reverted or refreshed role is visible on every
        recency surface instead of only in a diff of the file. This is a pure append: the
        role's own ``create`` reflog entry is never rewritten, pruned, or superseded by it.

        This is a roster-regen path, not a single mutation: an unrepaired skew is skipped and
        reported (the returned message) rather than refused, and the in-memory merge — both the
        attributes and the projected fields — is rolled back on skip so *item*
        stays truthful to what is actually on disk. Returns ``None`` when nothing changed or
        the write went through.

        **The merge is mirrored into the index, in the same transaction.** The values this
        merges are read from ``resolve_role_with_base``, which layers a project's
        ``.overrides/roles/<slug>.toml`` over the bundled catalog — so this is the write that
        carries an adopter's renamed role title (or model, or mission) onto the item. Every
        consumer of that title reads the *index*, not the frontmatter: :meth:`roster` builds
        its ``RoleView`` list from the index, and that list is what both backends
        compile ``CLAUDE.md``/``AGENTS.md`` from. Writing the frontmatter alone left the
        override's title durable but invisible — the generated roster kept rendering the
        bundled value until an unrelated ``sq repair`` happened to rebuild the index, with
        ``sq check`` clean the whole time. Markdown first, index commit last (invariant 8), so
        an interrupted refresh leaves the sanctioned one-sided skew ``sq repair`` heals. The
        projected top-level fields ride the same single ``update_frontmatter`` call — no new
        write, no new position in the order.

        **The projection never routes through the title-rename path.** ``item.title`` is
        assigned directly; ``_update_model``/``_rename`` are never called here, so ``item.slug``
        and ``item.path`` are untouched — a roster item's path slug is its role slug, not a
        slug of its title, and this call must never move the file.

        The attributes this call writes stay exempt from the skew guard everywhere — see
        ``_itemfile.PERMITTED_ATTRIBUTE_SKEW``, which lets a squad whose index already lags on
        those keys converge on its next sync instead of being refused by the guard first. The
        projected ``title``/``description`` fields are ordinary core keys the skew guard
        compares like any other.
        """
        slug = item.slug
        base_role = role_base_from_item(item, self.catalog)
        try:
            catalog_role = resolve_role_with_base(
                slug,
                self.paths.squad_dir,
                base=base_role,
                catalog=self.catalog,
                pinned_name=pinned_name_of(item),
            )
        except RoleNotFoundError:
            return None  # orphaned custom role item: no catalog entry, no override file
        # Whether the item carries ``tech`` (a templated developer) decides whether the
        # dev-only column (``model``) is part of this merge — see ``RoleDef.to_attributes``.
        catalog_attributes = catalog_role.to_attributes(templated=attrs.is_templated(item))
        item_fields = catalog_role.to_item_fields()
        base = item.model_copy(deep=True)
        previous_attributes: dict[str, Any] = {}
        previous_fields: dict[str, Any] = {}
        for key, value in catalog_attributes.items():
            if item.attributes.get(key) != value:
                previous_attributes[key] = item.attributes.get(key)
                item.attributes[key] = value
        for field, value in item_fields.items():
            if getattr(item, field) != value:
                previous_fields[field] = getattr(item, field)
                setattr(item, field, value)
        if not previous_attributes and not previous_fields:
            return None
        previous_updated_at = item.updated_at
        previous_modified_session = item.modified_session
        item.updated_at = clock.now()
        sid, _psid = actor.current_session()
        item.modified_session = sid
        delta: dict[str, Any] = {
            **{key: [old, item.attributes.get(key)] for key, old in previous_attributes.items()},
            **{field: [old, getattr(item, field)] for field, old in previous_fields.items()},
        }
        try:
            async with self.store.transaction() as db:
                await update_frontmatter(
                    item_file(self.paths, item), item, base, default_kind=default_kind
                )
                db.add(item)
                self.store.log("update", item.id, delta)
        except SquadsError as exc:
            for key, old_value in previous_attributes.items():
                if old_value is None:
                    item.attributes.pop(key, None)
                else:
                    item.attributes[key] = old_value
            for field, old_value in previous_fields.items():
                setattr(item, field, old_value)
            item.updated_at = previous_updated_at
            item.modified_session = previous_modified_session
            return str(exc)
        return None

    # ------------------------------------------------------------------ migrations
    async def run_pending_migrations(self) -> MigrationRun:
        """Apply each migration whose target schema exceeds the on-disk one, in order.

        Rebuilds the index from the migrated frontmatter and stamps the new schema version.

        Returns the applied :class:`Migration` records **and the rebuild's own**
        :class:`~squads._services._results.RepairResult`, because that rebuild is also the
        corpus sweep and this is the only route a squad behind the current schema takes: an
        operator migrating an older squad gets files rewritten, and ``sq migrate up`` reports
        them rather than saying only "index rebuilt". The
        caller announces it with
        :meth:`~squads._services._results.RepairResult.strip_notice`, the same sentence ``sq
        repair`` prints.

        The :meth:`repair` call below is the one place that verb runs against a corpus not yet
        at the current schema, and it sits after every runner deliberately: see
        :meth:`repair` for the ordering prohibition that placement satisfies. It is also why a
        squad already at the current stamp is not swept here — no runner applies, so nothing
        rebuilds, and the ordinary verb is that corpus's only route to the sweep. That is also
        why ``repair`` is ``None`` exactly when ``applied`` is empty.
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
        """Stamp SKILL-… ids onto the bundled managed skill body files (idempotent).

        Called by ``sq init`` after ``refresh_managed()`` has created the skill body files.
        Each bundled skill receives a full ``Item`` of the ``skill`` roster type with the
        roster-type profile (status ``Active``, no sub-entities), allocated through
        ``IndexStore.transaction()`` in lexical-by-slug order.

        Files are written with the convention-correct name
        ``agents/skills/SKILL-<NNNNNN>-<slug>.md``. The legacy slug-named file ``write_managed``
        creates (``<slug>.md``, carrying an empty ``sq:body`` region — a system skill's
        definition is rendered on read, never stored) is renamed to the convention name at this
        step; the ``sq init`` flow always ends with convention-named files on disk.

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
                    slug_in_file=True,
                    attributes={AttributeKey.ORIGIN: skill_origin(slug, self.spec)},
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
                    item.id,
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
        types from the very start — a fresh squad with a custom type has no
        unindexed skill body files waiting for someone to run `sq sync`).
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
        *,
        report: bool = True,
    ) -> tuple[int | None, str | None]:
        """One file's third-state handling, shared by every branch of
        :meth:`_rebuild_index_from_disk` that cannot produce an ``Item`` from *md* (unreadable
        bytes, unparseable YAML, valid YAML with no ``id``, or a type-invalid field): report
        *message* under *md*'s name, and carry *md*'s previous entry from ``known_corpus``
        forward into *db* unchanged when one exists — recovered by the sequence number parsed
        from the filename stem alone, since the frontmatter is exactly what this file cannot
        supply. Returns that stem's ``(seq, digit_run)`` so the caller can fold it into its own
        running counter/padding floor via :func:`fold_stem_into_floor` — this method only
        touches ``db``/``unreadable``, never the floor, which is a whole-rebuild value no
        single file owns.
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
        """Converge every role's and skill's ``sq:body`` region onto its placement tag, in
        place — the one piece of :meth:`repair`'s corpus sweep :meth:`sync` needs on the
        ordinary path (see the call site in :meth:`sync`), without
        :meth:`repair`'s index rebuild, retired-region strip, or ref-encoding
        canonicalisation.

        Reuses :meth:`_repair_body_tag` for the classification (which tag, if any, a given
        item's body converges onto — the same question ``sq repair`` asks, so the two callers
        can never disagree about what "the tag this item should carry" means) and
        :func:`_converge_body_tag` for the mutation, directly — not through
        :func:`_strip_retired_regions`/:func:`_record_pending_rewrite`, which also compose in
        the retired-region strip and the ref-encoding rewrite that are :meth:`repair`'s job,
        not this call's. A file this call writes gets **only** its ``sq:body`` region touched;
        nothing else in it changes.

        No index rebuild: nothing about an item's *indexed* fields (title, status, and so on)
        changes here, only body content the index has never stored, so there is nothing for a
        rebuild to reconcile. That is also why this needs no reflog entry of its own — the same
        posture ``sync``'s other file writes already have.

        Never declines: :func:`_converge_body_tag` is strict unconditionally, so it either
        converges a genuinely empty region or leaves a non-empty one untouched, silently —
        this function has no channel to report either outcome on."""
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
        """The placement tag name the repair sweep converges/backfills *item*'s ``sq:body``
        onto, or ``None`` when this sweep leaves the region alone. Naming a tag here is only
        the classification half — :func:`_converge_body_tag` decides, strictly and
        unconditionally, how much of that classification it actually acts on: a genuinely
        empty region only.

        The classification itself is :func:`~squads._views.roster_body_view_name` — the same
        pure function of a role's/skill's item type and slug that the roster write refusal and
        the ``sq check`` finding both read (:func:`~squads._views.seeded_view_names`), so this
        sweep can never disagree with either about which view a
        document carries. See that function's own docstring for the three shapes it names (a
        role, a permanently-system skill, a per-item-type ``sq-<type>`` skill) and the
        declared-view gate every one of them shares — dropping a view via a
        ``.overrides/workflow.toml`` ``[selected]`` block is ordinary, supported customisation,
        so a dropped view's region is left alone here (genuinely empty or plain, never
        dangling), matching the standard "empty — activate/sync" guidance rather than needing a
        repair of its own.

        A role's region converging is not deletion — see :func:`_strip_retired_regions`, which
        records what was driven: no read path branches on the region's own bytes, so rewriting
        it changes nothing any read surface observes beyond what the tag itself resolves
        to. It is the marker pair every item file carries, and keeping it is the cheaper of two
        harmless choices."""
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

        Returns ``(db, unreadable, canonicalized, stripped)`` — ``unreadable`` names
        every file whose content could not be read or parsed, **or** that parsed but cannot
        become an item
        (no ``id``, or a type-invalid field — :meth:`Item.from_frontmatter` is the load boundary
        for the latter, raising :class:`SquadsError` for both). Each is reported, never silently
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
        rebuild's counter/padding floor (:func:`fold_stem_into_floor`) — an unreadable file's
        own number must never be free for reissue just because its frontmatter couldn't
        contribute to the ordinary ``max_n``/``max_filename_width`` scan below.

        A timestamp the markdown does not carry is *not* re-read as an invented ``now`` and
        committed over the entry the index already holds: it is carried forward from
        ``known_corpus`` (:func:`carry_forward_indexed_timestamps`) — the same carry-the-
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

        **The file, not only the index, is made canonical.** For every item whose raw on-disk
        ``refs`` encoding differs from what the fold just produced
        (:func:`_ref_encoding_is_stale`) — a spelled ref that folds to a different literal (a
        spelled-default edge) — the file's frontmatter is rewritten
        to the canonical encoding, markdown before the index commit below as always. Nothing new
        is stored: the fold already produced *item*'s canonical ``refs``; this only writes what
        the rebuild already holds the data to write. ``canonicalized`` names every item so
        rewritten; a corpus that needs no correction has this list empty and writes no file at
        all, and a second rebuild over an already-canonical corpus is byte-identical to the
        first — the on-disk encoding a comparison like :func:`_ref_encoding_is_stale` reads is
        exactly what the previous rebuild just wrote.

        **Retired regions are stripped, in the same walk and the same deferred write.** A
        marker region whose writer has retired and whose replacement is computed on every read
        can only disagree with the frontmatter that is its sole source, so it is removed
        wherever it is still stored (:func:`_strip_retired_regions`), and so are the retired
        keys a role item still mirrors (:func:`_retired_role_keys`) — from the
        parsed ``Item`` as well as from the file, since the index entry committed below is
        built from it. ``stripped`` names every item so rewritten. What may be removed is a
        **frozen list** of named regions and keys, each satisfying three conditions in this
        same build: no live write path produces it, no read path consumes it as authoritative
        because its computed replacement has already shipped, and its content is derived
        rather than authored. A role's stored body converges onto its placement tag on the same
        terms and in the same write (:meth:`_repair_body_tag`); a general template-owned
        skill's does not, because being *derived* is not on its own enough — the sweep also has
        to be able to prove that nothing authored what it is about to overwrite, and only the
        role case (and, on the same license, the three permanently-system skills — see
        :meth:`_repair_body_tag`) can. Adding a name is a
        decision, not a developer's choice, and a name added before its writer retires puts
        this sweep and that writer into a loop where each undoes the other on alternate
        commands. ``tests/service/test_repair_strips_only_retired_regions.py`` is the
        falsifiable guard: it drives a fresh squad through the write path and asserts none of
        the listed names comes back.

        The same properties as canonicalization hold, for the same reason — a corpus carrying
        none of them writes no file at all, and a second rebuild over a stripped corpus is
        byte-identical to the first, since the strip's own output is what the next scan reads.
        Every transformation composes into **one** queued entry per path
        (:func:`_record_pending_rewrite`), so none of them can discard another's edit.

        **A body-tag convergence that declines is reported, not fatal.** When
        :func:`_strip_retired_regions` catches a marker-shaped ``sq:body`` its convergence has no
        model for, that one file's region is left untouched and its message is collected into
        ``skipped`` — every other file in the same corpus still converges normally, since the
        decline is caught per file inside the loop below rather than propagating out of it.
        """
        db = SquadsDB(counter=0)
        max_n = 0
        max_filename_width = 0
        unreadable: list[str] = []
        # Every file this rebuild decides to rewrite — one entry per path, composing both
        # transformations a file can need — collected here and written only after the
        # corpus-alignment refusal check below passes, so a refusal that aborts the whole
        # rebuild (nothing committed) never leaves a rewritten file behind with no matching
        # index commit. See _PendingRewrites.
        pending = _PendingRewrites()
        # Resolved once for the whole rebuild, before the per-file loop and its own
        # per-file SquadsError handling below — a spec declaring the wrong number of
        # default ref kinds must fail as one clean refusal naming the spec, never be
        # caught and mis-reported as N separate "unreadable file" issues.
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

        # Markdown before the index, as everywhere else: every rewritten file is written
        # here, once the rebuild is known to proceed, strictly before the index commit
        # below.
        for md, new_text in pending.files:
            await write_text(md, new_text)

        await self.store.overwrite(db)
        return db, unreadable, pending.canonicalized, pending.stripped

    async def repair(self, *, renumber: bool = False, rerun: str = "`sq repair`") -> RepairResult:
        """Rebuild the index from the markdown frontmatter, and sweep the corpus while walking
        it (:meth:`_rebuild_index_from_disk`).

        **A strip must never run ahead of a surface regeneration that reads what it removes,
        and must regenerate nothing itself.** That is a constraint on where a stripping step
        may sit relative to a surface-touching one, not an instruction to order two particular
        calls — a local phrasing survives only until someone reorders two adjacent lines for
        tidiness, whereas a property is inherited by a future step without being told.

        On this verb the first half holds **by construction**, which is worth recording rather
        than re-engineering. ``require_current_schema`` (``_cli/_common.py``) refuses every
        subcommand but ``migrate`` on a mismatched stamp, so ``sq repair`` can only ever run
        against a corpus already at the current schema; the single call on a behind-schema
        corpus is the tail of :meth:`run_pending_migrations`, after every ordered runner has
        finished — a runner's own surface regeneration included. A regeneration therefore
        always reads a corpus this sweep has not yet touched.

        What that protects is not hypothetical: a runner's surface step compiles the managed
        regions and every backend pointer from the roster projection it reads off the corpus,
        and a strip landing first would regenerate them from what it had just removed —
        silently, with nothing near the cause failing. The second half of the prohibition (the
        sweep regenerates nothing itself) is asserted by outcome in
        ``tests/integration/test_migration_corpus.py``: the compiled regions and pointers are
        byte-identical across the sweep. An assertion about which call ran first would pass on
        a sweep that quietly rewrote them.
        """
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

        renumbered = SameIdRenumber()
        if renumber:
            renumbered = await self._renumber_same_id(
                previous_counter, previous_padding, known_corpus
            )
            await self._renumber()

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
            renumber_report=renumbered.lines,
            references_left=renumbered.references_left,
        )

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
                # `missing_dirent_message`), so one dirent cannot be a "broken symlink" to
                # `check` and a "No such file or directory" to `repad`.
                raise SquadsError(
                    f"{missing_dirent_message(md, is_symlink=await _aio.path_is_symlink(md))}"
                    " — refusing to rewrite ids while a file in the corpus cannot be read"
                ) from exc
            fid = read_frontmatter(text=text, source=str(md)).get("id")
            if not fid:
                continue
            seq = seq_from_frontmatter_id(fid)
            if seq is None:
                # Same "cannot correctly rewrite an identity it cannot read" refusal as the
                # unreadable-file branch above, for a file whose `id:` itself is corrupt
                # (`id: 5`, `id: TASK-abc`). Repad/renumber rewrite identity across the whole
                # corpus, so refusing is right -- but as a clean SquadsError, never the raw
                # AttributeError/InvalidIdError the parse would otherwise throw.
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
        # An id carried by several files is not a number collision: no reference to it can be
        # attributed to one copy, so those files are left to the same-id handling.
        shared = {
            md for files in duplicate_groups((r[0], r[1]) for r in records).values() for md in files
        }
        records = [r for r in records if r[1] not in shared]
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
        operator actually supplied, the full remap, and the items the shared rebuild's corpus
        sweep rewrote) — never a replayable diff. That last part is reported for the same
        reason ``repair`` reports it: the rebuild this verb borrows also strips retired
        regions, so a shift that said nothing about it would rewrite content under a verb
        whose advertised job is identity. It reaches the operator's console through
        :meth:`~squads._services._results.RenumberResult.strip_notice`, in the one sentence
        every sweep-reaching command prints. Every
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
            db = await self.store.load()
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
