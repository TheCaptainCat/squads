#!/usr/bin/env python3
"""Generate the per-release provenance manifest for every overridable bundled artifact: the
24 bundled templates plus ``workflow.toml``, ``roles.toml`` and ``playbook.toml``.

Run this script before building a release wheel to update
``src/squads/_rendering/templates_manifest.json`` (the hash INDEX) and
``src/squads/_rendering/content_store.json`` (the content STORE).

Usage::

    python scripts/gen_template_manifest.py                # write mode (release)
    python scripts/gen_template_manifest.py --check         # verify mode (CI / local gate)
    python scripts/gen_template_manifest.py --release-gate  # verify mode, whole index, also
                                                             # fails on an orphaned blob —
                                                             # run after the rebuild, right
                                                             # before the tag

Two documents, two write modes:
- The INDEX's per-version entry is a **wholesale replacement**, keyed on
  ``[project].version`` — existing entries for other versions are untouched, so
  ``sq override diff`` can recover the base-version bundled content for any release the
  index still names.
- The STORE is **insert-if-absent, and never deletes.** No revision an index entry names is
  ever removed by this script. Removing a blob is a capability of the **rebuild**
  (``python scripts/seed_content_store.py --rebuild``), which recomputes the store as the
  closure of every index-named hash — sourced from each version's release tag whenever one
  exists, and from the working tree only for a version with no tag at all — and drops whatever
  is not in that closure. Never this script: it never reads git, so from inside the working
  tree it cannot tell a discarded scratch revision of an unreleased version from a shipped
  revision of a released one, and any sweep it performed would destroy the latter the moment a
  release is tagged.

**This script never reads git.** Its steady-state contract is "hash the current tree, replace
this version's index entry, insert what is absent from the store" — nothing more. The store's
history below this widening release was populated once, as a one-time data step against the
release tags — see ``scripts/seed_content_store.py`` — not a capability of this script.

**Recovery from a mis-ordered regeneration** (running this script while ``[project].version``
still names an already-shipped release): that release's index entry gets overwritten with the
working tree's current hashes, which is wrong, but the store loses nothing — this script never
deletes. Restoring just that one index entry from its release tag by hand is not enough either:
it fixes the entry you noticed and nothing else, and it is a manual JSON edit against a file
this script otherwise owns. Run the rebuild (``python scripts/seed_content_store.py
--rebuild``) instead — **you do not need to move the version off the shipped release first**:
the rebuild sources every tagged version from its own tag regardless of what
``[project].version`` currently names, so it corrects the one you found and any other entry
quietly out of step with its tag, and is what actually completes the recovery.

**Write mode** (default): regenerates/updates both documents and exits 0. A no-op run where
the index is already current for the running version still ensures store coverage (idempotent
either way: regenerating twice at the same version replaces the index entry and leaves the
store unchanged — nothing is gained or lost).

**Check mode** (``--check``, or ``--release-gate`` which implies it): verifies the index is
current for the running version against the working tree (missing/phantom/stale hashes,
scoped to that one entry), and that store coverage holds across the **whole index** — every
version, every key it names resolves to a blob in the store — without writing anything. A
failure names the version and the artifact, e.g. ``0.9.0:_rendering/templates/workflow.md.j2``.
An orphaned blob (one no index entry, running or historic, references) is always reported to
stderr; only ``--release-gate`` fails the check over it — an ordinary ``--check`` does not,
because between releases an orphan is ordinary development residue the next rebuild clears.
Exits 0 if fresh (and, under ``--release-gate``, orphan-free too); exits 1 otherwise.

Release integration checklist:
  1. Run: ``python scripts/gen_template_manifest.py``  (updates both documents)
  2. Commit them together with any template/spec-document changes.
  3. Before tagging: ``git fetch --tags`` then
     ``python scripts/seed_content_store.py --rebuild``, then
     ``python scripts/gen_template_manifest.py --release-gate``.
  4. Run ``uv build`` — both ship automatically as package data.
"""

