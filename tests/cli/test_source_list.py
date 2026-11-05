"""`sq source list`: the sources a squad declares in `sources.toml`."""

import json

import pytest

from tests import _tracker_harness as harness
from tests.cli import _source_declared as source_declared
from tests.cli import _source_links as source_links

pytestmark = pytest.mark.anyio


BASE = 'base_url = "http://127.0.0.1:9"\n'


GITLAB = f'[sources.platform]\nconnector = "gitlab"\n{BASE}'


def _types(profile) -> str:
    return f'\n[sources.platform.maps.types.labels]\nbug = "{profile.ref}"\n'


async def _listed(invoke, project, text: str) -> tuple[int, str]:
    """Write `text` as the squad's sources override and load it through `sq source list`."""
    path = project.squad_dir / ".overrides" / "sources.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")
    result = await invoke(["source", "list", "--json"])
    return result.exit_code, result.output.replace(str(path), "sources.toml")


def _listing(connector: str = "gitlab", version: str = "v4") -> dict[str, object]:
    """The `source list --json` document of the one `platform` source, which has no credential
    and has pulled nothing."""
    return {
        "sources": [
            {
                "name": "platform",
                "connector": connector,
                "version": version,
                "enabled": True,
                "credential": False,
                "items": 0,
                "newest_updated_at": None,
            }
        ]
    }


@pytest.mark.covers("source list")
async def test_a_broken_sources_document_leaves_the_rest_of_the_squad_working(
    project, invoke, credentials_home, profile
) -> None:
    source_declared.declare(project, profile, "[sources.platform\n")

    listed = await invoke(["list", "--json"])
    refused = await invoke(["source", "list"])

    origin = project.squad_dir / ".overrides" / "sources.toml"
    assert (listed.exit_code, [row["id"] for row in json.loads(listed.output)]) == (0, ["ROLE-1"])
    assert (refused.exit_code, refused.output) == (
        1,
        f"error: malformed sources override {origin}: "
        "Expected ']' at the end of a table declaration (at line 1, column 18)\n",
    )


@pytest.mark.covers("source list", "--json")
async def test_source_list_shows_each_source_and_whether_a_credential_is_stored(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_links.declare(invoke, project, profile, tracker.base_url)
        source_links.declare_more(
            project,
            '\n[sources.idle]\nconnector = "gitlab"\nproject = "platform/api"\nbase_url = "http://127.0.0.1:9"\n'
            "enabled = false\n"
            f'\n[sources.idle.maps.types.type]\nissue = "{profile.ref}"\n',
        )
        await source_links.pull(invoke)
        listed = await invoke(["source", "list", "--json"])

    assert listed.exit_code == 0, listed.output
    assert json.loads(listed.output) == {
        "sources": [
            {
                "name": "idle",
                "connector": "gitlab",
                "version": "v4",
                "enabled": False,
                "credential": False,
                "items": 0,
                "newest_updated_at": None,
            },
            {
                "name": "platform",
                "connector": "gitlab",
                "version": "v4",
                "enabled": True,
                "credential": True,
                "items": 2,
                "newest_updated_at": "2026-11-03T10:30:00Z",
            },
        ]
    }
    assert source_links.SECRET not in listed.output


@pytest.mark.covers("source list", "--json")
async def test_a_multi_line_expression_in_a_literal_string_loads(project, invoke, profile) -> None:
    text = (
        f'{GITLAB}project = "platform/api"\n\n[sources.platform.filter]\n'
        "labels = '''\n  (type::epic or type::story)\n  and not \"help wanted\"\n'''\n"
        "type = 'issue or incident'\n" + _types(profile)
    )

    exit_code, output = await _listed(invoke, project, text)

    assert exit_code == 0, output
    assert json.loads(output) == _listing()


@pytest.mark.covers("source list", "--json")
async def test_a_long_run_of_line_breaks_in_an_expression_loads(project, invoke, profile) -> None:
    text = (
        f'{GITLAB}project = "platform/api"\n\n[sources.platform.filter]\n'
        f'labels = "a and{"\\r\\n" * 1500}b"\n' + _types(profile)
    )

    exit_code, output = await _listed(invoke, project, text)

    assert exit_code == 0, output
    assert json.loads(output) == _listing()


@pytest.mark.covers("source list", "--json")
async def test_a_quoted_value_takes_any_character_but_a_control_one(
    project, invoke, profile
) -> None:
    text = (
        f'{GITLAB}project = "platform/api"\n\n[sources.platform.filter]\n'
        'labels = "\\"a\u00a0b\\""\n' + _types(profile)
    )

    exit_code, output = await _listed(invoke, project, text)

    assert exit_code == 0, output
    assert json.loads(output) == _listing()


@pytest.mark.covers("source list", "--json")
async def test_a_jira_jql_quoting_order_by_loads(project, invoke, profile) -> None:
    text = (
        '[sources.platform]\nconnector = "jira"\nversion = "cloud-v3"\n'
        'base_url = "http://127.0.0.1:9"\n'
        "jql = 'text ~ \"order by\" AND labels = x'\n"
        f'\n[sources.platform.maps.types.type]\nStory = "{profile.ref}"\n'
    )

    exit_code, output = await _listed(invoke, project, text)

    assert exit_code == 0, output
    assert json.loads(output) == _listing("jira", "cloud-v3")
