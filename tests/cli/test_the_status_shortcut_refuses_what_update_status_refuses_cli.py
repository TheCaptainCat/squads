"""The ``status`` verb is a shortcut for ``update --status``, so it refuses the same states.

``status`` reached a mutation path of its own that never ran the per-item catalog gate, so on an
item whose parent chain forms a cycle it exited 0 and wrote the transition while
``update --status`` on the same item exited 1. The floor validator's whole point is that an item
inside a cycle is unwritable until the loop is broken; a second door around the gate makes that
untrue for the shortest verb an operator reaches for.

The refusal is only safe because the recovery route does not run through here: ``--no-parent``
nulls the parent before the gate reads it, so clearing the closing edge stays possible on an
item the gate otherwise refuses to touch. Both halves are driven below.
"""

import pytest

from _helpers import create_item
from squads import _sections as sections
from squads._index._resolver import item_file
from squads._itemfile import read_frontmatter
from squads._models._item import Item

pytestmark = pytest.mark.anyio


async def _mutual_cycle_on_disk(svc) -> tuple[Item, Item]:
    """A two-item cycle written straight into frontmatter, then indexed by ``repair``.

    No gate ever sees it — which is the only way to build one now, and the shape an adopted or
    hand-edited corpus arrives in.
    """
    first = (await create_item(svc, "bug", "Alpha")).item
    second = (await create_item(svc, "review", "Beta")).item
    for item, parent_id in ((first, second.id), (second, first.id)):
        path = item_file(svc.paths, item)
        text = path.read_text(encoding="utf-8")
        fm = read_frontmatter(text=text)
        fm["parent"] = parent_id
        path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")
    await svc.repair()
    return first, second


async def test_the_status_verb_refuses_an_item_whose_parent_chain_forms_a_cycle(svc, invoke):
    first, second = await _mutual_cycle_on_disk(svc)
    before = (await svc.get(first.id)).status

    result = await invoke(["bug", str(first.sequence_id), "status", "InProgress"])

    assert result.exit_code != 0, result.output
    assert "forms a cycle" in result.output
    assert "--no-parent" in result.output
    assert second.id in result.output
    assert (await svc.get(first.id)).status == before


async def test_the_status_verb_and_update_status_agree_on_the_same_item(svc, invoke):
    """The verb documents itself as a shortcut for ``update --status``; the two exit alike."""
    first, _second = await _mutual_cycle_on_disk(svc)

    shortcut = await invoke(["bug", str(first.sequence_id), "status", "InProgress"])
    long_form = await invoke(["bug", str(first.sequence_id), "update", "--status", "InProgress"])

    assert shortcut.exit_code != 0, shortcut.output
    assert long_form.exit_code != 0, long_form.output
    assert "forms a cycle" in shortcut.output
    assert "forms a cycle" in long_form.output


async def test_force_does_not_carry_the_status_verb_past_the_gate(svc, invoke):
    """``--force`` overrides the lifecycle's own transition edge, never the catalog."""
    first, _second = await _mutual_cycle_on_disk(svc)
    before = (await svc.get(first.id)).status

    result = await invoke(["bug", str(first.sequence_id), "status", "InProgress", "--force"])

    assert result.exit_code != 0, result.output
    assert "forms a cycle" in result.output
    assert (await svc.get(first.id)).status == before


async def test_an_item_outside_the_cycle_still_transitions_through_the_status_verb(svc, invoke):
    """The refusal is about the item's own parent chain, not about the corpus holding a cycle
    somewhere: an unrelated item transitions exactly as before."""
    await _mutual_cycle_on_disk(svc)
    bystander = (await create_item(svc, "bug", "Bystander")).item

    result = await invoke(["bug", str(bystander.sequence_id), "status", "InProgress"])

    assert result.exit_code == 0, result.output
    assert (await svc.get(bystander.id)).status == "InProgress"


async def test_clearing_the_closing_edge_reopens_the_status_verb(svc, invoke):
    """The recovery route the refusal names, driven end to end through the CLI. It survives the
    new gate because ``--no-parent`` nulls the parent before the gate reads it."""
    first, second = await _mutual_cycle_on_disk(svc)

    cleared = await invoke(["review", str(second.sequence_id), "update", "--no-parent"])
    assert cleared.exit_code == 0, cleared.output
    assert (await svc.get(second.id)).parent is None

    result = await invoke(["bug", str(first.sequence_id), "status", "InProgress"])
    assert result.exit_code == 0, result.output
    assert (await svc.get(first.id)).status == "InProgress"


async def test_the_roster_status_verb_reaches_the_same_gate(svc, invoke):
    """The roster ``status`` verb calls its own service entry point, and the roster types are
    the one category whose status axis is unreachable through ``update`` at all — so if the gate
    lived on the update seam instead of the shared transition core, this door would stay open.
    """
    entry = await svc.add_operator("Reviewer Of Record", slug="rec")
    path = item_file(svc.paths, entry)
    text = path.read_text(encoding="utf-8")
    fm = read_frontmatter(text=text)
    fm["parent"] = entry.id  # a self-parent: the shortest cycle there is
    path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")
    await svc.repair()
    before = (await svc.get(entry.id)).status

    result = await invoke(["operator", "rec", "status", "Archived"])

    assert result.exit_code != 0, result.output
    assert "forms a cycle" in result.output
    assert (await svc.get(entry.id)).status == before
