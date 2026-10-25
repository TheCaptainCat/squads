"""Which file is which item is answered once, by the same rule, for the write guard, the
detector, the restamp and the renumber scan; and a refused write changes nothing."""

import hashlib
from collections.abc import Awaitable, Callable
from pathlib import Path

import pytest

from _helpers import make_service
from squads import _aio
from squads._errors import SquadsError
from squads._sections import replace_frontmatter, split_frontmatter
from squads._services import _service as service

pytestmark = pytest.mark.anyio


@pytest.fixture
async def svc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal")
    return make_service(result.paths)


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _copy(md: Path, *, name: str | None = None, folder: Path | None = None, **fm: object) -> Path:
    text = md.read_text()
    if fm:
        data = split_frontmatter(text)[0]
        data.update(fm)
        text = replace_frontmatter(text, data)
    target = (folder or md.parent) / (name or md.name)
    target.write_text(text)
    return target


async def _task(svc, title: str):
    created = await svc.create("task", title, author="manager")
    return created.item, created.path


# --------------------------------------------------------------- one definition of identity

# How a second file can carry the id: each builder returns the copy.
_SHAPES: dict[str, Callable[[service.Service, Path], Path]] = {
    "prefixed-name": lambda svc, md: _copy(md, name=md.name.replace("alpha", "other")),
    "unprefixed-name": lambda svc, md: _copy(md, name="alpha-copy.md"),
    "other-type-folder": lambda svc, md: _copy(md, folder=_bugs(svc)),
}


def _bugs(svc) -> Path:
    folder = svc.paths.squad_dir / "bugs"
    folder.mkdir(exist_ok=True)
    return folder


@pytest.mark.parametrize("shape", list(_SHAPES))
async def test_the_guard_finds_what_the_detector_finds(svc, shape):
    item, md = await _task(svc, "Alpha")
    copy = _SHAPES[shape](svc, md)

    detected = [i for i in await svc.check() if "carry this id" in i.message]
    guard = await svc.duplicate_id_error(item)
    with pytest.raises(SquadsError, match="carry this id"):
        await svc.comment(item.id, ["x"], as_slug="manager")

    assert len(detected) == 1
    assert guard is not None
    for path in (md, copy):
        rel = path.relative_to(svc.paths.squad_dir).as_posix()
        assert rel in detected[0].message and rel in guard


async def test_a_copy_named_for_another_number_is_left_to_check_and_repair(svc):
    """The write guard reads only files whose name could carry the item's number (or no
    number); a well-formed name for a different number is found by `check` and `repair`."""
    item, md = await _task(svc, "Alpha")
    copy = _copy(md, name="TASK-000099-alpha.md")

    assert await svc.duplicate_id_error(item) is None
    detected = [i for i in await svc.check() if "carry this id" in i.message]
    assert len(detected) == 1
    assert copy.relative_to(svc.paths.squad_dir).as_posix() in detected[0].message
    assert (await svc.repair()).unreadable


async def test_an_interrupted_rename_is_not_reported_as_a_duplicate(svc):
    item, md = await _task(svc, "Alpha")
    md.rename(md.with_name(md.name.replace("alpha", "alpha2")))

    assert await svc.duplicate_id_error(item) is None
    with pytest.raises(SquadsError) as raised:
        await svc.comment(item.id, ["x"], as_slug="manager")
    assert "carry this id" not in str(raised.value)


# --------------------------------------------------------------- guard before mutation

_Verb = Callable[[service.Service, str, str], Awaitable[object]]

_VERBS: dict[str, _Verb] = {
    "comment": lambda svc, i, r: svc.comment(i, ["x"], as_slug="manager"),
    "body": lambda svc, i, r: svc.set_body(i, "x"),
    "retitle": lambda svc, i, r: svc.update(i, title="Renamed"),
    "status": lambda svc, i, r: svc.set_status(i, "InProgress"),
    "add-ref": lambda svc, i, r: svc.add_ref(i, r),
    "add-subtask": lambda svc, i, r: svc.add_subtask(i, "a subtask"),
    "retype": lambda svc, i, r: svc.retype(i, "bug"),
    "remove": lambda svc, i, r: svc.remove_work_item(i),
    "retype-with-duplicated-referrer": lambda svc, i, r: svc.retype(r, "bug"),
    "remove-force-with-duplicated-referrer": lambda svc, i, r: svc.remove_work_item(r, force=True),
}


