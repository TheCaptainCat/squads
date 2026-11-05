"""`sq source …`: the sources a squad declares in `sources.toml`, and the credentials stored for
them where the squad is served."""

import json
import os
import stat
import sys
from pathlib import Path

import pytest

from squads import __version__
from squads._paths import SquadPaths
from tests.cli._output import json_text, read_json

pytestmark = pytest.mark.anyio

TRACKER = "http://127.0.0.1:9"
SECRET = "glpat-not-a-real-token"
HEAD = (
    f'[sources.platform]\nconnector = "gitlab"\nproject = "platform/api"\nbase_url = "{TRACKER}/"\n'
)


def _types(profile) -> str:
    return f'\n[sources.platform.maps.types.labels]\nbug = "{profile.ref}"\n'


def _declare(project: SquadPaths, profile, text: str | None = None) -> None:
    """Write the squad's `sources.toml` override: *text*, or `platform` with its type map."""
    text = HEAD + _types(profile) if text is None else text
    path = project.squad_dir / ".overrides" / "sources.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _posix_modes_only() -> None:
    """Skip a case about file modes where the platform keeps none."""
    if sys.platform == "win32":
        pytest.skip("Windows files carry no POSIX mode")


def _written(path: Path, source: str = "platform") -> str:
    return json_text(
        {
            "source": source,
            "base_url": f"{TRACKER}/",
            "fields": ["token"],
            "path": str(path),
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
    assert [row for row in listed if row["name"] == "sources"] == [
        {
            "name": "sources",
            "kind": "sources",
            "base_version": __version__,
            "state": "current",
        }
    ]


@pytest.mark.bundled_only("the scaffolded worked example maps tracker types onto bundled ones")
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


@pytest.mark.covers("source list")
async def test_a_broken_sources_document_leaves_the_rest_of_the_squad_working(
    project, invoke, credentials_home, profile
) -> None:
    _declare(project, profile, "[sources.platform\n")

    listed = await invoke(["list", "--json"])
    refused = await invoke(["source", "list"])

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
    project, invoke, credentials_home, credential_file, profile
) -> None:
    _posix_modes_only()
    _declare(project, profile)

    result = await invoke(
        ["source", "credential", "set", "platform", "--json"], input=f"{SECRET}\n"
    )
    modes = (
        stat.S_IMODE(credential_file.stat().st_mode),
        stat.S_IMODE(credential_file.parent.stat().st_mode),
    )
    removed = await read_json(invoke, ["source", "credential", "remove", "platform", "--json"])

    assert (result.exit_code, result.stdout, result.stderr) == (
        0,
        _written(credential_file),
        "platform token: ",
    )
    assert modes == (0o600, 0o700)
    assert removed["removed"] is True


@pytest.mark.covers("source credential set", "source")
async def test_credential_set_ignores_what_a_crash_left_and_tightens_an_open_directory(
    project, invoke, credentials_home, credential_file, profile
) -> None:
    _posix_modes_only()
    _declare(project, profile)
    store = credential_file
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
    project, invoke, credentials_home, credential_file, profile
) -> None:
    _declare(project, profile)
    await invoke(["source", "credential", "set", "platform"], input=f"{SECRET}\n")

    first = await invoke(["source", "credential", "remove", "platform"])
    second = await read_json(invoke, ["source", "credential", "remove", "platform", "--json"])

    assert (first.exit_code, " ".join(first.stdout.split())) == (
        0,
        f"removed the credential of source platform for {TRACKER}/",
    )
    assert second == {"source": "platform", "base_url": f"{TRACKER}/", "removed": False}
    assert SECRET not in credential_file.read_text(encoding="utf-8")


@pytest.mark.covers("source credential remove", "source")
async def test_a_store_other_users_can_read_is_refused_naming_chmod(
    project, invoke, credentials_home, credential_file, profile
) -> None:
    _posix_modes_only()
    _declare(project, profile)
    await invoke(["source", "credential", "set", "platform"], input=f"{SECRET}\n")
    credential_file.chmod(0o640)

    result = await invoke(["source", "credential", "remove", "platform"])

    assert result.exit_code == 1
    assert f"run `chmod 600 {credential_file}`" in " ".join(result.output.split())
    assert stat.S_IMODE(credential_file.stat().st_mode) == 0o640
