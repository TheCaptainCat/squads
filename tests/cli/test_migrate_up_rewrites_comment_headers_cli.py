"""``sq migrate up`` on a 0.15 squad that a released tool wrote with comments in every kind of
discussion: it prints the 0.16 step, its report and the manual-steps hint, rewrites each header
and nothing else, and leaves a squad that cannot resolve a name exactly as it was."""

import hashlib
import json
import re
import shutil
import tomllib
from pathlib import Path

import pytest

from squads._migrations import _v0_15_to_v0_16 as step
from squads._models._schema import SCHEMA_VERSION
from squads._sections import split_frontmatter

pytestmark = pytest.mark.anyio

_FIXTURES = Path(__file__).parent.parent / "fixtures"
_CORPUS = _FIXTURES / "corpus" / "v0_15_discussions"
_REFERENCE = _FIXTURES / "corpus_references" / "v0_15_discussions"

# legacy name -> slug, for every author the fixture was written with
SLUG_OF = {
    "Catherine Manager": "manager",
    "Olivia Lead": "tech-lead",
    "Paul Reviewer": "reviewer",
    "Mara Tester": "qa",
    "Elias Python": "python-dev",
    "Zoë Müller": "op-zo",
    "Pierre Chat": "op-pierre",
    "Operator": "operator",
    "squads": "squads",
}


@pytest.fixture
def squad(tmp_path, monkeypatch) -> Path:
    root = tmp_path / "squad"
    shutil.copytree(_CORPUS, root)
    monkeypatch.chdir(root)
    return root


def _tree(root: Path) -> dict[str, str]:
    """Every item file and the config, hashed; the index is rebuilt by the run's first step."""
    return _hashes(root)


def _hashes(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and (p.suffix == ".md" or p.name == ".squads.toml")
    }


def _stamp(root: Path) -> str:
    return tomllib.loads((root / ".squads.toml").read_text(encoding="utf-8"))["schema_version"]


def _legacy_headers_by_counting(root: Path) -> int:
    """Column-0 header lines inside discussion regions, counted without the step's own scan."""
    total = 0
    for path in root.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for region in re.findall(
            r"<!-- sq:((?:[\w:-]+:)?discussion) -->(.*?)<!-- sq:\1:end -->", text, re.S
        ):
            total += len(re.findall(r"^- \[", region[1], re.M))
    return total


# --------------------------------------------------------------------------- the step's output


async def test_help_and_chlog_show_the_step(squad, invoke) -> None:
    helped = await invoke(["migrate", "help"])
    chlog = await invoke(["migrate", "chlog", "v0.15.0..v0.16.0"])

    assert helped.exit_code == 0 and chlog.exit_code == 0
    assert "v0.16.0" in helped.output and "v0.15→v0.16" in helped.output
    assert "v0.16.0 — manual steps (schema v0.15→v0.16)" in chlog.output
    assert "checks every part before it writes any file" in chlog.output
    assert "Comment headers name the author's slug" in chlog.output


async def test_migrate_up_prints_the_step_its_report_and_the_manual_hint(squad, invoke) -> None:
    headers = _legacy_headers_by_counting(squad)

    r = await invoke(["migrate", "up"])

    assert r.exit_code == 0, r.output
    out = " ".join(r.output.split())
    assert "0.16.0 (schema v0.15→v0.16)" in out
    assert f"{headers} comment header(s) rewritten in 10 file(s); 0 already carried a slug" in out
    assert "manual steps remain — read them with `sq migrate chlog v0.15.0..v0.16.0`" in out
    assert _stamp(squad) == SCHEMA_VERSION == "0.16"
    assert _legacy_headers_by_counting(squad) == headers  # same count, now in the new form
    assert not re.search(r"^- \[[^\]]+\] [^`]", _discussion_text(squad), re.M)

    again = await invoke(["migrate", "up"])
    assert again.exit_code == 0 and "already at schema v0.16" in again.output


