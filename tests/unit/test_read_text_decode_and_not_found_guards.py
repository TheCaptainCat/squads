"""``_aio.read_text``'s UTF-8 decode guard and ``_paths.load_config``'s equivalent, plus the
invariant that ``read_text`` keeps propagating a bare ``FileNotFoundError`` unchanged, since
two callers read a missing file as a signal rather than a failure."""

from pathlib import Path

import pytest

from squads import _aio
from squads._errors import SquadsError, UndecodableFileError
from squads._paths import load_config

pytestmark = pytest.mark.anyio


async def test_read_text_raises_a_squads_error_naming_the_file_on_bad_bytes(tmp_path: Path):
    path = tmp_path / "item.md"
    path.write_bytes(b"hello \x80 world")

    with pytest.raises(UndecodableFileError) as excinfo:
        await _aio.read_text(path)
    assert isinstance(excinfo.value, SquadsError)
    assert str(path) in str(excinfo.value)


async def test_read_text_error_carries_the_offending_byte_and_offset(tmp_path: Path):
    path = tmp_path / "item.md"
    path.write_bytes(b"0123456789\x80rest")

    with pytest.raises(UndecodableFileError) as excinfo:
        await _aio.read_text(path)
    message = str(excinfo.value)
    assert "0x80" in message
    assert "10" in message


async def test_read_text_still_propagates_file_not_found_unchanged(tmp_path: Path):
    """A missing file is a plain ``FileNotFoundError``, never converted here."""
    with pytest.raises(FileNotFoundError):
        await _aio.read_text(tmp_path / "does-not-exist.md")


async def test_read_text_reads_a_well_formed_file_exactly_as_before(tmp_path: Path):
    path = tmp_path / "item.md"
    path.write_text("hello world", encoding="utf-8")

    assert await _aio.read_text(path) == "hello world"


def test_load_config_raises_squads_error_on_undecodable_bytes(tmp_path: Path):
    config_path = tmp_path / ".squads.toml"
    config_path.write_bytes(b'squad_dir = "squads\x80"\n')

    with pytest.raises(SquadsError) as excinfo:
        load_config(config_path)
    assert str(config_path) in str(excinfo.value)
