#!/usr/bin/env python3
"""One-time data step: seed the content store back to the index's own floor from the release
tags, and rekey every historic index entry onto the package-root-relative artifact namespace.

This is run **once**, by hand, for the widening release that introduces the content store —
never wired into CI or into ``scripts/gen_template_manifest.py``, which never reads git. If it
is ever run again (e.g. a squads fork that adopts the widening late), it is idempotent: every
write is either a rekey of an already-correct hash or an insert-if-absent into the store.

What it does, per version already present in ``templates_manifest.json`` that has a matching
release tag (``v<version>``):

1. For every key already recorded for that version (today still in the OLD "relative to
   ``_rendering/templates/``" namespace), fetch that template's content at the tag and
   recompute its hash. When it matches the recorded hash — the overwhelming majority — the
   entry is rewritten under the new ``_rendering/templates/...`` key with **the hash value
   carried over unchanged**, only the key gaining its package-root prefix. When it does
   *not* match, the release tag (ground truth — this is a one-time data step against the
   release tags) wins and the recorded hash is corrected to match it: this is squads' own
   internal bookkeeping (no adopter stamp ever names a hash, only a version), so correcting
   it to agree with the actual shipped tree is a data-integrity fix, not a breaking change.
   Every correction is printed loudly so it is never a silent rewrite.
2. For each of the three spec TOML documents, fetch it at that tag if it exists there (it may
   not — ``roles.toml``/``workflow.toml``/``playbook.toml`` were introduced partway through the
   index's history) and add its key/hash to that version's entry — genuinely new coverage, not
   a rekey, which is why the widening needs this one-time pass rather than being expressible as
   an ordinary regeneration.
3. Every (rekeyed or new) hash's normalized content is inserted into the store, insert-if-absent.

A version with **no matching tag** (the running, not-yet-released version) is left untouched —
that entry is ``scripts/gen_template_manifest.py``'s to write, from the working tree, with no
git access needed.

**Rebuild mode** (``--rebuild``) is a separate, repeatable capability: recompute the whole
content store as the closure of every hash the index names, and drop whatever is not in that
closure. This is the store's only removal path; ``scripts/gen_template_manifest.py`` never
deletes, because it never reads git and so cannot tell a discarded scratch revision of the
running version from a shipped revision of a released one. Run it before every release tag.

**Publication is the discriminator, not "is this the running version".** Every indexed version
that has a release tag is sourced from that tag — *including* one that also happens to be the
version ``[project].version`` currently names, which is exactly the window a mis-ordered
regeneration opens and the case a tree-based read would get wrong. The working tree is ground
truth only for a version with **no tag at all**: the one genuinely unreleased case.

It is **all-or-nothing**. A version whose ground truth it cannot reach — no local tag and it is
not the running version, or a tag that does not reproduce every artifact the index names for it
(a git-level failure, or a tag that resolves to zero templates though the version previously
recorded some) — is a refusal: it names the version, suggests ``git fetch --tags`` first (a
stale local tag list is the likeliest cause), and writes nothing at all, for any version. Never
a skip: skipping is what turns an incomplete tag list into silent data loss, the same failure
mode this script exists to close. Along the way it reports (and corrects to the tag) any index
entry that disagrees with its own release tag — the mis-ordered regeneration that
``gen_template_manifest.py --check`` alone cannot see.

A refusal writes nothing, and a write that does happen never leaves a partial document: both
documents are staged to temporaries and only then renamed onto their targets, so an interrupted
run leaves either the previous pair intact or the new one, never a truncated file. That does not
make the pair one transaction — a crash between the two renames can still leave the index
rewritten while the store behind a restored hash lags — but it removes truncation, the one state
a caller could not already diagnose (a truncated document raises a named parse error rather than
an unhandled traceback; an index naming a hash the store lacks fails ``--check`` at exit 1).

**Recovery from a mis-ordered regeneration**: if ``gen_template_manifest.py`` was run while
``[project].version`` named an already-shipped release, that release's index entry now reflects
the working tree instead of what actually shipped, though the store itself lost nothing (the
generator never deletes). Restoring the index entry from the tag by hand fixes only the entry
you noticed. ``--rebuild`` is the complete recovery, and it works **without moving the version
off the shipped release first** — because a tagged version is always sourced from its tag
regardless of what ``[project].version`` currently names, running ``--rebuild`` in that exact
state corrects the entry back to what its tag ships rather than re-deriving it from the tree.

Usage::

    git fetch --tags   # local tag list can be stale — run this first
    python scripts/seed_content_store.py             # write mode: one-time seed/rekey pass
    python scripts/seed_content_store.py --check     # verify mode: exit 1 if a re-run would change
    python scripts/seed_content_store.py --rebuild   # rebuild mode: recompute the store from
                                                       # ground truth, all-or-nothing (see above)
"""