def _discussion_text(root: Path) -> str:
    parts: list[str] = []
    for path in root.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        parts += [
            m[1]
            for m in re.findall(
                r"<!-- sq:((?:[\w:-]+:)?discussion) -->(.*?)<!-- sq:\1:end -->", text, re.S
            )
        ]
    return "\n".join(parts)


# --------------------------------------------------------------------------- what is rewritten


async def test_every_comment_reads_back_with_the_slug_of_its_author(squad, invoke) -> None:
    await invoke(["migrate", "up"])
    found: list[tuple[str, str]] = []
    items = json.loads((await invoke(["list", "-a", "--json"])).stdout)
    for item in items:
        if item["type"] in ("role", "operator"):
            continue
        shown = json.loads(
            (await invoke([item["type"], item["id"].split("-")[1], "show", "--json"])).stdout
        )
        found += [(c["author"], c["author_slug"]) for c in shown["discussion"]]
        for sub in shown.get("subentities", []):
            found += [(c["author"], c["author_slug"]) for c in sub["discussion"]]

    assert found, "the fixture holds comments"
    assert {pair for pair in found} <= {(n, s) for n, s in SLUG_OF.items()}
    seen = {slug for _name, slug in found}
    assert seen == set(SLUG_OF.values()), (
        "every author, the retired ones and both reserved included"
    )


async def test_the_diff_of_every_item_file_is_header_lines_and_the_flattened_frontmatter(
    squad, invoke
) -> None:
    before = {p: p.read_text(encoding="utf-8") for p in sorted(squad.rglob("*.md"))}

    r = await invoke(["migrate", "up"])

    assert r.exit_code == 0, r.output
    changed = 0
    for path, was in before.items():
        now = path.read_text(encoding="utf-8")
        old_front, old_body = split_frontmatter(was)
        new_front, new_body = split_frontmatter(now)
        was_lines, now_lines = old_body.splitlines(), new_body.splitlines()
        # the body keeps its line count and every other line: only headers change
        assert len(was_lines) == len(now_lines), path
        for old, new in zip(was_lines, now_lines, strict=True):
            if old != new:
                changed += 1
                legacy = re.fullmatch(r"- \[([^\]]+)\] (.+):", old)
                assert legacy, (path, old)
                assert (
                    new == f"- [{legacy.group(1)}] `{SLUG_OF[legacy.group(2)]}` {legacy.group(2)}:"
                )
        # the frontmatter loses `extra`, gains what it held, and no other key changes
        lifted = set(old_front.get("extra") or {})
        assert "extra" not in new_front, path
        for key, value in old_front.items():
            if key != "extra":
                assert new_front.get(key, value) == value or key == "title", (path, key)
        assert set(new_front) - set(old_front) <= lifted | {"slug"}, path
    assert changed == _legacy_headers_by_counting(squad)


async def test_search_and_inbox_return_what_the_released_tool_returned_before(
    squad, invoke
) -> None:
    await invoke(["migrate", "up"])

    for term in ("colons", "Second", "Retiring"):
        r = await invoke(["search", term, "--json"])
        expected = (_REFERENCE / f"search_{term.lower()}.json").read_text(encoding="utf-8")
        assert json.loads(r.stdout) == json.loads(expected), term
    # The released tool read an indented checkbox inside a comment as a second header and
    # attributed this hit to comment 5, "Done"; the shared parser attributes it to comment 3.
    nested = json.loads((await invoke(["search", "nested", "--json"])).stdout)
    (hit,) = nested[0]["hits"]
    assert (hit["region"], hit["snippet"]) == (
        "discussion#3",
        "[2025-05-20T11:32:00Z] Catherine Manager: - nested bullet",
    )
    for role in ("python-dev", "reviewer"):
        r = await invoke(["inbox", role, "--json"])
        expected = (_REFERENCE / f"inbox_{role}.json").read_text(encoding="utf-8")
        assert json.loads(r.stdout) == json.loads(expected), role


