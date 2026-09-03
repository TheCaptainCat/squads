"""Both walks behind the tree surface terminate on a parent relation that holds a cycle.

They are two independent faults, not one seen twice. The upward walk that builds the keep set
alternates between the same items forever — a busy loop with no stack growth, so it presents as
a hang rather than a crash. The downward recursion behind it raises ``RecursionError``. Whether
the upward one reaches its failure first depends on the shape of the call, so each is proved
here against the function itself, with no corpus and no service in between: the downward walk in
particular is the one a corpus-level test can only reach by accident.

Identity in both visited sets is the sequence number, never the id string — a stored parent may
carry a different zero-pad width than the item's own id (the state ``sq migrate repad`` leaves
behind), and comparing id strings walks straight past the repeat.
"""

from datetime import UTC, datetime

import pytest

from squads._models._item import Item
from squads._services._base import _compute_keep_set, _walk_tree

_NOW = datetime(2026, 1, 1, tzinfo=UTC)

#: How many id lookups the upward walk is allowed before :class:`_BoundedIdMap` calls it a
#: non-terminating walk. Every fixture below holds at most four items, so a walk that respects
#: its visited set uses a handful; the unguarded loop reaches this within microseconds.
_LOOKUP_BUDGET = 500


class _BoundedIdMap(dict[str, Item]):
    """An ``id_map`` that refuses to be read forever.

    The upward walk's failure mode is a busy ``while`` loop with no stack growth: it raises
    nothing, allocates nothing and never returns, so removing its guard would hang this test
    process rather than fail it — and a test that can only hang has not been shown to fail.
    Capping the lookups turns that into an ordinary, fast assertion failure while leaving a
    guarded walk (a handful of lookups over these fixtures) untouched.
    """

    def __init__(self, items: dict[str, Item]) -> None:
        super().__init__(items)
        self.lookups = 0

    def get(self, key: str, default: Item | None = None) -> Item | None:  # type: ignore[override]
        self.lookups += 1
        if self.lookups > _LOOKUP_BUDGET:
            raise AssertionError(
                f"the upward walk read the id map {self.lookups} times over "
                f"{len(self)} items — it is not terminating"
            )
        return super().get(key, default)


def _item(seq: int, parent: str | None = None, *, width: int = 6) -> Item:
    return Item(  # type: ignore[arg-type]
        sequence_id=seq,
        type="bug",
        prefix="BUG",
        title=f"item {seq}",
        slug=f"item-{seq}",
        status="Open",
        path=f"bugs/BUG-{seq:0{width}d}.md",
        parent=parent,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _maps(items: list[Item]):
    id_map = _BoundedIdMap({i.id: i for i in items})
    seq_to_id = {i.sequence_id: i.id for i in items}
    children: dict[str | None, list[Item]] = {}
    for i in items:
        key = seq_to_id.get(int(i.parent.rsplit("-", 1)[-1])) if i.parent else None
        children.setdefault(key, []).append(i)
    return id_map, seq_to_id, children


# --------------------------------------------------------------------------- the upward walk


@pytest.mark.parametrize(
    ("label", "parents"),
    [
        ("self", {1: 1}),
        ("mutual", {1: 2, 2: 1}),
        ("three-item chain", {1: 2, 2: 3, 3: 1}),
    ],
)
def test_the_keep_set_walk_terminates_on_a_cycle(label, parents):
    items = [_item(seq, f"BUG-{parents[seq]:06d}") for seq in sorted(parents)]
    id_map, seq_to_id, _children = _maps(items)
    keep = _compute_keep_set({i.id for i in items}, id_map, seq_to_id)
    assert keep == {i.id for i in items}, label


def test_the_keep_set_walk_terminates_when_the_stored_parent_has_another_pad_width():
    """The two items' own ids are six-wide; their stored parents are nine-wide. A visited set
    of id strings never sees a repeat here and the walk never ends."""
    a = _item(1, "BUG-000000002")
    b = _item(2, "BUG-000000001")
    id_map, seq_to_id, _children = _maps([a, b])
    assert a.id not in {a.parent, b.parent}, "the fixture must differ in width from the ids"
    assert _compute_keep_set({a.id, b.id}, id_map, seq_to_id) == {a.id, b.id}


def test_an_item_whose_ancestor_chain_reaches_a_cycle_it_is_not_part_of_terminates():
    """A -> B -> C -> B: the walk from A enters a loop it never closes on A itself."""
    a = _item(1, "BUG-000002")
    b = _item(2, "BUG-000003")
    c = _item(3, "BUG-000002")
    id_map, seq_to_id, _children = _maps([a, b, c])
    assert _compute_keep_set({a.id}, id_map, seq_to_id) == {a.id, b.id, c.id}


# --------------------------------------------------------------------------- the downward walk


@pytest.mark.parametrize(
    ("label", "parents"),
    [
        ("self", {1: 1}),
        ("mutual", {1: 2, 2: 1}),
        ("three-item chain", {1: 2, 2: 3, 3: 1}),
    ],
)
def test_the_downward_recursion_terminates_over_a_cyclic_children_map(label, parents):
    items = [_item(seq, f"BUG-{parents[seq]:06d}") for seq in sorted(parents)]
    id_map, _seq_to_id, children = _maps(items)
    ids = set(id_map)
    node = _walk_tree(items[0], 0, keep_set=ids, match_set=ids, children_map=children, depth=None)
    assert node is not None, label
    # No item twice on one path: the repeat is truncated, not rendered again.
    path: list[str] = []
    current = node
    while True:
        path.append(current.item.id)
        if not current.children:
            break
        current = current.children[0]
    assert len(path) == len(set(path)), f"{label}: {path}"


def test_the_downward_recursion_truncates_the_repeat_rather_than_dropping_the_branch():
    """A cyclic pair rooted at one of its members still renders the other — a poisoned corpus
    should show the operator what they are looking at, not an empty tree."""
    a = _item(1, "BUG-000002")
    b = _item(2, "BUG-000001")
    id_map, _seq_to_id, children = _maps([a, b])
    ids = set(id_map)
    node = _walk_tree(a, 0, keep_set=ids, match_set=ids, children_map=children, depth=None)
    assert node is not None
    assert [c.item.id for c in node.children] == [b.id]
    assert node.children[0].children == []


def test_the_downward_recursion_terminates_when_the_stored_parent_has_another_pad_width():
    a = _item(1, "BUG-000000002")
    b = _item(2, "BUG-000000001")
    id_map, _seq_to_id, children = _maps([a, b])
    ids = set(id_map)
    node = _walk_tree(a, 0, keep_set=ids, match_set=ids, children_map=children, depth=None)
    assert node is not None
    assert [c.item.id for c in node.children] == [b.id]
    assert node.children[0].children == []


def test_a_sibling_repeated_across_two_branches_is_not_mistaken_for_a_cycle():
    """The guard is per-path, not global: an item reached once under each of two roots stays
    visible under both."""
    root_a = _item(1)
    root_b = _item(2)
    shared_under_a = _item(3, "BUG-000001")
    shared_under_b = _item(4, "BUG-000002")
    items = [root_a, root_b, shared_under_a, shared_under_b]
    id_map, _seq_to_id, children = _maps(items)
    ids = set(id_map)
    for root, child in ((root_a, shared_under_a), (root_b, shared_under_b)):
        node = _walk_tree(root, 0, keep_set=ids, match_set=ids, children_map=children, depth=None)
        assert node is not None
        assert [c.item.id for c in node.children] == [child.id]
