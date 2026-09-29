"""A skill's real identity is its ``extra.slug``, never re-derived from the filename — the one
shared derivation both ``sq check`` and the write-path refusal call, so a hand-renamed skill
file is classified the same way by both."""

import pytest

from squads._index._resolver import item_file
from squads._models import _markers as markers

pytestmark = pytest.mark.anyio


async def test_a_hand_renamed_skill_file_is_classified_the_same_by_check_and_the_write_path(
    svc,
) -> None:
    await svc.seed_bundled_skills()
    skill = await svc.roster_item("skill", "sq-bug")
    assert skill is not None
    path = item_file(svc.paths, skill)

    renamed = path.with_name(path.name.replace("sq-bug", "bugnotes"))
    text = path.read_text(encoding="utf-8").replace(
        f"{markers.open_marker(markers.view_tag('item_skill'))}\n", ""
    )
    path.rename(renamed)
    renamed.write_text(text, encoding="utf-8")

    issues = await svc.check()
    matches = [i for i in issues if i.item == renamed.name]
    assert matches, [i.message for i in issues]
    assert any("sq skill sq-bug view add item_skill" in m.message for m in matches)


async def test_the_shared_derivation_matches_on_an_ordinary_unrenamed_skill(svc) -> None:
    """For an ordinary, unrenamed skill, both derivations already agree."""
    await svc.seed_bundled_skills()
    skill = await svc.roster_item("skill", "sq-task")
    assert skill is not None

    issues = await svc.check()

    path = item_file(svc.paths, skill)
    assert not [i for i in issues if i.item == path.name]
