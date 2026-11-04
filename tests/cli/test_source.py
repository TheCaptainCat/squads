"""`sq source …`: the sources a squad declares in `sources.toml`, and the credentials stored for
them where the squad is served."""

import json
import os
import stat
import sys

import pytest

from squads import __version__
from squads._paths import SquadPaths
from squads._sources import CredentialStore
from tests.cli._output import json_text, read_json

pytestmark = pytest.mark.anyio

TRACKER = "http://127.0.0.1:9"
SECRET = "glpat-not-a-real-token"
HEAD = (
    f'[sources.platform]\nconnector = "gitlab"\nproject = "platform/api"\nbase_url = "{TRACKER}/"\n'
)
TYPES = '\n[sources.platform.maps.types.labels]\nbug = "task"\n'
SOURCE = HEAD + TYPES


def _declare(project: SquadPaths, text: str = SOURCE) -> None:
    """Write the squad's `sources.toml` override."""
    path = project.squad_dir / ".overrides" / "sources.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _posix_modes_only() -> None:
    """Skip a case about file modes where the platform keeps none."""
    if sys.platform == "win32":
        pytest.skip("Windows files carry no POSIX mode")


def _written(source: str = "platform") -> str:
    return json_text(
        {
            "source": source,
            "base_url": f"{TRACKER}/",
            "fields": ["token"],
            "path": str(CredentialStore().path()),
        }
    )


# ------------------------------------------------------------------------------------ override


@pytest.mark.covers("override scaffold", "name")
async def test_override_scaffold_sources_writes_a_stamped_starter(project, invoke) -> None:
    scaffolded = await invoke(["override", "scaffold", "sources"])
    listed = await read_json(invoke, ["override", "list", "--json"])

    path = project.squad_dir / ".overrides" / "sources.toml"
    assert scaffolded.exit_code == 0
    assert path.read_text(encoding="utf-8").startswith(f"# squads:override-base:{__version__}\n")
    assert listed == [
        {
            "name": "sources",
            "kind": "sources",
            "base_version": __version__,
            "state": "current",
        }
    ]


@pytest.mark.covers("override scaffold", "name")
async def test_the_scaffolded_worked_example_loads_once_uncommented(project, invoke) -> None:
    await invoke(["override", "scaffold", "sources"])
    path = project.squad_dir / ".overrides" / "sources.toml"
    lines = path.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("# --- Worked example"))
    example = [line.removeprefix("# ") if line != "#" else "" for line in lines[start + 2 : -1]]
    path.write_text("\n".join([*lines[: start + 1], *example]) + "\n", encoding="utf-8")

    listed = await read_json(invoke, ["source", "list", "--json"])

    assert [s["name"] for s in listed["sources"]] == ["platform"]


# ------------------------------------------------------------------------------------ validation


@pytest.mark.covers("source credential remove", "source")
async def test_a_map_target_the_squad_does_not_declare_fails_naming_source_map_and_value(
    project, invoke, credentials_home
) -> None:
    _declare(project, HEAD + '\n[sources.platform.maps.types.labels]\nbug = "defect"\n')

    result = await invoke(["source", "credential", "remove", "platform"])

    origin = project.squad_dir / ".overrides" / "sources.toml"
    assert (result.exit_code, " ".join(result.output.split())) == (
        1,
        f"error: {origin}: invalid sources after merge: source 'platform': maps.types.labels: "
        "'bug' -> 'defect' is not an item type",
    )


@pytest.mark.covers("source credential remove", "source")
async def test_a_source_with_no_type_map_fails_naming_the_source_and_the_map(
    project, invoke, credentials_home
) -> None:
    _declare(project, HEAD)

    result = await invoke(["source", "credential", "remove", "platform"])

    assert result.exit_code == 1
    assert "source 'platform': maps.types is empty" in " ".join(result.output.split())


@pytest.mark.covers("source credential remove", "source")
async def test_a_gitlab_version_it_does_not_register_lists_the_known_ones(
    project, invoke, credentials_home
) -> None:
    _declare(project, HEAD + 'version = "v1"\n' + TYPES)

    result = await invoke(["source", "credential", "remove", "platform"])

    assert result.exit_code == 1
    assert "connector 'gitlab' has no version 'v1' (known: v4)" in " ".join(result.output.split())


