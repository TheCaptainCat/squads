"""Priority field, hide-closed defaults, and the search / blocked / workload / mine views."""

from squads._cli import app
from squads._itemfile import read_frontmatter
from squads._models._enums import ItemType, Priority, Status

# --------------------------------------------------------------------------- priority (service)


def test_create_with_priority_writes_frontmatter(svc):
    res = svc.create(ItemType.TASK, "Token validation", priority=Priority.HIGH)
    assert res.item.priority is Priority.HIGH
    fm = read_frontmatter(res.path)
    assert fm["priority"] == "high"


def test_create_without_priority_omits_it(svc):
    res = svc.create(ItemType.TASK, "no prio")
    assert res.item.priority is None
    assert "priority" not in read_frontmatter(res.path)


def test_update_sets_and_clears_priority(svc):
    res = svc.create(ItemType.TASK, "t")
    svc.update(res.item.id, priority=Priority.URGENT)
    assert read_frontmatter(res.path)["priority"] == "urgent"
    assert svc.get(res.item.id).priority is Priority.URGENT
    svc.update(res.item.id, clear_priority=True)
    assert "priority" not in read_frontmatter(res.path)
    assert svc.get(res.item.id).priority is None


def test_list_filters_by_priority(svc):
    hi = svc.create(ItemType.TASK, "hi", priority=Priority.HIGH)
    svc.create(ItemType.TASK, "lo", priority=Priority.LOW)
    got = svc.list_items(priority=Priority.HIGH)
    assert [i.id for i in got] == [hi.item.id]


def test_priority_survives_repair(svc):
    """Frontmatter is the source of truth: a rebuilt index keeps the priority."""
    res = svc.create(ItemType.BUG, "b", priority=Priority.MEDIUM)
    svc.repair()
    assert svc.get(res.item.id).priority is Priority.MEDIUM


# --------------------------------------------------------------------------- search


def test_search_matches_title_and_body(svc):
    res = svc.create(ItemType.TASK, "Token validation")
    svc.set_body(res.item.id, "Validate the JWT expiry and signature.")
    by_title = svc.search("token")
    assert [i.id for i, _ in by_title] == [res.item.id]
    by_body = svc.search("expiry")
    assert res.item.id in [i.id for i, _ in by_body]
    assert svc.search("nonexistent-needle") == []


# --------------------------------------------------------------------------- blocked


def test_blocked_view(svc):
    a = svc.create(ItemType.TASK, "blocked one").item
    b = svc.create(ItemType.TASK, "the blocker").item
    svc.add_ref(b.id, a.id, kind="blocks")  # "B blocks A" → A is blocked while B is open
    rows = svc.blocked()
    assert [(t.id, [x.id for x in bs]) for t, bs in rows] == [(a.id, [b.id])]
    # closing the blocker clears it
    svc.set_status(b.id, Status.IN_PROGRESS)
    svc.set_status(b.id, Status.DONE)
    assert svc.blocked() == []


# --------------------------------------------------------------------------- workload


def test_workload_counts_open_and_closed(svc):
    svc.create(ItemType.TASK, "t1", assignee="manager")
    done = svc.create(ItemType.TASK, "t2", assignee="manager").item
    svc.set_status(done.id, Status.IN_PROGRESS)
    svc.set_status(done.id, Status.DONE)
    svc.create(ItemType.TASK, "unassigned")
    rows = {r.assignee: r for r in svc.workload()}
    assert rows["manager"].open == 1 and rows["manager"].closed == 1 and rows["manager"].total == 2
    assert rows[None].open == 1


# --------------------------------------------------------------------------- CLI smoke


def test_priority_cli(project, runner):
    runner.invoke(app, ["create", "task", "T", "--author", "manager", "--priority", "high"])
    shown = runner.invoke(app, ["task", "2", "show"])
    assert shown.exit_code == 0 and "high" in shown.output
    listed = runner.invoke(app, ["list", "--priority", "high"])
    assert "TASK-000002" in listed.output
    none = runner.invoke(app, ["list", "--priority", "low"])
    assert "no items" in none.output


