"""Item lifecycle: status transitions, edits, links, regen, removal."""

from squads import _clock as clock
from squads import _sections as sections
from squads._errors import InvalidTransitionError, SquadsError
from squads._index._resolver import item_file, require_item
from squads._itemfile import update_frontmatter
from squads._models import _markers as markers
from squads._models._enums import ItemType, Priority
from squads._models._item import Item, Status
from squads._models._metadata import coerce_extra
from squads._roles._catalog import RoleDef
from squads._services._base import ServiceCore, reject_markers
from squads._util import slugify
from squads._workflow import can_transition

_AGENT_TYPES = {ItemType.ROLE, ItemType.SKILL}


class ItemsMixin(ServiceCore):
    def set_status(self, item_id: str, status: Status, *, force: bool = False) -> Item:
        with self.store.transaction() as db:
            item = require_item(db, item_id)
            self._apply_status(item, status, force=force)
            item.updated_at = clock.now()
            update_frontmatter(item_file(self.paths, item), item)
        return item

    def update(  # noqa: PLR0913 — the one metadata entry point
        self,
        item_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        assignee: str | None = None,
        priority: Priority | None = None,
        clear_priority: bool = False,
        add_labels: list[str] | None = None,
        rm_labels: list[str] | None = None,
        author: str | None = None,
        status: Status | None = None,
        force: bool = False,
        parent: str | None = None,
        clear_parent: bool = False,
        set_extra: dict[str, str] | None = None,
        unset_extra: list[str] | None = None,
    ) -> Item:
        with self.store.transaction() as db:
            item = require_item(db, item_id)
            if title is not None and title != item.title:
                self._rename(item, title)
            if description is not None:
                item.description = description
            if assignee is not None:
                self._check_assignee(db, assignee or None)
                item.assignee = assignee or None
            if clear_priority:
                item.priority = None
            elif priority is not None:
                item.priority = priority
            if author is not None:
                self._check_author(db, item.type, author, item.slug)
                item.author = author
            if status is not None:
                self._apply_status(item, status, force=force)
            if clear_parent:
                item.parent = None
            elif parent is not None:
                self._check_parent(db, item.type, parent)
                item.parent = parent
            self._apply_labels(item, add_labels, rm_labels)
            self._apply_extra(item, set_extra, unset_extra)
            item.updated_at = clock.now()
            update_frontmatter(item_file(self.paths, item), item)
        if item.type in _AGENT_TYPES:
            self.regen(item.id)  # keep the .claude/ pointer in sync with edited config
        return item

    @staticmethod
    def _apply_labels(item: Item, add: list[str] | None, rm: list[str] | None) -> None:
        for lbl in add or []:
            if lbl not in item.labels:
                item.labels.append(lbl)
        if rm:
            item.labels = [lab for lab in item.labels if lab not in rm]

    @staticmethod
    def _apply_extra(item: Item, set_extra: dict[str, str] | None, unset: list[str] | None) -> None:
        for key, raw in (set_extra or {}).items():
            item.extra[key] = coerce_extra(item.type, key, raw)
        for key in unset or []:
            item.extra.pop(key, None)

    def _apply_status(self, item: Item, status: Status, *, force: bool) -> None:
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

    def set_body(self, item_id: str, body: str, *, append: bool = False) -> Item:
        """Set (or ``--append`` to) an item's top-level ``:body`` region — no manual editing.

        The body is free-form markdown the agent owns; ``description`` stays a short frontmatter
        summary. Role/skill bodies are generated from their fields, so they're rejected here.
        """
        reject_markers(body)

        def mutate(text: str, item: Item) -> str:
            if item.type in _AGENT_TYPES:
                raise SquadsError(
                    f"{item_id} is a {item.type.value}; its body is generated from its fields"
                    " (edit via `sq update --set …` / `sq sync`)"
                )
            new_body = body
            if append:
                current = (sections.get_section(text, markers.BODY) or "").strip("\n")
                if current:
                    new_body = f"{current}\n\n{body}"
            return sections.replace_section(text, markers.BODY, new_body)

        return self._locked_section_edit(item_id, mutate)

    def read_body(self, item_id: str) -> str:
        """The item's top-level ``:body`` region content (for `sq show`)."""
        item = self.get(item_id)
        text = item_file(self.paths, item).read_text(encoding="utf-8")
        return (sections.get_section(text, markers.BODY) or "").strip("\n")

    def remove_item(self, item_id: str, *, purge: bool = False) -> Item:
        with self.store.transaction() as db:
            item = require_item(db, item_id)
            del db.items[item.sequence_id]
        if item.type in _AGENT_TYPES:
            self._backend().remove_artifacts(self._ctx, item)
        if purge:
            item_file(self.paths, item).unlink(missing_ok=True)
        return item
