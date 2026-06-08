"""Orchestration: the logic behind each CLI command.

Holds the rule that the ``.md`` frontmatter is the durable source of truth and the
``.squads.json`` index is kept in sync (and is rebuildable from those files).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from squads import __version__, clock, discussion, sections
from squads.backends import AgentBackend, BackendContext, get_backend
from squads.backends.base import RoleView
from squads.errors import (
    AlreadyInitializedError,
    InvalidTransitionError,
    ItemNotFoundError,
    SquadsError,
)
from squads.index import IndexStore
from squads.index.resolver import item_file, require_item
from squads.itemfile import update_frontmatter, write_new
from squads.models import FOLDER_BY_TYPE, Item, ItemType, SquadsConfig, SquadsDB, Status, markers
from squads.models.config import CONFIG_FILENAME
from squads.paths import SquadPaths, number_for_id, resolve
from squads.rendering import render
from squads.roles.catalog import RoleDef, resolve_roles, role_by_slug
from squads.util import slugify

_AGENT_TYPES = {ItemType.ROLE, ItemType.SKILL}

# (id, markdown path, type, slug, number) — one scanned item file, used by repair/renumber.
type _FileRec = tuple[str, Path, ItemType, str, int]


def _template_for(item_type: ItemType) -> str:
    if item_type is ItemType.ROLE:
        return "agents/role.md.j2"
    if item_type is ItemType.SKILL:
        return "agents/skill.md.j2"
    return f"items/{item_type.value}.md.j2"


def _marker_issues(text: str) -> list[str]:
    """Detect unbalanced or duplicated sq markers in a file."""
    from collections import Counter

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


def _ref_kinds(item: Item) -> dict[str, str]:
    """The item's per-edge ``ref_kinds`` map, typed (empty if absent/malformed)."""
    rk = item.extra.get("ref_kinds")
    return cast("dict[str, str]", rk) if isinstance(rk, dict) else {}


@dataclass
class CreateResult:
    item: Item
    path: Path


@dataclass
class CheckIssue:
    level: str  # "error" | "warn"
    item: str  # item id or filename ("" if global)
    message: str


@dataclass
class BlockResult:
    """Where an agent should write a scaffolded story/subtask body."""

    local_id: str
    path: Path
    body_tag: str
    start_line: int | None
    end_line: int | None


