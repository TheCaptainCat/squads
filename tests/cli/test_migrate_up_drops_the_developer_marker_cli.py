"""``sq migrate up`` removes the stored developer marker from role items and changes nothing
else in them: the name, ``tech`` and ``model`` stay, a second run and a repair change no file, and
the index rebuilds to the same values.

One table: corpus shape by step. Columns: which files changed, the attributes of each role in
its file and in the index, the schema stamp and the exit code.
"""

import hashlib
import json
import shutil
import tomllib
from collections.abc import Callable
from pathlib import Path

import pytest

from _helpers import check_is_clean_but_for_orphaned_roles
from squads._itemfile import read_frontmatter
from squads._sections import replace_frontmatter

pytestmark = pytest.mark.anyio

_CORPUS = Path(__file__).parent.parent / "fixtures" / "corpus"


def _roles(root: Path) -> dict[str, Path]:
    return {p.name: p for p in sorted(root.rglob("ROLE-*.md"))}


def _blank_title(root: Path) -> None:
    path = _roles(root)["ROLE-000003-go-dev.md"]
    text = path.read_text(encoding="utf-8")
    data = read_frontmatter(text=text, source=str(path))
    data["title"] = "  "
    path.write_text(replace_frontmatter(text, data, source=str(path)), encoding="utf-8")


def _declare(root: Path) -> None:
    path = root / ".overrides" / "roles" / "builder.toml"
    path.write_text(path.read_text(encoding="utf-8") + 'capabilities = ["dev"]\n', encoding="utf-8")


def _nothing(root: Path) -> None:
    return None


#: shape -> (corpus, edit applied to the copy before the run)
_SHAPES: dict[str, tuple[str, Callable[[Path], None]]] = {
    "no-developer": ("v0_15", _nothing),
    "templated-developer": ("v0_15_discussions", _nothing),
    "developers-one-with-a-model-one-with-a-role-file-override": ("v0_15_developers", _nothing),
    "retired-developer": ("v0_15_developers", _nothing),
    "developer-with-a-blank-stored-title": ("v0_15_developers", _blank_title),
    "declared-developer": ("v0_15_developers", _declare),
    "suffixed-role": ("v0_15_developers", _nothing),
}


def _hashes(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and ".git" not in p.parts and p.name != ".reflog.jsonl"
    }


def _files(root: Path) -> dict[str, dict[str, object]]:
    return {
        name: read_frontmatter(text=p.read_text(encoding="utf-8"), source=name)
        for name, p in _roles(root).items()
    }


def _indexed(root: Path) -> dict[str, dict[str, object]]:
    index = json.loads((root / ".squads.json").read_text(encoding="utf-8"))
    return {
        str(item["slug"]): dict(item.get("attributes", {}))
        for item in index["items"].values()
        if item["type"] == "role"
    }


def _stamp(root: Path) -> str:
    return tomllib.loads((root / ".squads.toml").read_text(encoding="utf-8"))["schema_version"]


def _kept(before: dict[str, object]) -> dict[str, object]:
    """What the run must preserve of a 0.15 role file: its name, slug and the developer keys."""
    nested = before.get("extra")
    extra = dict(nested) if isinstance(nested, dict) else {}  # pyright: ignore[reportUnknownArgumentType]
    kept: dict[str, object] = {"slug": before.get("slug") or extra.get("slug")}
    for key in ("tech", "model"):
        if key in extra:
            kept[key] = extra[key]
    return kept


