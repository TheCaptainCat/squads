"""Manage the squads-owned section of CLAUDE.md, delimited by stable markers.

Thin, file-specific wrapper over the shared managed-region mechanism in
``_backends/_managed_region.py`` (the marker/warning stamping every ``AgentBackend``
shares) — this module only supplies the CLAUDE.md-specific "create if missing" header.
"""

from pathlib import Path

from squads._backends import _managed_region as managed

START = managed.START
END = managed.END


def wrap(section_body: str) -> str:
    return managed.wrap(section_body)


async def inject(claude_md: Path, section_body: str) -> bool:
    """Insert or replace the managed section, preserving everything else in the file.

    Returns whether the block was inserted into pre-existing hand-written content (no
    markers yet) — see :func:`squads._backends._managed_region.inject`.
    """
    return await managed.inject(claude_md, section_body, missing_header="# Project guidance\n\n")
