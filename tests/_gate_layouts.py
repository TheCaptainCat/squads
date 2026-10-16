"""Shared fixtures for the tests that put a squad behind or ahead of the package's schema, lay
its folder out in one of the supported shapes, and compare directory trees byte for byte.
"""

import hashlib
import shutil
import tomllib
from pathlib import Path

from squads import __version__
from squads._models._schema import SCHEMA_VERSION

CORPUS_DIR = Path(__file__).parent / "fixtures" / "corpus"

OVERRIDES = ["none", "valid", "conflicting", "does-not-load"]


def stamp(root: Path, schema: str) -> None:
    text = (root / ".squads.toml").read_text(encoding="utf-8")
    current = tomllib.loads(text)["schema_version"]
    (root / ".squads.toml").write_text(
        text.replace(f'schema_version = "{current}"', f'schema_version = "{schema}"'),
        encoding="utf-8",
    )


def override(root: Path, kind: str) -> None:
    if kind == "none":
        return
    folder = root / ".overrides"
    folder.mkdir()
    header = f"# squads:override-base:{__version__}\n"
    body = {
        "valid": '[ref_kinds.mirrors]\nlabel = "Mirrors"\nhint = "mirror"\n',
        "conflicting": "[selected]\nitems = ['task', 'bug', 'feature', 'epic']\n",
        "does-not-load": "[items.broken\nnot toml ===",
    }[kind]
    (folder / "workflow.toml").write_text(header + body, encoding="utf-8")


def squad(tmp_path: Path, direction: str, override_kind: str) -> Path:
    root = tmp_path / "squad"
    shutil.copytree(CORPUS_DIR / ("v0_14" if direction != "equal" else "v0_16"), root)
    if direction == "ahead":
        stamp(root, "0.99")
    elif direction == "equal":
        stamp(root, SCHEMA_VERSION)
    override(root, override_kind)
    return root


def digest(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.name != ".reflog.jsonl"
    }


def move_into(root: Path, sub: str) -> Path:
    folder = root / sub
    folder.mkdir(parents=True, exist_ok=True)
    top = sub.split("/")[0]
    for child in [c for c in root.iterdir() if c.name not in (".squads.toml", top)]:
        shutil.move(child, folder / child.name)
    return folder


def set_squad_dir(root: Path, value: str) -> None:
    text = (root / ".squads.toml").read_text(encoding="utf-8")
    (root / ".squads.toml").write_text(text.replace('squad_dir = "."', f'squad_dir = "{value}"'))


def lay_out(root: Path, layout: str) -> Path:  # noqa: PLR0911 - one return per layout
    """Arrange the squad at *root* as *layout* says; return the squad folder."""
    if layout == "root":
        return root
    if layout == "dot-slash":
        set_squad_dir(root, "./")
        return root
    if layout in ("outside-relative", "outside-absolute"):
        shared = root.parent / "shared"
        shared.mkdir()
        for child in [c for c in root.iterdir() if c.name != ".squads.toml"]:
            shutil.move(child, shared / child.name)
        set_squad_dir(root, "../shared" if layout == "outside-relative" else str(shared))
        return shared
    if layout == "symlinked":
        real = move_into(root, "real")
        (root / "link").symlink_to(real, target_is_directory=True)
        set_squad_dir(root, "link")
        return root / "link"
    sub = {"nested": "squads", "multi-level": "work/squad", "renamed": "team"}.get(layout, "squads")
    folder = move_into(root, sub)
    set_squad_dir(root, sub)
    if layout == "at-the-project-root":
        return root
    if layout == "at-a-sibling-folder":
        (root / "docs").mkdir()
        return root / "docs"
    return folder


LAYOUTS = ["nested", "root", "dot-slash", "multi-level", "renamed", "symlinked"]
ENCLOSED = ["at-the-project-root", "at-a-sibling-folder"]
OUTSIDE = ["outside-relative", "outside-absolute"]

#: (layout, what -C names): every pair resolves the squad, as ``cd <target> && sq`` would.
RESOLVING = [
    *((layout, "folder") for layout in [*LAYOUTS, *ENCLOSED]),
    *((layout, "project") for layout in OUTSIDE),
]