import hashlib
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).parent.parent
_SQUADS_ROOT = _REPO_ROOT / "src" / "squads"
_MANIFEST_PATH = _SQUADS_ROOT / "_rendering" / "templates_manifest.json"
_STORE_PATH = _SQUADS_ROOT / "_rendering" / "content_store.json"
_PYPROJECT_PATH = _REPO_ROOT / "pyproject.toml"

_TEMPLATES_PREFIX = "_rendering/templates/"
_SPEC_KEYS = ("_specs/workflow.toml", "_specs/roles.toml", "_specs/playbook.toml")


def _tag_exists(tag: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "-q", "--verify", f"{tag}^{{commit}}"],
        cwd=_REPO_ROOT,
        capture_output=True,
    )
    return result.returncode == 0


def _git_show(tag: str, repo_path: str) -> bytes | None:
    result = subprocess.run(
        ["git", "show", f"{tag}:{repo_path}"], cwd=_REPO_ROOT, capture_output=True
    )
    if result.returncode != 0:
        return None
    return result.stdout


def _normalize(raw: bytes) -> bytes:
    return raw.replace(b"\r\n", b"\n")


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


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


def _seed_version(
    version: str, old_entry: dict[str, str], store: dict[str, str], corrections: list[str]
) -> dict[str, str]:
    """Return the rekeyed + widened entry for one release, inserting content into *store*."""
    tag = f"v{version}"
    new_entry: dict[str, str] = {}

    for old_key, recorded_hash in old_entry.items():
        if old_key in _SPEC_KEYS:
            continue  # Handled by the spec-doc pass below — must not treat these as templates.
        # Idempotent on a re-run: a key may already carry the new prefix.
        if old_key.startswith(_TEMPLATES_PREFIX):
            template_rel = old_key[len(_TEMPLATES_PREFIX) :]
        else:
            template_rel = old_key
        new_key = f"{_TEMPLATES_PREFIX}{template_rel}"
        raw = _git_show(tag, f"src/squads/_rendering/templates/{template_rel}")
        if raw is None:
            print(f"warn: {tag} missing {template_rel} — dropping stale key", file=sys.stderr)
            continue
        normalized = _normalize(raw)
        computed = _hash(normalized)
        if computed != recorded_hash:
            corrections.append(
                f"{tag} {template_rel}: recorded {recorded_hash} -> tag-derived {computed}"
            )
        new_entry[new_key] = computed
        store.setdefault(computed, normalized.decode("utf-8"))

    for spec_key in _SPEC_KEYS:
        spec_name = spec_key.removeprefix("_specs/")
        raw = _git_show(tag, f"src/squads/_specs/{spec_name}")
        if raw is None:
            continue  # This spec document did not exist yet at this release.
        normalized = _normalize(raw)
        h = _hash(normalized)
        new_entry[spec_key] = h
        store.setdefault(h, normalized.decode("utf-8"))

    return new_entry


