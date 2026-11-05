"""A scope and a filter expression that `sources.toml` accepts: the source loads and is listed."""

import json

import pytest

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


@pytest.mark.covers("source list", "--json")
async def test_a_multi_line_expression_in_a_literal_string_loads(project, invoke, profile) -> None:
    text = (
        f'{GITLAB}project = "platform/api"\n\n[sources.platform.filter]\n'
        "labels = '''\n  (type::epic or type::story)\n  and not \"help wanted\"\n'''\n"
        "type = 'issue or incident'\n" + _types(profile)
    )

    exit_code, output = await _listed(invoke, project, text)

    assert exit_code == 0, output
    assert [s["name"] for s in json.loads(output)["sources"]] == ["platform"]


@pytest.mark.covers("source list", "--json")
async def test_a_long_run_of_line_breaks_in_an_expression_loads(project, invoke, profile) -> None:
    text = (
        f'{GITLAB}project = "platform/api"\n\n[sources.platform.filter]\n'
        f'labels = "a and{"\\r\\n" * 1500}b"\n' + _types(profile)
    )

    exit_code, output = await _listed(invoke, project, text)

    assert exit_code == 0, output
    assert [s["name"] for s in json.loads(output)["sources"]] == ["platform"]


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
    assert [s["name"] for s in json.loads(output)["sources"]] == ["platform"]


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
