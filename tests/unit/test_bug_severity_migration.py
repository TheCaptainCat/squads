"""Schema 0.7 -> 0.8 runner: relocate a bug's item-level severity from `extra` to a top-level
key. A pure file transform — driven directly against a hand-built bug file, no live squad
needed (the runner only ever touches `paths.squad_dir / "bugs"`).
"""

from squads._migrations import _v0_7_to_v0_8
from squads._models._config import SquadsConfig
from squads._paths import SquadPaths
from squads._sections import replace_frontmatter, split_frontmatter

_BODY = "<!-- sq:body -->\nsome body\n<!-- sq:body:end -->\n"


def _paths(tmp_path) -> SquadPaths:
    return SquadPaths(root=tmp_path, squad_dir=tmp_path, config=SquadsConfig())


def _write_bug(tmp_path, seq: int, fm: dict[str, object]) -> None:
    bugs = tmp_path / "bugs"
    bugs.mkdir(exist_ok=True)
    text = replace_frontmatter(_BODY, {"id": f"BUG-{seq}", "sequence_id": seq, **fm})
    (bugs / f"BUG-{seq:06d}-x.md").write_text(text, encoding="utf-8")


def test_migrate_relocates_legacy_severity_and_drops_the_now_empty_extra_map(tmp_path):
    paths = _paths(tmp_path)
    _write_bug(tmp_path, 1, {"extra": {"severity": "critical"}})

    changed = _v0_7_to_v0_8.migrate(paths)
    assert changed == 1

    fm, _ = split_frontmatter((tmp_path / "bugs" / "BUG-000001-x.md").read_text())
    assert fm["severity"] == "critical"
    assert "extra" not in fm

    assert _v0_7_to_v0_8.migrate(paths) == 0  # idempotent


def test_migrate_preserves_other_extra_keys(tmp_path):
    paths = _paths(tmp_path)
    _write_bug(tmp_path, 1, {"extra": {"severity": "high", "other": "kept"}})

    changed = _v0_7_to_v0_8.migrate(paths)
    assert changed == 1

    fm, _ = split_frontmatter((tmp_path / "bugs" / "BUG-000001-x.md").read_text())
    assert fm["severity"] == "high"
    assert fm["extra"] == {"other": "kept"}


def test_migrate_does_not_overwrite_an_already_set_top_level_severity(tmp_path):
    """The top-level value wins over a stale, disagreeing legacy extra copy."""
    paths = _paths(tmp_path)
    _write_bug(tmp_path, 1, {"severity": "low", "extra": {"severity": "critical"}})

    changed = _v0_7_to_v0_8.migrate(paths)
    assert changed == 1

    fm, _ = split_frontmatter((tmp_path / "bugs" / "BUG-000001-x.md").read_text())
    assert fm["severity"] == "low"
    assert "extra" not in fm


def test_migrate_is_a_noop_with_no_legacy_extra_severity(tmp_path):
    paths = _paths(tmp_path)
    _write_bug(tmp_path, 1, {"severity": "low"})
    assert _v0_7_to_v0_8.migrate(paths) == 0


def test_migrate_only_walks_the_bugs_folder(tmp_path):
    """A non-bug type folder alongside `bugs/` is left completely untouched."""
    paths = _paths(tmp_path)
    _write_bug(tmp_path, 1, {"extra": {"severity": "high"}})

    tasks = tmp_path / "tasks"
    tasks.mkdir()
    task_text = replace_frontmatter(
        _BODY, {"id": "TASK-2", "sequence_id": 2, "extra": {"severity": "high"}}
    )
    task_path = tasks / "TASK-000002-x.md"
    task_path.write_text(task_text, encoding="utf-8")

    changed = _v0_7_to_v0_8.migrate(paths)
    assert changed == 1  # only the bug
    fm, _ = split_frontmatter(task_path.read_text())
    assert fm["extra"] == {"severity": "high"}  # untouched — not a bug file
