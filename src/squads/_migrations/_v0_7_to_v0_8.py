"""Schema 0.7 → 0.8 runner: relocate bug item-level severity from ``extra`` to top-level.

A bug's item-level severity historically lived at ``extra[severity]`` (see the frozen key
below); the model has since grown a real top-level ``severity:`` frontmatter field (mirroring
``priority``) with a load-time fallback that reads the legacy location when the new one is
absent. This runner makes that relocation durable on disk: for every bug file that still
carries the legacy ``extra`` copy, it lifts the value onto the top-level key and drops the
``extra`` entry (the whole ``extra`` map is dropped too, if that was its only member).

**One-way.** Once relocated, a file never round-trips back to the legacy shape.

**Frozen vocabulary.** This runner moves a stored *string*, verbatim — it never inspects,
validates, or ranks the severity value against any collection. The only two literals it needs
(the bug folder/prefix and the legacy ``extra`` key name) are pinned locally below rather than
read from the live spec, matching every other runner in this package.

Only bug files carry item-level severity — findings already store their own severity in the
sub-entity frontmatter block, and priority is already top-level on every type — so this runner
walks only the bug folder.

Idempotent: a file with no ``extra`` severity is left untouched.

Invoked by ``sq migrate up`` via ``_migrations._registry`` — never run directly (this module is
private).
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

        md.write_text(replace_frontmatter(text, fm), encoding="utf-8")
        changed += 1

    return changed
