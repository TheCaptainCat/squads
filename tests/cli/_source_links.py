"""Arrangements the links cases of several `tests/cli` modules share."""

from typing import Any

from tests import _tracker_harness as harness
from tests.cli._pulled import item

SECRET = "glpat-not-a-real-token"


HEAD = 'connector = "gitlab"\nproject = "platform/api"\n'


def maps_text(profile) -> str:
    return f'\n[sources.platform.maps.types.type]\nissue = "{profile.ref}"\n'


async def declare(
    invoke, project, profile, base_url: str, extra: str = "", head: str = HEAD
) -> None:
    """Declare the `platform` source on *base_url* with the keys of *extra*, and store its
    credential."""
    path = project.squad_dir / ".overrides" / "sources.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'[sources.platform]\n{head}base_url = "{base_url}"\n{extra}{maps_text(profile)}',
        encoding="utf-8",
    )
    stored = await invoke(["source", "credential", "set", "platform"], input=f"{SECRET}\n")
    assert stored.exit_code == 0, stored.output


def issue_route(tracker: harness.Tracker, number: int) -> dict[str, Any]:
    """The recorded body of the one-issue route, which a case edits to change the issue."""
    path = f"/api/v4/projects/platform%2Fapi/issues/{number}"
    return next(r for r in tracker.routes if r["path"] == path)["body"]


def listing(tracker: harness.Tracker) -> list[dict[str, Any]]:
    return next(r for r in tracker.routes if r["path"] == "/api/v4/projects/platform%2Fapi/issues")[
        "body"
    ]


def moved(text: str, project: str) -> str:
    return text.replace("platform/api", project)


def platform_item(profile, number: int, issue: int | None = None, **given: Any) -> dict[str, Any]:
    """The item a pull of this module's sources makes: no field is mapped from the labels."""
    return item(profile, number, issue, badge=False, **given)


async def pull(invoke) -> None:
    result = await invoke(["source", "pull", "platform", "--json"])
    assert result.exit_code == 0, (result.output, result.stderr)


def declare_more(project, text: str) -> None:
    path = project.squad_dir / ".overrides" / "sources.toml"
    path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")


LISTING_PATH = "/api/v4/projects/platform%2Fapi/issues"


REJECTING_FILTER = "\n[sources.platform.filter]\nlabels = 'not bug'\n"


def full_listings(tracker: harness.Tracker) -> list[str]:
    """The scope listing requests made, not counting the one-row read of the access check."""
    return [
        path
        for path, query, _headers in tracker.requests
        if path == LISTING_PATH and query.get("per_page") != "1"
    ]


def two_sources(profile, base: str, name: str, expression: str) -> str:
    return (
        f'connector = "gitlab"\nproject = "platform/api"\nbase_url = "{base}"\n'
        f"[sources.{name}.filter]\nlabels = '{expression}'\n"
        f'[sources.{name}.maps.types.type]\nissue = "{profile.ref}"\n'
    )


async def declare_two(invoke, project, profile, base_url: str) -> None:
    """Declare `epics` (the priority::high issue) and `stories` (the others) on one tracker, with
    the one credential they share."""
    path = project.squad_dir / ".overrides" / "sources.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            f"[sources.{name}]\n" + two_sources(profile, base_url, name, expression) + "\n"
            for name, expression in (
                ("epics", '"priority::high"'),
                ("stories", 'not "priority::high"'),
            )
        ),
        encoding="utf-8",
    )
    stored = await invoke(["source", "credential", "set", "epics"], input=f"{SECRET}\n")
    assert stored.exit_code == 0, stored.output


async def declare_overlap(invoke, project, profile, tracker: harness.Tracker) -> None:
    """Declare `narrow` (the project) and `wide` (its group) on one tracker, with the one
    credential they share."""
    listing = next(
        r for r in tracker.routes if r["path"].endswith("projects/platform%2Fapi/issues")
    )
    tracker.routes.append({**listing, "path": "/api/v4/groups/platform/issues"})
    path = project.squad_dir / ".overrides" / "sources.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            f'[sources.{name}]\nconnector = "gitlab"\n{scope}\n'
            f'base_url = "{tracker.base_url}"\n'
            f'[sources.{name}.maps.types.type]\nissue = "{profile.ref}"\n\n'
            for name, scope in (
                ("narrow", 'project = "platform/api"'),
                ("wide", 'group = "platform"'),
            )
        ),
        encoding="utf-8",
    )
    stored = await invoke(["source", "credential", "set", "narrow"], input=f"{SECRET}\n")
    assert stored.exit_code == 0, stored.output
