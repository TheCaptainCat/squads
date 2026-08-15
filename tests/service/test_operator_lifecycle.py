"""Operator CRUD: humans as registered, assignable, authoring participants (CLAUDE.md's
Operators section). ``sq operator add`` writes a real ``OP-`` item, rejects a duplicate slug,
survives ``repair``, is a valid author/assignee (including on sub-entities), ``sq check``
accepts an operator author/assignee, an unknown slug is still rejected, the author resolves to
the operator's full name, and an operator is excluded from workload counts but is explicitly
NEVER spawnable — operators are people, not agents (cross-ref ``can_spawn``, agents only, and
the shared slug validator, both proven elsewhere).
"""

import pytest

from _helpers import create_item
from squads._itemfile import read_frontmatter
from squads._util import operator_slug

pytestmark = pytest.mark.anyio


def test_operator_slug_is_op_prefixed_from_the_first_name() -> None:
    assert operator_slug("Alice Tester") == "op-alice"
    assert operator_slug("Casey") == "op-casey"
    assert operator_slug("José García") == "op-jos"  # slugify strips non-ascii


async def test_add_operator_writes_a_real_operator_item_under_operators_not_agents(svc):
    op = await svc.add_operator("Alice Tester")
    assert op.type == "operator"
    assert op.status == "Active"
    assert op.id.startswith("OP-")
    assert op.extra.get("slug") == "op-alice"
    fm = read_frontmatter(svc.paths.abspath(op.path))
    assert fm["extra"]["slug"] == "op-alice"  # durable in frontmatter
    assert "operators/" in op.path and "agents/" not in op.path
    assert [o.id for o in await svc.list_operators()] == [op.id]


async def test_add_operator_rejects_a_duplicate_slug(svc):
    await svc.add_operator("Alice Tester")
    with pytest.raises(Exception, match="already exists"):
        await svc.add_operator("Alice Other")  # same first name -> same op-alice slug


async def test_operator_survives_repair(svc):
    op = await svc.add_operator("Alice Tester")
    await svc.repair()
    again = await svc.get(op.id)
    assert again.type == "operator" and again.extra.get("slug") == "op-alice"


async def test_operator_is_a_valid_author_and_assignee(svc):
    await svc.add_operator("Alice Tester")
    res = await svc.create("task", "Manual deploy", author="op-alice", assignee="op-alice")
    assert res.item.author == "op-alice" and res.item.assignee == "op-alice"
    await svc.update(res.item.id, assignee="manager")  # a role assignee still works too
    assert (await svc.get(res.item.id)).assignee == "manager"


async def test_operator_is_assignable_on_a_subentity(svc):
    await svc.add_operator("Alice Tester")
    task = (await create_item(svc, "task", "t")).item
    await svc.add_subtask(task.id, "Sign off the release", assignee="op-alice")
    assert (await svc.list_subtasks(task.id))[0].assignee == "op-alice"


async def test_check_accepts_an_operator_author_and_assignee(svc):
    await svc.add_operator("Alice Tester")
    await svc.create("task", "Manual deploy", author="op-alice", assignee="op-alice")
    warnings = [i for i in await svc.check() if "not a registered agent" in i.message]
    assert warnings == []


async def test_an_unknown_slug_is_still_rejected(svc):
    task = (await create_item(svc, "task", "t")).item
    with pytest.raises(Exception, match="not a registered agent or operator"):
        await svc.update(task.id, assignee="op-ghost")


async def test_author_resolves_to_the_operators_full_name(svc):
    await svc.add_operator("Alice Tester")
    assert await svc.author("op-alice") == "Alice Tester"
    task = (await create_item(svc, "task", "t")).item
    await svc.comment(task.id, ["looks good"], as_slug="op-alice")
    text = svc.paths.abspath((await svc.get(task.id)).path).read_text(encoding="utf-8")
    assert "Alice Tester:" in text  # the comment renders the full name, not the slug


async def test_author_falls_back_to_a_bundled_but_not_yet_activated_role_then_to_the_slug_itself(
    svc,
):
    # "architect" isn't a live ROLE-/OP- item yet, but is still a known predefined role.
    assert await svc.author("architect") == "Robert Architect"
    # a genuinely unknown slug degrades to itself, never raising.
    assert await svc.author("totally-unknown-slug") == "totally-unknown-slug"


async def test_operator_counts_as_work_but_is_never_spawnable(svc, project):
    await svc.add_operator("Alice Tester")
    await create_item(svc, "task", "deploy", assignee="op-alice")
    rows = {r.assignee: r for r in await svc.workload()}
    assert rows["op-alice"].open == 1  # work assigned to the human counts
    assert None not in rows  # the operator DEFINITION item itself is not counted as work
    # operators are humans, not agents: no .claude subagent pointer is ever generated
    assert not (project.root / ".claude" / "agents" / "op-alice.md").exists()