async def test_check_is_clean_of_errors_after_the_migration(squad, invoke) -> None:
    await invoke(["migrate", "up"])

    r = await invoke(["check", "--json"])

    assert not [i for i in json.loads(r.stdout) if i["level"] == "error"], r.output


# --------------------------------------------------------------------------- refusal


def _retitle(root: Path, slug: str, new_title: str) -> None:
    (path,) = root.glob(f"agents/roles/*-{slug}.md")
    text = path.read_text(encoding="utf-8")
    path.write_text(
        re.sub(r"^title: .*$", f"title: {new_title}", text, flags=re.M), encoding="utf-8"
    )


async def test_a_name_that_matches_no_entry_refuses_with_every_header_and_writes_nothing(
    squad, invoke
) -> None:
    _retitle(squad, "python-dev", "Elias Renamed")
    before = _tree(squad)

    r = await invoke(["migrate", "up"])

    assert r.exit_code == 1, r.output
    out = r.output
    assert out.count("'Elias Python' matches no roster entry") == 2
    assert re.search(r"tasks/TASK-\d+-wire-login\.md:\d+: 'Elias Python' matches no roster", out)
    assert "2 problem(s) found." in out
    assert "'Elias Python': 2 header(s) in 1 file(s)" in out
    assert "This step wrote nothing and the schema stamp is unchanged." in out
    assert _tree(squad) == before
    assert _stamp(squad) == "0.15"
    second = await invoke(["migrate", "up"])
    assert second.exit_code == 1 and second.output == out


async def test_the_step_is_one_registry_entry_and_a_contribution_can_be_appended(
    squad, invoke, monkeypatch
) -> None:
    async def plan(_ctx, _db):
        async def write(_ctx):
            return 1

        return step.Planned(report=("stand-in report",), write=write)

    stand_in = step.Contribution("stand-in", plan, manual="stand-in manual", summary="Stand-in.")
    monkeypatch.setattr(step, "CONTRIBUTIONS", (*step.CONTRIBUTIONS, stand_in))

    r = await invoke(["migrate", "up"])

    assert r.exit_code == 0, r.output
    out = " ".join(r.output.split())
    assert "comment header(s) rewritten" in out and "stand-in report" in out
    assert out.index("comment header(s)") < out.index("stand-in report")
    assert _stamp(squad) == "0.16"


# Every contribution in the step has a row here: how to tell its work is done after one run.
POSTCONDITIONS = {
    "comment-headers": lambda root: (
        not re.search(r"^- \[[^\]]+\] [^`]", _discussion_text(root), re.M)
    ),
    "flat-frontmatter": lambda root: _frontmatter_is_flat(root),
    "developer-capability": lambda root: (
        not any(
            "is_dev" in split_frontmatter(p.read_text(encoding="utf-8"))[0]
            for p in root.rglob("ROLE-*.md")
        )
    ),
}


def _frontmatter_is_flat(root: Path) -> bool:
    """No item file carries `extra`, every roster file a top-level `slug`, no operator file a
    `full_name`."""
    for path in root.rglob("*.md"):
        front, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        if not front:
            continue
        kind = front.get("type")
        if "extra" in front:
            return False
        if kind in ("role", "skill", "operator") and not front.get("slug"):
            return False
        if kind == "operator" and "full_name" in front:
            return False
    return True


@pytest.mark.parametrize("name", [c.name for c in step.CONTRIBUTIONS])
async def test_every_contribution_leaves_its_postcondition_after_one_migrate_up(
    squad, invoke, name
) -> None:
    assert name in POSTCONDITIONS, f"add a POSTCONDITIONS row for the {name!r} contribution"

    r = await invoke(["migrate", "up"])

    assert r.exit_code == 0, r.output
    assert POSTCONDITIONS[name](squad)