@pytest.mark.parametrize("verb", list(_VERBS))
async def test_a_refused_write_leaves_every_file_byte_identical(svc, verb):
    subject, subject_md = await _task(svc, "Alpha")
    referrer, referrer_md = await _task(svc, "Beta")
    other, _ = await _task(svc, "Gamma")
    await svc.add_ref(other.id, referrer.id)
    # The subject is duplicated for most verbs; the referrer is for the two "referrer" verbs.
    target = referrer_md if "referrer" in verb else subject_md
    if "referrer" in verb:
        await svc.add_ref(referrer.id, subject.id)
    _copy(target, name=target.name.replace(".md", "-copy.md"))
    ids = {"subject": subject.id, "referrer": referrer.id}
    before = _tree_hash(svc.paths.squad_dir)

    with pytest.raises(SquadsError, match="carry this id"):
        await _VERBS[verb](svc, ids["subject"], ids["referrer"])

    assert _tree_hash(svc.paths.squad_dir) == before


async def test_a_clean_squad_still_takes_every_write(svc):
    subject, _ = await _task(svc, "Alpha")
    referrer, _ = await _task(svc, "Beta")

    await svc.comment(subject.id, ["x"], as_slug="manager")
    await svc.update(subject.id, title="Renamed")
    await svc.add_ref(referrer.id, subject.id)
    await svc.remove_work_item(referrer.id)


# --------------------------------------------------------------- renumber


async def test_a_group_with_a_misplaced_copy_is_refused_and_the_id_stays_indexed(svc):
    item, md = await _task(svc, "Alpha")
    copy = _copy(md, folder=_bugs(svc), name=md.name.replace("alpha", "other"), title="other")
    before = {p: p.read_bytes() for p in (md, copy)}

    result = await svc.repair(renumber=True)

    assert result.unreadable and not result.renumber_report
    assert {p: p.read_bytes() for p in (md, copy)} == before
    assert item.sequence_id in result.db.items
    assert not [i for i in await svc.check() if "not in index" in i.message]


async def test_a_whitespace_copy_never_takes_the_id_from_the_indexed_original(svc):
    item, md = await _task(svc, "Alpha")
    copy = _copy(md, name=md.name.replace(".md", "-copy.md"))
    copy.write_text(copy.read_text() + "  \n")

    await svc.repair(renumber=True)

    assert md.exists() and not copy.exists()
    assert item.sequence_id in (await make_service(svc.paths).repair()).db.items


async def test_the_renumbered_files_own_references_are_listed(svc):
    item, md = await _task(svc, "Alpha")
    other = _copy(md, name=md.name.replace("alpha", "other"), slug="other", title="other")
    other.write_text(other.read_text() + f"\nit supersedes {item.id}\n")

    result = await svc.repair(renumber=True)

    assert result.references_left, result.renumber_report
    assert any("body:" in line and "supersedes" in line for line in result.renumber_report)


async def test_a_later_groups_scan_sees_an_earlier_groups_renames(svc):
    first, first_md = await _task(svc, "Alpha")
    _, second_md = await _task(svc, "Beta")
    _copy(first_md, name=first_md.name.replace("alpha", "one"), slug="one", title="one")
    late = _copy(second_md, name=second_md.name.replace("beta", "two"), slug="two", title="two")
    late.write_text(late.read_text() + f"\nsee {first.id}\n")

    result = await svc.repair(renumber=True)

    assert result.references_left
    assert any(first.id in line and "body:" in line for line in result.renumber_report)


# --------------------------------------------------------------- skill slug (restamp)


async def _skill(svc, slug: str) -> Path:
    (found,) = (svc.paths.squad_dir / "agents" / "skills").glob(f"SKILL-*-{slug}.md")
    return found


def _stripped(md: Path) -> str:
    return split_frontmatter(md.read_text())[1]


async def test_a_slug_held_in_extra_is_seen_when_the_index_is_gone(svc):
    md = await _skill(svc, "sq-task")
    number = md.name.split("-")[1]
    renamed = md.with_name(md.name.replace("sq-task", "foo"))
    md.rename(renamed)
    stray = md.parent / "SKILL-000099-sq-task.md"
    stray.write_text(_stripped(renamed))
    (svc.paths.squad_dir / ".squads.json").unlink()
    fresh = make_service(svc.paths)
    await fresh.repair()

    skips = await fresh.sync()

    assert "id" not in split_frontmatter(stray.read_text())[0], (number, skips)
    assert any("sq-task" in s for s in skips), skips


