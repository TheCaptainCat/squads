"""The incoming-edge builder returns the supersession and the dependency sets from one walk of
the refs, resolves each kind through its declared role rather than its spelling, keys by sequence
number so any id width matches, and leaves `supersedes_incoming_seqs` reading the same answer.
"""

from datetime import UTC, datetime

import pytest

from _helpers import BUILTIN_FOLDER, BUILTIN_PREFIX
from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._services._validators import incoming_edges, supersedes_incoming_seqs
from squads._workflow import bundled_spec

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _task(seq: int, refs: list[str]) -> Item:
    prefix = BUILTIN_PREFIX["task"]
    return Item(
        sequence_id=seq,
        type="task",
        prefix=prefix,
        title=f"item {seq}",
        slug=f"item-{seq}",
        status="Draft",
        path=f"{BUILTIN_FOLDER['task']}/{prefix}-{seq:06d}-item-{seq}.md",
        created_at=_NOW,
        updated_at=_NOW,
        refs=refs,
    )


def _index(*items: Item) -> SquadsDB:
    db = SquadsDB(counter=max(i.sequence_id for i in items))
    for item in items:
        db.add(item)
    return db


#: (refs held by item 1, supersession targets, dependency targets). Items 2 to 6 hold no ref.
_CASES: dict[str, tuple[list[str], set[int], set[int]]] = {
    "no-ref": ([], set(), set()),
    "supersedes": (["TASK-000002:supersedes"], {2}, set()),
    "blocks": (["TASK-000003:blocks"], set(), {3}),
    "depends-on": (["TASK-000004:depends-on"], set(), {4}),
    "navigational-kinds": (
        ["TASK-000005:targets", "TASK-000006:implements", "TASK-000002"],
        set(),
        set(),
    ),
    "all-three": (
        ["TASK-000002:supersedes", "TASK-3:blocks", "TASK-000004:depends-on"],
        {2},
        {3, 4},
    ),
    "same-target-both-roles": (["TASK-000002:supersedes", "TASK-2:blocks"], {2}, {2}),
}


@pytest.mark.parametrize("case", _CASES)
def test_each_set_holds_exactly_the_targets_of_its_declared_role(case: str) -> None:
    refs, supersedes, dependency = _CASES[case]
    db = _index(_task(1, refs), *(_task(n, []) for n in range(2, 7)))
    found = incoming_edges(db, bundled_spec())
    assert (found.supersedes, found.dependency) == (supersedes, dependency)
    assert supersedes_incoming_seqs(db, bundled_spec()) == found.supersedes


def test_a_spec_declaring_no_dependency_kind_yields_an_empty_dependency_set() -> None:
    spec = bundled_spec()
    without = spec.model_copy(
        update={"ref_kinds": {k: v for k, v in spec.ref_kinds.items() if v.role != "dependency"}}
    )
    db = _index(
        _task(1, ["TASK-000002:blocks", "TASK-000003:supersedes"]), _task(2, []), _task(3, [])
    )
    found = incoming_edges(db, without)
    assert (found.supersedes, found.dependency) == ({3}, set())