def _current_version() -> str:
    data = tomllib.loads(_PYPROJECT_PATH.read_text(encoding="utf-8"))
    return data["project"]["version"]


def _git_ls_tree(tag: str, repo_subpath: str) -> list[str] | None:
    """Repo-root-relative file paths under *repo_subpath* as *tag*'s tree actually contains
    it. Returns ``None`` if the git command itself failed — an unreadable tag, a corrupted
    object, any git-level error — distinct from a legitimately empty listing (returncode 0, no
    output), e.g. the directory not existing yet at an early tag. Conflating the two is what let
    a git failure during the rebuild pass silently through as "nothing here", emptying entries
    instead of refusing."""
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", tag, "--", repo_subpath],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return [line for line in result.stdout.splitlines() if line]


def _git_path_exists_at(tag: str, repo_path: str) -> bool:
    """Whether *repo_path* exists at *tag* at all (any object type) — lets a spec document's
    ``git show`` failure be told apart from "did not exist yet at this release"."""
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{tag}:{repo_path}"], cwd=_REPO_ROOT, capture_output=True
    )
    return result.returncode == 0


def _collect_tree_at_tag(tag: str, old_entry: dict[str, str]) -> dict[str, tuple[str, str]] | None:
    """Every overridable bundled artifact's ``key -> (hash, text)`` exactly as *tag*'s own tree
    contains it — discovered from the tree itself (``git ls-tree``), not trusted from whatever
    key set the index currently happens to record for that version, since that is exactly what
    a mis-ordered regeneration corrupts. A hash disagreeing with *old_entry* is a correction, not
    a failure — the derivation is deliberately independent of the old key set so it can narrow a
    previously-corrupted entry back down.

    Returns ``None`` if the tag itself is unreachable, if ``git`` fails partway through, or if
    the derivation comes back with zero templates while *old_entry* previously recorded some —
    the one case ground truth cannot itself distinguish from a real loss (a moved or emptied
    tag, a broken listing), so it is treated as unreachable rather than as a wholesale
    correction. A shipped entry losing keys wholesale is never an ordinary correction."""
    if not _tag_exists(tag):
        return None
    listing = _git_ls_tree(tag, "src/squads/_rendering/templates")
    if listing is None:
        return None  # git ls-tree itself failed — an unreadable tag, not an empty one
    old_had_templates = any(k.startswith(_TEMPLATES_PREFIX) for k in old_entry)
    if not listing and old_had_templates:
        return None  # the tag resolves but names zero templates though this version once did
    entries: dict[str, tuple[str, str]] = {}
    for repo_path in sorted(listing):
        if not repo_path.endswith(".md.j2"):
            continue
        rel = repo_path.removeprefix("src/squads/_rendering/templates/")
        raw = _git_show(tag, repo_path)
        if raw is None:
            return None  # listed by ls-tree but unreadable — treat as unreachable, not a drop
        normalized = _normalize(raw)
        entries[f"{_TEMPLATES_PREFIX}{rel}"] = (_hash(normalized), normalized.decode("utf-8"))
    for spec_key in _SPEC_KEYS:
        spec_name = spec_key.removeprefix("_specs/")
        repo_path = f"src/squads/_specs/{spec_name}"
        if not _git_path_exists_at(tag, repo_path):
            continue  # this spec document did not exist yet at this release — not an error
        raw = _git_show(tag, repo_path)
        if raw is None:
            return None  # exists per cat-file but unreadable per show — a git-level failure
        normalized = _normalize(raw)
        entries[spec_key] = (_hash(normalized), normalized.decode("utf-8"))
    return entries


