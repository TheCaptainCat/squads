"""The index load count for ``sq show <id> --json`` on a multi-sub-entity item — the
acceptance criterion the design owes, not a timing (a wall-clock assertion proves nothing on
a loaded machine).

``sq show <id> --json`` (the root-level, any-type command, distinct from the per-type
``sq <type> <n> show``) is one flat ``@app.command`` wrapped once by ``command`` — no separate
id-resolving group callback ahead of it — so it is exactly the shape the request-scoped read
cache (``squads._index._store``'s ``_ReadScope``, opened once per CLI invocation by
``_cli/_common.py::command``) delivers its literal "one load" for. Before the cache, one load
happened per sub-entity (``get_block`` fanning out through ``get``), so the count scaled with
sub-entity count; after it, the count is flat at 1, independent of sub-entity count.

The per-type alias (``sq <type> <n> show --json``) is a second way to reach the same output,
through Typer's own id-resolving group callback ahead of the leaf verb — two separate calls
across the sync/async bridge for one user-facing invocation. Each used to build its own
``Service``/``IndexStore`` (the read scope's store-identity-keyed cache had no store to
share), costing a second, honestly-documented load. ``get_service`` (``_cli/_common.py``) now
memoizes the ``Service`` on the same Click root context the read scope already anchors to, so
both crossings share one store and the per-type alias is flat at 1 too — see
``test_per_type_show_json_loads_the_index_exactly_once`` below, and the store-identity test
that pins the *mechanism*, not just the resulting count, since a count alone cannot tell a
shared store apart from two stores that each happen to load once.
"""

import json

import pytest

from squads._index._store import IndexStore

pytestmark = pytest.mark.anyio

_SUBTASK_COUNT = 8


async def _count_loads(monkeypatch) -> list[int]:
    """Return a live counter cell wired into ``IndexStore._read_from_disk`` — the one seam
    every ``load()`` call (scope hit or miss) still funnels through, so this counts genuine
    disk reads regardless of how many are cache hits."""
    calls = [0]
    original = IndexStore._read_from_disk

    async def counted(self, *, validate_vocab):
        calls[0] += 1
        return await original(self, validate_vocab=validate_vocab)

    monkeypatch.setattr(IndexStore, "_read_from_disk", counted)
    return calls