import hashlib
import json
import os
import sys
import tomllib
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).parent.parent
_SQUADS_ROOT = _REPO_ROOT / "src" / "squads"
_TEMPLATES_DIR = _SQUADS_ROOT / "_rendering" / "templates"
_MANIFEST_PATH = _SQUADS_ROOT / "_rendering" / "templates_manifest.json"
_STORE_PATH = _SQUADS_ROOT / "_rendering" / "content_store.json"
_PYPROJECT_PATH = _REPO_ROOT / "pyproject.toml"

#: Artifact key namespace: every key is package-root-relative.
_TEMPLATES_PREFIX = "_rendering/templates/"
_SPEC_TOML_NAMES = ("workflow.toml", "roles.toml", "playbook.toml")


def _current_version() -> str:
    data = tomllib.loads(_PYPROJECT_PATH.read_text(encoding="utf-8"))
    try:
        return data["project"]["version"]
    except KeyError:
        raise SystemExit("error: could not read [project].version from pyproject.toml") from None


def _normalize(raw: bytes) -> bytes:
    # Normalize CRLF → LF before hashing so the digest is platform-independent.
    # Windows git may check out text files as CRLF without a .gitattributes; the
    # runtime hasher applies the same normalization, so the values stay consistent.
    return raw.replace(b"\r\n", b"\n")


def _hash_and_text(path: Path) -> tuple[str, str]:
    normalized = _normalize(path.read_bytes())
    return hashlib.sha256(normalized).hexdigest(), normalized.decode("utf-8")


def _collect_current_tree() -> dict[str, tuple[str, str]]:
    """Every overridable bundled artifact's ``key -> (sha256_hex, text)`` in the working tree."""
    entries: dict[str, tuple[str, str]] = {}
    for path in sorted(_TEMPLATES_DIR.rglob("*.md.j2")):
        rel = path.relative_to(_TEMPLATES_DIR).as_posix()
        entries[f"{_TEMPLATES_PREFIX}{rel}"] = _hash_and_text(path)
    for name in _SPEC_TOML_NAMES:
        path = _SQUADS_ROOT / "_specs" / name
        if path.is_file():
            entries[f"_specs/{name}"] = _hash_and_text(path)
    return entries


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        print(
            f"error: {path} is not valid JSON ({exc}) — likely a truncated write", file=sys.stderr
        )
        print(
            "recover with: git checkout -- "
            f"{_MANIFEST_PATH.relative_to(_REPO_ROOT)} {_STORE_PATH.relative_to(_REPO_ROOT)}, "
            "then re-run: python scripts/seed_content_store.py --rebuild",
            file=sys.stderr,
        )
        sys.exit(1)


