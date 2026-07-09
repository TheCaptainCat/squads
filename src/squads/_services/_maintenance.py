"""Whole-squad maintenance: sync managed files, repair/renumber the index, check, migrate."""

import re
from collections import Counter
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from squads import __version__, _aio
from squads import _actor as actor
from squads import _clock as clock
from squads import _discussion as discussion
from squads import _sections as sections
from squads._backends._base import BackendContext
from squads._errors import RoleNotFoundError, SquadsError
from squads._index._reflog import append_line, reflog_path
from squads._index._resolver import item_file
from squads._interactions import (
    TITLE_ADVISORY_MAX,
    bundled_skill_slugs,
    custom_item_skill_description,
    custom_skill_slugs,
    skill_description,
)
from squads._itemfile import read_frontmatter, rewrite_ids, update_frontmatter
from squads._migrations._registry import MIGRATIONS, Migration
from squads._models import _markers as markers
from squads._models._extras import ExtraKey as X
from squads._models._index import SquadsDB
from squads._models._item import (
    DEFAULT_ID_PADDING,
    DISPLAY_ID_PADDING,
    VALID_REF_KINDS,
    Item,
    format_item_id,
    split_ref,
)
from squads._models._schema import SCHEMA_VERSION, schema_tuple
from squads._models._vocab import prefix_for
from squads._paths import number_for_id
from squads._rendering._engine import render
from squads._roles._catalog import RoleDef
from squads._roles._resolver import resolve_role
from squads._sections import join_frontmatter
from squads._services._base import ServiceCore
from squads._services._results import CheckIssue, ReflogEntry, RenumberResult, RepairResult
from squads._workflow import META_ROLE, META_SKILL, STATUS_ACTIVE

# (id, markdown path, type, slug, number) — one scanned item file, used by repair/renumber.
# ``type`` is a plain ``str`` — every type (built-in or custom) resolves from the spec.
type _FileRec = tuple[str, Path, str, str, int]

# A leading status/lifecycle banner: "STATUS:" / "**STATUS…**" opening a line, or a
# hand-written "## Status" / "### Status" heading. Anchored so it only matches at the very
# start of the text being checked — never a bare keyword found anywhere in the middle.
_STATUS_BANNER_RE = re.compile(r"^\*{0,2}status\*{0,2}\s*:", re.IGNORECASE)
_STATUS_HEADING_RE = re.compile(r"^#{2,3}\s*status\s*:?\s*$", re.IGNORECASE)


def _opens_with_status_banner(text: str | None) -> bool:
    """True when *text* opens with a self-declared status/lifecycle banner.

    Only the leading line is examined — a whole-text keyword grep would also catch a body
    discussing lifecycle as a *topic* ("the Draft→Ready transition"), a cross-reference to
    another item's status ("blocks TASK-x until it lands"), or the word inside a fenced code
    example. None of those open the text, so anchoring here keeps the detector silent on them.
    """
    if not text:
        return False
    stripped = text.strip()
    if not stripped:
        return False
    first_line = stripped.splitlines()[0].strip()
    return bool(_STATUS_BANNER_RE.match(first_line) or _STATUS_HEADING_RE.match(first_line))


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


def _drift_issues(iid: str, item: Item, fdata: dict[str, Any]) -> list[CheckIssue]:
    issues: list[CheckIssue] = []
    if fdata.get("status") != item.status:
        issues.append(
            CheckIssue("warn", iid, "status drift between frontmatter and index (run `sq repair`)")
        )
    if (fdata.get("parent") or None) != item.parent:
        issues.append(
            CheckIssue("warn", iid, "parent drift between frontmatter and index (run `sq repair`)")
        )
    return issues


