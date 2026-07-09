"""Priority field, hide-closed defaults, and the search / blocked / workload / mine views."""

import pytest

from squads._itemfile import read_frontmatter
from squads._models._enums import Priority, Status

pytestmark = pytest.mark.anyio

# --------------------------------------------------------------------------- priority (service)


async def test_create_with_priority_writes_frontmatter(svc):
    res = await svc.create("task", "Token validation", priority=Priority.HIGH)
    assert res.item.priority is Priority.HIGH
    fm = read_frontmatter(res.path)
    assert fm["priority"] == "high"


async def test_create_without_priority_omits_it(svc):
    res = await svc.create("task", "no prio")
    assert res.item.priority is None
    assert "priority" not in read_frontmatter(res.path)


async def test_update_sets_and_clears_priority(svc):
    res = await svc.create("task", "t")
    await svc.update(res.item.id, priority=Priority.URGENT)
    assert read_frontmatter(res.path)["priority"] == "urgent"
    assert (await svc.get(res.item.id)).priority is Priority.URGENT
    await svc.update(res.item.id, clear_priority=True)
    assert "priority" not in read_frontmatter(res.path)
    assert (await svc.get(res.item.id)).priority is None


async def test_list_filters_by_priority(svc):
    hi = await svc.create("task", "hi", priority=Priority.HIGH)
    await svc.create("task", "lo", priority=Priority.LOW)
    got = await svc.list_items(priority=Priority.HIGH)
    assert [i.id for i in got] == [hi.item.id]


async def test_priority_survives_repair(svc):
    """Frontmatter is the source of truth: a rebuilt index keeps the priority."""
    res = await svc.create("bug", "b", priority=Priority.MEDIUM)
    await svc.repair()
    assert (await svc.get(res.item.id)).priority is Priority.MEDIUM


# --------------------------------------------------------------------------- search


async def test_search_matches_title_and_body(svc):
    res = await svc.create("task", "Token validation")
    await svc.set_body(res.item.id, "Validate the JWT expiry and signature.")
    by_title = await svc.search("token")
    assert [i.id for i, _ in by_title] == [res.item.id]
    by_body = await svc.search("expiry")
    assert res.item.id in [i.id for i, _ in by_body]
    assert await svc.search("nonexistent-needle") == []


# --------------------------------------------------------------------------- blocked


async def test_blocked_view(svc):
    a = (await svc.create("task", "blocked one")).item
    b = (await svc.create("task", "the blocker")).item
    await svc.add_ref(b.id, a.id, kind="blocks")  # "B blocks A" → A is blocked while B is open
    rows = await svc.blocked()
    assert [(t.id, [x.id for x in bs]) for t, bs in rows] == [(a.id, [b.id])]
    # closing the blocker clears it
    await svc.set_status(b.id, Status.IN_PROGRESS)
    await svc.set_status(b.id, Status.DONE)
    assert await svc.blocked() == []


# --------------------------------------------------------------------------- workload


async def test_workload_counts_open_and_closed(svc):
    await svc.create("task", "t1", assignee="manager")
    done = (await svc.create("task", "t2", assignee="manager")).item
    await svc.set_status(done.id, Status.IN_PROGRESS)
    await svc.set_status(done.id, Status.DONE)
    await svc.create("task", "unassigned")
    rows = {r.assignee: r for r in await svc.workload()}
    assert rows["manager"].open == 1 and rows["manager"].closed == 1 and rows["manager"].total == 2
    assert rows[None].open == 1


# --------------------------------------------------------------------------- CLI smoke


async def test_priority_cli(project, invoke):
    await invoke(["create", "task", "T", "--author", "manager", "--priority", "high"])
    shown = await invoke(["task", "2", "show"])
    assert shown.exit_code == 0 and "high" in shown.output
    listed = await invoke(["list", "--priority", "high"])
    assert "TASK-2" in listed.output
    none = await invoke(["list", "--priority", "low"])
    assert "no items" in none.output


async def test_priority_cli_rejects_unknown(project, invoke):
    r = await invoke(["create", "task", "T", "--author", "manager", "--priority", "huge"])
    assert r.exit_code == 1 and "unknown priority" in r.output


async def test_hide_closed_in_list_and_tree(project, invoke):
    await invoke(["create", "task", "Open one", "--author", "manager"])
    await invoke(["create", "task", "Closed one", "--author", "manager"])
    await invoke(["task", "3", "status", "InProgress"])
    await invoke(["task", "3", "status", "Done"])
    default = await invoke(["list", "--type", "task"])
    assert "TASK-2" in default.output and "TASK-3" not in default.output
    with_all = await invoke(["list", "--type", "task", "--all"])
    assert "TASK-3" in with_all.output
    by_status = await invoke(["list", "--status", "Done"])
    assert "TASK-3" in by_status.output
    tree_default = await invoke(["tree"])
    assert "TASK-3" not in tree_default.output
    tree_all = await invoke(["tree", "--all"])
    assert "TASK-3" in tree_all.output


async def test_search_cli(project, invoke):
    await invoke(["create", "task", "Token validation", "--author", "manager"])
    r = await invoke(["search", "token"])
    assert r.exit_code == 0 and "TASK-2" in r.output
    j = await invoke(["search", "token", "--json"])
    import json

    assert json.loads(j.output)[0]["id"] == "TASK-2"


async def test_blocked_and_workload_cli(project, invoke):
    await invoke(["create", "task", "A", "--author", "manager", "--assignee", "manager"])
    await invoke(["create", "task", "B", "--author", "manager"])
    await invoke(["task", "3", "ref", "add", "TASK-000002", "--kind", "blocks"])
    blocked = await invoke(["blocked"])
    assert "TASK-2" in blocked.output and "blocked by" in blocked.output
    work = await invoke(["workload", "--json"])
    import json

    rows = {r["assignee"]: r for r in json.loads(work.output)}
    assert rows["manager"]["open"] == 1


async def test_mine_cli(project, invoke):
    await invoke(["create", "task", "Mine", "--author", "manager", "--assignee", "manager"])
    # slug is now required; pass manager explicitly
    r = await invoke(["mine", "manager"])
    assert "TASK-2" in r.output
    # unknown slug is an error (exit 1) — bare sq mine is also an error
    bare = await invoke(["mine"])
    assert bare.exit_code != 0
    unknown = await invoke(["mine", "ghost"])
    assert unknown.exit_code == 1 and "unknown slug" in unknown.output


async def test_tree_priority_dot_separator(project, invoke):
    """BUG-000030: sq tree human rendering separates priority and title with a middle dot."""
    await invoke(
        ["create", "task", "My important task", "--author", "manager", "--priority", "high"],
    )
    out = (await invoke(["tree"])).output
    assert "·" in out, f"middle dot separator missing from tree output: {out!r}"
    # priority badge and title should be separated by ' · ' not a bare space
    assert "high · My important task" in out
    # --json surface is untouched (no dot in priority value)
    import json

    all_nodes = json.loads((await invoke(["tree", "--json"])).output)

    def find_node(nodes: list[dict[str, object]], item_id: str) -> dict[str, object] | None:
        for n in nodes:
            if n["id"] == item_id:
                return n
            hit = find_node(list(n["children"]), item_id)  # type: ignore[arg-type]
            if hit:
                return hit
        return None

    task_node = find_node(all_nodes, "TASK-2")
    assert task_node is not None
    assert task_node["priority"] == "high"
    assert "·" not in str(task_node["priority"])