@pytest.mark.parametrize("shape", list(_SHAPES))
async def test_the_marker_leaves_and_every_other_value_stays_across_the_steps(
    shape: str, tmp_path, monkeypatch, invoke
) -> None:
    corpus, edit = _SHAPES[shape]
    root = tmp_path / "squad"
    shutil.copytree(_CORPUS / corpus, root)
    edit(root)
    monkeypatch.chdir(root)
    before = {n: (_kept(d), d.get("title")) for n, d in _files(root).items()}

    first = await invoke(["migrate", "up"])
    assert first.exit_code == 0, first.output
    assert _stamp(root) == "0.17"
    migrated = _hashes(root)
    for name, front in _files(root).items():
        assert "is_dev" not in front, name
        kept, title = before[name]
        assert front.get("title") == title, name
        assert {k: front.get(k) for k in kept} == kept, name
    index_after_first = _indexed(root)
    assert all("is_dev" not in attrs for attrs in index_after_first.values())

    second = await invoke(["migrate", "up"])
    assert second.exit_code == 0, second.output
    assert _hashes(root) == migrated

    repaired = await invoke(["repair"])
    assert repaired.exit_code == 0, repaired.output
    assert _hashes(root) == migrated

    (root / ".squads.json").unlink()
    rebuilt = await invoke(["repair"])
    assert rebuilt.exit_code == 0, rebuilt.output
    assert _hashes(root) == migrated | {".squads.json": _hashes(root)[".squads.json"]}
    assert _indexed(root) == index_after_first
    orphans = ("dev-agent",) if shape == "no-developer" else ()
    await check_is_clean_but_for_orphaned_roles(invoke, orphans)


async def test_a_developer_file_missing_from_the_index_loses_the_marker_like_any_other(
    tmp_path, monkeypatch, invoke
) -> None:
    root = tmp_path / "squad"
    shutil.copytree(_CORPUS / "v0_15_developers", root)
    monkeypatch.chdir(root)
    (root / ".squads.json").unlink()

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert all("is_dev" not in front for front in _files(root).values())
    assert "python-dev" in _indexed(root)


async def test_a_role_file_with_unreadable_yaml_stops_the_run_beside_a_healthy_developer(
    tmp_path, monkeypatch, invoke
) -> None:
    root = tmp_path / "squad"
    shutil.copytree(_CORPUS / "v0_15_developers", root)
    monkeypatch.chdir(root)
    broken = _roles(root)["ROLE-000007-builder.md"]
    broken.write_text("---\nid: [unclosed\n---\n", encoding="utf-8")
    before = _hashes(root)

    result = await invoke(["migrate", "up"])

    assert result.exit_code != 0, result.output
    assert {k: v for k, v in _hashes(root).items() if k != ".squads.json"} == {
        k: v for k, v in before.items() if k != ".squads.json"
    }
    assert _stamp(root) == "0.15"


async def test_a_sixteen_file_that_still_carries_the_marker_reads_through_tech_and_checks_clean(
    tmp_path, monkeypatch, invoke
) -> None:
    root = tmp_path / "squad"
    shutil.copytree(_CORPUS / "v0_15_developers", root)
    monkeypatch.chdir(root)
    assert (await invoke(["migrate", "up"])).exit_code == 0
    path = _roles(root)["ROLE-000002-python-dev.md"]
    text = path.read_text(encoding="utf-8")
    data = read_frontmatter(text=text, source=str(path))
    data["template"] = "dev"  # the base is chosen by the stored template, never by `is_dev`
    path.write_text(replace_frontmatter(text, data, source=str(path)), encoding="utf-8")
    assert (await invoke(["repair"])).exit_code == 0
    text = path.read_text(encoding="utf-8")
    data = read_frontmatter(text=text, source=str(path))
    data["is_dev"] = True
    path.write_text(replace_frontmatter(text, data, source=str(path)), encoding="utf-8")

    shown = await invoke(["role", "python-dev", "show", "--json"])
    checked = await invoke(["check"])

    assert shown.exit_code == 0, shown.output
    assert json.loads(shown.output[shown.output.index("{") :])["capabilities"] == ["dev"]
    assert checked.exit_code == 0, checked.output


def _set_role_file(root: Path, slug: str, extra: str) -> None:
    path = root / ".overrides" / "roles" / f"{slug}.toml"
    path.write_text(path.read_text(encoding="utf-8") + extra, encoding="utf-8")


def _remove_role_file(root: Path, slug: str) -> None:
    (root / ".overrides" / "roles" / f"{slug}.toml").unlink()


def _empty_dev_table(root: Path) -> None:
    (root / ".overrides" / "roles.toml").write_text(
        "# squads:override-base:0.15.0\n[templates.dev]\ncapabilities = []\n", encoding="utf-8"
    )


