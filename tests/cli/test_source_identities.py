"""`sq operator <slug> update --identities`: an operator's tracker user IDs by source name, set as
given or resolved from a handle through the source's connector."""

import pytest

from tests import _tracker_harness as harness
from tests.cli._output import read_json

pytestmark = pytest.mark.anyio

SECRET = "glpat-not-a-real-token"


def _declare(project, base_url: str, extra: str = "") -> None:
    """Declare the `platform` source on *base_url*, with the keys of *extra* in its table."""
    path = project.squad_dir / ".overrides" / "sources.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'[sources.platform]\nconnector = "gitlab"\nfilter = "squads"\n'
        f'base_url = "{base_url}"\n{extra}'
        '\n[sources.platform.maps.types]\nbug = "task"\n',
        encoding="utf-8",
    )


async def _identities(invoke) -> object:
    return (await read_json(invoke, ["operator", "op-alice", "show", "--json"]))["identities"]


@pytest.fixture
async def alice(invoke) -> None:
    result = await invoke(["operator", "add", "Alice Tester"])
    assert result.exit_code == 0, result.output


@pytest.mark.covers("operator update", "--identities")
async def test_identities_set_a_key_as_given_and_remove_it_with_an_empty_value(
    project, invoke, alice
) -> None:
    first = await invoke(["operator", "op-alice", "update", "--identities", "src=4567"])
    set_value = await _identities(invoke)
    second = await invoke(["operator", "op-alice", "update", "--identities", "src="])

    assert (first.exit_code, second.exit_code) == (0, 0)
    assert set_value == {"src": "4567"}
    assert await _identities(invoke) == {}


@pytest.mark.covers("operator update", "--identities")
async def test_identities_resolve_a_handle_to_the_trackers_immutable_user_id(
    project, invoke, alice, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        _declare(project, tracker.base_url)
        stored = await invoke(["source", "credential", "set", "platform"], input=f"{SECRET}\n")
        assert stored.exit_code == 0, stored.output
        result = await invoke(["operator", "op-alice", "update", "--identities", "platform=@pchat"])
        assert result.exit_code == 0, result.output
        assert await _identities(invoke) == {"platform": "4567"}

        missing = await invoke(
            ["operator", "op-alice", "update", "--identities", "platform=@nobody"]
        )
    assert missing.exit_code == 1
    assert "has no user '@nobody'" in " ".join(missing.output.split())
    assert await _identities(invoke) == {"platform": "4567"}


@pytest.mark.covers("operator update", "--identities")
async def test_a_handle_on_a_source_without_a_credential_is_refused_naming_the_remedy(
    project, invoke, alice, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        _declare(project, tracker.base_url)
        result = await invoke(["operator", "op-alice", "update", "--identities", "platform=@pchat"])
    assert result.exit_code == 1
    assert "run `sq source credential set platform`" in " ".join(result.output.split())
    assert await _identities(invoke) == {}
    assert tracker.requests == []


@pytest.mark.covers("operator update", "--identities")
async def test_a_handle_on_a_disabled_or_an_undeclared_source_is_refused(
    project, invoke, alice, credentials_home
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        _declare(project, tracker.base_url, "enabled = false\n")
        stored = await invoke(["source", "credential", "set", "platform"], input=f"{SECRET}\n")
        assert stored.exit_code == 0, stored.output
        disabled = await invoke(
            ["operator", "op-alice", "update", "--identities", "platform=@pchat"]
        )
        undeclared = await invoke(["operator", "op-alice", "update", "--identities", "x=@pchat"])
    assert disabled.exit_code == 1
    assert "enabled = false" in " ".join(disabled.output.split())
    assert undeclared.exit_code == 1
    assert "no source 'x' is declared (declared: platform)" in " ".join(undeclared.output.split())
    assert tracker.requests == []


@pytest.mark.covers("operator update", "--identities")
async def test_a_pair_without_an_equals_sign_is_refused(project, invoke, alice) -> None:
    result = await invoke(["operator", "op-alice", "update", "--identities", "novalue"])
    assert result.exit_code == 1
    assert "--identities expects key=value, got 'novalue'" in result.output


@pytest.mark.covers("<type> update", "--set")
async def test_set_refuses_a_map_attribute_and_names_the_option(project, invoke) -> None:
    override = project.squad_dir / ".overrides" / "workflow.toml"
    override.parent.mkdir(parents=True, exist_ok=True)
    override.write_text('[items.task.attributes]\nlinks = { kind = "map" }\n', encoding="utf-8")
    created = await invoke(["create", "task", "Map host", "--author", "manager", "--json"])
    assert created.exit_code == 0, created.output

    refused = await invoke(["task", "2", "update", "--set", "links=a=b"])
    done = await invoke(["task", "2", "update", "--links", "a=b", "--links", "c=d"])
    row = await read_json(invoke, ["task", "2", "show", "--json"])

    assert refused.exit_code == 1
    assert "'links' is a map; set a key with `--links key=value`" in " ".join(
        refused.output.split()
    )
    assert done.exit_code == 0, done.output
    assert row["links"] == {"a": "b", "c": "d"}
