"""Arrangements the connectors cases of several `tests/cli` modules share."""

import json
from typing import Any

from tests.cli._pulled import BASE, RECORDS, item

SECRET = "not-a-real-token"


EMAIL = "svc-squads@acme.example"


async def declare(invoke, project, text: str, credential: str) -> None:
    """Write the squad's `sources.toml` override and store the `platform` credential."""
    path = project.squad_dir / ".overrides" / "sources.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    stored = await invoke(["source", "credential", "set", "platform"], input=credential)
    assert stored.exit_code == 0, stored.output


async def pull(invoke) -> dict[str, Any]:
    result = await invoke(["source", "pull", "platform", "--json"])
    assert result.exit_code == 0, (result.output, result.stderr, repr(result.exception))
    return json.loads(result.stdout)


def github(profile, base: str = "{base}") -> str:
    return (
        f'[sources.platform]\nconnector = "github"\nrepository = "acme/api"\nbase_url = "{base}"\n'
        f'\n[sources.platform.maps.types.labels]\nsquads = "{profile.ref}"\n'
        f"\n[sources.platform.maps.fields.{profile.badge}.labels]\n"
        f'"priority: high" = "{profile.badge_value}"\n'
    )


GITHUB_DESCRIPTION = (
    f"Steps in [the runbook]({BASE}/acme/api/issues/docs/runbook.md), see #13 and acme/other#4."
    f'\n\n<img src="{BASE}/user-attachments/assets/abc">'
)


def github_record(issue: int, **given: str) -> dict[str, str]:
    return {
        **RECORDS[issue],
        "id": f"I_kwDOAcmeApi{issue}",
        "key": f"acme/api#{issue}",
        **given,
    }


def github_item(
    profile, number: int, issue: int, repo: str = "acme/api", **given: Any
) -> dict[str, Any]:
    """The item a GitHub pull makes of issue 12 or 13 of *repo*, which links to the other issue
    only while it is in `acme/api`."""
    first = issue == 12
    text = GITHUB_DESCRIPTION.replace("acme/api", repo)
    resolved = text.replace("#13", profile.ref_id(3)) if repo == "acme/api" else text
    comment = {
        "author": '"asmith" via platform @asmith',
        "author_slug": "source:platform",
        "ts": "2026-11-02T09:14:00Z",
        "edited_ts": None,
        "body": "- The endpoint returns 500 when the body is empty.",
        "attributes": {
            "author_handle": "asmith",
            "author_id": "4568",
            "author_name": "asmith",
            "source_id": "301",
            "source_updated_at": "2026-11-02T09:20:31Z",
        },
        "source": "platform",
        "author_url": f"{BASE}/asmith",
        "identity": None,
        "trusted": False,
    }
    fields: dict[str, Any] = {
        "source": github_record(issue),
        "discussion": [comment] if first else [],
        **given,
    }
    return item(
        profile,
        number,
        issue,
        description=text if first else "",
        rendered=resolved if first else "",
        url=f"{BASE}/{repo}/issues/{given.get('source', {}).get('key', f'#{issue}').split('#')[1]}",
        **fields,
    )


USER_FIELD = f"{EMAIL}\n{SECRET}\n"


def jira(profile, version: str, base: str = "{base}") -> str:
    return (
        f'[sources.platform]\nconnector = "jira"\nversion = "{version}"\njql = "labels = squads"\n'
        f'base_url = "{base}"\n'
        f'\n[sources.platform.maps.types.type]\nBug = "{profile.ref}"\nTask = "{profile.ref}"\n'
        f"\n[sources.platform.maps.fields.{profile.badge}.priority]\n"
        f'High = "{profile.badge_value}"\nLow = "{profile.badge_other_value}"\n'
    )


PIERRE = "712020:0a1b2c3d-2222-4444-8888-bbbbbbbbbbbb"


ALICE = "712020:0a1b2c3d-1111-4444-8888-aaaaaaaaaaaa"


def jira_comment(who: str, handle: str, name: str, ident: str, body: str, **given: str):
    return {
        "author": f'"{name}" via platform @{handle}',
        "author_slug": "source:platform",
        "ts": given.get("ts", "2026-11-02T09:14:00Z"),
        "edited_ts": None,
        "body": body,
        "attributes": {
            "author_handle": handle,
            "author_id": ident,
            "author_name": name,
            "source_id": given["source_id"],
            "source_updated_at": given["updated"],
        },
        "source": "platform",
        "author_url": given["url"],
        "identity": None,
        "trusted": False,
    }


def jira_cloud_item(profile, number: int, **given: Any) -> dict[str, Any]:
    """The item a Jira Cloud pull makes of `PROJ-45` (first) or `PROJ-46` (second); the second
    issue's label maps the other priority."""
    first = number == 2
    key = "PROJ-45" if first else "PROJ-46"
    record = {
        "name": "platform",
        "id": "10042" if first else "10043",
        "key": key,
        "state": "open" if first else "closed",
        "updated_at": "2026-11-02T09:00:00.000Z" if first else "2026-11-03T10:30:00.000Z",
        "author_id": PIERRE if first else ALICE,
        "author_handle": PIERRE if first else ALICE,
    }
    record = given.get("source", record)
    key = record["key"]
    people = f"{BASE}/jira/people"
    comments = [
        jira_comment(
            "alice",
            ALICE,
            "Alice Smith",
            ALICE,
            "- The endpoint returns 500 when the body is empty.",
            source_id="20001",
            updated="2026-11-02T09:20:31.000Z",
            url=f"{people}/{ALICE.replace(':', '%3A')}",
        ),
        jira_comment(
            "pierre",
            PIERRE,
            "Pierre Chat",
            PIERRE,
            "- Fixed in **main**",
            ts="2026-11-02T10:00:00Z",
            source_id="20003",
            updated="2026-11-02T10:00:00.000Z",
            url=f"{people}/{PIERRE.replace(':', '%3A')}",
        ),
    ]
    steps = "Steps: see **PROJ-46** and the runbook."
    fields: dict[str, Any] = {
        "source": record,
        "discussion": comments if first else [],
        **given,
    }
    document = item(
        profile,
        number,
        description=steps if first else "",
        rendered=steps.replace("PROJ-46", profile.ref_id(3)) if first else "",
        url=f"{BASE}/browse/{key}",
        **fields,
    )
    if not first:
        value = profile.badge_other_value
        document |= {profile.badge: value, "badges": {profile.badge: value}}
        document["display"]["badges"] = {
            profile.badge: {
                "label": profile.badge.replace("_", " ").capitalize(),
                "badge": profile.badge_other_shown,
                "badge_label": profile.badge_other_shown_label,
            }
        }
    return document
