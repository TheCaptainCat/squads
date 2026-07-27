"""The read-path primitives behind the CLI-layer clean-failure behaviour, one layer below
`test_frontmatter_and_config_parse_guard.py`'s YAML/TOML *parse* guards: `_aio.read_text`'s own
UTF-8 *decode* guard, and `_paths.load_config`'s equivalent for the bytes it decodes itself
(inside `tomllib.load`, before the TOML grammar is ever reached, so the existing
`TOMLDecodeError` handler never sees it).

Also pins the one behaviour the rest of this task depends on staying put:
`_aio.read_text` must keep propagating a bare `FileNotFoundError` unchanged. Two callers read a
missing file as a signal rather than a failure -- the `check` confirm round's stale-path
fallback (`_services/_maintenance.py`) and the bulk importer's pre-pass skew guard
(`_services/_import.py`, pinned separately in its own test) -- and a decode-style conversion
placed in the shared helper would turn both into a crash on exactly the interrupted-rename
state this task exists to make friendly. If this test starts failing, the not-found guard has
been placed in the shared helper by mistake.
"""

from pathlib import Path

import pytest

from squads import _aio
from squads._errors import SquadsError, UndecodableFileError
from squads._paths import load_config

pytestmark = pytest.mark.anyio


async def test_read_text_raises_a_squads_error_naming_the_file_on_bad_bytes(tmp_path: Path):
    path = tmp_path / "item.md"
    path.write_bytes(b"hello \x80 world")

    with pytest.raises(UndecodableFileError, match=str(path)) as excinfo:
        await _aio.read_text(path)
    assert isinstance(excinfo.value, SquadsError)


async def test_read_text_error_carries_the_offending_byte_and_offset(tmp_path: Path):
    path = tmp_path / "item.md"
    path.write_bytes(b"0123456789\x80rest")

    with pytest.raises(UndecodableFileError) as excinfo:
        await _aio.read_text(path)
    message = str(excinfo.value)
    assert "0x80" in message
    assert "10" in message  # the byte's offset


async def test_read_text_still_propagates_file_not_found_unchanged(tmp_path: Path):
    """The one call `check`'s confirm round and the bulk importer's pre-pass both depend on:
    a missing file is a plain `FileNotFoundError`, not converted here -- see the module
    docstring for why."""
    with pytest.raises(FileNotFoundError):
        await _aio.read_text(tmp_path / "does-not-exist.md")


async def test_read_text_reads_a_well_formed_file_exactly_as_before(tmp_path: Path):
    path = tmp_path / "item.md"
    path.write_text("hello world", encoding="utf-8")

    assert await _aio.read_text(path) == "hello world"


def test_load_config_raises_squads_error_on_undecodable_bytes(tmp_path: Path):
    config_path = tmp_path / ".squads.toml"
    config_path.write_bytes(b'squad_dir = "squads\x80"\n')

    with pytest.raises(SquadsError, match=str(config_path)):
        load_config(config_path)