async def test_root_show_json_loads_the_index_exactly_once_for_a_multi_subentity_item(
    project, invoke, monkeypatch
) -> None:
    """The literal acceptance bar: one load for the whole invocation, on the root ``sq show``
    command — flat regardless of sub-entity count, never ``1 + subtask_count`` as it was
    before the read scope existed."""
    created = await invoke(["create", "task", "Parent", "--author", "manager"])
    assert created.exit_code == 0, created.output
    for i in range(_SUBTASK_COUNT):
        added = await invoke(["task", "2", "add-subtask", f"Child {i}"])
        assert added.exit_code == 0, added.output

    calls = await _count_loads(monkeypatch)
    result = await invoke(["show", "TASK-2", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert len(payload["subentities"]) == _SUBTASK_COUNT

    assert calls[0] == 1, (
        f"expected exactly one index load for the whole invocation, got {calls[0]}"
    )


async def test_root_show_json_load_count_does_not_grow_with_more_subentities(
    project, invoke, monkeypatch
) -> None:
    """Same assertion, more sub-entities — pins that the count is flat at 1, not merely small
    for one particular size."""
    created = await invoke(["create", "task", "Parent", "--author", "manager"])
    assert created.exit_code == 0, created.output
    for i in range(_SUBTASK_COUNT * 2):
        added = await invoke(["task", "2", "add-subtask", f"Child {i}"])
        assert added.exit_code == 0, added.output

    calls = await _count_loads(monkeypatch)
    result = await invoke(["show", "TASK-2", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert len(payload["subentities"]) == _SUBTASK_COUNT * 2

    assert calls[0] == 1


async def test_per_type_show_json_loads_the_index_exactly_once(
    project, invoke, monkeypatch
) -> None:
    """The per-type alias's own load count, now closed to the same "one" bar as the root
    command — see the module docstring. Still flat in sub-entity count (the N+1 bug is gone
    here too); the previously-documented flat-but-not-one shape (2: one per bridge crossing)
    is what the ``Service`` memo on the Click root context closes."""
    created = await invoke(["create", "task", "Parent", "--author", "manager"])
    assert created.exit_code == 0, created.output
    for i in range(_SUBTASK_COUNT):
        added = await invoke(["task", "2", "add-subtask", f"Child {i}"])
        assert added.exit_code == 0, added.output

    calls = await _count_loads(monkeypatch)
    result = await invoke(["task", "2", "show", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert len(payload["subentities"]) == _SUBTASK_COUNT

    assert calls[0] == 1, (
        f"expected exactly one index load for the whole invocation, got {calls[0]}"
    )


async def test_addressed_item_form_shares_one_store_identity_across_both_bridge_crossings(
    project, invoke, monkeypatch
) -> None:
    """The mechanism, not just the count. ``sq <type> <n> <verb>`` crosses the sync/async
    bridge twice — the id-resolving group callback (``_resolve``) and the leaf verb — and each
    calls ``get_service()`` (``_cli/_items.py``). A load-count assertion alone cannot tell
    "both crossings share one memoized ``Service``/``IndexStore``" apart from "each crossing
    happens to build its own store that each loads once" — both would report the same count in
    a different, coincidental scenario. So this asserts the thing the memo actually promises:
    every ``get_service()`` call observed during the invocation returns a ``Service`` whose
    ``store`` is the very same object.

    Swap the root-context anchor (``ctx.meta`` + ``call_on_close``) for a per-call scope and
    this goes red: each crossing would build its own ``Service`` again, and the recorded store
    ids would differ.
    """
    import squads._cli._items as items_mod

    created = await invoke(["create", "task", "Parent", "--author", "manager"])
    assert created.exit_code == 0, created.output

    store_ids: list[int] = []
    original_get_service = items_mod.get_service

    def spy():
        svc = original_get_service()
        store_ids.append(id(svc.store))
        return svc

    monkeypatch.setattr(items_mod, "get_service", spy)

    result = await invoke(["task", "2", "show", "--json"])
    assert result.exit_code == 0, result.output

    # Both bridge crossings (the group's id-resolving callback and the leaf ``show`` verb)
    # call ``get_service()`` — two recorded calls, and the mechanism under test is that they
    # are the *same* store, not merely two stores that each happened to load once.
    assert len(store_ids) == 2, (
        f"expected get_service() called from both bridge crossings, got {len(store_ids)}"
    )
    assert store_ids[0] == store_ids[1], (
        "the id-resolving callback and the leaf verb must share one Service/store instance, "
        f"got distinct stores {store_ids}"
    )


async def test_a_single_command_call_with_no_resolving_group_callback_loads_exactly_once(
    project, invoke, monkeypatch
) -> None:
    """The same "exactly one load" property on a second, unrelated single-``command``-call
    shape — ``sq list --json`` has no id-resolving group callback either."""
    await invoke(["create", "task", "a", "--author", "manager"])
    await invoke(["create", "task", "b", "--author", "manager"])

    calls = await _count_loads(monkeypatch)
    result = await invoke(["list", "--json"])
    assert result.exit_code == 0, result.output
    assert calls[0] == 1


async def test_show_json_payload_is_unchanged_for_a_small_item_with_no_subentities(
    project, invoke
) -> None:
    """A performance change that alters output is a different change — pin the small-item
    shape too, not only the multi-sub-entity one above."""
    await invoke(["create", "task", "Solo", "--author", "manager", "-m", "Body text."])

    r1 = await invoke(["show", "TASK-2", "--json"])
    r2 = await invoke(["show", "TASK-2", "--json"])
    assert r1.exit_code == 0 and r2.exit_code == 0
    assert r1.output == r2.output
    payload = json.loads(r1.output)
    assert payload["body"] == "Body text."
    assert payload["subentities"] == []
