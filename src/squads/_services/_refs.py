"""Forward reference edges (typed cross-links); backrefs are computed by inversion."""

from squads import _clock as clock
from squads._errors import SquadsError
from squads._index._resolver import item_file, require_item
from squads._itemfile import update_frontmatter
from squads._models._enums import PREFIX_BY_TYPE
from squads._models._item import (
    DEFAULT_KIND,
    VALID_REF_KINDS,
    Item,
    make_ref,
    ref_id_matches,
    split_ref,
)
from squads._paths import number_for_id
from squads._services._base import ServiceCore
from squads._workflow import is_open


class RefsMixin(ServiceCore):
    async def add_ref(self, from_id: str, to_id: str, *, kind: str = DEFAULT_KIND) -> Item:
        if from_id == to_id:
            raise SquadsError("an item cannot reference itself")
        if kind not in VALID_REF_KINDS:
            valid = ", ".join(sorted(VALID_REF_KINDS))
            raise SquadsError(f"unknown ref kind {kind!r}. Valid kinds: {valid}")
        async with self.store.transaction() as db:
            src = require_item(db, from_id)
            tgt = require_item(db, to_id)
            # The kind rides with the edge; re-adding an existing edge updates its kind.
            # Dedup by (prefix, seq) so old-width stored refs ("TASK-000007") are replaced
            # when re-adding across a repad boundary where to_id is "TASK-0000007"
            # (FEAT-000027: file contents are never rewritten, widths diverge).
            tgt_prefix = PREFIX_BY_TYPE[tgt.type]
            tgt_seq = tgt.sequence_id
            src.refs = [
                r for r in src.refs if not ref_id_matches(split_ref(r)[0], tgt_prefix, tgt_seq)
            ]
            src.refs.append(make_ref(to_id, kind))
            src.updated_at = clock.now()
            await update_frontmatter(item_file(self.paths, src), src)
            self.store._log(  # pyright: ignore[reportPrivateUsage]
                "ref",
                src.id,
                {"add": to_id, "kind": kind},
            )
        return src

    async def rm_ref(self, from_id: str, to_id: str) -> Item:
        async with self.store.transaction() as db:
            src = require_item(db, from_id)
            # Determine (prefix, seq) from the caller's to_id — width-tolerant: the stored
            # ref may carry an old width, the to_id may carry the new width.
            head, _, digits = to_id.rpartition("-")
            if head and digits.isdigit():
                to_prefix = head.upper()
                to_seq = int(digits)
                src.refs = [
                    r for r in src.refs if not ref_id_matches(split_ref(r)[0], to_prefix, to_seq)
                ]
            else:
                # Bare number or malformed — fall back to literal string comparison.
                src.refs = [r for r in src.refs if split_ref(r)[0] != to_id]
            src.updated_at = clock.now()
            await update_frontmatter(item_file(self.paths, src), src)
            self.store._log(  # pyright: ignore[reportPrivateUsage]
                "ref",
                src.id,
                {"remove": to_id},
            )
        return src

    async def refs_out(self, item_id: str) -> list[tuple[str, str]]:
        return [split_ref(r) for r in (await self.get(item_id)).refs]

    async def refs_in(self, item_id: str) -> list[tuple[str, str]]:
        """Backrefs computed by inverting forward edges (never stored).

        Comparison is by (prefix, seq) so old-width ref strings (``"TASK-000007"``) and
        new-width item IDs (``"TASK-0000007"``) match correctly after a ``sq migrate repad``
        (file contents are never rewritten, so refs keep their original width).
        """
        db = await self.store.load()
        target = require_item(db, item_id)
        target_prefix = PREFIX_BY_TYPE[target.type]
        target_seq = target.sequence_id
        out: list[tuple[str, str]] = []
        for it in db.items.values():
            for r in it.refs:
                rid, kind = split_ref(r)
                if ref_id_matches(rid, target_prefix, target_seq):
                    out.append((it.id, kind))
        return sorted(out, key=lambda p: number_for_id(p[0]))

    async def blocked(self) -> list[tuple[Item, list[Item]]]:
        """Open items with ≥1 open blocker, paired with those blockers.

        Two equivalent spellings are supported:
        - ``A ref add B --kind blocks`` ("A blocks B"): B is blocked while A stays open.
          The edge lives on the *blocker* A; B is the target.
        - ``A ref add B --kind depends-on`` ("A depends-on B"): A is blocked while B stays open.
          The edge lives on the *dependent* A; B is the blocker.

        Both spellings are consumed identically. An item blocked through both edges is
        deduplicated — it appears once with the union of its open blockers.
        """
        db = await self.store.load()
        # keyed by the blocked item's id; value is a set of blocker ids (dedup)
        blockers_by_target: dict[str, set[str]] = {}
        for it in db.items.values():
            for r in it.refs:
                rid, kind = split_ref(r)
                if kind == "blocks":
                    # it blocks rid → rid is the blocked item, it is the blocker
                    blockers_by_target.setdefault(rid, set()).add(it.id)
                elif kind == "depends-on":
                    # it depends-on rid → it is the blocked item, rid is the blocker
                    blockers_by_target.setdefault(it.id, set()).add(rid)
        out: list[tuple[Item, list[Item]]] = []
        for tid, blocker_ids in blockers_by_target.items():
            target = db.get(tid)
            if target is None or not is_open(target.status):
                continue
            open_blockers: list[Item] = []
            for bid in blocker_ids:
                b = db.get(bid)
                if b is not None and is_open(b.status):
                    open_blockers.append(b)
            open_blockers.sort(key=lambda b: number_for_id(b.id))
            if open_blockers:
                out.append((target, open_blockers))
        return sorted(out, key=lambda p: number_for_id(p[0].id))