async def test_two_unstamped_files_for_one_slug_are_both_left_alone(svc):
    md = await _skill(svc, "sq-task")
    twin = md.parent / "SKILL-000099-sq-task.md"
    md.write_text(_stripped(md))
    twin.write_text(md.read_text())
    (svc.paths.squad_dir / ".squads.json").unlink()
    fresh = make_service(svc.paths)
    await fresh.repair()

    skips = await fresh.sync()

    for path in (md, twin):
        assert "id" not in split_frontmatter(path.read_text())[0]
    assert any("also claims skill slug" in s for s in skips), skips


# --------------------------------------------------------------- output


async def test_check_does_not_send_the_operator_to_repair_for_a_refused_duplicate(svc):
    item, md = await _task(svc, "Alpha")
    _copy(md, name=md.name.replace(".md", "-copy.md"))
    (svc.paths.squad_dir / ".squads.json").unlink()
    fresh = make_service(svc.paths)
    await fresh.repair()

    issues = await fresh.check()

    assert not any("on disk but not in index" in i.message for i in issues)
    dup = [i for i in issues if "carry this id" in i.message]
    assert dup and not dup[0].message.startswith(item.id)


async def test_repair_prints_the_group_once(svc, invoke):
    _, md = await _task(svc, "Alpha")
    _copy(md, name=md.name.replace(".md", "-copy.md"))

    result = await invoke(["repair"])

    assert result.output.count("files carry this id") == 1, result.output


async def test_skill_show_warns_about_a_duplicate(svc, invoke):
    md = await _skill(svc, "sq-task")
    _copy(md, name=md.name.replace(".md", "-copy.md"))

    result = await invoke(["skill", "sq-task", "show"])

    assert result.exit_code == 0 and "carry this id" in result.output


async def test_check_on_damaged_skills_parses_the_index_and_reads_files_no_more_than_needed(
    svc, monkeypatch
):
    from squads._models._index import SquadsDB

    for slug in ("sq-task", "sq-bug", "squads"):
        md = await _skill(svc, slug)
        md.write_text(_stripped(md))
    parses = 0
    original = SquadsDB.model_validate_json.__func__

    def counted(cls, *args, **kwargs):
        nonlocal parses
        parses += 1
        return original(cls, *args, **kwargs)

    reads: dict[Path, int] = {}
    real_read = _aio.read_text

    async def counting_read(path: Path) -> str:
        reads[path] = reads.get(path, 0) + 1
        return await real_read(path)

    monkeypatch.setattr(SquadsDB, "model_validate_json", classmethod(counted))
    monkeypatch.setattr(_aio, "read_text", counting_read)

    await svc.check()

    reread = [p.name for p, n in reads.items() if n > 1]
    # Measured: one index parse for the load, one for the confirm round's fresh reload, and one
    # file (the confirm round's candidate) read twice; every other file is read once.
    assert parses == 2, parses
    assert len(reread) == 1, reread


async def test_the_indexed_file_keeps_the_id_even_when_another_name_sorts_first(svc):
    item, md = await _task(svc, "Alpha")
    early = _copy(md, name=md.name.replace("alpha", "aaa"), slug="aaa", title="aaa")

    result = await svc.repair(renumber=True)

    assert md.exists() and not early.exists(), result.renumber_report
    assert item.sequence_id in result.db.items


@pytest.mark.parametrize("corpus_size", [4, 40])
async def test_a_write_and_a_show_read_a_bounded_number_of_files(svc, monkeypatch, corpus_size):
    subject = None
    for n in range(corpus_size):
        item, _ = await _task(svc, f"Task {n}")
        subject = subject or item
    assert subject is not None
    reads: list[Path] = []
    real_read = _aio.read_text

    async def counting_read(path: Path) -> str:
        reads.append(path)
        return await real_read(path)

    monkeypatch.setattr(_aio, "read_text", counting_read)

    await svc.duplicate_id_error(subject)
    guard_reads = len(reads)
    reads.clear()
    await svc.comment(subject.id, ["x"], as_slug="manager")

    assert guard_reads == 0, "no file other than the item's own carries its number"
    assert len(reads) <= 3, [p.name for p in reads]


async def test_scan_state_is_never_kept_on_the_service(svc):
    for name in ("_skill_state", "_skill_texts", "_skill_items", "_id_cache"):
        assert not hasattr(svc, name), name
