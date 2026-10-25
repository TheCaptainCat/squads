"""Two item files carrying one id are reported by ``check`` and ``repair``, never resolved by
scan order; ``repair --renumber`` renumbers only files whose slugs all differ and lists, without
changing, every reference to the old id. Reads warn and writes refuse."""

from collections.abc import Callable
from pathlib import Path

import pytest

from _helpers import make_service
from squads._errors import SquadsError
from squads._sections import replace_frontmatter, split_frontmatter
from squads._services import _service as service

pytestmark = pytest.mark.anyio


@pytest.fixture
async def svc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal")
    return make_service(result.paths)


def _copy(md: Path, *, name: str | None = None, folder: Path | None = None, **fm_changes: object):
    """Write a copy of *md* (optionally renamed, moved, with frontmatter changes)."""
    text = md.read_text(encoding="utf-8")
    if fm_changes:
        fm = split_frontmatter(text)[0]
        fm.update(fm_changes)
        text = replace_frontmatter(text, fm)
    target = (folder or md.parent) / (name or md.name)
    target.write_text(text, encoding="utf-8", newline="")
    return target


async def _task(svc, title: str = "Alpha"):
    created = await svc.create("task", title, author="manager")
    return created.item, created.path


class Row:
    """One duplicate shape: how to build it and what the verbs should do with it."""

    def __init__(
        self, name: str, build: Callable[..., list[Path]], refused: bool, skill: bool = False
    ) -> None:
        self.name, self.build, self.refused, self.skill = name, build, refused, skill


def _different_slug_by_filename(svc, md):
    return [_copy(md, name=md.name.replace(".md", "-copy.md"))]


def _whitespace_copy(svc, md):
    target = _copy(md, name=md.name.replace(".md", "-copy.md"))
    target.write_text(target.read_text(encoding="utf-8") + "  \n", encoding="utf-8", newline="")
    return [target]


def _different_slug(svc, md):
    return [_copy(md, name=md.name.replace("alpha", "other"), slug="other", title="other")]


def _other_folder(svc, md):
    bugs = svc.paths.squad_dir / "bugs"
    bugs.mkdir(exist_ok=True)
    return [_copy(md, folder=bugs)]


def _padded_spelling(svc, md):
    fm = split_frontmatter(md.read_text(encoding="utf-8"))[0]
    number = int(fm["sequence_id"])
    padded = f"TASK-{number:06d}"
    return [_copy(md, name=f"TASK-{number}-alpha.md", id=padded)]


def _three_different(svc, md):
    return [
        _copy(md, name=md.name.replace("alpha", "other"), slug="other", title="other"),
        _copy(md, name=md.name.replace("alpha", "third"), slug="third", title="third"),
    ]


def _three_mixed(svc, md):
    (svc.paths.squad_dir / "bugs").mkdir(exist_ok=True)
    return [
        _copy(md, name=md.name.replace("alpha", "other"), slug="other", title="other"),
        _copy(md, folder=svc.paths.squad_dir / "bugs"),
    ]


_ROWS = [
    pytest.param(Row("copy", _different_slug_by_filename, True), id="identical-copy-renamed"),
    pytest.param(Row("spaced", _whitespace_copy, False), id="copy-differing-by-trailing-space"),
    pytest.param(Row("different-slug", _different_slug, False), id="different-slug-shadow"),
    pytest.param(Row("other-folder", _other_folder, True), id="other-type-folder"),
    pytest.param(Row("padded", _padded_spelling, True), id="padded-and-unpadded-spelling"),
    pytest.param(Row("three-different", _three_different, False), id="three-files-all-different"),
    pytest.param(Row("three-mixed", _three_mixed, True), id="three-files-mixed-slugs"),
]


async def _group(svc, row: Row):
    item, md = await _task(svc)
    copies = row.build(svc, md)
    return item, [md, *copies]


def _rel(svc, md: Path) -> str:
    return md.relative_to(svc.paths.squad_dir).as_posix()


