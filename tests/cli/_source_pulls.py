"""Arrangements the pulls cases of several `tests/cli` modules share."""

import json
from typing import Any

from tests import _tracker_harness as harness

SECRET = "glpat-not-a-real-token"


HEAD = 'connector = "gitlab"\nproject = "platform/api"\n'


def maps_text(profile, issue_type: str | None = None) -> str:
    return (
        f'\n[sources.platform.maps.types.type]\nissue = "{issue_type or profile.ref}"\n'
        f"\n[sources.platform.maps.fields.{profile.badge}.labels]\n"
        f'"priority::high" = "{profile.badge_value}"\n'
    )


async def declare(invoke, project, profile, base_url: str, extra: str = "") -> None:
    """Declare the `platform` source on *base_url* and store its credential."""
    path = project.squad_dir / ".overrides" / "sources.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'[sources.platform]\n{HEAD}base_url = "{base_url}"\n{extra}{maps_text(profile)}',
        encoding="utf-8",
    )
    stored = await invoke(["source", "credential", "set", "platform"], input=f"{SECRET}\n")
    assert stored.exit_code == 0, stored.output


def listing(tracker: harness.Tracker) -> list[dict[str, Any]]:
    """The recorded issue listing, which a case edits to change what the tracker answers."""
    route = next(r for r in tracker.routes if r["path"] == "/api/v4/projects/platform%2Fapi/issues")
    return route["body"]


def issue_route(tracker: harness.Tracker, number: int) -> dict[str, Any]:
    """The recorded body of the one-issue route, which a case edits to change the issue."""
    path = f"/api/v4/projects/platform%2Fapi/issues/{number}"
    return next(r for r in tracker.routes if r["path"] == path)["body"]


async def pull(invoke, *args: str) -> dict[str, Any]:
    result = await invoke(["source", "pull", *args, "--json"])
    assert result.exit_code == 0, (result.output, result.stderr, repr(result.exception))
    return json.loads(result.stdout)