class Service:
    def __init__(self, paths: SquadPaths):
        self.paths = paths
        self.store = IndexStore(paths.index_path, paths.lock_path)

    # ------------------------------------------------------------------ backend
    @property
    def _ctx(self) -> BackendContext:
        return BackendContext(paths=self.paths, version=__version__)

    def _backend(self) -> AgentBackend:
        return get_backend(self.paths.config.default_backend)

    def scaffold_backend(self) -> None:
        """Public entry for init(): create backend scaffolding."""
        self._backend().ensure_scaffold(self._ctx)

    # ------------------------------------------------------------------ create
    def create(
        self,
        item_type: ItemType,
        title: str,
        *,
        description: str = "",
        parent: str | None = None,
        labels: list[str] | None = None,
        refs: list[str] | None = None,
        assignee: str | None = None,
        extra: dict[str, Any] | None = None,
        status: Status | None = None,
        slug: str | None = None,
    ) -> CreateResult:
        from squads.workflow import initial_status

        slug = slug or slugify(title)
        now = clock.now()
        with self.store.transaction() as db:
            if parent:
                self._check_parent(db, item_type, parent)
            item_id = db.allocate_id(item_type)
            filename = f"{item_id}-{slug}.md"
            squad_rel = self.paths.squad_relative(item_type, filename)
            item = Item(
                id=item_id,
                type=item_type,
                title=title,
                slug=slug,
                status=status or initial_status(item_type),
                description=description,
                parent=parent,
                assignee=assignee,
                labels=labels or [],
                refs=refs or [],
                path=squad_rel,
                created_at=now,
                updated_at=now,
                extra=extra or {},
            )
            body = render(
                _template_for(item_type), item=item, description=description, extra=item.extra
            )
            write_new(self.paths.abspath(squad_rel), item, body)
            db.add(item)
        return CreateResult(item=item, path=self.paths.abspath(squad_rel))

    # ------------------------------------------------------------------ read
    def get(self, item_id: str) -> Item:
        return require_item(self.store.load(), item_id)

    def list(
        self,
        *,
        type: ItemType | None = None,
        status: Status | None = None,
        parent: str | None = None,
        label: str | None = None,
        assignee: str | None = None,
    ) -> list[Item]:
        items = self.store.load().items.values()
        out: list[Item] = []
        for it in items:
            if type and it.type is not type:
                continue
            if status and it.status is not status:
                continue
            if parent and it.parent != parent:
                continue
            if label and label not in it.labels:
                continue
            if assignee and it.assignee != assignee:
                continue
            out.append(it)
        return sorted(out, key=lambda i: number_for_id(i.id))

    def children(self, parent_id: str) -> list[Item]:
        return self.list(parent=parent_id)

    # ------------------------------------------------------------------ update / status
    def set_status(self, item_id: str, status: Status, *, force: bool = False) -> Item:
        from squads.workflow import can_transition

        with self.store.transaction() as db:
            item = require_item(db, item_id)
            if (
                not force
                and item.status != status
                and not can_transition(item.type, item.status, status)
            ):
                raise InvalidTransitionError(
                    f"{item.type.value} cannot move {item.status.value} → {status.value}"
                    " (use --force to override)"
                )
            item.status = status
            item.updated_at = clock.now()
            update_frontmatter(item_file(self.paths, item), item)
        return item

    def update(
        self,
        item_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        assignee: str | None = None,
        add_labels: list[str] | None = None,
        rm_labels: list[str] | None = None,
    ) -> Item:
        with self.store.transaction() as db:
            item = require_item(db, item_id)
            if title is not None and title != item.title:
                self._rename(item, title)
            if description is not None:
                item.description = description
            if assignee is not None:
                item.assignee = assignee or None
            if add_labels:
                for lbl in add_labels:
                    if lbl not in item.labels:
                        item.labels.append(lbl)
            if rm_labels:
                item.labels = [lab for lab in item.labels if lab not in rm_labels]
            item.updated_at = clock.now()
            update_frontmatter(item_file(self.paths, item), item)
        return item

    def _rename(self, item: Item, new_title: str) -> None:
        new_slug = slugify(new_title)
        old_path = item_file(self.paths, item)
        new_rel = self.paths.squad_relative(item.type, f"{item.id}-{new_slug}.md")
        new_path = self.paths.abspath(new_rel)
        if old_path.exists() and old_path != new_path:
            old_path.rename(new_path)
        item.title = new_title
        item.slug = new_slug
        item.path = new_rel

    def _check_parent(self, db: SquadsDB, child_type: ItemType, parent_id: str) -> None:
        from squads.workflow import parent_allowed, parent_hint

        parent = db.get(parent_id)
        if parent is None:
            raise ItemNotFoundError(f"parent {parent_id!r} does not exist")
        if not parent_allowed(child_type, parent.type):
            raise SquadsError(f"{parent_hint(child_type)} (got {parent.type.value})")

    # ------------------------------------------------------------------ link
    def link(self, child_id: str, parent_id: str) -> Item:
        with self.store.transaction() as db:
            child = require_item(db, child_id)
            self._check_parent(db, child.type, parent_id)
            child.parent = parent_id
            child.updated_at = clock.now()
            update_frontmatter(item_file(self.paths, child), child)
        return child

    def unlink(self, child_id: str) -> Item:
        with self.store.transaction() as db:
            child = require_item(db, child_id)
            child.parent = None
            child.updated_at = clock.now()
            update_frontmatter(item_file(self.paths, child), child)
        return child

    # ------------------------------------------------------------------ comments
    def comment(
        self,
        item_id: str,
        messages: list[str],
        *,
        as_slug: str = "operator",
        story: str | None = None,
        subtask: str | None = None,
    ) -> Item:
        if not messages:
            raise SquadsError("a comment needs at least one -m message")
        item = self.get(item_id)
        path = item_file(self.paths, item)
        tag = self._discussion_tag(story, subtask)
        text = path.read_text(encoding="utf-8")
        if not sections.has_section(text, tag):
            raise SquadsError(f"no discussion section {tag!r} in {item_id} (was it scaffolded?)")
        entry = discussion.format_comment(clock.iso(clock.now()), self.author(as_slug), messages)
        path.write_text(sections.append_to_section(text, tag, entry), encoding="utf-8")
        with self.store.transaction() as db:
            it = require_item(db, item_id)
            it.updated_at = clock.now()
            update_frontmatter(path, it)
        return item

    @staticmethod
    def _discussion_tag(story: str | None, subtask: str | None) -> str:
        if story and subtask:
            raise SquadsError("use either --story or --subtask, not both")
        if story:
            return markers.discussion_tag(markers.story_tag(story))
        if subtask:
            return markers.discussion_tag(markers.subtask_tag(subtask))
        return markers.DISCUSSION

    def author(self, slug: str) -> str:
        if slug == "operator":
            return "Operator"
        role_item = self._role_item(slug)
        if role_item is not None:
            return role_item.extra.get("full_name", slug)
        try:
            return role_by_slug(slug).full_name
        except SquadsError:
            return slug

    # ------------------------------------------------------------------ stories / subtasks
    def add_story(self, feature_id: str, title: str = "") -> BlockResult:
        return self._add_block(feature_id, ItemType.FEATURE, markers.STORIES, "story", title)

    def add_subtask(
        self, task_id: str, title: str = "", *, story: str | None = None
    ) -> BlockResult:
        if story:
            self._validate_subtask_story(task_id, story)
        return self._add_block(task_id, ItemType.TASK, markers.SUBTASKS, "subtask", title, story)

    def _validate_subtask_story(self, task_id: str, story: str) -> None:
        task = self.get(task_id)
        if not task.parent:
            raise SquadsError(
                f"{task_id} has no feature parent; set one before mapping a subtask to {story}"
            )
        parent = self.get(task.parent)
        if parent.type is not ItemType.FEATURE:
            raise SquadsError(f"{task_id}'s parent is a {parent.type.value}, not a feature")
        stories = {sid for sid, _ in discussion.list_blocks(self._read(parent.id), "story")}
        if story not in stories:
            raise SquadsError(f"user story {story} not found in {parent.id}")

    def _add_block(
        self,
        item_id: str,
        expect: ItemType,
        container: str,
        kind: str,
        title: str,
        story: str | None = None,
    ) -> BlockResult:
        item = self.get(item_id)
        if item.type is not expect:
            raise SquadsError(f"{item_id} is a {item.type.value}; {kind}s live on a {expect.value}")
        path = item_file(self.paths, item)
        content = path.read_text(encoding="utf-8")
        if not sections.has_section(content, container):
            raise SquadsError(f"no {container} section in {item_id}")
        local_id = discussion.next_local_id(content, kind)
        block = (
            discussion.build_story_block(local_id, title)
            if kind == "story"
            else discussion.build_subtask_block(local_id, title, story=story)
        )
        path.write_text(sections.append_to_section(content, container, block), encoding="utf-8")
        self._bump(item_id)
        btag = discussion.body_tag(kind, local_id)
        span = sections.region_lines(path.read_text(encoding="utf-8"), btag)
        return BlockResult(
            local_id=local_id,
            path=path,
            body_tag=btag,
            start_line=span[0] if span else None,
            end_line=span[1] if span else None,
        )

    def list_stories(self, feature_id: str) -> list[tuple[str, str]]:
        return discussion.list_blocks(self._read(feature_id), "story")

    def list_subtasks(self, task_id: str) -> list[tuple[str, str]]:
        return discussion.list_blocks(self._read(task_id), "subtask")

    def set_subtask_done(self, task_id: str, local_id: str, *, done: bool = True) -> None:
        item = self.get(task_id)
        path = item_file(self.paths, item)
        try:
            new = discussion.set_subtask_checkbox(path.read_text(encoding="utf-8"), local_id, done)
        except KeyError:
            raise SquadsError(f"no subtask {local_id} in {task_id}") from None
        path.write_text(new, encoding="utf-8")
        self._bump(task_id)

    def _read(self, item_id: str) -> str:
        return item_file(self.paths, self.get(item_id)).read_text(encoding="utf-8")

    def _bump(self, item_id: str) -> None:
        with self.store.transaction() as db:
            it = require_item(db, item_id)
            it.updated_at = clock.now()
            update_frontmatter(item_file(self.paths, it), it)

    # ------------------------------------------------------------------ inbox
    def inbox(self, slug: str) -> list[tuple[Item, list[str]]]:
        """Open items whose body/discussion mentions ``@slug``, with the matching lines."""
        from squads.workflow import is_open

        slug = slug.lstrip("@").lower()
        out: list[tuple[Item, list[str]]] = []
        for item in self.list():
            if not is_open(item.status):
                continue
            path = item_file(self.paths, item)
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            if slug not in discussion.extract_mentions(text):
                continue
            hits = [ln.strip() for ln in text.splitlines() if f"@{slug}" in ln.lower()]
            out.append((item, hits))
        return out

    # ------------------------------------------------------------------ roles
    def activate_role(self, slug: str) -> Item:
        role = role_by_slug(slug)
        existing = self._role_item(slug)
        if existing is not None:
            return existing
        from squads.interactions import skills_for_role

        res = self.create(
            ItemType.ROLE,
            role.full_name,
            description=role.mission,
            status=Status.ACTIVE,
            slug=role.slug,
            extra={
                **role.to_extra(),
                "description": role.description,
                "skills": skills_for_role(role.slug),
            },
        )
        self._backend().generate_role_pointer(self._ctx, res.item, role)
        return res.item

    def _role_item(self, slug: str) -> Item | None:
        for it in self.store.load().items.values():
            if it.type is ItemType.ROLE and it.extra.get("slug") == slug:
                return it
        return None

    def roster(self) -> list[RoleView]:
        views: list[RoleView] = []
        for it in self.list(type=ItemType.ROLE):
            views.append(
                RoleView(
                    slug=it.extra.get("slug", it.slug),
                    full_name=it.extra.get("full_name", it.title),
                    title=it.extra.get("title", it.title),
                    is_default=it.extra.get("is_default", False),
                )
            )
        return views

    def refresh_managed(self) -> None:
        self._backend().write_managed(self._ctx, self.roster())

    # ------------------------------------------------------------------ refs (forward edges)
    def add_ref(self, from_id: str, to_id: str, *, kind: str = "related") -> Item:
        if from_id == to_id:
            raise SquadsError("an item cannot reference itself")
        with self.store.transaction() as db:
            src = require_item(db, from_id)
            require_item(db, to_id)
            if to_id not in src.refs:
                src.refs.append(to_id)
            if kind and kind != "related":
                kinds = _ref_kinds(src)
                kinds[to_id] = kind
                src.extra["ref_kinds"] = kinds
            src.updated_at = clock.now()
            update_frontmatter(item_file(self.paths, src), src)
        return src

    def rm_ref(self, from_id: str, to_id: str) -> Item:
        with self.store.transaction() as db:
            src = require_item(db, from_id)
            src.refs = [r for r in src.refs if r != to_id]
            kinds = _ref_kinds(src)
            if kinds.pop(to_id, None) is not None:
                src.extra["ref_kinds"] = kinds
            src.updated_at = clock.now()
            update_frontmatter(item_file(self.paths, src), src)
        return src

    def refs_out(self, item_id: str) -> list[tuple[str, str]]:
        item = self.get(item_id)
        kinds = _ref_kinds(item)
        return [(to, kinds.get(to, "related")) for to in item.refs]

    def refs_in(self, item_id: str) -> list[tuple[str, str]]:
        """Backrefs computed by inverting forward edges (never stored)."""
        db = self.store.load()
        require_item(db, item_id)
        out: list[tuple[str, str]] = []
        for it in db.items.values():
            if item_id in it.refs:
                out.append((it.id, _ref_kinds(it).get(item_id, "related")))
        return sorted(out, key=lambda p: number_for_id(p[0]))

    # ------------------------------------------------------------------ developers
    def add_dev(self, tech: str, *, name: str | None = None, model: str | None = None) -> Item:
        from squads.interactions import skills_for_role
        from squads.roles.catalog import dev_role

        seq = sum(1 for it in self.list(type=ItemType.ROLE) if it.extra.get("is_dev"))
        role = dev_role(tech, name=name, seq=seq, model=model)
        if self._role_item(role.slug) is not None:
            raise SquadsError(f"a developer with slug {role.slug!r} already exists")
        res = self.create(
            ItemType.ROLE,
            role.full_name,
            description=role.mission,
            status=Status.ACTIVE,
            slug=role.slug,
            extra={
                **role.to_extra(),
                "description": role.description,
                "is_dev": True,
                "tech": tech,
                "skills": skills_for_role(role.slug),
            },
        )
        self._backend().generate_role_pointer(self._ctx, res.item, role)
        self.refresh_managed()
        return res.item

    # ------------------------------------------------------------------ skills
    def add_skill(
        self,
        name: str,
        *,
        description: str = "",
        when_to_use: str = "",
        allowed_tools: str = "",
        parent: str | None = None,
    ) -> Item:
        slug = slugify(name)
        if self._skill_item(slug) is not None:
            raise SquadsError(f"a skill with slug {slug!r} already exists")
        res = self.create(
            ItemType.SKILL,
            name,
            description=description,
            parent=parent,
            status=Status.ACTIVE,
            slug=slug,
            extra={
                "slug": slug,
                "description": description or name,
                "when_to_use": when_to_use,
                "allowed_tools": allowed_tools,
            },
        )
        self._backend().generate_skill_pointer(self._ctx, res.item)
        return res.item

    def _skill_item(self, slug: str) -> Item | None:
        for it in self.store.load().items.values():
            if it.type is ItemType.SKILL and it.extra.get("slug", it.slug) == slug:
                return it
        return None

    # ------------------------------------------------------------------ regen / remove
    def regen(self, item_id: str) -> Item:
        """Regenerate the backend pointer for a role or skill from its current item data."""
        item = self.get(item_id)
        if item.type is ItemType.ROLE:
            self._backend().generate_role_pointer(self._ctx, item, RoleDef.from_extra(item.extra))
        elif item.type is ItemType.SKILL:
            self._backend().generate_skill_pointer(self._ctx, item)
        else:
            raise SquadsError(f"{item_id} is a {item.type.value}; only roles/skills have pointers")
        return item

    def remove_item(self, item_id: str, *, purge: bool = False) -> Item:
        with self.store.transaction() as db:
            item = require_item(db, item_id)
            del db.items[item_id]
        if item.type in _AGENT_TYPES:
            self._backend().remove_artifacts(self._ctx, item)
        if purge:
            item_file(self.paths, item).unlink(missing_ok=True)
        return item

    # ------------------------------------------------------------------ sync
    def sync(self) -> None:
        """Regenerate all tool-owned managed files to the current version; stamp the config."""
        backend = self._backend()
        ctx = self._ctx
        backend.ensure_scaffold(ctx)
        for it in self.list(type=ItemType.ROLE):
            backend.generate_role_pointer(ctx, it, RoleDef.from_extra(it.extra))
        for it in self.list(type=ItemType.SKILL):
            backend.generate_skill_pointer(ctx, it)
        backend.write_managed(ctx, self.roster())
        self._stamp_version(__version__)

    def _stamp_version(self, version: str) -> None:
        cfg = self.paths.config.model_copy(update={"squads_version": version})
        self.paths.config_path.write_text(cfg.to_toml(), encoding="utf-8")

    # ------------------------------------------------------------------ repair
    def _renumber(self) -> dict[str, str]:
        """Resolve duplicate global ID numbers from a merge: reassign + rewrite references."""
        import re

        from squads.itemfile import read_frontmatter

        # scan files: id -> (path, type, slug, number)
        found: list[_FileRec] = []
        for item_type in ItemType:
            folder = self.paths.folder_for(item_type)
            if not folder.is_dir():
                continue
            for md in sorted(folder.glob(f"{item_type.prefix}-*.md")):
                fid = read_frontmatter(md).get("id")
                if not fid:
                    continue
                stem = md.name.removesuffix(".md")
                slug = stem.split("-", 2)[2] if stem.count("-") >= 2 else ""
                found.append((fid, md, item_type, slug, number_for_id(fid)))

        by_number: dict[int, list[_FileRec]] = {}
        for rec in found:
            by_number.setdefault(rec[4], []).append(rec)

        next_free = max((n for n in by_number), default=0) + 1
        remap: dict[str, str] = {}
        renamed: list[tuple[Path, ItemType, str, str]] = []  # (old_path, type, slug, new_id)
        for number in sorted(by_number):
            group = sorted(by_number[number], key=lambda r: r[0])
            for rec in group[1:]:  # keep the first id, reassign the rest
                fid, md, item_type, slug, _ = rec
                new_id = f"{item_type.prefix}-{next_free:06d}"
                next_free += 1
                remap[fid] = new_id
                renamed.append((md, item_type, slug, new_id))

        if not remap:
            return {}

        # rewrite every reference to a remapped id across all files (frontmatter + body + inline)
        for _, md, _, _, _ in found:
            text = md.read_text(encoding="utf-8")
            new_text = text
            for old, new in remap.items():
                new_text = re.sub(rf"\b{re.escape(old)}\b", new, new_text)
            if new_text != text:
                md.write_text(new_text, encoding="utf-8")

        # rename the files whose own id changed
        for old_path, item_type, slug, new_id in renamed:
            new_name = f"{new_id}-{slug}.md" if slug else f"{new_id}.md"
            old_path.rename(self.paths.folder_for(item_type) / new_name)
        return remap

    def repair(self, *, renumber: bool = False) -> SquadsDB:
        from squads.itemfile import read_frontmatter

        if renumber:
            self._renumber()

        db = SquadsDB(squads_version=__version__, counter=0)
        max_n = 0
        for item_type in ItemType:
            folder = self.paths.folder_for(item_type)
            if not folder.is_dir():
                continue
            for md in sorted(folder.glob(f"{item_type.prefix}-*.md")):
                data = read_frontmatter(md)
                if not data.get("id"):
                    continue
                squad_rel = self.paths.squad_relative(item_type, md.name)
                item = Item.from_frontmatter(data, path=squad_rel)
                db.add(item)
                max_n = max(max_n, number_for_id(item.id))
        db.counter = max_n
        self.store.overwrite(db)
        return db

    # ------------------------------------------------------------------ check
    def check(self) -> list[CheckIssue]:
        from squads.itemfile import read_frontmatter
        from squads.workflow import parent_allowed, parent_hint, workflow_for

        issues: list[CheckIssue] = []
        index = self.store.load()
        on_disk: dict[str, tuple[Path, dict[str, Any]]] = {}

        # scan files: marker pairing + collect ids
        for item_type in ItemType:
            folder = self.paths.folder_for(item_type)
            if not folder.is_dir():
                continue
            for md in sorted(folder.glob(f"{item_type.prefix}-*.md")):
                text = md.read_text(encoding="utf-8")
                for msg in _marker_issues(text):
                    issues.append(CheckIssue("error", md.name, msg))
                data = read_frontmatter(text=text)
                fid = data.get("id")
                if not fid:
                    issues.append(CheckIssue("error", md.name, "file has no `id` in frontmatter"))
                    continue
                on_disk[fid] = (md, data)

        # files ↔ index reconciliation
        for fid in on_disk:
            if fid not in index.items:
                issues.append(
                    CheckIssue("error", fid, "on disk but not in index (run `sq repair`)")
                )
        for iid in index.items:
            if iid not in on_disk:
                issues.append(CheckIssue("error", iid, "in index but no markdown file found"))

        # per-item validation
        for iid, item in index.items.items():
            if item.status not in workflow_for(item.type).states:
                issues.append(
                    CheckIssue(
                        "error",
                        iid,
                        f"status {item.status.value!r} not valid for a {item.type.value}",
                    )
                )
            if item.parent and item.parent not in index.items:
                issues.append(CheckIssue("error", iid, f"dangling parent {item.parent}"))
            elif item.parent:
                parent_type = index.items[item.parent].type
                if not parent_allowed(item.type, parent_type):
                    issues.append(
                        CheckIssue(
                            "error", iid, f"{parent_hint(item.type)} (got {parent_type.value})"
                        )
                    )
            for ref in item.refs:
                if ref not in index.items:
                    issues.append(CheckIssue("warn", iid, f"dangling ref {ref}"))
            if iid in on_disk:
                fdata = on_disk[iid][1]
                if fdata.get("status") != item.status.value:
                    issues.append(
                        CheckIssue(
                            "warn",
                            iid,
                            "status drift between frontmatter and index (run `sq repair`)",
                        )
                    )
                if (fdata.get("parent") or None) != item.parent:
                    issues.append(
                        CheckIssue(
                            "warn",
                            iid,
                            "parent drift between frontmatter and index (run `sq repair`)",
                        )
                    )

        # subtask → user-story references must resolve in the task's parent feature
        for iid, item in index.items.items():
            if item.type is not ItemType.TASK or iid not in on_disk:
                continue
            stories = discussion.subtask_stories(on_disk[iid][0].read_text())
            refs = [(stn, us) for stn, us in stories if us]
            if not refs:
                continue
            parent = index.items.get(item.parent) if item.parent else None
            if parent is None or parent.type is not ItemType.FEATURE:
                issues.append(
                    CheckIssue(
                        "error",
                        iid,
                        "subtask maps to a user story but the task has no feature parent",
                    )
                )
                continue
            feature_stories: set[str] = set()
            if parent.id in on_disk:
                blocks = discussion.list_blocks(on_disk[parent.id][0].read_text(), "story")
                feature_stories = {sid for sid, _ in blocks}
            for stn, us in refs:
                if us not in feature_stories:
                    issues.append(
                        CheckIssue("error", iid, f"subtask {stn} → {us} missing from {parent.id}")
                    )
        return issues