def test_priority_cli_rejects_unknown(project, runner):
    r = runner.invoke(app, ["create", "task", "T", "--author", "manager", "--priority", "huge"])
    assert r.exit_code == 1 and "unknown priority" in r.output


def test_hide_closed_in_list_and_tree(project, runner):
    runner.invoke(app, ["create", "task", "Open one", "--author", "manager"])
    runner.invoke(app, ["create", "task", "Closed one", "--author", "manager"])
    runner.invoke(app, ["task", "3", "status", "InProgress"])
    runner.invoke(app, ["task", "3", "status", "Done"])
    default = runner.invoke(app, ["list", "--type", "task"])
    assert "TASK-000002" in default.output and "TASK-000003" not in default.output
    with_all = runner.invoke(app, ["list", "--type", "task", "--all"])
    assert "TASK-000003" in with_all.output
    by_status = runner.invoke(app, ["list", "--status", "Done"])
    assert "TASK-000003" in by_status.output
    tree_default = runner.invoke(app, ["tree"])
    assert "TASK-000003" not in tree_default.output
    tree_all = runner.invoke(app, ["tree", "--all"])
    assert "TASK-000003" in tree_all.output


def test_search_cli(project, runner):
    runner.invoke(app, ["create", "task", "Token validation", "--author", "manager"])
    r = runner.invoke(app, ["search", "token"])
    assert r.exit_code == 0 and "TASK-000002" in r.output
    j = runner.invoke(app, ["search", "token", "--json"])
    import json

    assert json.loads(j.output)[0]["id"] == "TASK-000002"


def test_blocked_and_workload_cli(project, runner):
    runner.invoke(app, ["create", "task", "A", "--author", "manager", "--assignee", "manager"])
    runner.invoke(app, ["create", "task", "B", "--author", "manager"])
    runner.invoke(app, ["task", "3", "ref", "add", "TASK-000002", "--kind", "blocks"])
    blocked = runner.invoke(app, ["blocked"])
    assert "TASK-000002" in blocked.output and "blocked by" in blocked.output
    work = runner.invoke(app, ["workload", "--json"])
    import json

    rows = {r["assignee"]: r for r in json.loads(work.output)}
    assert rows["manager"]["open"] == 1


def test_mine_cli(project, runner):
    runner.invoke(app, ["create", "task", "Mine", "--author", "manager", "--assignee", "manager"])
    # slug is now required; pass manager explicitly
    r = runner.invoke(app, ["mine", "manager"])
    assert "TASK-000002" in r.output
    # unknown slug is an error (exit 1) — bare sq mine is also an error
    bare = runner.invoke(app, ["mine"])
    assert bare.exit_code != 0
    unknown = runner.invoke(app, ["mine", "ghost"])
    assert unknown.exit_code == 1 and "unknown slug" in unknown.output


def test_tree_priority_dot_separator(project, runner):
    """BUG-000030: sq tree human rendering separates priority and title with a middle dot."""
    runner.invoke(
        app,
        ["create", "task", "My important task", "--author", "manager", "--priority", "high"],
    )
    out = runner.invoke(app, ["tree"]).output
    assert "·" in out, f"middle dot separator missing from tree output: {out!r}"
    # priority badge and title should be separated by ' · ' not a bare space
    assert "high · My important task" in out
    # --json surface is untouched (no dot in priority value)
    import json

    all_nodes = json.loads(runner.invoke(app, ["tree", "--json"]).output)

    def find_node(nodes: list[dict[str, object]], item_id: str) -> dict[str, object] | None:
        for n in nodes:
            if n["id"] == item_id:
                return n
            hit = find_node(list(n["children"]), item_id)  # type: ignore[arg-type]
            if hit:
                return hit
        return None

    task_node = find_node(all_nodes, "TASK-000002")
    assert task_node is not None
    assert task_node["priority"] == "high"
    assert "·" not in str(task_node["priority"])
