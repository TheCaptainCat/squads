"""`sq source credential set|remove`: the credentials stored for the sources a squad declares."""

import os
import stat
import sys
from pathlib import Path

import pytest

from tests.cli import _source_declared as source_declared
from tests.cli._output import json_text, read_json

pytestmark = pytest.mark.anyio


SECRET = "glpat-not-a-real-token"


def _posix_modes_only() -> None:
    """Skip a case about file modes where the platform keeps none."""
    if sys.platform == "win32":
        pytest.skip("Windows files carry no POSIX mode")


def _written(path: Path, source: str = "platform") -> str:
    return json_text(
        {
            "source": source,
            "base_url": f"{source_declared.TRACKER}/",
            "fields": ["token"],
            "path": str(path),
        }
    )


@pytest.mark.covers("source credential set", "source")
@pytest.mark.covers("source credential set", "--json")
async def test_credential_set_reads_each_value_from_stdin_and_stores_it_privately(
    project, invoke, credentials_home, credential_file, profile
) -> None:
    _posix_modes_only()
    source_declared.declare(project, profile)

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
    source_declared.declare(project, profile)
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
    source_declared.declare(project, profile)
    await invoke(["source", "credential", "set", "platform"], input=f"{SECRET}\n")

    first = await invoke(["source", "credential", "remove", "platform"])
    second = await read_json(invoke, ["source", "credential", "remove", "platform", "--json"])

    assert (first.exit_code, first.stdout) == (
        0,
        f"removed the credential of source platform for {source_declared.TRACKER}/\n",
    )
    assert second == {
        "source": "platform",
        "base_url": f"{source_declared.TRACKER}/",
        "removed": False,
    }
    assert SECRET not in credential_file.read_text(encoding="utf-8")


@pytest.mark.covers("source credential remove", "source")
async def test_a_store_other_users_can_read_is_refused_naming_chmod(
    project, invoke, credentials_home, credential_file, profile
) -> None:
    _posix_modes_only()
    source_declared.declare(project, profile)
    await invoke(["source", "credential", "set", "platform"], input=f"{SECRET}\n")
    credential_file.chmod(0o640)

    result = await invoke(["source", "credential", "remove", "platform"])

    assert (result.exit_code, result.output) == (
        1,
        f"error: the credential store {credential_file} can be read by other users; "
        f"run `chmod 600 {credential_file}` and try again\n",
    )
    assert stat.S_IMODE(credential_file.stat().st_mode) == 0o640