#: shape -> (edit applied to the copy, the report lines expected for its -dev roles)
_REPORTED: dict[str, tuple[Callable[[Path], None], set[str]]] = {
    "suffixed-roles-are-reported-templated-and-other-slugs-are-not": (
        _nothing,
        {"legacy-dev", "old-dev (retired)"},
    ),
    "a-suffixed-role-that-declares-the-capability-is-not": (
        lambda r: _set_role_file(r, "legacy-dev", 'capabilities = ["dev"]\n'),
        {"old-dev (retired)"},
    ),
    "a-suffixed-role-declaring-another-capability-is": (
        lambda r: _set_role_file(r, "legacy-dev", 'capabilities = ["audit"]\n'),
        {"legacy-dev", "old-dev (retired)"},
    ),
    "a-suffixed-role-with-no-role-file-left-is": (
        lambda r: _remove_role_file(r, "legacy-dev"),
        {"legacy-dev (no role file left)", "old-dev (retired)"},
    ),
    "a-dev-table-without-the-capability-leaves-no-developer": (
        _empty_dev_table,
        {"python-dev", "go-dev", "legacy-dev", "old-dev (retired)", "rust-dev (retired)"},
    ),
}


@pytest.mark.parametrize("shape", list(_REPORTED))
async def test_roles_named_dev_without_the_capability_are_reported_and_nothing_is_written_for_it(
    shape: str, tmp_path, monkeypatch, invoke
) -> None:
    edit, expected = _REPORTED[shape]
    root = tmp_path / "squad"
    shutil.copytree(_CORPUS / "v0_15_developers", root)
    edit(root)
    monkeypatch.chdir(root)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    lines = {ln.strip() for ln in result.output.splitlines()}
    reported = {
        ln
        for ln in lines
        if ln.split(" (")[0] in {"python-dev", "go-dev", "rust-dev", "legacy-dev", "old-dev"}
    }
    assert reported == expected, result.output
    assert ("role(s) named -dev hold no developer capability" in result.output) is bool(expected)
    assert _stamp(root) == "0.17"
    overrides = sorted((root / ".overrides").rglob("*"))
    assert all(p.suffix == ".toml" or p.is_dir() for p in overrides)


async def test_a_corpus_with_no_role_named_dev_prints_no_report(tmp_path, monkeypatch, invoke):
    root = tmp_path / "squad"
    shutil.copytree(_CORPUS / "v0_15", root)
    monkeypatch.chdir(root)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert "hold no developer capability" not in result.output


#: (id, slug file, model planted under extra, kept in the file after the run)
MIRRORED = [
    ("catalog-role-the-mirror-of-its-model", "ROLE-000001-manager.md", "opus", None),
    ("catalog-role-a-different-model-is-kept", "ROLE-000001-manager.md", "haiku", "haiku"),
    ("role-with-a-role-file-and-no-tech", "ROLE-000007-builder.md", "haiku", None),
    ("developer-keeps-its-model", "ROLE-000002-python-dev.md", "haiku", "haiku"),
]


@pytest.mark.parametrize(
    ("name", "planted", "kept"), [r[1:] for r in MIRRORED], ids=[r[0] for r in MIRRORED]
)
async def test_a_mirrored_model_on_a_role_without_tech_is_dropped_only_when_it_is_the_resolved_one(
    name: str, planted: str, kept: str | None, tmp_path, monkeypatch, invoke
) -> None:
    root = tmp_path / "squad"
    shutil.copytree(_CORPUS / "v0_15_developers", root)
    path = _roles(root)[name]
    text = path.read_text(encoding="utf-8")
    data = read_frontmatter(text=text, source=str(path))
    extra = dict(data["extra"])  # pyright: ignore[reportUnknownArgumentType]
    extra["model"] = planted
    data["extra"] = extra
    path.write_text(replace_frontmatter(text, data, source=str(path)), encoding="utf-8")
    monkeypatch.chdir(root)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert read_frontmatter(path=_roles(root)[name]).get("model") == kept
    slug = name.split("-", 2)[2].removesuffix(".md")
    flat = " ".join(result.output.split())
    if name.startswith("ROLE-000001") and kept is None:
        assert f"dropped its stored model '{planted}'" in flat
    if kept is None:
        shown = await invoke(["role", slug, "show", "--json"])
        assert json.loads(shown.output[shown.output.index("{") :])["model"] != "haiku"
    elif name.startswith("ROLE-000001"):
        assert "kept its stored model 'haiku'" in " ".join(result.output.split())
