"""Whole-squad maintenance: sync managed files, repair/renumber the index, check, migrate."""

from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from squads import __version__
from squads import _actor as actor
from squads import _clock as clock
from squads import _sections as sections
from squads._errors import RoleNotFoundError, SquadsError
from squads._index._reflog import append_line, reflog_path
from squads._index._resolver import item_file
from squads._itemfile import read_frontmatter, rewrite_ids, update_frontmatter
from squads._migrations._registry import MIGRATIONS, Migration
from squads._models import _markers as markers
from squads._models._enums import ItemType
from squads._models._extras import ExtraKey as X
from squads._models._index import SquadsDB
from squads._models._item import (
    DEFAULT_ID_PADDING,
    VALID_REF_KINDS,
    Item,
    format_item_id,
    split_ref,
)
from squads._models._schema import SCHEMA_VERSION, schema_tuple
from squads._paths import number_for_id
from squads._rendering._engine import render
from squads._roles._catalog import RoleDef
from squads._roles._resolver import resolve_role
from squads._services._base import SUBENTITY_KIND, ServiceCore
from squads._services._results import CheckIssue, ReflogEntry, RepairResult
from squads._workflow import parent_allowed, parent_hint, subentity_workflow, workflow_for

# (id, markdown path, type, slug, number) — one scanned item file, used by repair/renumber.
type _FileRec = tuple[str, Path, ItemType, str, int]


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
    if fdata.get("status") != item.status.value:
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
    def sync(self) -> None:
        """Regenerate all tool-owned managed files to the current version; stamp the config."""
        backend = self._backend()
        ctx = self._ctx
        backend.ensure_scaffold(ctx)
        for it in self.list_items(item_type=ItemType.ROLE):
            self._refresh_catalog_extra(it)
            backend.generate_role_entry(ctx, it, RoleDef.from_extra(it.extra))
            self._regen_role_body(it)
        for it in self.list_items(item_type=ItemType.SKILL):
            backend.generate_skill_entry(ctx, it)
        backend.write_managed(ctx, self.roster(), self.operators())
        self._stamp_version(__version__)

    def _refresh_catalog_extra(self, item: Item) -> None:
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
            update_frontmatter(item_file(self.paths, item), item)

    def _regen_role_body(self, item: Item) -> None:
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
        existing = path.read_text(encoding="utf-8")
        updated = sections.replace_section(existing, markers.BODY, new_body_inner)
        path.write_text(updated, encoding="utf-8")

    def _stamp_version(self, version: str) -> None:
        cfg = self.paths.config.model_copy(update={"squads_version": version})
        self.paths.config_path.write_text(cfg.to_toml(), encoding="utf-8")

    def _stamp_schema(self, version: str) -> None:
        cfg = self.paths.config.model_copy(update={"schema_version": version})
        self.paths.config_path.write_text(cfg.to_toml(), encoding="utf-8")

    # ------------------------------------------------------------------ migrations
    def run_pending_migrations(self) -> list[Migration]:
        """Apply each migration whose target schema exceeds the on-disk one, in order.

        Rebuilds the index from the migrated frontmatter and stamps the new schema version.
        Returns the applied :class:`Migration` records (empty when already current).
        """
        disk = self.paths.config.schema_version
        applied = [m for m in MIGRATIONS if schema_tuple(m.to_schema) > schema_tuple(disk)]
        for m in applied:
            m.run(self.paths)
        if applied:
            self.repair()
            self._stamp_schema(SCHEMA_VERSION)
            # Reflog: log the migration batch after repair has completed.
            append_line(
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
            )
        return applied

    # ------------------------------------------------------------------ scan helpers
    def _iter_item_files(self) -> Iterator[tuple[ItemType, Path]]:
        """Yield (item_type, markdown path) for every item file across the type folders."""
        for item_type in ItemType:
            folder = self.paths.folder_for(item_type)
            if not folder.is_dir():
                continue
            yield from ((item_type, md) for md in sorted(folder.glob(f"{item_type.prefix}-*.md")))

    # ------------------------------------------------------------------ repair / renumber
    def repair(self, *, renumber: bool = False) -> RepairResult:
        # Snapshot the previous index (if any) before rebuilding, so we can:
        #  (a) preserve the high-water mark of the counter,
        #  (b) preserve the padding floor (ADR-000104), and
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
                prev = self.store.load()
                previous_counter = prev.counter
                previous_padding = prev.padding
                previous_seq_to_id = {it.sequence_id: it.id for it in prev.items.values()}
            except Exception:  # corrupt index — treat as empty
                pass

        if renumber:
            self._renumber()

        db = SquadsDB(squads_version=__version__, counter=0)
        found_seqs: set[int] = set()
        max_n = 0
        max_filename_width = 0
        for item_type, md in self._iter_item_files():
            data = read_frontmatter(md)
            if not data.get("id"):
                continue
            squad_rel = self.paths.squad_relative(item_type, md.name)
            item = Item.from_frontmatter(data, path=squad_rel)
            db.add(item)
            found_seqs.add(item.sequence_id)
            max_n = max(max_n, number_for_id(item.id))
            # Derive the filename digit-run width (PREFIX-<digits>-<slug>.md).
            # The filename, not the frontmatter id, is the in-corpus record of a repad.
            stem = md.stem  # e.g. "TASK-000007-fix-login"
            _, _, digits_slug = stem.partition("-")  # e.g. "000007-fix-login"
            digit_run = digits_slug.split("-", 1)[0]  # e.g. "000007"
            if digit_run.isdigit():
                max_filename_width = max(max_filename_width, len(digit_run))

        # Never let the counter regress: keep whichever is higher — the previous high-water mark
        # or the maximum sequence number found on disk.
        db.counter = max(previous_counter, max_n)
        # Padding (ADR-000104): max(stored_floor, corpus_max_filename_width).
        # The stored value is the floor; the filename scan is the recompute.
        # Backfill: previous_padding defaults to DEFAULT_ID_PADDING (6) for pre-existing squads.
        # F3 (REV-000105): collapsed to a single max() — the <6 guard can never fire when
        # previous_padding >= DEFAULT_ID_PADDING (always true via the model default), and the
        # >0 conditional arm was a no-op because max(floor, 0) == floor already.
        db.padding = max(previous_padding, max_filename_width)
        self.store.overwrite(db)

        missing_seqs = sorted(previous_seq_to_id.keys() - found_seqs)
        missing_ids = [previous_seq_to_id[s] for s in missing_seqs]

        # Reflog: append after overwrite (repair uses overwrite, not transaction).
        append_line(
            reflog_path(self.paths.squad_dir),
            ts=clock.iso(clock.now()),
            actor=actor.current_actor(),
            op="repair",
            target="",
            delta={"items": len(db.items), "missing": missing_ids},
        )

        return RepairResult(db=db, missing_ids=missing_ids)

    # ------------------------------------------------------------------ repad
    def repad(self, new_padding: int) -> int:
        """Raise the squad's ID padding to ``new_padding`` and rename every item file.

        One-way, irreversible format bump (FEAT-000027, ADR-000104):

        - Refuses if ``new_padding`` <= the current stored padding (padding never shrinks).
        - Renames every item file across all type folders to
          ``PREFIX-<seq zero-padded to new_padding>-<slug>.md``.
        - File *contents* are left byte-untouched — only filenames change.
        - Calls :meth:`repair` afterwards to rebuild the index with the new padding stored and
          all ``path`` fields updated.

        Returns the number of files renamed.
        """
        db = self.store.load()
        current = db.padding
        if new_padding <= current:
            raise SquadsError(
                f"new padding {new_padding} must be greater than the current padding {current}; "
                "padding can only increase (one-way format bump)"
            )

        renamed = 0
        for item_type, md in self._iter_item_files():
            stem = md.stem  # e.g. "TASK-000007-fix-login"
            # Parse digit-run from the stem: PREFIX-<digits>-<slug>
            _, _, digits_slug = stem.partition("-")  # "000007-fix-login"
            digit_run, _, slug_part = digits_slug.partition("-")  # "000007", "fix-login"
            if not digit_run.isdigit():
                continue  # malformed filename — skip
            seq = int(digit_run)
            # Build the new filename via the canonical formatter — no hand-rolled :0Nd here.
            base = format_item_id(item_type.prefix, seq, new_padding)
            new_name = f"{base}-{slug_part}.md" if slug_part else f"{base}.md"
            new_path = md.parent / new_name
            if new_path != md:
                md.rename(new_path)
                renamed += 1

        # Write the new padding into the index before calling repair, so repair's stored-floor
        # logic picks it up and writes it back out.
        with self.store.transaction() as _db:
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
        self.repair()
        return renamed

    def _scan_records(self) -> list[_FileRec]:
        records: list[_FileRec] = []
        for item_type, md in self._iter_item_files():
            fid = read_frontmatter(md).get("id")
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
    ) -> tuple[dict[str, str], list[tuple[Path, ItemType, str, str]]]:
        """Assign fresh numbers to ID-number collisions. Returns (id remap, files to rename).

        ``padding`` is the squad's current padding (from ``db.padding``); all minted IDs use it
        so renumber on a width-7 squad does not produce width-6 filenames (F1, REV-000105).
        """
        by_number: dict[int, list[_FileRec]] = {}
        for rec in records:
            by_number.setdefault(rec[4], []).append(rec)
        next_free = max(by_number, default=0) + 1
        remap: dict[str, str] = {}
        renames: list[tuple[Path, ItemType, str, str]] = []
        for number in sorted(by_number):
            for fid, md, item_type, slug, _ in sorted(by_number[number], key=lambda r: r[0])[1:]:
                new_id = format_item_id(item_type.prefix, next_free, padding)
                next_free += 1
                remap[fid] = new_id
                renames.append((md, item_type, slug, new_id))
        return remap, renames

    def _renumber(self) -> dict[str, str]:
        """Resolve duplicate global ID numbers from a merge: reassign + rewrite references."""
        records = self._scan_records()
        padding = self.store.load().padding if self.store.exists() else DEFAULT_ID_PADDING
        remap, renames = self._renumber_plan(records, padding)
        if not remap:
            return {}
        # rewrite every reference to a remapped id across all files (frontmatter + body + inline)
        rewrite_ids([md for _, md, *_ in records], remap)
        # rename the files whose own id changed, and resync their stored sequence_id
        for old_path, item_type, slug, new_id in renames:
            new_name = f"{new_id}-{slug}.md" if slug else f"{new_id}.md"
            new_path = self.paths.folder_for(item_type) / new_name
            old_path.rename(new_path)
            text = new_path.read_text(encoding="utf-8")
            fm, _ = sections.split_frontmatter(text)
            if fm:
                fm["sequence_id"] = number_for_id(new_id)
                new_path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")
        return remap

    # ------------------------------------------------------------------ reflog read
    def read_reflog(
        self,
        *,
        item: str | None = None,
        actor_filter: str | None = None,
        op_filter: str | None = None,
        since: str | None = None,
        tail: int | None = None,
    ) -> list[ReflogEntry]:
        """Read and filter the reflog (TASK-000113 / ADR-000117 reader contract).

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

        raw = read_lines(reflog_path(self.paths.squad_dir))

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
                )
            )

        if tail is not None:
            out = out[-tail:]
        return out

    # ------------------------------------------------------------------ check
    def check(self) -> list[CheckIssue]:
        from squads._overrides._service import check_override_issues

        index = self.store.load()
        issues, on_disk = self._scan_for_check()
        issues += self._check_reconciliation(index, on_disk)
        issues += self._check_items(index, on_disk)
        issues += self._check_subtask_stories(index)
        issues += self._check_subentity_status(index)
        issues += self._check_decisions(index)
        # ADR-000085 §3: two override checks — version-drift warn + missing-marker error.
        issues += [
            CheckIssue(level, item, msg)
            for level, item, msg in check_override_issues(self.paths.squad_dir)
        ]
        return issues

    def _scan_for_check(
        self,
    ) -> tuple[list[CheckIssue], dict[int, tuple[str, Path, dict[str, Any]]]]:
        """Scan every item file for marker issues and frontmatter.

        Returns ``(issues, on_disk)`` where ``on_disk`` is keyed by the item's **sequence
        number** (int) so reconciliation comparisons are width-tolerant — frontmatter ``id``
        fields keep their old width after ``sq migrate repad`` while the index reports the
        new width.  The stored tuple is ``(fid, path, frontmatter_data)`` so error messages
        can still name the original frontmatter ID.
        """
        issues: list[CheckIssue] = []
        on_disk: dict[int, tuple[str, Path, dict[str, Any]]] = {}
        for _, md in self._iter_item_files():
            text = md.read_text(encoding="utf-8")
            issues += [CheckIssue("error", md.name, msg) for msg in _marker_issues(text)]
            data = read_frontmatter(text=text)
            fid = data.get("id")
            if not fid:
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

    @staticmethod
    def _check_items(
        index: SquadsDB, on_disk: dict[int, tuple[str, Path, dict[str, Any]]]
    ) -> list[CheckIssue]:
        issues: list[CheckIssue] = []
        registered = {
            r.extra.get(X.SLUG)
            for r in index.items.values()
            if r.type in (ItemType.ROLE, ItemType.OPERATOR)
        }
        for item in index.items.values():
            iid = item.id
            if item.status not in workflow_for(item.type).states:
                issues.append(
                    CheckIssue(
                        "error", iid, f"status {item.status.value!r} invalid for {item.type.value}"
                    )
                )
            parent = index.get(item.parent) if item.parent else None
            if item.parent and parent is None:
                issues.append(CheckIssue("error", iid, f"dangling parent {item.parent}"))
            elif parent is not None and not parent_allowed(item.type, parent.type):
                msg = f"{parent_hint(item.type)} (got {parent.type.value})"
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

    @staticmethod
    def _check_subtask_stories(index: SquadsDB) -> list[CheckIssue]:
        issues: list[CheckIssue] = []
        for item in index.items.values():
            if item.type is not ItemType.TASK:
                continue
            refs = [(s.local_id, s.story) for s in item.subentities if s.story]
            if not refs:
                continue
            parent = index.get(item.parent) if item.parent else None
            if parent is None or parent.type is not ItemType.FEATURE:
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

    @staticmethod
    def _check_subentity_status(index: SquadsDB) -> list[CheckIssue]:
        issues: list[CheckIssue] = []
        for item in index.items.values():
            kind = SUBENTITY_KIND.get(item.type)
            if kind is None:
                continue
            valid = {s.value for s in subentity_workflow(kind).states}
            issues += [
                CheckIssue(
                    "error", item.id, f"{kind} {s.local_id} has invalid status {s.status.value!r}"
                )
                for s in item.subentities
                if s.status.value not in valid
            ]
        return issues

    @staticmethod
    def _check_decisions(index: SquadsDB) -> list[CheckIssue]:
        """Warn on Superseded decisions with no incoming ``supersedes`` edge.

        The ``supersedes`` target is stored as a ref string with whatever width it had when it
        was written — sequence-number comparison makes it width-tolerant after a repad.
        """
        from squads._models._enums import Status

        issues: list[CheckIssue] = []
        # Collect sequence numbers of decisions that have an incoming supersedes edge.
        has_incoming_supersedes: set[int] = set()
        for it in index.items.values():
            for r in it.refs:
                rid, kind = split_ref(r)
                if kind == "supersedes":
                    has_incoming_supersedes.add(number_for_id(rid))
        for item in index.items.values():
            if item.type is not ItemType.DECISION:
                continue
            if item.status is Status.SUPERSEDED and item.sequence_id not in has_incoming_supersedes:
                issues.append(
                    CheckIssue(
                        "warn",
                        item.id,
                        "status is Superseded but no incoming supersedes edge found",
                    )
                )
        return issues
