"""The shared service core: state, backend access, and the primitives every concern builds on.

Each concern lives in its own ``_services/_*.py`` mixin subclassing ``ServiceCore``; the public
``Service`` (in ``_service.py``) multiply-inherits them. ``ServiceCore`` defines what's used across
concerns (create/get/list, the backend, the role/skill lookups + roster projection) so the mixins
only ever call core methods + their own.
"""

from collections.abc import Callable
from typing import Any

from squads import __version__, _aio
from squads import _clock as clock
from squads import _sections as sections
from squads._backends._base import AgentBackend, BackendContext, OperatorView, RoleView
from squads._backends._registry import get_backend
from squads._errors import ItemNotFoundError, SquadsError
from squads._index._resolver import item_file, require_item
from squads._index._store import IndexStore
from squads._itemfile import update_frontmatter, write_new
from squads._models import _markers as markers
from squads._models._enums import ItemType, Priority, Status
from squads._models._extras import ExtraKey as X
from squads._models._index import SquadsDB
from squads._models._item import VALID_REF_KINDS, Item, split_ref
from squads._paths import SquadPaths, number_for_id
from squads._rendering._engine import render, set_active_squad_dir
from squads._roles._resolver import resolve_role
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


def reject_markers(text: str, what: str = "body") -> None:
    """Raise ``SquadsError`` when *text* contains a well-formed sq marker tag.

    All prose inputs that land inside marker-delimited regions must pass through
    this guard before any file write.  The ``what`` label appears in the message
    (e.g. ``"body"``, ``"comment message"``, ``"title"``).

    For the legacy ``"body"`` label the message is kept verbatim so existing
    callers and tests stay unchanged.  All other labels get the extended message
    that points the author at a safe formulation.
    """
    if not sections.find_markers(text):
        return
    if what == "body":
        raise SquadsError("body must not contain sq marker comments (<!-- sq:… -->)")
    raise SquadsError(
        f"{what} must not contain sq marker comments (<!-- sq:… -->). "
        "Write the tag without its HTML-comment wrapper (e.g. sq:body rather than "
        "the comment form) — backtick-wrapping does not neutralize a well-formed tag."
    )


def _template_for(item_type: ItemType) -> str:
    if item_type is ItemType.ROLE:
        return "agents/role.md.j2"
    if item_type is ItemType.SKILL:
        return "agents/skill.md.j2"
    if item_type is ItemType.OPERATOR:
        return "agents/operator.md.j2"
    return f"items/{item_type.value}.md.j2"


