"""Operator CRUD: humans as registered, assignable, authoring participants (CLAUDE.md's
Operators section). ``sq operator add`` writes a real ``OP-`` item, rejects a duplicate slug,
survives ``repair``, is a valid author/assignee (including on sub-entities), ``sq check``
accepts an operator author/assignee, an unknown slug is still rejected, the author resolves to
the operator's full name, and an operator is excluded from workload counts but is explicitly
NEVER spawnable — operators are people, not agents (cross-ref ``can_spawn``, agents only, and
the shared slug validator, both proven elsewhere).
"""

import pytest

from squads._itemfile import read_frontmatter
from squads._util import operator_slug

pytestmark = pytest.mark.anyio


def test_operator_slug_is_op_prefixed_from_the_first_name() -> None:
    assert operator_slug("Pierre Chat") == "op-pierre"
    assert operator_slug("Casey") == "op-casey"
    assert operator_slug("José García") == "op-jos"  # slugify strips non-ascii


async def test_add_operator_writes_a_real_operator_item_under_operators_not_agents(svc):
    op = await svc.add_operator("Pierre Chat")
    assert op.type == "operator"
    assert op.status == "Active"
    assert op.id.startswith("OP-")
    assert op.extra.get("slug") == "op-pierre"
    fm = read_frontmatter(svc.paths.abspath(op.path))
    assert fm["extra"]["slug"] == "op-pierre"  # durable in frontmatter
    assert "operators/" in op.path and "agents/" not in op.path
    assert [o.id for o in await svc.list_operators()] == [op.id]


async def test_add_operator_rejects_a_duplicate_slug(svc):
    await svc.add_operator("Pierre Chat")
    with pytest.raises(Exception, match="already exists"):
        await svc.add_operator("Pierre Other")  # same first name -> same op-pierre slug


async def test_operator_survives_repair(svc):
    op = await svc.add_operator("Pierre Chat")
    await svc.repair()
    again = await svc.get(op.id)
    assert again.type == "operator" and again.extra.get("slug") == "op-pierre"


async def test_operator_is_a_valid_author_and_assignee(svc):
    await svc.add_operator("Pierre Chat")
    res = await svc.create("task", "Manual deploy", author="op-pierre", assignee="op-pierre")
    assert res.item.author == "op-pierre" and res.item.assignee == "op-pierre"
    await svc.update(res.item.id, assignee="manager")  # a role assignee still works too
    assert (await svc.get(res.item.id)).assignee == "manager"


async def test_operator_is_assignable_on_a_subentity(svc):
    await svc.add_operator("Pierre Chat")
    task = (await svc.create("task", "t")).item
    await svc.add_subtask(task.id, "Sign off the release", assignee="op-pierre")
    assert (await svc.list_subtasks(task.id))[0].assignee == "op-pierre"


async def test_check_accepts_an_operator_author_and_assignee(svc):
    await svc.add_operator("Pierre Chat")
    await svc.create("task", "Manual deploy", author="op-pierre", assignee="op-pierre")
    warnings = [i for i in await svc.check() if "not a registered agent" in i.message]
    assert warnings == []


async def test_an_unknown_slug_is_still_rejected(svc):
    task = (await svc.create("task", "t")).item
    with pytest.raises(Exception, match="not a registered agent or operator"):
        await svc.update(task.id, assignee="op-ghost")


async def test_author_resolves_to_the_operators_full_name(svc):
    await svc.add_operator("Pierre Chat")
    assert await svc.author("op-pierre") == "Pierre Chat"
    task = (await svc.create("task", "t")).item
    await svc.comment(task.id, ["looks good"], as_slug="op-pierre")
    text = svc.paths.abspath((await svc.get(task.id)).path).read_text(encoding="utf-8")
    assert "Pierre Chat:" in text  # the comment renders the full name, not the slug


async def test_operator_counts_as_work_but_is_never_spawnable(svc, project):
    await svc.add_operator("Pierre Chat")
    await svc.create("task", "deploy", assignee="op-pierre")
    rows = {r.assignee: r for r in await svc.workload()}
    assert rows["op-pierre"].open == 1  # work assigned to the human counts
    assert None not in rows  # the operator DEFINITION item itself is not counted as work
    # operators are humans, not agents: no .claude subagent pointer is ever generated
    assert not (project.root / ".claude" / "agents" / "op-pierre.md").exists()