def _collect_tree_from_disk() -> dict[str, tuple[str, str]]:
    """Every overridable bundled artifact's ``key -> (hash, text)`` in the working tree — the
    running version's ground truth, no git access needed."""
    templates_dir = _SQUADS_ROOT / "_rendering" / "templates"
    entries: dict[str, tuple[str, str]] = {}
    for path in sorted(templates_dir.rglob("*.md.j2")):
        rel = path.relative_to(templates_dir).as_posix()
        normalized = _normalize(path.read_bytes())
        entries[f"{_TEMPLATES_PREFIX}{rel}"] = (_hash(normalized), normalized.decode("utf-8"))
    for spec_key in _SPEC_KEYS:
        spec_name = spec_key.removeprefix("_specs/")
        path = _SQUADS_ROOT / "_specs" / spec_name
        if path.is_file():
            normalized = _normalize(path.read_bytes())
            entries[spec_key] = (_hash(normalized), normalized.decode("utf-8"))
    return entries


def _resolve_version(
    version: str, old_entry: dict[str, str], *, running_version: str
) -> tuple[dict[str, tuple[str, str]] | None, str]:
    """Ground truth for one version, and where it came from. **Publication is the
    discriminator, not "is this the running version"**: a tagged version is always sourced
    from its own tag, even when it also happens to be the one ``[project].version`` currently
    names — that equality is exactly the window a mis-ordered regeneration opens, and trusting
    the tree there is what let the withdrawn sweep's loss resurface here. The working tree is
    only ever ground truth for a version that is *not yet* published — the one case with no tag
    to prefer instead."""
    tag = f"v{version}"
    if _tag_exists(tag):
        return _collect_tree_at_tag(tag, old_entry), tag
    if version == running_version:
        return _collect_tree_from_disk(), "working tree"
    return None, tag


def _rebuild(
    manifest: dict[str, dict[str, str]],
) -> tuple[dict[str, dict[str, str]], dict[str, str], list[str]] | None:
    """Recompute the whole index and store as the closure of ground truth: each version's
    entry re-derived from its own release tag whenever one exists — the working tree is used
    only for a version with no tag at all — rather than trusted from the possibly-corrupted key
    set already on file. That independence is what lets this catch a mis-ordered regeneration's
    wrong key set, not only its wrong hashes. The store becomes exactly the union of every
    re-derived entry's hashes; anything else is dropped.

    All-or-nothing: returns ``None`` — refusing, nothing written — the moment one version's
    ground truth cannot be reached in full. Never a skip: a version present in *manifest* is
    always either resolved in full or the whole rebuild is refused."""
    running_version = _current_version()
    new_manifest: dict[str, dict[str, str]] = {}
    new_store: dict[str, str] = {}
    corrections: list[str] = []

    for version in sorted(manifest):
        old_entry = manifest[version]
        collected, source = _resolve_version(version, old_entry, running_version=running_version)
        if collected is None:
            if source == f"v{version}" and not _tag_exists(source):
                print(
                    f"error: v{version} is indexed but not tagged locally — the rebuild is "
                    "all-or-nothing and refuses rather than silently dropping its history",
                    file=sys.stderr,
                )
                print("run: git fetch --tags", file=sys.stderr)
            else:
                print(
                    f"error: {source} exists locally but its tree could not be read in full "
                    f"(a git-level failure, or it resolved to zero templates though v{version} "
                    "previously recorded some) — the rebuild is all-or-nothing and refuses "
                    "rather than silently emptying its history",
                    file=sys.stderr,
                )
                print(
                    f"run: git fetch --tags, then git show {source} to check the tag by hand",
                    file=sys.stderr,
                )
            return None

        new_entry = {key: h for key, (h, _text) in collected.items()}
        new_store.update({h: text for h, text in collected.values()})
        if new_entry != old_entry:
            corrections.extend(
                f"{source} {key}: recorded {old_entry.get(key, '<absent>')} -> "
                f"ground-truth {new_entry.get(key, '<absent>')}"
                for key in sorted(set(old_entry) | set(new_entry))
                if old_entry.get(key) != new_entry.get(key)
            )
        new_manifest[version] = new_entry

    return new_manifest, new_store, corrections


