#!/usr/bin/env python3
"""Generate the per-release template content-hash manifest.

Run this script before building a release wheel to update
``src/squads/_rendering/templates_manifest.json``.

Usage::

    python scripts/gen_template_manifest.py           # write mode (release)
    python scripts/gen_template_manifest.py --check   # verify mode (CI / local gate)

The manifest maps squads version → dict of template-name → SHA-256 hex digest.
Each release appends a new version entry; existing entries are preserved so
``sq override diff`` can recover the base-version bundled template content.

**Write mode** (default): regenerates/updates the manifest file and exits 0.
A no-op run where the manifest is already current also exits 0.

**Check mode** (``--check``): verifies the manifest is current for the running
version without writing anything.  Exits 0 if the manifest is fresh, exits 1
if the manifest is missing, stale, or covers different templates than the tree.
Use this in CI to prove the manifest was committed correctly.

Release integration checklist:
  1. Run: ``python scripts/gen_template_manifest.py``  (updates the manifest)
  2. Commit the updated manifest together with any template changes.
  3. Run ``uv build`` — the manifest ships automatically as package data.
  4. Confirm with: ``python -c "import importlib.resources as r; \\
       p = r.files('squads._rendering') / 'templates_manifest.json'; \\
       print(p.read_text()[:80])"``
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_TEMPLATES_DIR = _REPO_ROOT / "src" / "squads" / "_rendering" / "templates"
_MANIFEST_PATH = _REPO_ROOT / "src" / "squads" / "_rendering" / "templates_manifest.json"
_VERSION_PATH = _REPO_ROOT / "src" / "squads" / "__init__.py"


def _current_version() -> str:
    text = _VERSION_PATH.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("__version__"):
            _, _, rhs = line.partition("=")
            return rhs.strip().strip('"').strip("'")
    raise SystemExit("error: could not parse __version__ from squads/__init__.py")


def _hash_file(path: Path) -> str:
    # Normalize CRLF → LF before hashing so the digest is platform-independent.
    # Windows git may check out .j2 files as CRLF without a .gitattributes; the
    # runtime hasher applies the same normalization, so the values stay consistent.
    raw = path.read_bytes()
    normalized = raw.replace(b"\r\n", b"\n")
    return hashlib.sha256(normalized).hexdigest()


def _collect_hashes() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(_TEMPLATES_DIR.rglob("*.md.j2")):
        rel = path.relative_to(_TEMPLATES_DIR).as_posix()
        hashes[rel] = _hash_file(path)
    return hashes


def _check_mode(version: str, current_hashes: dict[str, str]) -> None:
    """Verify the manifest is current without writing.  Exits 1 on any mismatch."""
    if not _MANIFEST_PATH.exists():
        print(f"error: manifest not found at {_MANIFEST_PATH}", file=sys.stderr)
        print("run: python scripts/gen_template_manifest.py", file=sys.stderr)
        sys.exit(1)

    manifest: dict[str, dict[str, str]] = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))

    if version not in manifest:
        print(f"error: manifest has no entry for v{version}", file=sys.stderr)
        print("run: python scripts/gen_template_manifest.py", file=sys.stderr)
        sys.exit(1)

    recorded = manifest[version]
    problems: list[str] = []

    missing = set(current_hashes) - set(recorded)
    if missing:
        problems.extend(f"  missing in manifest: {name}" for name in sorted(missing))

    extra = set(recorded) - set(current_hashes)
    if extra:
        problems.extend(f"  phantom in manifest: {name}" for name in sorted(extra))

    stale = [name for name, h in current_hashes.items() if name in recorded and recorded[name] != h]
    if stale:
        problems.extend(f"  stale hash: {name}" for name in sorted(stale))

    if problems:
        n = len(problems)
        print(f"error: manifest v{version} is not current ({n} problem(s)):", file=sys.stderr)
        for line in problems:
            print(line, file=sys.stderr)
        print("run: python scripts/gen_template_manifest.py", file=sys.stderr)
        sys.exit(1)

    print(f"manifest v{version} is current ({len(current_hashes)} templates)")


def _write_mode(version: str, current_hashes: dict[str, str]) -> None:
    """Regenerate/update the manifest file."""
    if _MANIFEST_PATH.exists():
        manifest: dict[str, dict[str, str]] = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    else:
        manifest = {}

    if version in manifest and manifest[version] == current_hashes:
        print(f"manifest already up to date for v{version} ({len(current_hashes)} templates)")
        return

    manifest[version] = current_hashes
    _MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"wrote manifest for v{version}: {len(current_hashes)} template hashes"
        f" → {_MANIFEST_PATH.relative_to(_REPO_ROOT)}"
    )


def main() -> None:
    check = "--check" in sys.argv[1:]
    version = _current_version()
    current_hashes = _collect_hashes()

    if check:
        _check_mode(version, current_hashes)
    else:
        _write_mode(version, current_hashes)


if __name__ == "__main__":
    main()
    sys.exit(0)
