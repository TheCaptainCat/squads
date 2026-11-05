"""Arrangements the checks cases of several `tests/cli` modules share."""

import json
from typing import Any

from tests import _tracker_harness as harness

SECRET = "glpat-not-a-real-token"


HEAD = '[sources.platform]\nconnector = "gitlab"\nproject = "platform/api"\n'


def maps_text(profile) -> str:
    return f'\n[sources.platform.maps.types.type]\nissue = "{profile.ref}"\n'


async def declare(
    invoke, project, profile, base_url: str, maps: str | None = None, head: str = HEAD
) -> None:
    """Declare the `platform` source on *base_url* and store its credential."""
    maps = maps_text(profile) if maps is None else maps
    path = project.squad_dir / ".overrides" / "sources.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'{head}base_url = "{base_url}"\n{maps}', encoding="utf-8")
    stored = await invoke(["source", "credential", "set", "platform"], input=f"{SECRET}\n")
    assert stored.exit_code == 0, stored.output


def route(tracker: harness.Tracker, path: str) -> dict[str, Any]:
    return next(r for r in tracker.routes if r["path"] == path)


TOKEN_REFUSED = (
    "error: http://tracker did not accept the token: http://tracker rejected the credential "
    "(HTTP 401)\n  fix: run `sq source credential set platform` with a valid personal or "
    "project token\n"
)


def failing_token(tracker: harness.Tracker) -> None:
    """Make the tracker refuse the token at its user endpoint."""
    route(tracker, "/api/v4/user").update(status=401, body={"message": "401 Unauthorized"})


async def stopped(invoke, tracker: harness.Tracker, args: list[str]) -> tuple[str, list[str]]:
    """The error a fetching command stops with when the token is refused, the tracker's address
    made constant, and the paths it asked the tracker for; checked to be the line
    `sq source check --json` gives."""
    before = len(tracker.requests)
    result = await invoke(args)
    asked = [path for path, _, _ in tracker.requests[before:]]
    checked = await invoke(["source", "check", "--json"])
    fail = next(
        line
        for line in json.loads(checked.output)["sources"][0]["lines"]
        if line["verdict"] == "fail"
    )
    lines = json.loads(checked.output)["sources"][0]["lines"]
    assert (result.exit_code, checked.exit_code) == (1, 1)
    assert lines[-1] == fail
    assert result.output == f"error: {fail['text']}\n  fix: {fail['fix']}\n"
    return result.output.replace(tracker.base_url, "http://tracker"), asked
