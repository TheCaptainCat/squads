"""What the daemon keeps of the files it parsed is keyed by their content: a file rewritten behind
its back, to the same size and with its timestamp restored, is read back as it now is."""

import os
from pathlib import Path

from squads._paths import SquadPaths
from tests._daemon_harness import Served, serve_squad
from tests.check._arrange import write_override

RETITLED = ("Alpha beta", "Alpha beto")


def rewrite_in_place(path: Path, old: str, new: str) -> None:
    """Replace *old* by *new*, of the same length, and give the file its timestamps back."""
    assert len(old) == len(new)
    before = path.stat()
    path.write_text(path.read_text(encoding="utf-8").replace(old, new, 1), encoding="utf-8")
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    assert (path.stat().st_size, path.stat().st_mtime_ns) == (before.st_size, before.st_mtime_ns)


def make_task(daemon: Served, title: str) -> str:
    made = daemon.request(
        "POST", "/v1/items", {"type": "task", "title": title, "author": "manager"}
    )
    return str(made.json()["data"]["path"])


def drift_messages(daemon: Served) -> list[str]:
    report = daemon.get("/v1/check").json()["data"]["items"]
    return [row["message"] for row in report if row["rule"] == "frontmatter_matches_index"]


def test_an_item_file_rewritten_to_the_same_size_and_time_is_read_as_it_is_now(
    project: SquadPaths, serve
) -> None:
    daemon = serve(project)
    item = project.squad_dir / make_task(daemon, RETITLED[0])
    assert drift_messages(daemon) == []
    rewrite_in_place(item, *RETITLED)
    assert drift_messages(daemon) == [
        "title drift between frontmatter and index; run `sq repair` before this item is "
        "mutated again, or the fix is lost silently"
    ]


def test_an_index_rewritten_to_the_same_size_and_time_is_read_as_it_is_now(
    project: SquadPaths, serve
) -> None:
    daemon = serve(project)
    make_task(daemon, RETITLED[0])
    assert daemon.get("/v1/items/TASK-2").json()["data"]["title"] == RETITLED[0]
    rewrite_in_place(project.squad_dir / ".squads.json", *RETITLED)
    assert daemon.get("/v1/items/TASK-2").json()["data"]["title"] == RETITLED[1]


def test_a_refused_override_check_is_answered_once_the_index_changes(project: SquadPaths) -> None:
    with serve_squad(project) as first:
        make_task(first, "Held")
    write_override(project, "workflow.toml", '[items.task]\nprefix = "JOB"\n')
    with serve_squad(project) as daemon:
        refused = daemon.get("/v1/items")
        assert refused.status != 200
        assert "incompatible with the live index" in refused.body.decode()
        index = project.squad_dir / ".squads.json"
        index.write_text(index.read_text(encoding="utf-8").replace('"TASK-2"', '"x"'))
        assert daemon.get("/v1/items").status == 200


def test_an_entry_for_a_file_that_is_gone_is_dropped_by_the_corpus_walks_that_follow(
    project: SquadPaths, serve
) -> None:
    daemon = serve(project)
    item = project.squad_dir / make_task(daemon, "Doomed")
    daemon.get("/v1/check")
    assert any(key.endswith(item.name) for key in daemon.state.parse_cache.item_files())
    item.unlink()
    for _ in range(3):
        daemon.get("/v1/check")
    assert not any(key.endswith(item.name) for key in daemon.state.parse_cache.item_files())
