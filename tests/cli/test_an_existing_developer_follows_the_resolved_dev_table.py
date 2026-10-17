"""An existing developer's definition is regenerated from the ``[dev]`` table of the catalog the
squad resolves, on every read. The colour follows a ``[dev]`` change after the developer was
added; the stored model and the stored name do not change.

One table: the ``[dev]`` override when the developer is added, by what changes afterwards, by the
per-slug role file. Each cell compares the generated pointer with ``sq role rust-dev show``.
"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

from squads import __version__

pytestmark = pytest.mark.anyio

_BUNDLED_MODEL = "sonnet"
_BUNDLED_COLOR = "green"
_ADDED_NAME = "Elias Rust"


def _write_dev_table(squad_dir: Path, model: str | None, color: str | None) -> None:
    overrides = squad_dir / ".overrides"
    overrides.mkdir(exist_ok=True)
    lines = [f"# squads:override-base:{__version__}", "[dev]"]
    if model is not None:
        lines.append(f'model = "{model}"')
    if color is not None:
        lines.append(f'color = "{color}"')
    (overrides / "roles.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_slug_file(squad_dir: Path, body: str) -> None:
    roles = squad_dir / ".overrides" / "roles"
    roles.mkdir(parents=True, exist_ok=True)
    (roles / "rust-dev.toml").write_text(
        f"# squads:override-base:{__version__}\n{body}", encoding="utf-8"
    )


def _pointer(root: Path) -> tuple[str, str, str]:
    text = (root / ".claude" / "agents" / "rust-dev.md").read_text(encoding="utf-8")
    model = re.search(r"^model: (\S+)$", text, re.M)
    color = re.search(r"^color: (\S+)$", text, re.M)
    assert model is not None and color is not None, text
    return model.group(1), color.group(1), text


def _card(output: str) -> tuple[str, str]:
    model = re.search(r"model: (\S+)", output)
    color = re.search(r"color: (\S+)", output)
    assert model is not None and color is not None, output
    return model.group(1), color.group(1)


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file() and ".git" not in path.parts:
            digest.update(str(path.relative_to(root)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


@dataclass(frozen=True)
class _Add:
    model: str | None
    color: str | None


@dataclass(frozen=True)
class _After:
    """What changes after the developer exists, and the ``[dev]`` table that results."""

    writes: _Add | None  # a new [dev] table, or None to leave the file as it is
    removes: bool = False


_AT_ADD = {"no-override": None, "colour-and-model": _Add("haiku", "pink")}
_AFTER = {
    "nothing": _After(None),
    "override-added": _After(_Add("opus", "teal")),
    "colour-changed": _After(_Add("haiku", "orange")),
    "model-changed": _After(_Add("opus", "pink")),
    "override-removed": _After(None, removes=True),
}
_SLUG_FILES = {
    "no-file": ("", None, None),
    "sets-colour": ('color = "red"\n', None, "red"),
    "sets-model": ('model = "inherit"\n', "inherit", None),
    "sets-full-name": ('full_name = "Renamed Person"\n', None, None),
}

#: Which (at-add, after) pairs describe a reachable story.
_PAIRS = [
    ("no-override", "nothing"),
    ("no-override", "override-added"),
    ("colour-and-model", "nothing"),
    ("colour-and-model", "colour-changed"),
    ("colour-and-model", "model-changed"),
    ("colour-and-model", "override-removed"),
]


@pytest.mark.parametrize("slug_file", list(_SLUG_FILES))
@pytest.mark.parametrize(("at_add", "after"), _PAIRS)
async def test_the_colour_follows_the_dev_table_and_the_stored_model_and_name_do_not(
    at_add: str, after: str, slug_file: str, project, svc, invoke
) -> None:
    added = _AT_ADD[at_add]
    change = _AFTER[after]
    file_body, file_model, file_color = _SLUG_FILES[slug_file]

    if added is not None:
        _write_dev_table(project.squad_dir, added.model, added.color)
    result = await invoke(["dev", "add", "--tech", "rust"])
    assert result.exit_code == 0, result.output

    stored_model = added.model if added is not None and added.model else _BUNDLED_MODEL
    table_color = added.color if added is not None and added.color else _BUNDLED_COLOR
    if change.removes:
        (project.squad_dir / ".overrides" / "roles.toml").unlink()
        table_color = _BUNDLED_COLOR
    elif change.writes is not None:
        _write_dev_table(project.squad_dir, change.writes.model, change.writes.color)
        table_color = change.writes.color or table_color
    if file_body:
        _write_slug_file(project.squad_dir, file_body)

    expected_model = file_model or stored_model
    expected_color = file_color or table_color

    seen: list[tuple[str, str]] = []
    hashes: list[str] = []
    for _ in range(2):
        synced = await invoke(["sync"])
        assert synced.exit_code == 0, synced.output
        model, color, _text = _pointer(project.root)
        seen.append((model, color))
        shown = await invoke(["role", "rust-dev", "show"])
        assert shown.exit_code == 0, shown.output
        assert _card(shown.output) == (model, color)
        assert _ADDED_NAME in shown.output
        hashes.append(_tree_hash(project.root))

    assert seen == [(expected_model, expected_color)] * 2
    assert hashes[0] == hashes[1]
    item = await svc.roster_item("role", "rust-dev")
    assert item is not None
    assert item.title == _ADDED_NAME


async def test_a_dev_table_override_reaches_a_developer_added_before_it_existed(
    project, svc, invoke
) -> None:
    """The reproduction of the reverted override: pointer at haiku and pink after the add,
    after the first sync and after the second."""
    _write_dev_table(project.squad_dir, "haiku", "pink")
    assert (await invoke(["dev", "add", "--tech", "rust"])).exit_code == 0
    assert _pointer(project.root)[:2] == ("haiku", "pink")
    for _ in range(2):
        assert (await invoke(["sync"])).exit_code == 0
        assert _pointer(project.root)[:2] == ("haiku", "pink")


async def test_a_changed_name_pool_leaves_an_existing_name_and_feeds_the_next_developer(
    project, svc, invoke
) -> None:
    assert (await invoke(["dev", "add", "--tech", "rust"])).exit_code == 0
    overrides = project.squad_dir / ".overrides"
    overrides.mkdir(exist_ok=True)
    (overrides / "roles.toml").write_text(
        f'# squads:override-base:{__version__}\n[dev]\nname_pool = ["Zed"]\n', encoding="utf-8"
    )
    for _ in range(2):
        assert (await invoke(["sync"])).exit_code == 0
    first = await svc.roster_item("role", "rust-dev")
    assert first is not None and first.title == _ADDED_NAME

    assert (await invoke(["dev", "add", "--tech", "go"])).exit_code == 0
    second = await svc.roster_item("role", "go-dev")
    assert second is not None and second.title == "Zed Go"
    assert (await svc.roster_item("role", "rust-dev")).title == _ADDED_NAME  # type: ignore[union-attr]
