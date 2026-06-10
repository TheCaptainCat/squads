"""The shared service core: state, backend access, and the primitives every concern builds on.

Each concern lives in its own ``_services/_*.py`` mixin subclassing ``ServiceCore``; the public
``Service`` (in ``_service.py``) multiply-inherits them. ``ServiceCore`` defines what's used across
concerns (create/get/list, the backend, the role/skill lookups + roster projection) so the mixins
only ever call core methods + their own.
"""

from typing import Any

from squads import __version__
from squads import _clock as clock
from squads import _sections as sections
from squads._backends._base import AgentBackend, BackendContext, RoleView
from squads._backends._registry import get_backend
from squads._errors import ItemNotFoundError, SquadsError
from squads._index._resolver import item_file, require_item
from squads._index._store import IndexStore
from squads._itemfile import update_frontmatter, write_new
from squads._models import _markers as markers
from squads._models._enums import ItemType, Priority, Status
from squads._models._extras import ExtraKey as X
from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._paths import SquadPaths, number_for_id
from squads._rendering._engine import render
from squads._roles._catalog import role_by_slug
from squads._services._results import CreateResult
from squads._util import slugify
from squads._workflow import initial_status, parent_allowed, parent_hint

# Body-local sub-entities: kind → parent item type and its container marker. Package-internal
# (non-underscore so sibling mixins can import them without tripping reportPrivateUsage).
SUBENTITY_PARENT: dict[str, ItemType] = {
    "story": ItemType.FEATURE,
    "subtask": ItemType.TASK,
    "finding": ItemType.REVIEW,
}
SUBENTITY_CONTAINER: dict[str, str] = {
    "story": markers.STORIES,
    "subtask": markers.SUBTASKS,
    "finding": markers.FINDINGS,
}
SUBENTITY_KIND: dict[ItemType, str] = {p: k for k, p in SUBENTITY_PARENT.items()}


def _template_for(item_type: ItemType) -> str:
    if item_type is ItemType.ROLE:
        return "agents/role.md.j2"
    if item_type is ItemType.SKILL:
        return "agents/skill.md.j2"
    return f"items/{item_type.value}.md.j2"


