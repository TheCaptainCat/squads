"""Item lifecycle: status transitions, edits, links, regen, removal."""

from squads import _clock as clock
from squads._errors import InvalidTransitionError, SquadsError
from squads._index._resolver import item_file, require_item
from squads._itemfile import update_frontmatter
from squads._models._enums import ItemType
from squads._models._item import Item, Status
from squads._roles._catalog import RoleDef
from squads._services._base import ServiceCore
from squads._util import slugify
from squads._workflow import can_transition

_AGENT_TYPES = {ItemType.ROLE, ItemType.SKILL}


class ItemsMixin(ServiceCore):
    def set_status(self, item_id: str, status: Status, *, force: bool = False) -> Item:
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

    def remove_item(self, item_id: str, *, purge: bool = False) -> Item:
        with self.store.transaction() as db:
            item = require_item(db, item_id)
            del db.items[item_id]
        if item.type in _AGENT_TYPES:
            self._backend().remove_artifacts(self._ctx, item)
        if purge:
            item_file(self.paths, item).unlink(missing_ok=True)
        return item
