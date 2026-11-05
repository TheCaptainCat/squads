"""Arrangements the declared cases of several `tests/cli` modules share."""

from squads._paths import SquadPaths

TRACKER = "http://127.0.0.1:9"


HEAD = (
    f'[sources.platform]\nconnector = "gitlab"\nproject = "platform/api"\nbase_url = "{TRACKER}/"\n'
)


def types(profile) -> str:
    return f'\n[sources.platform.maps.types.labels]\nbug = "{profile.ref}"\n'


def declare(project: SquadPaths, profile, text: str | None = None) -> None:
    """Write the squad's `sources.toml` override: *text*, or `platform` with its type map."""
    text = HEAD + types(profile) if text is None else text
    path = project.squad_dir / ".overrides" / "sources.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
