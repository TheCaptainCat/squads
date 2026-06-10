"""Forward reference edges (typed cross-links); backrefs are computed by inversion."""

from squads import _clock as clock
from squads._errors import SquadsError
from squads._index._resolver import item_file, require_item
from squads._itemfile import update_frontmatter
from squads._models._item import Item, make_ref, split_ref
from squads._paths import number_for_id
from squads._services._base import ServiceCore
from squads._workflow import is_open


class RefsMixin(ServiceCore):
    def add_ref(self, from_id: str, to_id: str, *, kind: str = "related") -> Item:
        if from_id == to_id:
            raise SquadsError("an item cannot reference itself")
        with self.store.transaction() as db:
            src = require_item(db, from_id)
            require_item(db, to_id)
            # the kind rides with the edge; re-adding an existing edge updates its kind
            src.refs = [r for r in src.refs if split_ref(r)[0] != to_id]
            src.refs.append(make_ref(to_id, kind))
            src.updated_at = clock.now()
            update_frontmatter(item_file(self.paths, src), src)
        return src

    def rm_ref(self, from_id: str, to_id: str) -> Item:
        with self.store.transaction() as db:
            src = require_item(db, from_id)
            src.refs = [r for r in src.refs if split_ref(r)[0] != to_id]
            src.updated_at = clock.now()
            update_frontmatter(item_file(self.paths, src), src)
        return src

    def refs_out(self, item_id: str) -> list[tuple[str, str]]:
        return [split_ref(r) for r in self.get(item_id).refs]

    def refs_in(self, item_id: str) -> list[tuple[str, str]]:
        """Backrefs computed by inverting forward edges (never stored)."""
        db = self.store.load()
        require_item(db, item_id)
        out: list[tuple[str, str]] = []
        for it in db.items.values():
            for r in it.refs:
                rid, kind = split_ref(r)
                if rid == item_id:
                    out.append((it.id, kind))
        return sorted(out, key=lambda p: number_for_id(p[0]))

    def blocked(self) -> list[tuple[Item, list[Item]]]:
        """Open items with ≥1 open blocker (the ``blocks`` ref kind), paired with those blockers.

        ``A ref add B --kind blocks`` reads "A blocks B": B is blocked while A stays open.
        """
        db = self.store.load()
        blockers_by_target: dict[str, list[Item]] = {}
        for it in db.items.values():
            for r in it.refs:
                rid, kind = split_ref(r)
                if kind == "blocks":
                    blockers_by_target.setdefault(rid, []).append(it)
        out: list[tuple[Item, list[Item]]] = []
        for tid, blockers in blockers_by_target.items():
            target = db.get(tid)
            if target is None or not is_open(target.status):
                continue
            open_blockers = sorted(
                (b for b in blockers if is_open(b.status)), key=lambda b: number_for_id(b.id)
            )
            if open_blockers:
                out.append((target, open_blockers))
        return sorted(out, key=lambda p: number_for_id(p[0].id))
