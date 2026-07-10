"""A sub-entity title longer than the advisory threshold (120 chars) never blocks creation —
the advisory rides back on the result and into the reflog delta, names the actual length and
the body command to use instead, and is silent at or below the threshold. One shared code path
(`add_block`) backs story/subtask/finding, so the threshold math is proven once and parametrized
over the three kinds rather than tripled.
"""

import pytest

from squads._index._reflog import read_lines, reflog_path
from squads._interactions import TITLE_ADVISORY_MAX

pytestmark = pytest.mark.anyio

LONG_TITLE = "A" * (TITLE_ADVISORY_MAX + 1)
EXACT_TITLE = "A" * TITLE_ADVISORY_MAX
SHORT_TITLE = "Short title"

_KIND_SETUP = {
    "story": ("feature", lambda svc, parent_id, title: svc.add_story(parent_id, title)),
    "subtask": ("task", lambda svc, parent_id, title: svc.add_subtask(parent_id, title)),
    "finding": ("review", lambda svc, parent_id, title: svc.add_finding(parent_id, title)),
}


@pytest.mark.parametrize("kind", ["story", "subtask", "finding"])
async def test_over_threshold_title_returns_an_advisory_naming_length_and_body_command(svc, kind):
    parent_type, add = _KIND_SETUP[kind]
    parent = (await svc.create(parent_type, "p")).item
    res = await add(svc, parent.id, LONG_TITLE)
    assert res.title_advisory is not None
    assert str(len(LONG_TITLE)) in res.title_advisory
    assert "body" in res.title_advisory
    assert res.local_id in res.title_advisory
    assert res.path.exists()  # the sub-entity is created regardless (warn-and-proceed)


@pytest.mark.parametrize(
    ("kind", "title"), [(k, t) for k in _KIND_SETUP for t in (EXACT_TITLE, SHORT_TITLE)]
)
async def test_at_or_below_threshold_title_has_no_advisory(svc, kind, title):
    parent_type, add = _KIND_SETUP[kind]
    parent = (await svc.create(parent_type, "p")).item
    res = await add(svc, parent.id, title)
    assert res.title_advisory is None


async def test_advisory_wording_has_no_enforcement_language(svc):
    feat = (await svc.create("feature", "F")).item
    res = await svc.add_story(feat.id, LONG_TITLE)
    advisory = (res.title_advisory or "").lower()
    for forbidden in ("enforce", "guarantee", "secur", "forbid", "blocked", "prevented"):
        assert forbidden not in advisory


async def test_advisory_is_recorded_in_the_reflog_delta_only_when_it_fires(svc, frozen_time):
    feat = (await svc.create("feature", "F")).item
    await svc.add_story(feat.id, LONG_TITLE)
    lines = await read_lines(reflog_path(svc.paths.squad_dir))
    add_lines = [
        ln
        for ln in lines
        if ln.op == "subentity" and ln.target == feat.id and ln.delta.get("op") == "add"
    ]
    delta = add_lines[-1].delta
    assert delta["title_advisory"] == {"advisory": True, "title_len": len(LONG_TITLE)}

    task = (await svc.create("task", "T")).item
    await svc.add_subtask(task.id, SHORT_TITLE)
    lines2 = await read_lines(reflog_path(svc.paths.squad_dir))
    add_lines2 = [
        ln
        for ln in lines2
        if ln.op == "subentity" and ln.target == task.id and ln.delta.get("op") == "add"
    ]
    assert "title_advisory" not in add_lines2[-1].delta


class TestCheckSubentityTitleLengthAdvisory:
    """``sq check`` mirrors the same threshold as a warn-level (never error-level) issue."""

    async def test_over_threshold_title_emits_exactly_one_warn_issue_naming_length_and_threshold(
        self, svc
    ):
        feat = (await svc.create("feature", "F")).item
        await svc.add_story(feat.id, LONG_TITLE)
        issues = [i for i in await svc.check() if "advisory" in i.message and "chars" in i.message]
        assert len(issues) == 1
        assert issues[0].level == "warn"
        assert issues[0].item == feat.id
        assert str(len(LONG_TITLE)) in issues[0].message
        assert str(TITLE_ADVISORY_MAX) in issues[0].message

    async def test_at_threshold_and_short_titles_emit_no_advisory_issue(self, svc):
        feat = (await svc.create("feature", "F")).item
        await svc.add_story(feat.id, EXACT_TITLE)
        await svc.add_story(feat.id, SHORT_TITLE)
        issues = [i for i in await svc.check() if "advisory" in i.message and "chars" in i.message]
        assert not issues

    async def test_mixed_titles_flag_only_the_over_long_one(self, svc):
        feat = (await svc.create("feature", "F")).item
        await svc.add_story(feat.id, LONG_TITLE)
        await svc.add_story(feat.id, SHORT_TITLE)
        issues = [i for i in await svc.check() if "advisory" in i.message and "chars" in i.message]
        assert len(issues) == 1
