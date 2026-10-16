"""``sq sync`` writes a managed skill file back whole: frontmatter from the index entry, the
body untouched. A file that is not a managed skill is never re-stamped from the index."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from squads import _aio
from squads import _clock as clock
from squads._errors import SquadsError
from squads._sections import find_markers, split_frontmatter
from squads._services import _service as service

pytestmark = pytest.mark.anyio

_SLUGS = ["squads", "sq-task"]


def _strip_whole(text: str) -> str:
    return split_frontmatter(text)[1]


def _strip_id_only(text: str) -> str:
    fm, body = split_frontmatter(text)
    fm.pop("id")
    return "---\n" + "".join(f"{k}: {v!r}\n" for k, v in fm.items()) + "---" + body


_DAMAGES = {
    "deleted": None,
    "frontmatter-stripped": _strip_whole,
    "id-missing-only": _strip_id_only,
    "empty-file": lambda _text: "",
}


@pytest.fixture
async def svc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal")
    return service.Service(result.paths)


def _skill_file(svc, slug: str) -> Path:
    (found,) = (svc.paths.squad_dir / "agents" / "skills").glob(f"SKILL-*-{slug}.md")
    return found


@pytest.mark.parametrize("damage", list(_DAMAGES))
@pytest.mark.parametrize("slug", _SLUGS)
async def test_sync_restores_frontmatter_matching_the_index(svc, slug, damage):
    md = _skill_file(svc, slug)
    original = await _aio.read_text(md)
    transform = _DAMAGES[damage]
    if transform is None:
        md.unlink()
    else:
        md.write_text(transform(original))

    await svc.sync()

    restored = await _aio.read_text(md)
    fm, body = split_frontmatter(restored)
    item = next(i for i in await svc.list_items(item_type="skill") if i.path.endswith(md.name))
    assert fm["id"] == item.id
    assert fm["sequence_id"] == item.sequence_id
    assert fm["type"] == "skill"
    assert fm["title"] == item.title
    assert fm["status"] == item.status
    assert find_markers(body), "the body region's markers must survive"
    assert not [i for i in await svc.check() if i.level == "error"]


@pytest.mark.parametrize("slug", _SLUGS)
async def test_round_trip_settles_and_a_second_sync_is_byte_identical(svc, slug):
    md = _skill_file(svc, slug)
    md.unlink()

    await svc.sync()
    await svc.repair()
    assert not [i for i in await svc.check() if i.level == "error"]
    settled = md.read_bytes()

    await svc.sync()
    assert md.read_bytes() == settled


async def test_a_body_survives_the_restamp(svc):
    md = _skill_file(svc, "sq-task")
    fm, body = split_frontmatter(await _aio.read_text(md))
    marked = body.replace("\n\n", "\n\nkept prose\n\n", 1) if "\n\n" in body else body + "kept"
    md.write_text(marked)

    await svc.sync()

    assert split_frontmatter(md.read_text())[1] == marked
    assert split_frontmatter(md.read_text())[0]["id"] == fm["id"]


async def test_a_stripped_authored_item_is_not_restamped(svc):
    item = await svc.create("task", "An authored task", author="manager")
    md = svc.paths.squad_dir / item.path
    stripped = split_frontmatter(md.read_text())[1]
    md.write_text(stripped)

    await svc.sync()

    assert md.read_text() == stripped
    messages = [i.message for i in await svc.check() if i.level == "error"]
    assert any("no `id` in frontmatter" in m for m in messages)


@pytest.mark.parametrize("slug", _SLUGS)
async def test_check_names_sync_for_a_stripped_managed_skill(svc, slug):
    md = _skill_file(svc, slug)
    md.write_text(split_frontmatter(md.read_text())[1])

    messages = [i.message for i in await svc.check() if i.item == md.name]

    assert any("`sq sync`" in m for m in messages)


def _ids_by_file(folder: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for md in folder.glob("SKILL-*.md"):
        fm = split_frontmatter(md.read_text())[0]
        if fm.get("id"):
            out[md.name] = fm["id"]
    return out


def _assert_no_shared_id(folder: Path) -> None:
    ids = list(_ids_by_file(folder).values())
    assert len(ids) == len(set(ids)), _ids_by_file(folder)


async def test_restamp_needs_no_index_entry(svc):
    md = _skill_file(svc, "sq-task")
    md.write_text(_strip_whole(md.read_text()))
    (svc.paths.squad_dir / ".squads.json").unlink()
    await service.Service(svc.paths).repair()

    fresh = service.Service(svc.paths)
    await fresh.sync()

    assert split_frontmatter(md.read_text())[0]["id"].startswith("SKILL-")
    assert not list(md.parent.glob("sq-task.md")), "no unprefixed stray body file"
    assert await fresh.roster_item("skill", "sq-task") is not None
    assert not [i for i in await fresh.check() if i.level == "error"]


# How a managed skill file can be renamed away from its slug.
_RENAMES = {
    "frontmatter-intact": lambda text: text,
    "frontmatter-stripped": _strip_whole,
}


@pytest.mark.parametrize("shape", list(_RENAMES))
async def test_a_renamed_file_never_ends_as_two_files_with_one_id(svc, shape):
    md = _skill_file(svc, "sq-task")
    renamed = md.with_name(md.name.replace("sq-task", "foo"))
    renamed.write_text(_RENAMES[shape](md.read_text()))
    md.unlink()

    skips = await svc.sync()

    _assert_no_shared_id(md.parent)
    if shape == "frontmatter-intact":
        assert any("already carries id" in s for s in skips), skips


_BROKEN_YAML = "---\ntitle: [unclosed\nid: SKILL-1\n---\n"


@pytest.mark.parametrize("slug", _SLUGS)
async def test_invalid_yaml_is_rebuilt_by_sync(svc, slug):
    md = _skill_file(svc, slug)
    body = split_frontmatter(md.read_text())[1]
    md.write_text(_BROKEN_YAML + body)

    await svc.sync()

    fm, restored_body = split_frontmatter(md.read_text())
    assert fm["type"] == "skill"
    assert restored_body == body
    assert not [i for i in await svc.check() if i.level == "error"]


async def test_check_names_sync_for_invalid_yaml_in_a_managed_skill(svc):
    md = _skill_file(svc, "sq-task")
    md.write_text(_BROKEN_YAML + split_frontmatter(md.read_text())[1])

    messages = [i.message for i in await svc.check() if i.item == md.name]

    assert any("`sq sync`" in m for m in messages)


async def test_repair_gives_the_one_remedy_for_a_stripped_managed_skill(svc, invoke):
    md = _skill_file(svc, "sq-task")
    md.write_text(_strip_whole(md.read_text()))

    result = await invoke(["repair"])

    assert result.exit_code == 1
    assert "`sq sync`" in result.output
    assert "fix the file and repair again" not in result.output


@pytest.mark.parametrize("damage", [*_DAMAGES, "invalid-yaml"])
@pytest.mark.parametrize("slug", _SLUGS)
async def test_a_restamp_leaves_no_timestamp_drift_on_a_real_clock(svc, slug, damage):
    md = _skill_file(svc, slug)
    original = md.read_text()
    later = datetime.now(UTC) + timedelta(hours=3)
    if damage == "invalid-yaml":
        md.write_text(_BROKEN_YAML + split_frontmatter(original)[1])
    elif (transform := _DAMAGES[damage]) is None:
        md.unlink()
    else:
        md.write_text(transform(original))

    clock.set_now(later)
    try:
        await svc.sync()
    finally:
        clock.set_now(None)

    assert not [i for i in await svc.check() if "drift" in i.message], await svc.check()


async def test_a_stray_stripped_copy_is_not_restamped_into_a_second_skill(svc):
    md = _skill_file(svc, "sq-task")
    stray = md.parent / "SKILL-000099-sq-task.md"
    stray.write_text(_strip_whole(md.read_text()))

    skips = await svc.sync()

    assert "id" not in split_frontmatter(stray.read_text())[0]
    holders = [i for i in await svc.list_items(item_type="skill") if i.slug == "sq-task"]
    assert len(holders) == 1
    assert any("already" in s and "sq-task" in s for s in skips), skips


def _wrap_whole_file(text: str) -> str:
    return f"<<<<<<< HEAD\n{text}=======\n{text}>>>>>>> other\n"


def _span_frontmatter_and_body(text: str) -> str:
    fm, body = split_frontmatter(text)
    head = "".join(f"{k}: {v!r}\n" for k, v in fm.items())
    return f"---\n<<<<<<< HEAD\n{head}=======\ntitle: other\n---\n{body}>>>>>>> other\n"


def _body_only_with_no_frontmatter(text: str) -> str:
    return f"{_strip_whole(text)}\n<<<<<<< HEAD\nours\n=======\ntheirs\n>>>>>>> other\n"


def _inside_frontmatter(text: str) -> str:
    fm, body = split_frontmatter(text)
    head = "".join(f"{k}: {v!r}\n" for k, v in fm.items())
    return f"---\n{head}<<<<<<< HEAD\ntitle: a\n=======\ntitle: b\n>>>>>>> other\n---{body}"


# (transform, rebuilt): a conflict wholly inside the frontmatter is rebuilt; any other
# position is a merge a human must resolve, so sync refuses.
_CONFLICTS = [
    pytest.param(_inside_frontmatter, True, id="inside-frontmatter"),
    pytest.param(_span_frontmatter_and_body, False, id="spans-frontmatter-and-body"),
    pytest.param(_wrap_whole_file, False, id="wraps-the-whole-file"),
    pytest.param(_body_only_with_no_frontmatter, False, id="in-the-body-after-lost-frontmatter"),
]


@pytest.mark.parametrize(("transform", "rebuilt"), _CONFLICTS)
@pytest.mark.parametrize("slug", _SLUGS)
async def test_only_a_frontmatter_conflict_is_rebuilt(svc, slug, transform, rebuilt):
    md = _skill_file(svc, slug)
    md.write_text(transform(md.read_text()))
    damaged = md.read_bytes()

    if rebuilt:
        await svc.sync()
        assert "<<<<<<<" not in md.read_text()
        assert split_frontmatter(md.read_text())[0]["type"] == "skill"
    else:
        with pytest.raises(SquadsError, match="merge conflict"):
            await svc.sync()
        assert md.read_bytes() == damaged


async def test_check_names_the_remedy_that_works_for_each_refusal(svc):
    md = _skill_file(svc, "sq-task")
    twin = md.with_name(md.name.replace("sq-task", "foo"))
    twin.write_text(md.read_text())
    md.write_text(_strip_whole(md.read_text()))

    blocked = [i.message for i in await svc.check() if i.item == md.name]

    assert any("remove or rename one of the two files" in m for m in blocked), blocked
    assert not any("run `sq sync`" in m for m in blocked)

    twin.unlink()
    md.write_text(_wrap_whole_file(md.read_text()))
    conflicted = [i.message for i in await svc.check() if i.item == md.name]
    assert not any("run `sq sync`" in m for m in conflicted), conflicted