def _stage_json(path: Path, data: dict[str, Any]) -> Path:
    """Serialize *data* to a temporary file beside *path*, fsynced but not yet renamed — the
    write half of the ``os.replace`` durability pattern already used by
    ``src/squads/_index/_store.py``, split out from the rename so a caller writing more than
    one document can stage every one of them before committing any."""
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    try:
        with tmp.open("w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return tmp


def _write_json(path: Path, data: dict[str, Any]) -> None:
    """Atomically replace *path* with *data*. *path* ends up holding either its previous
    complete bytes or the new complete bytes — never a truncated write."""
    _stage_json(path, data).replace(path)


def _write_json_pair(
    first: tuple[Path, dict[str, Any]], second: tuple[Path, dict[str, Any]]
) -> None:
    """Write two JSON documents as a group: both are fully serialized and fsynced to their own
    temporaries before either replaces its target, so an interruption during serialization
    cannot leave one document new and the other old. A fault staging the second document also
    cleans up the first's already-staged temporary — a partial group leaves no orphaned temp
    file, whichever half failed. The two renames stay two operations, not one transaction —
    each is atomic on its own, but a crash between them can still land between the two
    documents."""
    staged: list[Path] = []
    try:
        staged.append(_stage_json(*first))
        staged.append(_stage_json(*second))
    except BaseException:
        for tmp in staged:
            tmp.unlink(missing_ok=True)
        raise
    tmp_first, tmp_second = staged
    tmp_first.replace(first[0])
    tmp_second.replace(second[0])


def _whole_index_unresolved(manifest: dict[str, Any], store: dict[str, Any]) -> list[str]:
    """Every ``version:key`` the index names, over every version it covers, whose hash has no
    entry in the store — the retention promise's own scope, not only the running version's."""
    return sorted(
        f"{v}:{key}" for v, entry in manifest.items() for key, h in entry.items() if h not in store
    )


def _orphaned_blobs(manifest: dict[str, Any], store: dict[str, Any]) -> list[str]:
    """Every blob in the store no index entry — running or historic — references."""
    referenced = {h for entry in manifest.values() for h in entry.values()}
    return sorted(set(store) - referenced)


def _check_mode(
    version: str, current: dict[str, tuple[str, str]], *, release_gate: bool = False
) -> None:
    """Verify the running version is current against the tree, and that store coverage holds
    across the whole index — every version, every key — writing nothing. An orphaned blob is
    always reported; it only fails the check under ``release_gate``. Exits 1 on any failure."""
    if not _MANIFEST_PATH.exists():
        print(f"error: manifest not found at {_MANIFEST_PATH}", file=sys.stderr)
        print("run: python scripts/gen_template_manifest.py", file=sys.stderr)
        sys.exit(1)

    manifest = _load_json(_MANIFEST_PATH)
    store = _load_json(_STORE_PATH)

    if version not in manifest:
        print(f"error: manifest has no entry for v{version}", file=sys.stderr)
        print("run: python scripts/gen_template_manifest.py", file=sys.stderr)
        sys.exit(1)

    recorded: dict[str, str] = manifest[version]
    current_hashes = {key: h for key, (h, _text) in current.items()}

    # Two remediation classes, kept separate because they point at different remedies: this
    # script can only ever fix the running version's own freshness against the tree, never a
    # store gap — write mode is insert-if-absent from the current tree alone, so a hash a
    # historic entry names and the tree no longer produces is never re-inserted by it. Naming
    # the wrong one hands the operator a command that exits 0 and repairs nothing.
    freshness_problems: list[str] = []
    store_problems: list[str] = []

    # The running version's own freshness against the working tree — scoped to this one entry.
    missing = set(current_hashes) - set(recorded)
    if missing:
        freshness_problems.extend(f"  missing in manifest: {name}" for name in sorted(missing))

    extra = set(recorded) - set(current_hashes)
    if extra:
        freshness_problems.extend(f"  phantom in manifest: {name}" for name in sorted(extra))

    stale = [name for name, h in current_hashes.items() if recorded.get(name) != h]
    if stale:
        freshness_problems.extend(f"  stale hash: {name}" for name in sorted(stale))

    # Store coverage across the WHOLE index — every version, every key — not only the running
    # version's entry: the retention promise is stated over every release the index covers, so
    # the gate that discharges it has to be stated over the same set. Named as
    # "version:artifact", not a count, so the operator knows what to go recover.
    unresolved = _whole_index_unresolved(manifest, store)
    store_problems.extend(f"  hash not in content store: {name}" for name in unresolved)

    # An orphan — a blob no index entry (this version's or any historic one's) references — is
    # reported but never removes one: --check writes nothing, ever. It fails an ordinary check
    # only under --release-gate; between releases it is ordinary development residue the next
    # rebuild clears.
    orphaned = _orphaned_blobs(manifest, store)
    for h in orphaned:
        print(f"note: orphaned blob in content store: {h}", file=sys.stderr)
    if orphaned and release_gate:
        store_problems.extend(f"  orphaned blob in content store: {h}" for h in orphaned)

    problems = freshness_problems + store_problems
    if problems:
        n = len(problems)
        print(f"error: manifest v{version} is not current ({n} problem(s)):", file=sys.stderr)
        for line in problems:
            print(line, file=sys.stderr)
        # Name whichever remedy actually fixes what failed — both, if both classes are present.
        if store_problems:
            print("run: python scripts/seed_content_store.py --rebuild", file=sys.stderr)
        if freshness_problems:
            print("run: python scripts/gen_template_manifest.py", file=sys.stderr)
        sys.exit(1)

    _print_check_success(
        version,
        len(current_hashes),
        manifest=manifest,
        store=store,
        orphaned=orphaned,
        release_gate=release_gate,
    )


def _print_check_success(
    version: str,
    artifact_count: int,
    *,
    manifest: dict[str, Any],
    store: dict[str, Any],
    orphaned: list[str],
    release_gate: bool,
) -> None:
    """The one success line ``_check_mode`` prints — split out so ``--release-gate``'s and
    plain ``--check``'s lines are composed in one place and can never drift back into the
    byte-identical shape this exists to end."""
    versions_checked = len(manifest)
    keys_checked = sum(len(entry) for entry in manifest.values())
    blobs_checked = len(store)
    counts = f"({keys_checked} index reference(s) over {blobs_checked} stored blob(s))"
    if release_gate:
        # Orphan-freeness is the one property only the gate verifies (an orphan present here
        # would already have exited above) — say so, and word the pair of counts so a reader
        # can tell 416 index references apart from 85 stored blobs rather than reconciling two
        # unlabeled numbers by hand. This line must never be reachable with the same wording as
        # an ordinary --check's, so the two are never mistaken for each other in a release
        # thread.
        print(
            f"manifest v{version} is current ({artifact_count} artifacts); release gate "
            f"passed — orphan-free, store coverage verified across all {versions_checked} "
            f"indexed version(s) {counts}"
        )
    else:
        orphan_note = f"; {len(orphaned)} orphan(s) reported" if orphaned else ""
        print(
            f"manifest v{version} is current ({artifact_count} artifacts); store coverage "
            f"verified across all {versions_checked} indexed version(s) {counts}{orphan_note}"
        )


def _write_mode(version: str, current: dict[str, tuple[str, str]]) -> None:
    """Regenerate/update both documents."""
    manifest = _load_json(_MANIFEST_PATH)
    store = _load_json(_STORE_PATH)

    current_hashes = {key: h for key, (h, _text) in current.items()}
    already_fresh = manifest.get(version) == current_hashes

    # Index: wholesale replacement of this version's entry.
    manifest[version] = current_hashes

    # Store: insert-if-absent, and never deletes — no revision an index entry names is ever
    # removed by this script. Removal is the rebuild's alone (scripts/seed_content_store.py
    # --rebuild); see the module docstring for why it cannot safely live here.
    inserted = 0
    for h, text in current.values():
        if h not in store:
            store[h] = text
            inserted += 1

    _write_json_pair((_MANIFEST_PATH, manifest), (_STORE_PATH, store))

    if already_fresh and inserted == 0:
        print(f"manifest already up to date for v{version} ({len(current_hashes)} artifacts)")
    else:
        print(
            f"wrote manifest for v{version}: {len(current_hashes)} artifact hashes "
            f"({inserted} new blob(s) inserted) → {_MANIFEST_PATH.relative_to(_REPO_ROOT)}"
        )


_VALID_FLAGS = {"--check", "--release-gate"}


def main() -> None:
    args = sys.argv[1:]
    unknown = sorted({a for a in args if a not in _VALID_FLAGS})
    if unknown:
        print(f"error: unrecognized argument(s): {' '.join(unknown)}", file=sys.stderr)
        print("usage: gen_template_manifest.py [--check | --release-gate]", file=sys.stderr)
        sys.exit(2)

    release_gate = "--release-gate" in args
    check = release_gate or "--check" in args
    version = _current_version()
    current = _collect_current_tree()

    if check:
        _check_mode(version, current, release_gate=release_gate)
    else:
        _write_mode(version, current)


if __name__ == "__main__":
    main()
    sys.exit(0)