def _rebuild_mode() -> None:
    manifest = _load_json(_MANIFEST_PATH)
    if not manifest:
        print(f"error: manifest not found or empty at {_MANIFEST_PATH}", file=sys.stderr)
        sys.exit(1)
    store_before = _load_json(_STORE_PATH)

    result = _rebuild(manifest)
    if result is None:
        sys.exit(1)
    new_manifest, new_store, corrections = result

    if corrections:
        print(
            f"NOTE: {len(corrections)} hash(es) disagreed with their own ground truth (release "
            "tag, or the working tree for the running version) and were corrected:",
            file=sys.stderr,
        )
        for line in corrections:
            print(f"  {line}", file=sys.stderr)

    # Two independently computed sets, not a size delta: a run that only restores (recovery's
    # headline case) must not be able to print "0 dropped" and read as having done nothing, and
    # a run that inserts must never be able to print a negative count — set sizes can't go
    # negative, unlike the delta this replaces.
    restored = set(new_store) - set(store_before)
    dropped = set(store_before) - set(new_store)

    _write_json_pair((_MANIFEST_PATH, new_manifest), (_STORE_PATH, new_store))
    print(
        f"rebuilt from ground truth: {len(new_manifest)} version(s), {len(new_store)} blob(s) "
        f"({len(restored)} restored, {len(dropped)} dropped — not in the closure of any index "
        "entry)"
    )


_VALID_FLAGS = {"--check", "--rebuild"}


def main() -> None:
    args = sys.argv[1:]
    unknown = sorted({a for a in args if a not in _VALID_FLAGS})
    if unknown:
        print(f"error: unrecognized argument(s): {' '.join(unknown)}", file=sys.stderr)
        print("usage: seed_content_store.py [--check | --rebuild]", file=sys.stderr)
        sys.exit(2)

    check = "--check" in args
    rebuild = "--rebuild" in args
    if check and rebuild:
        # --check means "writes nothing, ever" everywhere else in this tool; --rebuild always
        # writes and has no dry-run mode. Never let the combination silently pick one.
        print(
            "error: --check and --rebuild are mutually exclusive — --check verifies only the "
            "one-time seed pass, and --rebuild has no dry-run form",
            file=sys.stderr,
        )
        sys.exit(2)
    if rebuild:
        _rebuild_mode()
        return

    manifest = _load_json(_MANIFEST_PATH)
    store = _load_json(_STORE_PATH)

    original_manifest = json.loads(json.dumps(manifest))
    original_store_size = len(store)

    seeded = 0
    skipped_untagged: list[str] = []
    corrections: list[str] = []
    for version in sorted(manifest):
        tag = f"v{version}"
        if not _tag_exists(tag):
            skipped_untagged.append(version)
            continue
        manifest[version] = _seed_version(version, manifest[version], store, corrections)
        seeded += 1

    if corrections:
        print(
            f"NOTE: {len(corrections)} pre-existing hash(es) disagreed with their own release "
            "tag and were corrected to match the tag (ground truth) — a pre-existing "
            "data-integrity defect independent of the rekey itself, not new corruption:",
            file=sys.stderr,
        )
        for line in corrections:
            print(f"  {line}", file=sys.stderr)

    if check:
        changed = manifest != original_manifest or len(store) != original_store_size
        if changed:
            print(
                "error: seeding would change the manifest/store — run without --check",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"content store is current: {seeded} tagged version(s) seeded, {len(store)} blob(s)")
        return

    _write_json_pair((_MANIFEST_PATH, manifest), (_STORE_PATH, store))
    print(
        f"seeded {seeded} tagged version(s); store now holds {len(store)} blob(s) "
        f"(+{len(store) - original_store_size} new); "
        f"left untouched (no tag): {', '.join(skipped_untagged) or '(none)'}"
    )


if __name__ == "__main__":
    main()
    sys.exit(0)