class ServiceCore:
    def __init__(self, paths: SquadPaths):
        self.paths = paths
        self.store = IndexStore(paths.index_path, paths.lock_path)
        # Activate the squad-aware template search path so render() picks up any project
        # overrides under <squad_dir>/.overrides/templates/ for this service's squad.
        set_active_squad_dir(paths.squad_dir)

    # ------------------------------------------------------------------ backend
    @property
    def _ctx(self) -> BackendContext:
        return BackendContext(paths=self.paths, version=__version__)

    def _backends(self) -> list[AgentBackend]:
        """Return one backend instance for each active (deduped) backend name.

        Empty ``active_backends`` returns an empty list (sq-only squad).
        """
        return [get_backend(name) for name in self.paths.config.active_backends]

    async def scaffold_backend(self) -> None:
        """Public entry for init(): create backend scaffolding for every active backend."""
        ctx = self._ctx
        for backend in self._backends():
            await backend.ensure_scaffold(ctx)

    # ------------------------------------------------------------------ create / read
    async def create(  # noqa: PLR0913 — a creation entrypoint with clear keyword-only fields
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
        if refs:
            for ref_str in refs:
                _, kind = split_ref(ref_str)
                if kind not in VALID_REF_KINDS:
                    valid = ", ".join(sorted(VALID_REF_KINDS))
                    raise SquadsError(f"unknown ref kind {kind!r}. Valid kinds: {valid}")
        now = clock.now()
        async with self.store.transaction() as db:
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
                id_padding=db.padding,
            )
            rendered = render(
                _template_for(item_type), item=item, description=description, extra=item.extra
            )
            if body is not None:
                reject_markers(body)
                rendered = sections.replace_section(rendered, markers.BODY, body)
            await write_new(self.paths.abspath(squad_rel), item, rendered)
            db.add(item)
            self.store._log(  # pyright: ignore[reportPrivateUsage]
                "create",
                item.id,
                {"title": item.title, "type": item_type.value, "status": item.status.value},
            )
        return CreateResult(item=item, path=self.paths.abspath(squad_rel))

    async def get(self, item_id: str) -> Item:
        return require_item(await self.store.load(), item_id)

    async def list_items(
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
        for it in (await self.store.load()).items.values():
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
    def _is_participant(db: SquadsDB, slug: str) -> bool:
        """A slug that can author/be-assigned work: a registered role agent or a human operator."""
        return any(
            it.type in (ItemType.ROLE, ItemType.OPERATOR) and it.extra.get(X.SLUG) == slug
            for it in db.items.values()
        )

    def _check_author(self, db: SquadsDB, item_type: ItemType, author: str, slug: str) -> None:
        # an agent/operator definition may self-author (bootstrap); else it names a participant
        if item_type in (ItemType.ROLE, ItemType.SKILL, ItemType.OPERATOR) and author == slug:
            return
        if not self._is_participant(db, author):
            raise SquadsError(
                f"author {author!r} is not a registered agent or operator — register it first"
            )

    def _check_assignee(self, db: SquadsDB, assignee: str | None) -> None:
        # an assignee is optional, but when set it must name a participant (a role or an operator)
        if assignee and not self._is_participant(db, assignee):
            raise SquadsError(
                f"assignee {assignee!r} is not a registered agent or operator — register it first"
            )

    # ------------------------------------------------------------------ shared helpers
    async def _read(self, item_id: str) -> str:
        """Read an item's file text on a worker thread."""
        return await _aio.read_text(item_file(self.paths, await self.get(item_id)))

    async def _bump(self, item_id: str) -> None:
        async with self.store.transaction() as db:
            it = require_item(db, item_id)
            it.updated_at = clock.now()
            await update_frontmatter(item_file(self.paths, it), it)

    async def _locked_section_edit(self, item_id: str, mutate: Callable[[str, Item], str]) -> Item:
        """Edit an item's prose under the index lock, atomically with the ``updated_at`` bump.

        ``mutate(text, item)`` returns the new file text (sync callable — may raise to abort
        before any write). The whole read → mutate → write happens within one ``transaction()``,
        so concurrent ``sq`` processes (e.g. parallel subagents commenting on the same item)
        can't lose each other's edits.
        """
        async with self.store.transaction() as db:
            it = require_item(db, item_id)
            path = item_file(self.paths, it)
            text = await _aio.read_text(path)
            new_text = mutate(text, it)
            it.updated_at = clock.now()
            await _aio.write_text(
                path, sections.replace_frontmatter(new_text, it.to_frontmatter_dict())
            )
        return it

    # ------------------------------------------------------------------ role / skill lookups
    async def _role_item(self, slug: str) -> Item | None:
        for it in (await self.store.load()).items.values():
            if it.type is ItemType.ROLE and it.extra.get(X.SLUG) == slug:
                return it
        return None

    async def role_body(self, slug: str) -> str | None:
        """Return the body-region content of the active role item for ``slug``, or None.

        Returns ``None`` when no tracked item exists for this slug (bundled-only role).
        The returned string is stripped of leading/trailing newlines.
        """
        item = await self._role_item(slug)
        if item is None:
            return None
        text = await _aio.read_text(item_file(self.paths, item))
        body = sections.get_section(text, markers.BODY)
        if body is None:
            return None
        return body.strip("\n")

    async def _skill_item(self, slug: str) -> Item | None:
        for it in (await self.store.load()).items.values():
            if it.type is ItemType.SKILL and it.extra.get(X.SLUG, it.slug) == slug:
                return it
        return None

    async def _operator_item(self, slug: str) -> Item | None:
        for it in (await self.store.load()).items.values():
            if it.type is ItemType.OPERATOR and it.extra.get(X.SLUG) == slug:
                return it
        return None

    async def author(self, slug: str) -> str:
        """Display (full) name for a participant slug; falls back to the slug if unknown."""
        if slug == "operator":
            return "Operator"
        participant = await self._role_item(slug) or await self._operator_item(slug)
        if participant is not None:
            return participant.extra.get(X.FULL_NAME, slug)
        try:
            return resolve_role(slug, self.paths.squad_dir).full_name
        except SquadsError:
            return slug

    async def roster(self) -> list[RoleView]:
        return [
            RoleView(
                slug=it.extra.get(X.SLUG, it.slug),
                full_name=it.extra.get(X.FULL_NAME, it.title),
                title=it.extra.get(X.TITLE, it.title),
                is_default=it.extra.get(X.IS_DEFAULT, False),
            )
            for it in await self.list_items(item_type=ItemType.ROLE)
        ]

    async def operators(self) -> list[OperatorView]:
        return [
            OperatorView(
                slug=it.extra.get(X.SLUG, it.slug),
                full_name=it.extra.get(X.FULL_NAME, it.title),
            )
            for it in await self.list_items(item_type=ItemType.OPERATOR)
        ]

    async def refresh_managed(self) -> None:
        ctx = self._ctx
        roster = await self.roster()
        ops = await self.operators()
        for backend in self._backends():
            await backend.write_managed(ctx, roster, ops)
