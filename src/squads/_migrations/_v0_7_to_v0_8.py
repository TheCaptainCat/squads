"""Schema 0.7 → 0.8 runner: relocate bug item-level severity from ``extra`` to the top-level
``severity:`` field (which mirrors ``priority`` and has a load-time fallback to the legacy
location). For every bug file still carrying the legacy ``extra[severity]`` it lifts the value to
the top-level key and drops the ``extra`` entry (and the whole ``extra`` map if that was its only
member). It is one-way: a relocated file never returns to the legacy shape.

It moves a stored string verbatim, never inspecting or ranking it against a collection, and pins its
only two literals (the bug folder/prefix and the legacy ``extra`` key) locally rather than reading
the live spec. Only bug files carry item-level severity (findings store theirs in sub-entity
frontmatter, priority is already top-level), so it walks only the bug folder. It is idempotent (a
file with no ``extra`` severity is untouched) and runs only through ``sq migrate up`` via
``_migrations._registry``.
"""

from typing import Any, cast

from squads._paths import SquadPaths
from squads._sections import replace_frontmatter, split_frontmatter

# Frozen v0.7 structural literals — pinned locally, never re-derived from the live model/spec.
_BUG_PREFIX = "BUG"
_BUG_FOLDER = "bugs"
_LEGACY_EXTRA_KEY = "severity"  # the extra-dict key a pre-0.8 bug's severity lived under

MANUAL = """\
## Schema 0.7 → 0.8 — bug severity moves from `extra` to a top-level key

No manual steps are required — `sq migrate up` automatically, for every existing bug file that
still carries a legacy `extra.severity` entry:

1. Lifts the value onto a top-level `severity:` frontmatter key (skipped if one is already set).
2. Drops the `extra` entry, and the whole `extra:` map if severity was its only member.
3. Runs `sq repair` to rebuild the index.

Priority (already top-level) and finding severity (already stored on the sub-entity block) are
untouched. If you hand-edited a bug file's `extra` block yourself, re-run `sq migrate up` after —
the relocation is idempotent and safe to repeat.

**Verify with:**

```
sq check                  # should be clean
sq bug <n> show --full    # severity badge renders as before
```
"""


def migrate(paths: SquadPaths) -> int:
    """Relocate every bug's legacy ``extra`` severity to the top-level key.

    Returns the count of files whose content changed.
    """
    folder = paths.squad_dir / _BUG_FOLDER
    if not folder.is_dir():
        return 0

    changed = 0
    for md in sorted(folder.glob(f"{_BUG_PREFIX}-*.md")):
        text = md.read_text(encoding="utf-8")
        fm, _ = split_frontmatter(text)
        raw_extra = fm.get("extra")
        if not isinstance(raw_extra, dict) or _LEGACY_EXTRA_KEY not in raw_extra:
            continue  # no legacy severity to relocate — already migrated or never set
        extra = cast("dict[str, Any]", raw_extra)

        legacy_value = extra.pop(_LEGACY_EXTRA_KEY)
        if not fm.get("severity"):
            fm["severity"] = legacy_value
        if extra:
            fm["extra"] = extra
        else:
            fm.pop("extra", None)

        md.write_text(replace_frontmatter(text, fm), encoding="utf-8", newline="")
        changed += 1

    return changed
