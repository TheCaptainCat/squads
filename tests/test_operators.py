"""Operator items: humans as registered, assignable, authoring participants."""

import json

import pytest

from squads._cli import app
from squads._itemfile import read_frontmatter
from squads._models._enums import ItemType, Status
from squads._util import operator_slug

# --------------------------------------------------------------------------- slug rule


def test_operator_slug_is_op_prefixed_first_name():
    assert operator_slug("Pierre Chat") == "op-pierre"
    assert operator_slug("Casey") == "op-casey"
    assert operator_slug("José García") == "op-jos"  # slugify strips non-ascii


# --------------------------------------------------------------------------- model (service)


def test_add_operator_writes_operator_item(svc):
    op = svc.add_operator("Pierre Chat")
    assert op.type is ItemType.OPERATOR
    assert op.status is Status.ACTIVE
    assert op.id.startswith("OP-")
    assert op.extra.get("slug") == "op-pierre"
    fm = read_frontmatter(svc.paths.abspath(op.path))
    assert fm["extra"]["slug"] == "op-pierre"  # durable in frontmatter
    # lives under operators/, not agents/
    assert "operators/" in op.path and "agents/" not in op.path
    assert [o.id for o in svc.list_operators()] == [op.id]


def test_add_operator_rejects_duplicate_slug(svc):
    svc.add_operator("Pierre Chat")
    with pytest.raises(Exception, match="already exists"):
        svc.add_operator("Pierre Other")  # same first name → same op-pierre slug


def test_operator_survives_repair(svc):
    op = svc.add_operator("Pierre Chat")
    svc.repair()  # rebuild the index purely from frontmatter
    again = svc.get(op.id)
    assert again.type is ItemType.OPERATOR and again.extra.get("slug") == "op-pierre"


# --------------------------------------------------------------------------- gates


def test_operator_is_a_valid_author_and_assignee(svc):
    svc.add_operator("Pierre Chat")
    res = svc.create(ItemType.TASK, "Manual deploy", author="op-pierre", assignee="op-pierre")
    assert res.item.author == "op-pierre" and res.item.assignee == "op-pierre"
    # and on update
    svc.update(res.item.id, assignee="manager")  # a role still works (no regression)
    assert svc.get(res.item.id).assignee == "manager"


def test_operator_assignable_on_subentities(svc):
    svc.add_operator("Pierre Chat")
    task = svc.create(ItemType.TASK, "t").item
    svc.add_subtask(task.id, "Sign off the release", assignee="op-pierre")
    assert svc.list_subtasks(task.id)[0].assignee == "op-pierre"


def test_unknown_slug_still_rejected(svc):
    task = svc.create(ItemType.TASK, "t").item
    with pytest.raises(Exception, match="not a registered agent or operator"):
        svc.update(task.id, assignee="op-ghost")


# --------------------------------------------------------------------------- display


def test_author_resolves_operator_full_name(svc):
    svc.add_operator("Pierre Chat")
    assert svc.author("op-pierre") == "Pierre Chat"
    task = svc.create(ItemType.TASK, "t").item
    svc.comment(task.id, ["looks good"], as_slug="op-pierre")
    text = svc.paths.abspath(svc.get(task.id).path).read_text(encoding="utf-8")
    assert "Pierre Chat:" in text  # the comment renders the full name, not the slug


# --------------------------------------------------------------------------- surfaces


def test_operator_not_counted_in_workload_but_is_not_spawnable(svc, project):
    svc.add_operator("Pierre Chat")
    svc.create(ItemType.TASK, "deploy", assignee="op-pierre")
    rows = {r.assignee: r for r in svc.workload()}
    assert rows["op-pierre"].open == 1  # work assigned to the human counts
    assert None not in rows  # the operator *definition* item is not counted as work
    # operators are humans, not agents: no .claude subagent pointer is generated
    assert not (project.claude_dir / "agents" / "op-pierre.md").exists()


# --------------------------------------------------------------------------- CLI


def test_operator_cli_add_list_and_assign(project, runner):
    add = runner.invoke(app, ["operator", "add", "Pierre Chat"])
    assert add.exit_code == 0 and "op-pierre" in add.output
    listed = runner.invoke(app, ["operator", "list"])
    assert "Pierre Chat" in listed.output and "op-pierre" in listed.output
    # assign a task to the human end to end
    runner.invoke(app, ["create", "task", "Manual step", "--author", "manager"])
    upd = runner.invoke(app, ["task", "3", "update", "--assignee", "op-pierre"])
    assert upd.exit_code == 0
    j = json.loads(runner.invoke(app, ["task", "3", "show", "--json"]).output)
    assert j["assignee"] == "op-pierre"
