#!/usr/bin/env python3
"""Automate the mechanical release version bump documented in the
``releasing-squads`` skill's Prep section.

Usage::

    uv run python scripts/bump_version.py X.Y.Z            # bump for real
    uv run python scripts/bump_version.py X.Y.Z --dry-run  # print the plan only

Steps, in order (each prints as it runs; any failure exits non-zero with a
clear message):

  1. Read the CURRENT version from ``pyproject.toml`` ``[project].version``
     (the "prior" version, needed for step 5's tag lookup).
  2. Rewrite ``pyproject.toml`` ``version`` -> the new version.
  3. Rewrite ``clients/vscode/package.json`` ``version`` -> the new version.
  4. ``uv sync --all-extras`` so ``squads.__version__`` reflects the bump.
  5. Template-manifest gotcha: ``git checkout v<prior> --
     src/squads/_rendering/templates_manifest.json`` (restoring the prior
     release's entry byte-identical to its tag), then run
     ``scripts/gen_template_manifest.py`` in write mode so a clean new-version
     entry appends. If tag ``v<prior>`` does not exist, the checkout is
     skipped with a clear note (first-run case).
  6. Regenerate the version-embedding goldens:
     ``UPDATE_GOLDENS=1 uv run --all-extras pytest
     tests/cli/test_json_output_shape.py -q -n0``.
  7. ``sq sync`` to re-stamp this repo's managed files.
  8. Print a summary of every file/step, old -> new.

This script never edits CHANGELOG.md, and never runs ``git commit``,
``git tag``, or ``git push`` — those stay human (or the coordinating agent
loop, outside this script).
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PYPROJECT_PATH = _REPO_ROOT / "pyproject.toml"
_PACKAGE_JSON_PATH = _REPO_ROOT / "clients" / "vscode" / "package.json"
_MANIFEST_REL_PATH = Path("src") / "squads" / "_rendering" / "templates_manifest.json"
_GEN_MANIFEST_SCRIPT = Path("scripts") / "gen_template_manifest.py"
_GOLDENS_TEST_PATH = Path("tests") / "cli" / "test_json_output_shape.py"

_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[.\-][0-9A-Za-z.]+)?$")

# ---------------------------------------------------------------------------
# Pure rewrite helpers — no I/O, no side effects. Take/return text so they are
# trivially unit-testable in isolation from the filesystem.
# ---------------------------------------------------------------------------

_PYPROJECT_PROJECT_SECTION_RE = re.compile(r"(?ms)^\[project\]\n(.*?)(?=^\[|\Z)")
_PYPROJECT_VERSION_LINE_RE = re.compile(r'(?m)^version\s*=\s*"([^"]*)"\s*$')


def read_pyproject_version(text: str) -> str:
    """Return the ``[project].version`` value from ``pyproject.toml`` text.

    Raises ``ValueError`` if the ``[project]`` section or its ``version``
    field is missing (a malformed or absent-version file).
    """
    section_match = _PYPROJECT_PROJECT_SECTION_RE.search(text)
    if section_match is None:
        raise ValueError("pyproject.toml: no [project] section found")
    version_match = _PYPROJECT_VERSION_LINE_RE.search(section_match.group(1))
    if version_match is None:
        raise ValueError("pyproject.toml: no version field found in [project] section")
    return version_match.group(1)


def set_pyproject_version(text: str, new_version: str) -> str:
    """Return ``pyproject.toml`` text with ``[project].version`` rewritten.

    Only the ``version`` line inside ``[project]`` is touched; every other
    byte (comments, other tables, formatting) is preserved. Raises
    ``ValueError`` on the same malformed/absent-version conditions as
    ``read_pyproject_version``.
    """
    section_match = _PYPROJECT_PROJECT_SECTION_RE.search(text)
    if section_match is None:
        raise ValueError("pyproject.toml: no [project] section found")
    section = section_match.group(1)
    if _PYPROJECT_VERSION_LINE_RE.search(section) is None:
        raise ValueError("pyproject.toml: no version field found in [project] section")
    new_section = _PYPROJECT_VERSION_LINE_RE.sub(f'version = "{new_version}"', section, count=1)
    start, end = section_match.span(1)
    return text[:start] + new_section + text[end:]


_PACKAGE_JSON_VERSION_RE = re.compile(r'("version"\s*:\s*")([^"]*)(")')


def read_package_json_version(text: str) -> str:
    """Return the top-level ``"version"`` value from ``package.json`` text.

    Raises ``ValueError`` if no ``"version"`` field is present.
    """
    match = _PACKAGE_JSON_VERSION_RE.search(text)
    if match is None:
        raise ValueError('package.json: no "version" field found')
    return match.group(2)


def set_package_json_version(text: str, new_version: str) -> str:
    """Return ``package.json`` text with its ``"version"`` field rewritten.

    Preserves formatting (indentation, key order, trailing commas) by
    replacing only the matched value in place. Raises ``ValueError`` if no
    ``"version"`` field is present.
    """
    match = _PACKAGE_JSON_VERSION_RE.search(text)
    if match is None:
        raise ValueError('package.json: no "version" field found')
    start, end = match.span()
    replacement = f"{match.group(1)}{new_version}{match.group(3)}"
    return text[:start] + replacement + text[end:]


# ---------------------------------------------------------------------------
# Side-effecting orchestration — file I/O + subprocess calls to the same
# tools a human would run by hand.
# ---------------------------------------------------------------------------


class BumpError(SystemExit):
    """Raised (as a SystemExit) to fail loudly with a clear message."""

    def __init__(self, message: str) -> None:
        super().__init__(f"error: {message}")


def _run(cmd: list[str], *, env: dict[str, str] | None = None) -> None:
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=_REPO_ROOT, env=env, check=False)
    if result.returncode != 0:
        raise BumpError(f"command failed ({result.returncode}): {' '.join(cmd)}")


def _tag_exists(tag: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}"],
        cwd=_REPO_ROOT,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def _step(n: int, title: str) -> None:
    print(f"\n[{n}/8] {title}")


def _step1_read_current_version() -> tuple[str, str]:
    _step(1, "read current version from pyproject.toml")
    pyproject_text = _PYPROJECT_PATH.read_text(encoding="utf-8")
    try:
        current_version = read_pyproject_version(pyproject_text)
    except ValueError as exc:
        raise BumpError(str(exc)) from exc
    print(f"  current version: {current_version}")
    return current_version, pyproject_text


def _step2_bump_pyproject(pyproject_text: str, new_version: str, *, dry_run: bool) -> None:
    _step(2, f"bump pyproject.toml -> {new_version}")
    if dry_run:
        print("  [dry-run] would rewrite pyproject.toml")
        return
    new_text = set_pyproject_version(pyproject_text, new_version)
    _PYPROJECT_PATH.write_text(new_text, encoding="utf-8")
    print(f"  wrote {_PYPROJECT_PATH.relative_to(_REPO_ROOT)}")


def _step3_bump_package_json(new_version: str, *, dry_run: bool) -> None:
    _step(3, f"bump clients/vscode/package.json -> {new_version}")
    package_json_text = _PACKAGE_JSON_PATH.read_text(encoding="utf-8")
    try:
        read_package_json_version(package_json_text)
    except ValueError as exc:
        raise BumpError(str(exc)) from exc
    if dry_run:
        print("  [dry-run] would rewrite clients/vscode/package.json")
        return
    new_text = set_package_json_version(package_json_text, new_version)
    _PACKAGE_JSON_PATH.write_text(new_text, encoding="utf-8")
    print(f"  wrote {_PACKAGE_JSON_PATH.relative_to(_REPO_ROOT)}")


def _step4_uv_sync(*, dry_run: bool) -> None:
    _step(4, "uv sync --all-extras")
    if dry_run:
        print("  [dry-run] would run: uv sync --all-extras")
        return
    _run(["uv", "sync", "--all-extras"])


def _step5_template_manifest(current_version: str, *, dry_run: bool) -> None:
    prior_tag = f"v{current_version}"
    _step(5, f"template-manifest gotcha (prior tag {prior_tag})")
    if dry_run:
        print(f"  [dry-run] would check for tag {prior_tag}; if present, restore the manifest")
        print("  [dry-run] would run: uv run python scripts/gen_template_manifest.py")
        return
    if _tag_exists(prior_tag):
        print(f"  restoring prior manifest entry from {prior_tag}")
        _run(["git", "checkout", prior_tag, "--", str(_MANIFEST_REL_PATH)])
    else:
        print(f"  note: tag {prior_tag} not found — skipping checkout (first-run case)")
    _run(["uv", "run", "python", str(_GEN_MANIFEST_SCRIPT)])


def _step6_regen_goldens(*, dry_run: bool) -> None:
    _step(6, "regenerate version-embedding goldens")
    goldens_cmd = ["uv", "run", "--all-extras", "pytest", str(_GOLDENS_TEST_PATH), "-q", "-n0"]
    if dry_run:
        print(f"  [dry-run] would run (with UPDATE_GOLDENS=1): {' '.join(goldens_cmd)}")
        return
    env = {**os.environ, "UPDATE_GOLDENS": "1"}
    _run(goldens_cmd, env=env)


def _step7_sq_sync(*, dry_run: bool) -> None:
    _step(7, "sq sync")
    if dry_run:
        print("  [dry-run] would run: uv run sq sync")
        return
    _run(["uv", "run", "sq", "sync"])


def bump_version(new_version: str, *, dry_run: bool = False) -> None:
    """Run the full release version-bump sequence (or print its plan)."""
    if not _VERSION_RE.match(new_version):
        raise BumpError(f"{new_version!r} does not look like a version (expected X.Y.Z)")

    mode = " (dry run — no changes will be made)" if dry_run else ""
    print(f"squads release version bump -> {new_version}{mode}")

    current_version, pyproject_text = _step1_read_current_version()
    if current_version == new_version:
        raise BumpError(f"new version {new_version!r} matches the current version — nothing to do")

    _step2_bump_pyproject(pyproject_text, new_version, dry_run=dry_run)
    _step3_bump_package_json(new_version, dry_run=dry_run)
    _step4_uv_sync(dry_run=dry_run)
    _step5_template_manifest(current_version, dry_run=dry_run)
    _step6_regen_goldens(dry_run=dry_run)
    _step7_sq_sync(dry_run=dry_run)

    _step(8, "summary")
    _print_summary(current_version, new_version, dry_run=dry_run)


def _print_summary(current_version: str, new_version: str, *, dry_run: bool) -> None:
    suffix = " (dry-run — nothing was written)" if dry_run else ""
    rows = [
        ("pyproject.toml [project].version", current_version, new_version),
        ("clients/vscode/package.json version", current_version, new_version),
    ]
    print(f"Summary{suffix}:")
    width = max(len(label) for label, _, _ in rows)
    for label, old, new in rows:
        print(f"  {label.ljust(width)}  {old} -> {new}")
    print(f"  {'template manifest'.ljust(width)}  new v{new_version} entry appended")
    print(f"  {'version-embedding goldens'.ljust(width)}  regenerated")
    print(f"  {'.squads.toml squads_version'.ljust(width)}  re-stamped via sq sync")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0] if __doc__ else "")
    parser.add_argument("new_version", help="new release version, e.g. 0.13.0")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the plan without writing or running anything",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    bump_version(args.new_version, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
    sys.exit(0)