# --------------------------------------------------------------------------- init


@dataclass
class InitResult:
    paths: SquadPaths
    roles: list[Item]


def init(
    *,
    root: Path | None = None,
    squad_dir: str = "squads",
    backend: str = "claude_code",
    roles_spec: str = "all",
    no_claude: bool = False,
    force: bool = False,
) -> InitResult:
    root = (root or Path.cwd()).resolve()
    config_path = root / CONFIG_FILENAME
    if config_path.exists() and not force:
        raise AlreadyInitializedError(f"{config_path} already exists (use --force to overwrite)")

    config = SquadsConfig(
        squad_dir=squad_dir,
        default_backend=backend,
        default_role="manager",
        squads_version=__version__,
    )
    config_path.write_text(config.to_toml(), encoding="utf-8")

    sp = SquadPaths(root=root, squad_dir=root / squad_dir, config=config)
    sp.squad_dir.mkdir(parents=True, exist_ok=True)
    for folder in FOLDER_BY_TYPE.values():
        (sp.squad_dir / folder).mkdir(parents=True, exist_ok=True)
    (sp.squad_dir / ".gitignore").write_text(".squads.json.lock\n*.tmp\n", encoding="utf-8")

    store = IndexStore(sp.index_path, sp.lock_path)
    store.create_empty(__version__)

    svc = Service(sp)
    if not no_claude:
        svc.scaffold_backend()

    role_defs: list[RoleDef] = resolve_roles(roles_spec) if roles_spec else []
    created = [svc.activate_role(r.slug) for r in role_defs]

    if not no_claude:
        svc.refresh_managed()

    return InitResult(paths=sp, roles=created)


def open_service(dir_override: str | None = None) -> Service:
    return Service(resolve(dir_override))
