"""The comment-header contribution's pipeline invariants: a refused run writes nothing wherever
the failure sits, a completed run changes header lines only, reads back as the same comments
under the live parser, is idempotent, and converges after an interrupted write pass."""

import hashlib
import re
import shutil
from pathlib import Path

import pytest

from _legacy_squad import TS, inject, read, reopen, roster, stamp_behind, task
from squads import _discussion as discussion
from squads._errors import SquadsError
from squads._migrations import _v0_15_to_v0_16 as step
from squads._models import _markers as markers

pytestmark = pytest.mark.anyio

_CORPUS = Path(__file__).parent.parent / "fixtures" / "corpus"
BAD = f"- [{TS}] Nobody Known:\n  - refused\n"
GOOD = f"- [{TS}] Catherine Manager:\n  - fine\n"
AGED_GOOD = f"- [{TS}] Dev Agent:\n  - fine\n"
AGED_BAD = f"- [{TS}] Nobody Known:\n  - refused\n"


def _hash(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and (p.suffix == ".md" or p.name == ".squads.toml")
    }


async def _block(svc, kind: str):
    """An item holding one sub-entity of *kind*, and that sub-entity's discussion tag."""
    parent, adder = {
        "story": ("feature", svc.add_story),
        "subtask": ("task", svc.add_subtask),
        "finding": ("review", svc.add_finding),
    }[kind]
    from _helpers import create_item

    item = (await create_item(svc, parent, f"Holds a {kind}")).item
    block = await adder(item.id, "A block")
    return item.id, markers.discussion_tag(f"{kind}:{block.local_id}")


@pytest.mark.parametrize("where", ["top-level", "story", "subtask", "finding"])
@pytest.mark.parametrize("position", ["first", "middle", "last"])
async def test_a_failure_anywhere_in_a_discussion_refuses_the_run_and_writes_nothing(
    project, svc, where, position
) -> None:
    await roster(svc)
    if where == "top-level":
        item_id, tag = await task(svc), markers.DISCUSSION
    else:
        item_id, tag = await _block(svc, where)
    text = {"first": BAD + GOOD + GOOD, "middle": GOOD + BAD + GOOD, "last": GOOD + GOOD + BAD}
    await inject(svc, item_id, text[position], tag)
    stamp_behind(project.root)
    before = _hash(project.root)

    with pytest.raises(SquadsError) as raised:
        await reopen(project.root).run_pending_migrations()

    assert str(raised.value).count("'Nobody Known' matches no roster entry") == 1
    assert _hash(project.root) == before


async def test_one_failing_header_among_many_resolvable_files_still_writes_none(
    project, svc
) -> None:
    await roster(svc)
    for n in range(4):
        await inject(svc, await task(svc, f"Fine {n}"), GOOD)
    await inject(svc, await task(svc, "Broken"), BAD)
    stamp_behind(project.root)
    before = _hash(project.root)

    with pytest.raises(SquadsError):
        await reopen(project.root).run_pending_migrations()

    assert _hash(project.root) == before


async def test_every_kind_of_failure_is_reported_in_one_run(project, svc) -> None:
    await roster(svc)
    first = await task(svc, "First")
    second = await task(svc, "Second")
    story_item, story_tag = await _block(svc, "story")
    await inject(svc, first, BAD)
    await inject(svc, first, f"- [{TS}] Sam Lee:\n  - two\n")
    await inject(svc, second, "- [yesterday] Catherine Manager:\n  - when\n")
    await inject(svc, story_item, BAD, story_tag)
    stamp_behind(project.root)

    with pytest.raises(SquadsError) as raised:
        await reopen(project.root).run_pending_migrations()

    out = str(raised.value)
    assert "'Nobody Known' matches no roster entry" in out
    assert "'Sam Lee' matches 2 entries: op-sam, qa" in out
    assert "'yesterday' is not a timestamp sq writes" in out
    assert out.count("matches no roster entry") == 2
    assert "4 problem(s) found." in out
    assert "  'Nobody Known': 2 header(s) in 2 file(s)" in out
    assert "  'Sam Lee': 1 header(s) in 1 file(s)" in out


