"""Manage the squads-owned section of AGENTS.md, delimited by stable markers."""

from pathlib import Path

from squads import _aio

START = "<!-- squads:start -->"
END = "<!-- squads:end -->"


def wrap(section_body: str) -> str:
    return f"{START}\n{section_body.rstrip()}\n{END}\n"


async def inject(agents_md: Path, section_body: str) -> None:
    """Insert or replace the managed section, preserving everything else in the file."""
    block = wrap(section_body)
    if not await _aio.path_exists(agents_md):
        header = "# AGENTS.md — Project AI agent guidance\n\n"
        await _aio.write_text(agents_md, f"{header}{block}")
        return
    text = await _aio.read_text(agents_md)
    si, ei = text.find(START), text.find(END)
    if si != -1 and ei != -1:
        new = text[:si] + block.rstrip("\n") + text[ei + len(END) :]
        await _aio.write_text(agents_md, new)
    else:
        sep = "" if text.endswith("\n") else "\n"
        await _aio.write_text(agents_md, f"{text}{sep}\n{block}")
