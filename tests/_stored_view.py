"""A view declared stored through an override, for the cases that need a paired view tag that
no pull writes."""

import re
from pathlib import Path

from squads import __version__

VIEW = "imported_description"
OPEN_TAG = f"<!-- sq:view:{VIEW} -->"
CLOSE_TAG = f"<!-- sq:view:{VIEW}:end -->"
#: The stored text as it sits on disk: its comment opener carries the extra `!` the escape adds.
STORED = "Reported upstream.\n\nSee <!!-- the note --> for more."
#: What a projection reads once the escape is undone.
RESTORED = "Reported upstream.\n\nSee <!-- the note --> for more."
RENDERED = f"Imported:\n{RESTORED}"

_TEMPLATE = "Imported:\n{{ body }}"


def declare_stored_view(squad_dir: Path, name: str = VIEW) -> None:
    """Add the stored view *name* and its presentation template to the squad's workflow override,
    keeping whatever the override already declares."""
    overrides = squad_dir / ".overrides"
    (overrides / "templates" / "views").mkdir(parents=True, exist_ok=True)
    path = overrides / "workflow.toml"
    kept = (
        path.read_text(encoding="utf-8")
        if path.exists()
        else f"# squads:override-base:{__version__}\n"
    )
    kept = _select(kept, name)
    workflow = f'[views.{name}]\nsource = {{ kind = "source" }}\nstored = true\n'
    path.write_text(f"{kept.rstrip()}\n\n{workflow}", encoding="utf-8")
    (overrides / "templates" / "views" / f"{name}.md.j2").write_text(_TEMPLATE, encoding="utf-8")


def _select(text: str, name: str) -> str:
    """*text* with *name* added to the `views` the override selects, when it selects a list."""
    return re.sub(
        r"^(views = \[[^\]]*?)(\s*\])$", lambda m: f'{m[1]}, "{name}"]', text, count=1, flags=re.M
    )


def pair(inner: str = STORED) -> str:
    """The paired tag holding *inner* on lines of its own; empty text is the empty pair."""
    return f"{OPEN_TAG}\n{inner}\n{CLOSE_TAG}" if inner else f"{OPEN_TAG}\n{CLOSE_TAG}"
