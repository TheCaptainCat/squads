"""Category-aware default visibility through ``Service.tree_view``: a records-category item
(e.g. a decision) stays in the default (non-``include_closed``) walk past a final-but-live
status, and only drops out once retired — while a work item keeps hiding on any terminal
status, unchanged. ``sq list``'s own default-hiding lives at the CLI layer (see
``tests/cli/test_list_tree_default_filters_and_depth_cli.py``); this covers the
``tree_view`` candidate gate directly.
"""

import pytest

pytestmark = pytest.mark.anyio


def _ids(nodes) -> set[str]:
    out: set[str] = set()
    for n in nodes:
        out.add(n.item.id)
        out |= _ids(n.children)
    return out


async def test_accepted_decision_stays_visible_by_default_while_done_feature_hides(svc):
    decision = (await svc.create("decision", "Use JWT")).item
    await svc.set_status(decision.id, "Accepted")

    feature = (await svc.create("feature", "Feat")).item
    await svc.set_status(feature.id, "InProgress")
    await svc.set_status(feature.id, "Done")

    tree_ids = _ids(await svc.tree_view())
    assert decision.id in tree_ids
    assert feature.id not in tree_ids

    # --all (include_closed) reveals both, as before.
    all_ids = _ids(await svc.tree_view(include_closed=True))
    assert {decision.id, feature.id} <= all_ids


async def test_superseded_decision_hides_by_default(svc):
    old = (await svc.create("decision", "Old choice")).item
    await svc.set_status(old.id, "Accepted")
    await svc.set_status(old.id, "Superseded")

    assert old.id not in _ids(await svc.tree_view())
    assert old.id in _ids(await svc.tree_view(include_closed=True))


async def test_deprecated_guide_hides_by_default(svc):
    guide = (await svc.create("guide", "Old guide")).item
    await svc.set_status(guide.id, "Published")
    await svc.set_status(guide.id, "Deprecated")

    assert guide.id not in _ids(await svc.tree_view())
    assert guide.id in _ids(await svc.tree_view(include_closed=True))


async def test_published_guide_stays_visible_by_default(svc):
    guide = (await svc.create("guide", "Live guide")).item
    await svc.set_status(guide.id, "Published")

    assert guide.id in _ids(await svc.tree_view())


async def test_done_task_still_hides_by_default_unchanged(svc):
    task = (await svc.create("task", "T1")).item
    await svc.set_status(task.id, "InProgress")
    await svc.set_status(task.id, "Done")

    assert task.id not in _ids(await svc.tree_view())
