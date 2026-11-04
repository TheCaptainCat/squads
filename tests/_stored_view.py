"""A view declared stored through an override, for the cases that need a paired view tag that
no pull writes."""

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
    """Write the override that declares the stored view *name* and its presentation template."""
    overrides = squad_dir / ".overrides"
    (overrides / "templates" / "views").mkdir(parents=True, exist_ok=True)
    workflow = f'[views.{name}]\nsource = {{ kind = "source" }}\nstored = true\n'
    (overrides / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n\n{workflow}", encoding="utf-8"
    )
    (overrides / "templates" / "views" / f"{name}.md.j2").write_text(_TEMPLATE, encoding="utf-8")


def pair(inner: str = STORED) -> str:
    """The paired tag holding *inner* on lines of its own; empty text is the empty pair."""
    return f"{OPEN_TAG}\n{inner}\n{CLOSE_TAG}" if inner else f"{OPEN_TAG}\n{CLOSE_TAG}"