COMMENT_SHAPES = {
    "fenced code with a header-like line": (
        f"- [{TS}] Catherine Manager:\n  - see\n    ```\n    - [{TS}] Fake Person:\n    ```\n"
    ),
    "blank continuation lines": f"- [{TS}] Catherine Manager:\n  - one\n\n    still one\n",
    "nested list": f"- [{TS}] Catherine Manager:\n  - top\n    - inner\n      - deeper\n",
    "indented header-like line": f"- [{TS}] Catherine Manager:\n  - a\n    - [{TS}] Fake Person:\n",
}


@pytest.mark.parametrize("shape", COMMENT_SHAPES.values(), ids=COMMENT_SHAPES)
@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
async def test_only_header_lines_differ_and_the_comments_read_back_the_same(
    project, svc, shape, newline
) -> None:
    await roster(svc)
    item_id = await task(svc)
    path = await inject(svc, item_id, shape.replace("\n", newline))
    stamp_behind(project.root)
    before = await read(path)
    legacy_comments = _legacy_comments(before)

    await reopen(project.root).run_pending_migrations()

    after = await read(path)
    changed = [
        (old, new)
        for old, new in zip(
            before.splitlines(keepends=True), after.splitlines(keepends=True), strict=True
        )
        if old != new
    ]
    assert len(changed) == 1
    old, new = changed[0]
    assert new == old.replace("] Catherine Manager:", "] `manager` Catherine Manager:")
    assert new.endswith(newline) and old.endswith(newline)
    assert after.splitlines()[:5] == before.splitlines()[:5]  # the frontmatter block
    live = discussion.split_discussion(_region(after), sequence_id=1)
    assert [(c.timestamp, c.author, c.body) for c in live] == legacy_comments
    assert [c.author_slug for c in live] == ["manager"]


def _region(text: str) -> str:
    start = text.index(markers.open_marker(markers.DISCUSSION)) + len(
        markers.open_marker(markers.DISCUSSION)
    )
    return text[start : text.index(markers.close_marker(markers.DISCUSSION))]


def _legacy_comments(text: str) -> list[tuple[str, str, str]]:
    """The legacy parse of the top-level discussion: (timestamp, name, body) per comment."""
    comments: list[tuple[str, str, str]] = []
    current: list[str] | None = None
    for line in _region(text).splitlines():
        header = re.match(r"^- \[([^\]]+)\] (.+?):$", line)
        if header:
            current = []
            comments.append((header.group(1), header.group(2), ""))
            continue
        if current is not None:
            current.append(line[2:] if line.startswith("  ") else line)
            ts, name, _ = comments[-1]
            comments[-1] = (ts, name, "\n".join(current).strip())
    return comments


async def test_a_second_run_writes_nothing_and_a_squad_stamped_back_migrates_to_the_same_tree(
    project, svc
) -> None:
    await roster(svc)
    await inject(svc, await task(svc), GOOD + f"- [{TS}] Elias Python:\n  - x\n")
    stamp_behind(project.root)
    await reopen(project.root).run_pending_migrations()
    done = _hash(project.root)
    stamp_behind(project.root)

    run = await reopen(project.root).run_pending_migrations()

    assert run.changed["0.16"] == 0
    assert _hash(project.root) == done


async def test_a_write_pass_interrupted_after_some_files_ends_in_the_same_tree_when_run_again(
    project, svc, tmp_path_factory, monkeypatch
) -> None:
    await roster(svc)
    for n in range(5):
        await inject(svc, await task(svc, f"Item {n}"), GOOD)
    stamp_behind(project.root)
    clone = tmp_path_factory.mktemp("clone") / "squad"
    shutil.copytree(project.root, clone)
    await reopen(clone).run_pending_migrations()

    real = step.write_text
    calls = {"n": 0}

    async def flaky(path, text):
        calls["n"] += 1
        if calls["n"] == 3:
            raise SquadsError("injected failure")
        await real(path, text)

    monkeypatch.setattr(step, "write_text", flaky)
    with pytest.raises(SquadsError, match="injected failure"):
        await reopen(project.root).run_pending_migrations()
    monkeypatch.setattr(step, "write_text", real)
    await reopen(project.root).run_pending_migrations()

    assert _same_md(project.root, clone)