@pytest.mark.parametrize("row", _ROWS)
async def test_check_errors_and_names_every_file(svc, row):
    _, files = await _group(svc, row)

    issues = [i for i in await svc.check() if i.level == "error" and "carry this id" in i.message]

    assert len(issues) == 1, issues
    for md in files:
        assert _rel(svc, md) in issues[0].message


@pytest.mark.parametrize("row", _ROWS)
async def test_repair_refuses_to_pick_a_winner(svc, row):
    _, files = await _group(svc, row)
    before = {md: md.read_bytes() for md in files}

    result = await svc.repair()

    assert result.unreadable, "repair must report the duplicate"
    joined = "\n".join(result.unreadable)
    for md in files:
        assert _rel(svc, md) in joined
    assert {md: md.read_bytes() for md in files} == before


@pytest.mark.parametrize("row", _ROWS)
async def test_renumber_refuses_same_slug_and_renumbers_different_slugs(svc, row):
    item, files = await _group(svc, row)
    before = {md: md.read_bytes() for md in files}

    result = await svc.repair(renumber=True)

    if row.refused:
        assert result.unreadable
        assert {md: md.read_bytes() for md in files} == before
        assert not result.renumber_report
    else:
        assert not result.unreadable, result.unreadable
        original = files[0]
        assert original.read_bytes() == before[original], "the indexed file keeps the id"
        for md in files[1:]:
            assert not md.exists(), "the renumbered files are renamed"
        ids = [
            split_frontmatter(p.read_text(encoding="utf-8"))[0]["id"]
            for p in original.parent.glob("TASK-*.md")
        ]
        assert len(ids) == len(set(ids)) == len(files)
        assert not [i for i in await svc.check() if i.level == "error"]
        assert item.sequence_id in (await svc.repair()).db.items


@pytest.mark.parametrize("row", _ROWS)
async def test_list_shows_at_most_one_row_and_writes_refuse(svc, row):
    item, _ = await _group(svc, row)
    await svc.repair()

    rows = [i for i in await svc.list_items(item_type="task") if i.sequence_id == item.sequence_id]
    assert len(rows) <= 1
    assert await svc.duplicate_id_error(item) is not None
    with pytest.raises(SquadsError, match="carry this id"):
        await svc.comment(item.id, ["a write"], as_slug="manager")
    with pytest.raises(SquadsError, match="carry this id"):
        await svc.set_body(item.id, "a body")


async def test_a_skill_with_a_copied_file_is_reported_and_refused(svc):
    (md,) = (svc.paths.squad_dir / "agents" / "skills").glob("SKILL-*-sq-task.md")
    copy = _copy(md, name=md.name.replace(".md", "-copy.md"))

    issues = [i for i in await svc.check() if "carry this id" in i.message]
    result = await svc.repair()
    renumbered = await svc.repair(renumber=True)

    assert len(issues) == 1 and _rel(svc, copy) in issues[0].message
    assert result.unreadable and renumbered.unreadable
    assert copy.exists() and md.exists()


async def test_a_clean_squad_reports_no_duplicate(svc):
    await _task(svc)

    assert not [i for i in await svc.check() if "carry this id" in i.message]
    result = await svc.repair(renumber=True)
    assert not result.unreadable and not result.renumber_report and not result.references_left


async def test_distinct_ids_sharing_a_number_are_renumbered_by_repair(svc):
    _task_item, task_md = await _task(svc)
    bug = await svc.create("bug", "Beta", author="manager")
    fm = split_frontmatter(bug.path.read_text(encoding="utf-8"))[0]
    fm["sequence_id"] = split_frontmatter(task_md.read_text(encoding="utf-8"))[0]["sequence_id"]
    fm["id"] = f"BUG-{fm['sequence_id']}"
    bug.path.write_text(
        replace_frontmatter(bug.path.read_text(encoding="utf-8"), fm), encoding="utf-8", newline=""
    )

    assert not [i for i in await svc.check() if "carry this id" in i.message]
    result = await svc.repair(renumber=True)

    assert not result.unreadable and not result.renumber_report
    numbers = [it.sequence_id for it in result.db.items.values()]
    assert len(numbers) == len(set(numbers))


