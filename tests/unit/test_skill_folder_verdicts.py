"""The restamp's decision for a managed skill file, from the skill folder alone (no index)."""

import pytest

from squads._services._skill_files import SkillFolder
from squads._workflow import bundled_spec

_SPEC = bundled_spec()
_STAMPED = (
    "---\nid: SKILL-{n}\nextra:\n  slug: {slug}\n---\n<!-- sq:body -->\n<!-- sq:body:end -->\n"
)
_BARE = "<!-- sq:body -->\n<!-- sq:body:end -->\n"


def _folder(files: dict[str, str]) -> SkillFolder:
    return SkillFolder.build(files, _SPEC)


def _stamped(n: int, slug: str) -> str:
    return _STAMPED.format(n=n, slug=slug)


# (files, file asked about, expected kind)
_ROWS = [
    pytest.param({"SKILL-000019-sq-task.md": _BARE}, "SKILL-000019-sq-task.md", "act", id="lone"),
    pytest.param(
        {"SKILL-000019-foo.md": _stamped(19, "sq-task"), "SKILL-000099-sq-task.md": _BARE},
        "SKILL-000099-sq-task.md",
        "blocked",
        id="slug-held-in-extra-by-a-renamed-file",
    ),
    pytest.param(
        {"SKILL-000019-sq-task.md": _BARE, "SKILL-000099-sq-task.md": _BARE},
        "SKILL-000099-sq-task.md",
        "blocked",
        id="two-unstamped-files-claim-one-slug",
    ),
    pytest.param(
        {"SKILL-000019-sq-task.md": _BARE, "SKILL-000099-sq-task.md": _BARE},
        "SKILL-000019-sq-task.md",
        "blocked",
        id="the-other-unstamped-file-is-blocked-too",
    ),
    pytest.param(
        {"SKILL-000019-foo.md": _stamped(19, "other"), "SKILL-000019-sq-task.md": _BARE},
        "SKILL-000019-sq-task.md",
        "blocked",
        id="another-file-carries-the-id",
    ),
    pytest.param(
        {"SKILL-000019-sq-task.md": "<<<<<<< HEAD\nx\n=======\ny\n>>>>>>> o\n"},
        "SKILL-000019-sq-task.md",
        "conflict",
        id="conflict-marks-a-file-with-no-frontmatter",
    ),
]


@pytest.mark.parametrize(("files", "name", "kind"), _ROWS)
def test_verdict(files, name, kind):
    verdict = _folder(files).verdict(name, _SPEC)

    assert verdict is not None and verdict.kind == kind


def test_a_file_that_already_carries_an_id_needs_nothing():
    files = {"SKILL-000019-sq-task.md": _stamped(19, "sq-task")}

    assert _folder(files).verdict("SKILL-000019-sq-task.md", _SPEC) is None