def _same_md(a: Path, b: Path) -> bool:
    def md(root: Path) -> dict[str, str]:
        return {
            p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*.md"))
        }

    return md(a) == md(b)


async def test_a_squad_stamped_below_0_15_migrates_through_the_whole_chain_in_one_run(
    tmp_path,
) -> None:
    root = tmp_path / "old"
    shutil.copytree(_CORPUS / "v0_11", root)
    (path,) = list(root.glob("tasks/*implement-auth*.md"))
    text = (await read(path)).replace(
        markers.close_marker(markers.DISCUSSION),
        f"{AGED_GOOD}{markers.close_marker(markers.DISCUSSION)}",
        1,
    )
    path.write_bytes(text.encode("utf-8"))

    run = await reopen(root).run_pending_migrations()

    assert run.applied[-1].to_schema == "0.16"
    assert f"- [{TS}] `dev-agent` Dev Agent:" in await read(
        next(root.rglob("TASK-*implement-auth*.md"))
    )


async def test_a_refusal_below_0_15_names_the_release_that_reads_0_15(tmp_path) -> None:
    root = tmp_path / "old"
    shutil.copytree(_CORPUS / "v0_11", root)
    (path,) = list(root.glob("tasks/*implement-auth*.md"))
    text = (await read(path)).replace(
        markers.close_marker(markers.DISCUSSION),
        f"{AGED_BAD}{markers.close_marker(markers.DISCUSSION)}",
        1,
    )
    path.write_bytes(text.encode("utf-8"))

    with pytest.raises(SquadsError) as first:
        await reopen(root).run_pending_migrations()
    with pytest.raises(SquadsError) as second:
        await reopen(root).run_pending_migrations()

    message = " ".join(str(first.value).split())
    assert "Earlier steps of this run have already been applied" in message
    assert (
        "change the roster with a squads release that reads schema v0.15 (v0.15.0 is one)"
        in message
    )
    assert "This step wrote nothing" in message and "Nothing was written" not in message
    assert "matches no roster entry" in str(second.value)


async def test_a_refusal_by_the_first_step_of_a_run_claims_no_earlier_steps(project, svc) -> None:
    await roster(svc)
    await inject(svc, await task(svc), BAD)
    stamp_behind(project.root)

    with pytest.raises(SquadsError) as raised:
        await reopen(project.root).run_pending_migrations()

    assert "Earlier steps" not in str(raised.value)
    assert (
        "Change the roster with a squads release that reads schema v0.15 (v0.15.0 is one)"
        in str(raised.value)
    )
    assert "This step wrote nothing and the schema stamp is unchanged." in str(raised.value)


async def test_two_contributions_that_edit_one_file_both_land(project, svc, monkeypatch) -> None:
    await roster(svc)
    item_id = await task(svc)
    path = await inject(svc, item_id, GOOD)
    stamp_behind(project.root)

    async def plan(_ctx, _db):
        async def write(ctx):
            target = ctx.paths.abspath(
                next(i.path for i in (await svc.store.load()).items.values() if i.id == item_id)
            )
            text = target.read_text(encoding="utf-8")
            target.write_text(text.replace("  - fine", "  - fine (touched)"), encoding="utf-8")
            return 1

        return step.Planned(write=write)

    other = step.Contribution("touch", plan, manual="m", summary="s.")
    monkeypatch.setattr(step, "CONTRIBUTIONS", (*step.CONTRIBUTIONS, other))

    await reopen(project.root).run_pending_migrations()

    text = await read(path)
    assert f"- [{TS}] `manager` Catherine Manager:" in text and "  - fine (touched)" in text