async def test_repair_with_no_previous_index_leaves_the_id_out_and_still_reports(svc):
    item, _ = await _group(svc, Row("s", _other_folder, True))
    (svc.paths.squad_dir / ".squads.json").unlink()

    result = await make_service(svc.paths).repair()

    assert result.unreadable
    assert item.sequence_id not in result.db.items


# --------------------------------------------------------------------- references and order


async def _referenced_group(svc):
    """A duplicate with different slugs, plus a third task naming the old id in every position
    a reference can sit."""
    item, alpha = await _task(svc)
    other = _different_slug(svc, alpha)[0]
    beta_item, beta = await _task(svc, "Beta")
    await svc.add_subtask(beta_item.id, "a subtask")
    await svc.set_body(beta_item.id, f"see {item.id} for the details")
    await svc.comment(beta_item.id, [f"@manager {item.id} is in play"], as_slug="manager")
    text = beta.read_text(encoding="utf-8")
    fm = split_frontmatter(text)[0]
    fm["refs"] = [item.id]
    fm["parent"] = item.id
    fm["subentities"][0]["title"] = f"check {item.id}"
    beta.write_text(replace_frontmatter(text, fm), encoding="utf-8", newline="")
    return item, alpha, other, beta


async def test_renumber_lists_every_reference_and_changes_none(svc):
    _, alpha, other, beta = await _referenced_group(svc)
    before = beta.read_bytes()

    result = await svc.repair(renumber=True)

    assert result.references_left
    report = "\n".join(result.renumber_report)
    assert f"kept       {_rel(svc, alpha)}" in report
    assert "renumbered" in report and _rel(svc, other) in report
    for where in ("refs", "parent", "subentities", "body:", "comment:"):
        assert where in report, report
    assert beta.read_bytes() == before, "a reference file is never rewritten"


async def test_renumber_with_no_references_reports_none_and_is_clean(svc):
    _, alpha = await _task(svc)
    _different_slug(svc, alpha)

    result = await svc.repair(renumber=True)

    assert not result.references_left
    assert "no references" in "\n".join(result.renumber_report)


async def test_with_no_index_the_first_name_is_kept_whatever_the_scan_order(svc, monkeypatch):
    _, alpha = await _task(svc)
    first = _copy(alpha, name=alpha.name.replace("alpha", "aaa"), slug="aaa", title="aaa")
    (svc.paths.squad_dir / ".squads.json").unlink()
    fresh = make_service(svc.paths)
    original = fresh._id_carriers

    async def reversed_carriers(*args, **kwargs):
        return list(reversed(await original(*args, **kwargs)))

    monkeypatch.setattr(fresh, "_id_carriers", reversed_carriers)

    await fresh.repair(renumber=True)

    assert first.exists(), "the first name keeps the id when no index says otherwise"
    assert not alpha.exists()


async def test_check_repair_and_show_through_the_cli(svc, invoke):
    item, files = await _group(svc, Row("t", _other_folder, True))
    number = str(item.sequence_id)

    checked = await invoke(["check"])
    repaired = await invoke(["repair"])
    shown = await invoke(["task", number, "show"])
    written = await invoke(["task", number, "comment", "--as", "manager", "-m", "hi"])

    assert checked.exit_code != 0 and "carry this id" in checked.output
    assert repaired.exit_code == 1 and "sq repair" in repaired.output
    assert "fix the file and repair again" not in repaired.output
    assert shown.exit_code == 0 and "carry this id" in shown.output
    assert written.exit_code != 0 and "carry this id" in written.output
    assert all(md.exists() for md in files)
