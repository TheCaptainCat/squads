"""Arrangements the ownership cases of several `tests/cli` modules share."""

import json
from pathlib import Path

from tests import _tracker_harness as harness

SECRET = "glpat-not-a-real-token"


def maps_text(profile, item_type: str) -> str:
    return (
        f'\n[sources.platform.maps.types.type]\nissue = "{item_type}"\n'
        f"\n[sources.platform.maps.fields.{profile.badge}.labels]\n"
        f'"priority::high" = "{profile.badge_value}"\n'
    )


async def mirror(invoke, project, profile, item_type: str | None = None) -> None:
    """Pull `platform/api#12` as the first item of *item_type* (the reference type by default),
    with the comment the source wrote on it."""
    override = project.squad_dir / ".overrides" / "sources.toml"
    override.parent.mkdir(parents=True, exist_ok=True)
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        override.write_text(
            f'[sources.platform]\nconnector = "gitlab"\nproject = "platform/api"\n'
            f'base_url = "{tracker.base_url}"\n{maps_text(profile, item_type or profile.ref)}',
            encoding="utf-8",
        )
        stored = await invoke(["source", "credential", "set", "platform"], input=f"{SECRET}\n")
        assert stored.exit_code == 0, stored.output
        pulled = await invoke(["source", "pull", "platform"])
        assert pulled.exit_code == 0, pulled.output


def events(*events: dict[str, str]) -> None:
    """Write *events* as `events.jsonl` in the working directory."""
    Path("events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8"
    )


async def run(invoke, args: list[str]) -> tuple[int, str]:
    result = await invoke(args)
    return result.exit_code, result.output


NO_AS = (
    "cannot act as 'source:platform': only `sq source pull` writes as a source, and no "
    "`--as` can name one"
)
