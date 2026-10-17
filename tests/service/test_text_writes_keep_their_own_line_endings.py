"""Every text write keeps the line endings it was given, whatever the platform default is.

Windows translates a text-mode ``\\n`` to ``\\r\\n``; the shim below does the same where the
caller leaves ``newline`` unset, so a writer that forgets ``newline=""`` shows up on Linux.
"""

import pathlib
from pathlib import Path
from typing import Any

import pytest

from squads import _aio
from squads._models._config import SquadsConfig

_real_write_text = pathlib.Path.write_text
_real_open = pathlib.Path.open


@pytest.fixture(autouse=True)
def windows_newlines(monkeypatch: pytest.MonkeyPatch) -> None:
    def write_text(self: Path, data: str, encoding=None, errors=None, newline=None) -> int:
        if newline is None:
            data = data.replace("\n", "\r\n")
        return _real_write_text(self, data, encoding, errors, newline="")

    def open_(self: Path, mode="r", buffering=-1, encoding=None, errors=None, newline=None):
        if "b" not in mode and ("w" in mode or "a" in mode) and newline is None:
            raise AssertionError(f"text-mode {mode!r} open of {self} leaves newline unset")
        return _real_open(self, mode, buffering, encoding, errors, newline)

    monkeypatch.setattr(pathlib.Path, "write_text", write_text)
    monkeypatch.setattr(pathlib.Path, "open", open_)


_MIXED = "a\nb\r\nc\r\r\n"


async def test_the_plain_write_keeps_every_byte(tmp_path: Path) -> None:
    path = tmp_path / "f.txt"

    await _aio.write_text(path, _MIXED)

    assert path.read_bytes() == _MIXED.encode()


async def test_the_atomic_write_keeps_every_byte(tmp_path: Path) -> None:
    path = tmp_path / "f.txt"

    await _aio.atomic_write_text(path, _MIXED)

    assert path.read_bytes() == _MIXED.encode()


def test_a_config_with_a_windows_squad_dir_reads_back() -> None:
    import tomllib

    cfg = SquadsConfig(squad_dir="C:\\Users\\me\\shared")

    back: dict[str, Any] = tomllib.loads(cfg.to_toml())

    assert back["squad_dir"] == "C:\\Users\\me\\shared"
