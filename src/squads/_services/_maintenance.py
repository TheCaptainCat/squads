"""Whole-squad maintenance: sync managed files, repair/renumber the index, check, migrate."""

from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from squads import __version__
from squads import _sections as sections
from squads._errors import RoleNotFoundError
from squads._index._resolver import item_file
from squads._itemfile import read_frontmatter, rewrite_ids, update_frontmatter
from squads._migrations._registry import MIGRATIONS, Migration
from squads._models import _markers as markers
from squads._models._enums import ItemType
from squads._models._extras import ExtraKey as X
from squads._models._index import SquadsDB
from squads._models._item import VALID_REF_KINDS, Item, split_ref
from squads._models._schema import SCHEMA_VERSION, schema_tuple
from squads._paths import number_for_id
from squads._rendering._engine import render
from squads._roles._catalog import RoleDef, role_by_slug
from squads._services._base import SUBENTITY_KIND, ServiceCore
from squads._services._results import CheckIssue, RepairResult
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
            backend.generate_role_pointer(ctx, it, RoleDef.from_extra(it.extra))
            self._regen_role_body(it)
        for it in self.list_items(item_type=ItemType.SKILL):
            backend.generate_skill_pointer(ctx, it)
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
            catalog_role = role_by_slug(slug)
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
        #  (a) preserve the high-water mark of the counter, and
        #  (b) report items that were indexed but whose files have gone missing.
        previous_counter = 0
        previous_ids: set[str] = set()
        if self.store.exists():
            try:
                prev = self.store.load()
                previous_counter = prev.counter
                previous_ids = {it.id for it in prev.items.values()}
            except Exception:  # corrupt index — treat as empty
                pass

        if renumber:
            self._renumber()

        db = SquadsDB(squads_version=__version__, counter=0)
        found_ids: set[str] = set()
        max_n = 0
        for item_type, md in self._iter_item_files():
            data = read_frontmatter(md)
            if not data.get("id"):
                continue
            squad_rel = self.paths.squad_relative(item_type, md.name)
            item = Item.from_frontmatter(data, path=squad_rel)
            db.add(item)
            found_ids.add(item.id)
            max_n = max(max_n, number_for_id(item.id))

        # Never let the counter regress: keep whichever is higher — the previous high-water mark
        # or the maximum sequence number found on disk.
        db.counter = max(previous_counter, max_n)
        self.store.overwrite(db)

        missing_ids = sorted(previous_ids - found_ids)
        return RepairResult(db=db, missing_ids=missing_ids)

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
    ) -> tuple[dict[str, str], list[tuple[Path, ItemType, str, str]]]:
        """Assign fresh numbers to ID-number collisions. Returns (id remap, files to rename)."""
        by_number: dict[int, list[_FileRec]] = {}
        for rec in records:
            by_number.setdefault(rec[4], []).append(rec)
        next_free = max(by_number, default=0) + 1
        remap: dict[str, str] = {}
        renames: list[tuple[Path, ItemType, str, str]] = []
        for number in sorted(by_number):
            for fid, md, item_type, slug, _ in sorted(by_number[number], key=lambda r: r[0])[1:]:
                new_id = f"{item_type.prefix}-{next_free:06d}"
                next_free += 1
                remap[fid] = new_id
                renames.append((md, item_type, slug, new_id))
        return remap, renames

    def _renumber(self) -> dict[str, str]:
        """Resolve duplicate global ID numbers from a merge: reassign + rewrite references."""
        records = self._scan_records()
        remap, renames = self._renumber_plan(records)
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

    # ------------------------------------------------------------------ check
    def check(self) -> list[CheckIssue]:
        index = self.store.load()
        issues, on_disk = self._scan_for_check()
        issues += self._check_reconciliation(index, on_disk)
        issues += self._check_items(index, on_disk)
        issues += self._check_subtask_stories(index)
        issues += self._check_subentity_status(index)
        issues += self._check_decisions(index)
        return issues

    def _scan_for_check(self) -> tuple[list[CheckIssue], dict[str, tuple[Path, dict[str, Any]]]]:
        issues: list[CheckIssue] = []
        on_disk: dict[str, tuple[Path, dict[str, Any]]] = {}
        for _, md in self._iter_item_files():
            text = md.read_text(encoding="utf-8")
            issues += [CheckIssue("error", md.name, msg) for msg in _marker_issues(text)]
            data = read_frontmatter(text=text)
            fid = data.get("id")
            if not fid:
                issues.append(CheckIssue("error", md.name, "file has no `id` in frontmatter"))
                continue
            on_disk[fid] = (md, data)
        return issues, on_disk

    @staticmethod
    def _check_reconciliation(
        index: SquadsDB, on_disk: dict[str, tuple[Path, dict[str, Any]]]
    ) -> list[CheckIssue]:
        index_ids = {it.id for it in index.items.values()}
        issues = [
            CheckIssue("error", fid, "on disk but not in index (run `sq repair`)")
            for fid in on_disk
            if fid not in index_ids
        ]
        issues += [
            CheckIssue("error", it.id, "in index but no markdown file found")
            for it in index.items.values()
            if it.id not in on_disk
        ]
        return issues

    @staticmethod
    def _check_items(
        index: SquadsDB, on_disk: dict[str, tuple[Path, dict[str, Any]]]
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
            if iid in on_disk:
                issues += _drift_issues(iid, item, on_disk[iid][1])
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
        """Warn on Superseded decisions with no incoming ``supersedes`` edge."""
        from squads._models._enums import Status

        issues: list[CheckIssue] = []
        # Collect decision ids that have an incoming supersedes edge from any item.
        has_incoming_supersedes: set[str] = set()
        for it in index.items.values():
            for r in it.refs:
                rid, kind = split_ref(r)
                if kind == "supersedes":
                    has_incoming_supersedes.add(rid)
        for item in index.items.values():
            if item.type is not ItemType.DECISION:
                continue
            if item.status is Status.SUPERSEDED and item.id not in has_incoming_supersedes:
                issues.append(
                    CheckIssue(
                        "warn",
                        item.id,
                        "status is Superseded but no incoming supersedes edge found",
                    )
                )
        return issues