@pytest.mark.covers("source credential remove", "source")
async def test_a_broken_sources_document_leaves_the_rest_of_the_squad_working(
    project, invoke, credentials_home
) -> None:
    _declare(project, "[sources.platform\n")

    listed = await invoke(["list", "--json"])
    refused = await invoke(["source", "credential", "remove", "platform"])

    origin = project.squad_dir / ".overrides" / "sources.toml"
    assert (listed.exit_code, [row["id"] for row in json.loads(listed.output)]) == (0, ["ROLE-1"])
    assert refused.exit_code == 1
    assert " ".join(refused.output.split()).startswith(
        f"error: malformed sources override {origin}: "
    )


# ------------------------------------------------------------------------------------ credential


@pytest.mark.covers("source credential set", "source")
@pytest.mark.covers("source credential set", "--json")
async def test_credential_set_reads_each_value_from_stdin_and_stores_it_privately(
    project, invoke, credentials_home
) -> None:
    _posix_modes_only()
    _declare(project)

    result = await invoke(
        ["source", "credential", "set", "platform", "--json"], input=f"{SECRET}\n"
    )

    stored = CredentialStore().path()
    assert (result.exit_code, result.stdout, result.stderr) == (
        0,
        _written(),
        "platform token: ",
    )
    assert stat.S_IMODE(stored.stat().st_mode) == 0o600
    assert stat.S_IMODE(stored.parent.stat().st_mode) == 0o700
    assert SECRET in stored.read_text(encoding="utf-8")


@pytest.mark.covers("source credential set", "source")
async def test_credential_set_ignores_what_a_crash_left_and_tightens_an_open_directory(
    project, invoke, credentials_home
) -> None:
    _posix_modes_only()
    _declare(project)
    store = CredentialStore().path()
    store.parent.mkdir(parents=True)
    store.parent.chmod(0o755)
    victim = store.parent / "victim"
    victim.write_text("keep", encoding="utf-8")
    stale = store.with_name(f".{store.name}.{os.getpid()}.tmp")
    stale.symlink_to(victim)

    result = await invoke(["source", "credential", "set", "platform"], input=f"{SECRET}\n")

    assert result.exit_code == 0, result.output
    assert victim.read_text(encoding="utf-8") == "keep"
    assert (stat.S_IMODE(store.stat().st_mode), stat.S_IMODE(store.parent.stat().st_mode)) == (
        0o600,
        0o700,
    )
    assert not stale.exists()


@pytest.mark.covers("source credential remove", "source")
@pytest.mark.covers("source credential remove", "--json")
async def test_credential_remove_deletes_the_entry_and_a_second_removal_finds_none(
    project, invoke, credentials_home
) -> None:
    _declare(project)
    await invoke(["source", "credential", "set", "platform"], input=f"{SECRET}\n")

    first = await invoke(["source", "credential", "remove", "platform"])
    second = await read_json(invoke, ["source", "credential", "remove", "platform", "--json"])

    assert (first.exit_code, " ".join(first.stdout.split())) == (
        0,
        f"removed the credential of source platform for {TRACKER}/",
    )
    assert second == {"source": "platform", "base_url": f"{TRACKER}/", "removed": False}
    assert SECRET not in CredentialStore().path().read_text(encoding="utf-8")


@pytest.mark.covers("source credential remove", "source")
async def test_a_store_other_users_can_read_is_refused_naming_chmod(
    project, invoke, credentials_home
) -> None:
    _posix_modes_only()
    _declare(project)
    await invoke(["source", "credential", "set", "platform"], input=f"{SECRET}\n")
    CredentialStore().path().chmod(0o640)

    result = await invoke(["source", "credential", "remove", "platform"])

    assert result.exit_code == 1
    assert f"run `chmod 600 {CredentialStore().path()}`" in " ".join(result.output.split())
    assert SECRET in CredentialStore().path().read_text(encoding="utf-8")
