"""Manage the squads-owned section of CLAUDE.md, delimited by stable markers."""

from pathlib import Path

START = "<!-- squads:start -->"
END = "<!-- squads:end -->"


def wrap(section_body: str) -> str:
    return f"{START}\n{section_body.rstrip()}\n{END}\n"


def inject(claude_md: Path, section_body: str) -> None:
    """Insert or replace the managed section, preserving everything else in the file."""
    block = wrap(section_body)
    if not claude_md.exists():
        claude_md.write_text(f"# Project guidance\n\n{block}", encoding="utf-8")
        return
    text = claude_md.read_text(encoding="utf-8")
    si, ei = text.find(START), text.find(END)
    if si != -1 and ei != -1:
        new = text[:si] + block.rstrip("\n") + text[ei + len(END) :]
        claude_md.write_text(new, encoding="utf-8")
    else:
        sep = "" if text.endswith("\n") else "\n"
        claude_md.write_text(f"{text}{sep}\n{block}", encoding="utf-8")
