"""Arrangements the record cases of several `tests/cli` modules share."""

from tests import _tracker_harness as harness

SECRET = "glpat-not-a-real-token"


async def pulled(invoke, project, profile, tracker: harness.Tracker) -> None:
    """Pull the two issues of the recorded tracker into the squad as items 2 and 3."""
    path = project.squad_dir / ".overrides" / "sources.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'[sources.platform]\nconnector = "gitlab"\nproject = "platform/api"\n'
        f'base_url = "{tracker.base_url}"\n'
        f'\n[sources.platform.maps.types.type]\nissue = "{profile.ref}"\n',
        encoding="utf-8",
    )
    stored = await invoke(["source", "credential", "set", "platform"], input=f"{SECRET}\n")
    assert stored.exit_code == 0, stored.output
    pulled = await invoke(["source", "pull", "platform"])
    assert pulled.exit_code == 0, pulled.output