class ServiceCore:
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

    # ------------------------------------------------------------------ create / read
    def create(  # noqa: PLR0913 — a creation entrypoint with clear keyword-only fields
        self,
        item_type: ItemType,
        title: str,
        *,
        description: str = "",
        parent: str | None = None,
        author: str | None = None,
        labels: list[str] | None = None,
        refs: list[str] | None = None,
        assignee: str | None = None,
        priority: Priority | None = None,
        extra: dict[str, Any] | None = None,
        status: Status | None = None,
        slug: str | None = None,
        body: str | None = None,
    ) -> CreateResult:
        slug = slug or slugify(title)
        author = author or self.paths.config.default_role
        now = clock.now()
        with self.store.transaction() as db:
            if parent:
                self._check_parent(db, item_type, parent)
            self._check_author(db, item_type, author, slug)
            self._check_assignee(db, assignee)
            item_id = db.allocate_id(item_type)  # bumps the counter; item_id == its formatted form
            filename = f"{item_id}-{slug}.md"
            squad_rel = self.paths.squad_relative(item_type, filename)
            item = Item(
                sequence_id=db.counter,
                type=item_type,
                title=title,
                slug=slug,
                status=status or initial_status(item_type),
                description=description,
                parent=parent,
                author=author,
                assignee=assignee,
                priority=priority,
                labels=labels or [],
                refs=refs or [],
                path=squad_rel,
                created_at=now,
                updated_at=now,
                extra=extra or {},
            )
            rendered = render(
                _template_for(item_type), item=item, description=description, extra=item.extra
            )
            if body is not None:
                if sections.find_markers(body):
                    raise SquadsError("body must not contain sq marker comments (<!-- sq:… -->)")
                rendered = sections.replace_section(rendered, markers.BODY, body)
            write_new(self.paths.abspath(squad_rel), item, rendered)
            db.add(item)
        return CreateResult(item=item, path=self.paths.abspath(squad_rel))

    def get(self, item_id: str) -> Item:
        return require_item(self.store.load(), item_id)

    def list_items(
        self,
        *,
        item_type: ItemType | None = None,
        status: Status | None = None,
        parent: str | None = None,
        label: str | None = None,
        assignee: str | None = None,
        priority: Priority | None = None,
    ) -> list[Item]:
        out: list[Item] = []
        for it in self.store.load().items.values():
            if item_type and it.type is not item_type:
                continue
            if status and it.status is not status:
                continue
            if parent and it.parent != parent:
                continue
            if label and label not in it.labels:
                continue
            if assignee and it.assignee != assignee:
                continue
            if priority and it.priority is not priority:
                continue
            out.append(it)
        return sorted(out, key=lambda i: number_for_id(i.id))

    def _check_parent(self, db: SquadsDB, child_type: ItemType, parent_id: str) -> None:
        parent = db.get(parent_id)
        if parent is None:
            raise ItemNotFoundError(f"parent {parent_id!r} does not exist")
        if not parent_allowed(child_type, parent.type):
            raise SquadsError(f"{parent_hint(child_type)} (got {parent.type.value})")

    @staticmethod
    def _is_registered_agent(db: SquadsDB, slug: str) -> bool:
        return any(
            it.type is ItemType.ROLE and it.extra.get(X.SLUG) == slug for it in db.items.values()
        )

    def _check_author(self, db: SquadsDB, item_type: ItemType, author: str, slug: str) -> None:
        # an agent definition may self-author (bootstrap); everything else names a registered agent
        if item_type in (ItemType.ROLE, ItemType.SKILL) and author == slug:
            return
        if not self._is_registered_agent(db, author):
            raise SquadsError(f"author {author!r} is not a registered agent — activate it first")

    def _check_assignee(self, db: SquadsDB, assignee: str | None) -> None:
        # an assignee is optional, but when set it must name a registered agent (no self-reference)
        if assignee and not self._is_registered_agent(db, assignee):
            raise SquadsError(
                f"assignee {assignee!r} is not a registered agent — activate it first"
            )

    # ------------------------------------------------------------------ shared helpers
    def _read(self, item_id: str) -> str:
        return item_file(self.paths, self.get(item_id)).read_text(encoding="utf-8")

    def _bump(self, item_id: str) -> None:
        with self.store.transaction() as db:
            it = require_item(db, item_id)
            it.updated_at = clock.now()
            update_frontmatter(item_file(self.paths, it), it)

    # ------------------------------------------------------------------ role / skill lookups
    def _role_item(self, slug: str) -> Item | None:
        for it in self.store.load().items.values():
            if it.type is ItemType.ROLE and it.extra.get(X.SLUG) == slug:
                return it
        return None

    def _skill_item(self, slug: str) -> Item | None:
        for it in self.store.load().items.values():
            if it.type is ItemType.SKILL and it.extra.get(X.SLUG, it.slug) == slug:
                return it
        return None

    def author(self, slug: str) -> str:
        """Resolve an agent slug to its display (full) name; falls back to the slug if unknown."""
        if slug == "operator":
            return "Operator"
        role_item = self._role_item(slug)
        if role_item is not None:
            return role_item.extra.get(X.FULL_NAME, slug)
        try:
            return role_by_slug(slug).full_name
        except SquadsError:
            return slug

    def roster(self) -> list[RoleView]:
        return [
            RoleView(
                slug=it.extra.get(X.SLUG, it.slug),
                full_name=it.extra.get(X.FULL_NAME, it.title),
                title=it.extra.get(X.TITLE, it.title),
                is_default=it.extra.get(X.IS_DEFAULT, False),
            )
            for it in self.list_items(item_type=ItemType.ROLE)
        ]

    def refresh_managed(self) -> None:
        self._backend().write_managed(self._ctx, self.roster())
