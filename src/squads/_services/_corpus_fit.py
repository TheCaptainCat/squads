"""The check before the first migration runner: does the reconciled index fit the vocabulary the
run resolved?

It writes nothing and refuses only what the completed run would refuse. It asks whether every
indexed file sits where a declared type lives, whether every file named for an item where a
declared type lives has an entry, and whether the corpus fits the declared vocabulary. A runner
that renames or retires vocabulary declares the names it consumes on its migration record and the
check is blind to them; no shipped runner does.
"""

import os
import posixpath
import re
from pathlib import Path

from squads._index._reconcile import entry_name
from squads._index._store import badge_code_problems
from squads._models._index import SquadsDB
from squads._workflow._loader import validate_against_index
from squads._workflow._models import WorkflowSpec

_OVERRIDE_HINT = re.compile(r" \(add it to the override or fix the item frontmatter\)")


def _norm(folder: str) -> str:
    """*folder* as one relative POSIX spelling, however a declaration or a path writes it."""
    return posixpath.normpath(folder)


_ITEM_SHAPED = re.compile(r"-\d+(?:-|\.md$)")


def _named_for(prefix: str) -> re.Pattern[str]:
    """A file name of an item of *prefix*, exactly as declared: the prefix, a hyphen, digits, then
    a hyphen and a slug or the extension."""
    return re.compile(rf"^{re.escape(prefix)}-\d+(?:-.+)?\.md$")


def _declared_locations(spec: WorkflowSpec) -> set[tuple[str, str]]:
    return {(_norm(ts.folder), ts.prefix) for ts in spec.items.values()}


def _misplaced(db: SquadsDB, spec: WorkflowSpec) -> list[str]:
    """Indexed files that sit where no declared type lives, with where their type does."""
    declared = _declared_locations(spec)
    folders = {folder for folder, _ in declared}
    found: list[str] = []
    for entry in db.items.values():
        directory = _norm(posixpath.dirname(entry.path) or ".")
        name = posixpath.basename(entry.path)
        at_a_declared_location = any(
            folder == directory and _named_for(prefix).match(name) for folder, prefix in declared
        )
        if at_a_declared_location or (directory in folders and not _ITEM_SHAPED.search(name)):
            continue
        home = spec.items.get(entry.type)
        where = (
            f"its type lives in {_norm(home.folder)}/"
            if home
            else f"type {entry.type!r} is not declared"
        )
        found.append(f"{entry.path} ({entry_name(entry)}; {where})")
    return sorted(found)


def _unindexed(db: SquadsDB, spec: WorkflowSpec, squad_dir: Path) -> list[str]:
    """Files named for an item of a declared type's own prefix, exactly as declared, where that
    type lives, that the index holds no entry for."""
    indexed = {_norm(entry.path) for entry in db.items.values()}
    found: list[str] = []
    for folder, prefix in sorted(_declared_locations(spec)):
        directory = squad_dir / folder
        if not directory.is_dir():
            continue
        named = _named_for(prefix)
        for entry in os.scandir(directory):
            rel = _norm(f"{folder}/{entry.name}")
            if named.match(entry.name) and rel not in indexed:
                found.append(rel)
    return sorted(found)


def corpus_fit_refusal(
    db: SquadsDB,
    spec: WorkflowSpec,
    squad_dir: Path,
    *,
    had_index: bool,
    override_path: Path | None,
    reader: str,
    rebuilt: str = "",
) -> str | None:
    """The refusal text for a reconciled index that does not fit *spec*, or ``None``. Remedies
    are hand fixes and a re-run of ``sq migrate up``; an override is named only when there is
    one. *reader* names a squads release that reads the squad's schema; *rebuilt* says what the
    index rebuild indexed or dropped, when it was kept."""
    misplaced = _misplaced(db, spec)
    if misplaced:
        if had_index:
            cause = "these indexed files sit where no type of this squad lives"
            remedy = "move each file into the folder its type lives in"
            if override_path is not None:
                remedy += f", or restore the declaration in the override ({override_path})"
        else:
            cause = (
                "there was no readable index, so every item-shaped file under the squad "
                "directory was taken for an item, and these sit where no type of this squad "
                "lives"
            )
            remedy = (
                f"restore the index (from version control, or with the index rebuild of "
                f"{reader}) or move these files out of the squad directory"
            )
        return _refusal(cause, misplaced, remedy, rebuilt)
    unindexed = _unindexed(db, spec, squad_dir)
    if unindexed:
        remedy = (
            f"when a file is not one of the squad's items, move it out of the folder; when it "
            f"is, {reader} indexes it with its own index rebuild"
        )
        if had_index and not db.items:
            remedy += (
                "; the index holds no items, and removing the index file lets this run read "
                "the tree for items instead"
            )
        return _refusal(
            "these files are named for an item where this squad keeps items, and the index "
            "holds no entry for them",
            unindexed,
            remedy,
            rebuilt,
        )
    problems = [
        _OVERRIDE_HINT.sub("", p) if override_path is None else p
        for p in validate_against_index(spec, db, alignment=override_path is not None)
    ]
    if problems:
        remedy = "correct the named frontmatter by hand"
        if override_path is not None:
            remedy = f"restore the declaration in the override ({override_path}), or {remedy}"
        return _refusal(
            "the corpus does not fit the vocabulary this squad declares", problems, remedy, rebuilt
        )
    stranded = badge_code_problems(db, spec)
    if stranded:
        return _refusal(
            "these stored badge codes are not declared by their collection",
            stranded,
            "correct the named frontmatter values by hand",
            rebuilt,
        )
    return None


def _refusal(cause: str, lines: list[str], remedy: str, rebuilt: str) -> str:
    bullets = "\n".join(f"  - {line}" for line in lines)
    return (
        f"no migration has run: {cause}:\n{bullets}\n{remedy}, then re-run `sq migrate up`. "
        f"The schema is unchanged.{rebuilt}"
    )
