"""`Service.check()`'s two vocabulary-drift warnings: an edge whose stored kind isn't in the
active spec's ref-kind vocabulary, and a decision left at a "superseded" status with no
incoming `supersedes` edge to justify it. Both are warn-level — they never flip `sq check`'s
exit code (proven generically elsewhere); this file proves the two rules actually fire.
"""

import pytest

from squads import _sections as sections
from squads._itemfile import read_frontmatter

pytestmark = pytest.mark.anyio


async def test_check_warns_on_an_unknown_ref_kind(svc):
    a = (await svc.create("task", "a")).item
    b = (await svc.create("task", "b")).item

    # Inject a kind outside the vocabulary directly into frontmatter, bypassing add_ref's
    # own validation (the only way an unknown kind reaches disk).
    path = svc.paths.abspath((await svc.get(a.id)).path)
    text = path.read_text(encoding="utf-8")
    fm = read_frontmatter(text=text)
    fm["refs"] = [f"{b.id}:not-a-real-kind"]
    path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")
    await svc.repair()  # sync the index with the rewritten frontmatter

    issues = await svc.check()
    hits = [i for i in issues if i.level == "warn" and "not-a-real-kind" in i.message]
    assert len(hits) == 1
    assert hits[0].item == a.id


async def test_check_warns_on_a_superseded_decision_with_no_incoming_edge(svc):
    old_adr = (await svc.create("decision", "old decision")).item
    await svc.set_status(old_adr.id, "Proposed")
    await svc.set_status(old_adr.id, "Superseded", force=True)

    issues = await svc.check()
    hits = [
        i
        for i in issues
        if i.level == "warn" and "supersedes" in i.message and i.item == old_adr.id
    ]
    assert len(hits) == 1


async def test_check_does_not_warn_when_the_supersedes_edge_is_present(svc):
    old_adr = (await svc.create("decision", "old decision")).item
    new_adr = (await svc.create("decision", "new decision")).item

    await svc.set_status(old_adr.id, "Proposed")
    await svc.set_status(old_adr.id, "Superseded", force=True)
    await svc.add_ref(new_adr.id, old_adr.id, kind="supersedes")

    issues = await svc.check()
    hits = [
        i
        for i in issues
        if i.level == "warn" and "supersedes" in i.message and i.item == old_adr.id
    ]
    assert not hits