class MaintenanceMixin(ServiceCore):
    # ------------------------------------------------------------------ sync
    async def sync(self) -> None:
        """Regenerate all tool-owned managed files to the current version; stamp the config."""
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
        for it in await self.list_items(item_type=META_ROLE):
            await self._refresh_catalog_extra(it)
            for backend in backends:
                await backend.generate_role_entry(ctx, it, RoleDef.from_extra(it.extra))
            await self._regen_role_body(it)
        for it in await self.list_items(item_type=META_SKILL):
            for backend in backends:
                await backend.generate_skill_entry(ctx, it)
        skill_map = await self._skill_paths()
        ctx_with_skills = BackendContext(paths=self.paths, skill_paths=skill_map, spec=self.spec)
        roster = await self.roster()
        ops = await self.operators()
        for backend in backends:
            await backend.write_managed(ctx_with_skills, roster, ops)
        # Seed SKILL ids for any custom types declared in the spec (idempotent).
        await self.seed_custom_skills()
        await self._stamp_version(__version__)

    async def _refresh_catalog_extra(self, item: Item) -> None:
        """Merge current catalog fields into a predefined role's item extra.

        When a new field is added to :class:`RoleDef` (e.g. ``agreements``), existing items
        created before that field existed will lack it in their frontmatter.  Sync is the
        reconciliation point: for every predefined role we pull the authoritative definition
        from the catalog and merge its ``to_extra()`` output into the live item, then persist
        the updated frontmatter so subsequent reads see the new fields.

        Developer roles (``is_dev=True``) and custom items without a catalog entry are skipped —
        their extra is fully owned by the ``add_dev`` / ``create`` call-site.
        """
        slug = item.extra.get(X.SLUG, "")
        try:
            catalog_role = resolve_role(slug, self.paths.squad_dir)
        except RoleNotFoundError:
            return  # dev role or unknown slug — not catalog-managed
        catalog_extra = catalog_role.to_extra()
        changed = False
        for key, value in catalog_extra.items():
            if item.extra.get(key) != value:
                item.extra[key] = value
                changed = True
        if changed:
            await update_frontmatter(item_file(self.paths, item), item)

    async def _regen_role_body(self, item: Item) -> None:
        """Re-render the role template's body section into the existing role item file.

        Keeps the discussion region intact — only the ``<!-- sq:body -->`` region is touched.
        The frontmatter is not modified; no index transaction is needed (no metadata change).
        """
        rendered = render(
            "agents/role.md.j2", item=item, description=item.description, extra=item.extra
        )
        new_body_inner = sections.get_section(rendered, markers.BODY)
        if new_body_inner is None:
            return
        path = self.paths.abspath(item.path)
        existing = await _aio.read_text(path)
        updated = sections.replace_section(existing, markers.BODY, new_body_inner)
        await _aio.write_text(path, updated)

    async def _stamp_version(self, version: str) -> None:
        cfg = self.paths.config.model_copy(update={"squads_version": version})
        await _aio.write_text(self.paths.config_path, cfg.to_toml())

    async def _stamp_schema(self, version: str) -> None:
        cfg = self.paths.config.model_copy(update={"schema_version": version})
        await _aio.write_text(self.paths.config_path, cfg.to_toml())

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
        Each bundled skill receives a full ``Item`` of the ``skill`` meta-type with the
        meta-type profile (status ``Active``, no sub-entities), allocated through
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
        skill_prefix = prefix_for(META_SKILL, self.spec)
        skills_folder = self.paths.squad_dir / self.spec.items[META_SKILL].folder
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
                item_id = db.allocate_id(META_SKILL, prefix=skill_prefix)
                # Convention-correct filename from the allocated id.
                seq = number_for_id(item_id)
                # Padded filename stem — deliberately NOT the displayed item.id.
                new_name = f"{skill_prefix}-{seq:0{db.padding}d}-{slug}.md"
                squad_rel = self.paths.squad_relative(META_SKILL, new_name, spec=self.spec)
                item = Item(
                    sequence_id=db.counter,
                    type=META_SKILL,
                    prefix=skill_prefix,
                    title=slug,
                    slug=slug,
                    status=STATUS_ACTIVE,
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
                await _aio.write_text(convention_path, stamped)
                db.add(item)
                self.store._log(  # pyright: ignore[reportPrivateUsage]
                    "create",
                    item_id,
                    {"title": slug, "type": META_SKILL, "status": STATUS_ACTIVE},
                )
            # Remove the legacy slug-named file now that convention file is written.
            await _aio.path_unlink(legacy_path)
            # Rewrite each backend's .claude pointer to reference the convention-named body.
            # write_managed ran before seeding and wrote the pointer to the old slug path;
            # generate_skill_entry rewrites it to item.path (= SKILL-NNNNNN-slug.md).
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
        the same lexical-by-slug order as :func:`bundled_skill_slugs`, satisfying AC#6 (no
        SKILL-id churn for existing bundled skills — custom slugs sort independently into the
        full sorted slug space).

        Called from :meth:`sync` so custom skills are seeded whenever the squad is synced
        (not at init, which only knows about bundled types).
        """
        now = clock.now()
        seeded: list[Item] = []
        skill_prefix = prefix_for(META_SKILL, self.spec)
        skills_folder = self.paths.squad_dir / self.spec.items[META_SKILL].folder
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
                item_id = db.allocate_id(META_SKILL, prefix=skill_prefix)
                seq = number_for_id(item_id)
                # Padded filename stem — deliberately NOT the displayed item.id.
                new_name = f"{skill_prefix}-{seq:0{db.padding}d}-{slug}.md"
                squad_rel = self.paths.squad_relative(META_SKILL, new_name, spec=self.spec)
                item = Item(
                    sequence_id=db.counter,
                    type=META_SKILL,
                    prefix=skill_prefix,
                    title=slug,
                    slug=slug,
                    status=STATUS_ACTIVE,
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
                await _aio.write_text(convention_path, stamped)
                db.add(item)
                self.store._log(  # pyright: ignore[reportPrivateUsage]
                    "create",
                    item_id,
                    {"title": slug, "type": META_SKILL, "status": STATUS_ACTIVE},
                )
            # Remove the legacy slug-named file now that convention file is written.
            await _aio.path_unlink(legacy_path)
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
            if item_type == META_SKILL:
                # Convention files follow SKILL-*.md (post-migration / fresh init).
                # Also include legacy <slug>.md files so pre-migration squads can still be
                # repaired/checked (they will be silently skipped by callers that require an id).
                convention = sorted(folder.glob(f"{prefix}-*.md"))
                legacy = sorted(md for md in folder.glob("*.md") if not md.name.startswith(prefix))
                yield from ((item_type, md) for md in convention + legacy)
            else:
                yield from ((item_type, md) for md in sorted(folder.glob(f"{prefix}-*.md")))

    # ------------------------------------------------------------------ repair / renumber
    async def _rebuild_index_from_disk(
        self, *, previous_counter: int, previous_padding: int
    ) -> SquadsDB:
        """Scan every item file fresh and commit a rebuilt index — the core of :meth:`repair`,
        factored out so :meth:`renumber` can reuse it *without* repair's previous-snapshot /
        missing-file / reflog bookkeeping, which is specific to the ``sq repair`` verb (a
        renumber shift makes old sequence numbers vanish on purpose; repair's missing-file
        detector has no way to tell that apart from a genuine deletion, so `renumber` must not
        route through it — see :meth:`renumber`).

        ``previous_counter``/``previous_padding`` are the floors the rebuilt counter/padding
        must never regress below: the caller's most recent index read.
        """
        db = SquadsDB(squads_version=__version__, counter=0)
        max_n = 0
        max_filename_width = 0
        for item_type, md in self._iter_item_files():
            data = read_frontmatter(text=await _aio.read_text(md))
            if not data.get("id"):
                continue
            squad_rel = self.paths.squad_relative(item_type, md.name, spec=self.spec)
            item = Item.from_frontmatter(data, path=squad_rel)
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
            stem = md.stem  # e.g. "TASK-XXXXXX-fix-login"
            _, _, digits_slug = stem.partition("-")  # e.g. "000042-fix-login"
            digit_run = digits_slug.split("-", 1)[0]  # e.g. "000007"
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
        await self.store.overwrite(db)
        return db

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
        if self.store.exists():
            try:
                prev = await self.store.load()
                previous_counter = prev.counter
                previous_padding = prev.padding
                previous_seq_to_id = {it.sequence_id: it.id for it in prev.items.values()}
            except Exception:  # corrupt index — treat as empty
                pass

        if renumber:
            await self._renumber()

        db = await self._rebuild_index_from_disk(
            previous_counter=previous_counter, previous_padding=previous_padding
        )

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
            delta={"items": len(db.items), "missing": missing_ids},
            session_id=sid,
            parent_session_id=psid,
        )

        return RepairResult(db=db, missing_ids=missing_ids)

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

        renamed = 0
        for _item_type, md in self._iter_item_files():
            stem = md.stem  # e.g. "TASK-XXXXXX-fix-login"
            # Parse PREFIX and digit-run from the stem: PREFIX-<digits>-<slug>
            file_prefix, _, digits_slug = stem.partition("-")  # "TASK", "000042-fix-login"
            digit_run, _, slug_part = digits_slug.partition("-")  # "000042", "fix-login"
            if not digit_run.isdigit():
                continue  # malformed filename — skip
            seq = int(digit_run)
            # Build the new filename via the canonical formatter — no hand-rolled :0Nd here.
            # Use the prefix extracted from the filename (works for both built-in and custom
            # types). Padded filename stem — deliberately NOT item.id, which is unpadded;
            # formatted from the sequence number at new_padding instead.
            base = format_item_id(file_prefix, seq, new_padding)
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
            self.store._log(  # pyright: ignore[reportPrivateUsage]
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
            fid = read_frontmatter(text=await _aio.read_text(md)).get("id")
            if not fid:
                continue
            stem = md.name.removesuffix(".md")
            slug = stem.split("-", 2)[2] if stem.count("-") >= 2 else ""
            records.append((fid, md, item_type, slug, number_for_id(fid)))
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
                # Extract prefix from the existing ID (works for both built-in and custom types).
                fid_prefix = fid.split("-", 1)[0]
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
            fm, _ = sections.split_frontmatter(text)
            if fm:
                fm["sequence_id"] = number_for_id(new_id)
                await _aio.write_text(new_path, sections.replace_frontmatter(text, fm))

    async def _renumber(self) -> dict[str, str]:
        """Resolve duplicate global ID numbers from a merge: reassign + rewrite references."""
        records = await self._scan_records()
        padding = (await self.store.load()).padding if self.store.exists() else DEFAULT_ID_PADDING
        remap, renames = self._renumber_plan(records, padding)
        if not remap:
            return {}
        await self._apply_remap((md for _, md, *_ in records), remap, renames)
        return remap

    # ------------------------------------------------------------------ renumber (pre-merge)
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
            fid_prefix = fid.split("-", 1)[0]
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
            db = await self._rebuild_index_from_disk(
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
        from squads._overrides._service import check_override_issues

        index = await self.store.load()
        issues, on_disk = await self._scan_for_check()
        issues += self._check_reconciliation(index, on_disk)
        issues += self._check_items(index, on_disk)
        issues += self._check_subtask_stories(index)
        issues += self._check_subentity_status(index)
        issues += self._check_decisions(index)
        issues += await self._check_unwritten_subentity_bodies(index, on_disk)
        issues += await self._check_status_banners(index, on_disk)
        # Two override checks — version-drift warn + missing-marker error.
        issues += [
            CheckIssue(level, item, msg)
            for level, item, msg in check_override_issues(self.paths.squad_dir)
        ]
        # Verify each active backend's managed files are present.
        issues += self._check_backends()
        # Advisory title-length audit across all sub-entities.
        issues += self._check_subentity_title_lengths(index)
        return issues

    def _check_backends(self) -> list[CheckIssue]:
        """For each active (deduped) backend, verify its managed files exist on disk.

        Empty ``active_backends = []`` → nothing to check (sq-only squad is clean).
        Deactivated backends are not probed.
        """
        ctx = self._ctx
        issues: list[CheckIssue] = []
        for backend in self._backends():
            for rel_path in backend.managed_paths(ctx):
                full = ctx.root / rel_path
                if not full.exists():
                    issues.append(
                        CheckIssue(
                            "error",
                            rel_path,
                            f"managed file missing — run `sq sync` (backend: {backend.name})",
                        )
                    )
        return issues

    async def _scan_for_check(
        self,
    ) -> tuple[list[CheckIssue], dict[int, tuple[str, Path, dict[str, Any]]]]:
        """Scan every item file for marker issues and frontmatter.

        Returns ``(issues, on_disk)`` where ``on_disk`` is keyed by the item's **sequence
        number** (int) so reconciliation comparisons are width-tolerant — frontmatter ``id``
        fields keep their old width after ``sq migrate repad`` while the index reports the
        new width.  The stored tuple is ``(fid, path, frontmatter_data)`` so error messages
        can still name the original frontmatter ID.

        Skill files with no ``id`` in their frontmatter are silently skipped (pre-migration
        body files that have not yet been stamped as SKILL items).  Only ID-prefixed skill
        files (``SKILL-*.md``) without a valid frontmatter id are reported as errors.
        """
        issues: list[CheckIssue] = []
        on_disk: dict[int, tuple[str, Path, dict[str, Any]]] = {}
        skill_prefix = prefix_for(META_SKILL, self.spec) + "-"
        for item_type, md in self._iter_item_files():
            text = await _aio.read_text(md)
            issues += [CheckIssue("error", md.name, msg) for msg in _marker_issues(text)]
            data = read_frontmatter(text=text)
            fid = data.get("id")
            if not fid:
                # Slug-named skill body files (e.g. squads.md) are pre-migration: skip silently.
                # Only ID-prefixed files that are missing an id are a real error.
                if item_type == META_SKILL and not md.name.startswith(skill_prefix):
                    continue
                issues.append(CheckIssue("error", md.name, "file has no `id` in frontmatter"))
                continue
            seq = number_for_id(fid)
            on_disk[seq] = (fid, md, data)
        return issues, on_disk

    @staticmethod
    def _check_reconciliation(
        index: SquadsDB, on_disk: dict[int, tuple[str, Path, dict[str, Any]]]
    ) -> list[CheckIssue]:
        """Reconcile index items against on-disk files, comparing by sequence number.

        Using sequence numbers (not full-ID strings) makes the comparison width-tolerant:
        frontmatter ``id`` fields keep their old padding after ``sq migrate repad``, but the
        index reports the current-padding ID — both sides map to the same integer sequence.
        """
        index_seqs = {it.sequence_id for it in index.items.values()}
        issues = [
            CheckIssue("error", fid, "on disk but not in index (run `sq repair`)")
            for seq, (fid, _md, _data) in on_disk.items()
            if seq not in index_seqs
        ]
        issues += [
            CheckIssue("error", it.id, "in index but no markdown file found")
            for it in index.items.values()
            if it.sequence_id not in on_disk
        ]
        return issues

    def _check_items(
        self,
        index: SquadsDB,
        on_disk: dict[int, tuple[str, Path, dict[str, Any]]],
    ) -> list[CheckIssue]:
        issues: list[CheckIssue] = []
        registered = {
            r.extra.get(X.SLUG) for r in index.items.values() if self.spec.item_is_meta(r.type)
        }
        for item in index.items.values():
            iid = item.id
            if item.status not in self.spec.workflow_for(item.type).states:
                issues.append(
                    CheckIssue("error", iid, f"status {item.status!r} invalid for {item.type}")
                )
            parent = index.get(item.parent) if item.parent else None
            if item.parent and parent is None:
                issues.append(CheckIssue("error", iid, f"dangling parent {item.parent}"))
            elif parent is not None and not self.spec.parent_allowed(item.type, parent.type):
                msg = f"{self.spec.parent_hint(item.type)} (got {parent.type})"
                issues.append(CheckIssue("error", iid, msg))
            for r in item.refs:
                rid, kind = split_ref(r)
                if index.get(rid) is None:
                    issues.append(CheckIssue("warn", iid, f"dangling ref {rid}"))
                if kind not in VALID_REF_KINDS:
                    issues.append(
                        CheckIssue("warn", iid, f"unknown ref kind {kind!r} on edge → {rid}")
                    )
            for field in ("author", "assignee"):
                slug = getattr(item, field)
                if slug and slug not in registered:
                    issues.append(
                        CheckIssue(
                            "warn", iid, f"{field} {slug!r} is not a registered agent or operator"
                        )
                    )
            # Lookup by sequence number: frontmatter id width may differ from item.id after repad.
            disk_entry = on_disk.get(item.sequence_id)
            if disk_entry is not None:
                issues += _drift_issues(iid, item, disk_entry[2])
        return issues

    def _check_subtask_stories(self, index: SquadsDB) -> list[CheckIssue]:
        issues: list[CheckIssue] = []
        for item in index.items.values():
            if self.spec.item_subentity_kind(item.type) != "subtask":
                continue
            refs = [(s.local_id, s.story) for s in item.subentities if s.story]
            if not refs:
                continue
            parent = index.get(item.parent) if item.parent else None
            required_parent = self.spec.item_parent_required(item.type)
            if parent is None or (required_parent is not None and parent.type != required_parent):
                issues.append(
                    CheckIssue(
                        "error",
                        item.id,
                        "subtask maps to a user story but the task has no feature parent",
                    )
                )
                continue
            known = {s.local_id for s in parent.subentities}
            issues += [
                CheckIssue("error", item.id, f"subtask {stn} → {us} missing from {parent.id}")
                for stn, us in refs
                if us not in known
            ]
        return issues

    def _check_subentity_status(self, index: SquadsDB) -> list[CheckIssue]:
        issues: list[CheckIssue] = []
        for item in index.items.values():
            # Routed through the ACTIVE resolved spec (not the bundled-only SUBENTITY_KIND
            # constant) so a project override that renames/drops a type's subentity_kind is
            # reflected here too — a dropped/renamed type cleanly loses this check instead of
            # silently keeping (or silently missing) it.
            kind = self.spec.item_subentity_kind(item.type)
            if kind is None:
                continue
            valid = self.spec.subentity_workflow(kind).states
            issues += [
                CheckIssue("error", item.id, f"{kind} {s.local_id} has invalid status {s.status!r}")
                for s in item.subentities
                if s.status not in valid
            ]
        return issues

    def _check_decisions(self, index: SquadsDB) -> list[CheckIssue]:
        """Warn on Superseded decisions with no incoming ``supersedes`` edge.

        The ``supersedes`` target is stored as a ref string with whatever width it had when it
        was written — sequence-number comparison makes it width-tolerant after a repad.
        """
        issues: list[CheckIssue] = []
        # Collect sequence numbers of items that have an incoming supersedes edge.
        has_incoming_supersedes: set[int] = set()
        for it in index.items.values():
            for r in it.refs:
                rid, kind = split_ref(r)
                if kind == "supersedes":
                    has_incoming_supersedes.add(number_for_id(rid))
        for item in index.items.values():
            # Only types that declare a "supersedes" ref rule need the check.
            if not any(rr.kind == "supersedes" for rr in self.spec.item_ref_rules(item.type)):
                continue
            if (
                self.spec.status_role(item.status) == "superseded"
                and item.sequence_id not in has_incoming_supersedes
            ):
                issues.append(
                    CheckIssue(
                        "warn",
                        item.id,
                        "status is Superseded but no incoming supersedes edge found",
                    )
                )
        return issues

    async def _check_unwritten_subentity_bodies(
        self,
        index: SquadsDB,
        on_disk: dict[int, tuple[str, Path, dict[str, Any]]],
    ) -> list[CheckIssue]:
        """Advisory: flag any sub-entity whose stored body is still the kind's placeholder.

        Sub-entity body prose lives in the item file's ``:body`` marker region, not in the
        index/frontmatter, so — unlike the sibling index-only ``_check_*`` helpers — this one
        reads each sub-entity-bearing item's file text (reusing the path already resolved by
        :meth:`_scan_for_check`'s ``on_disk`` scan, keyed by sequence number). Exact-equality
        only: a body that has started to diverge from the placeholder, even by a single
        character, is treated as written and never flagged.

        Warn-level (advisory, non-blocking) — mirrors :meth:`_check_subentity_title_lengths`;
        no Draft→Ready gate is added.
        """
        issues: list[CheckIssue] = []
        for item in index.items.values():
            kind = self.spec.item_subentity_kind(item.type)
            if kind is None or not item.subentities:
                continue
            entry = on_disk.get(item.sequence_id)
            if entry is None:
                continue
            text = await _aio.read_text(entry[1])
            placeholder = discussion.body_placeholder(kind)
            for sub in item.subentities:
                body = sections.get_section(text, discussion.body_tag(kind, sub.local_id))
                if body is not None and body.strip() == placeholder:
                    issues.append(
                        CheckIssue(
                            "warn",
                            item.id,
                            f"{sub.local_id} body is unwritten (still the placeholder stub)",
                        )
                    )
        return issues

    async def _check_status_banners(
        self,
        index: SquadsDB,
        on_disk: dict[int, tuple[str, Path, dict[str, Any]]],
    ) -> list[CheckIssue]:
        """Advisory: flag an item whose body or description opens with a status banner.

        Mirrors :meth:`_check_unwritten_subentity_bodies`: body prose lives in the item file's
        ``:body`` marker region, not the index, so this reads the on-disk text (already scanned
        into ``on_disk``, keyed by sequence number) via ``sections.get_section`` — which returns
        only that one region, so the discussion section is never in scope. ``description`` comes
        straight from the index. Detection is anchored to the leading line only (see
        :func:`_opens_with_status_banner`), so it stays false-positive-averse by design.

        Warn-level (advisory, non-blocking) — mirrors :meth:`_check_subentity_title_lengths`: a
        self-declared lifecycle state is a maintenance smell (it can drift from the real
        frontmatter status), not a structural error worth blocking on.
        """
        issues: list[CheckIssue] = []
        for item in index.items.values():
            entry = on_disk.get(item.sequence_id)
            body = None
            if entry is not None:
                text = await _aio.read_text(entry[1])
                body = sections.get_section(text, markers.BODY)
            if _opens_with_status_banner(body):
                issues.append(
                    CheckIssue(
                        "warn",
                        item.id,
                        "body opens with a status/lifecycle banner"
                        " — move state to frontmatter or a dated discussion comment",
                    )
                )
            elif _opens_with_status_banner(item.description):
                issues.append(
                    CheckIssue(
                        "warn",
                        item.id,
                        "description opens with a status/lifecycle banner"
                        " — move state to frontmatter or a dated discussion comment",
                    )
                )
        return issues

    def _check_subentity_title_lengths(self, index: SquadsDB) -> list[CheckIssue]:
        """Advisory: flag sub-entity titles longer than TITLE_ADVISORY_MAX chars.

        Read-only — does not mutate any item. Each over-long title emits a warn-level
        CheckIssue (advisory only; does not affect the exit code). Fires strictly above
        the threshold (> 120); titles at or below 120 are silent.
        """
        issues: list[CheckIssue] = []
        for item in index.items.values():
            kind = self.spec.item_subentity_kind(item.type)
            if kind is None:
                continue
            issues.extend(
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
            )
        return issues
