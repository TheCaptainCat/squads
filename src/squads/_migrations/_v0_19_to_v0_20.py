"""Schema 0.19 → 0.20 runner. The 0.20 schema makes ``source`` a core item key, reserves the role
slug ``source``, adds the comment-attribute line under a comment header and the paired view tag,
none of which a 0.19 file holds in that meaning. The runner writes nothing to item files. Before the
schema is stamped it scans every item file and refuses the whole run, listing every case, when an
item carries a top-level ``source`` key, a role has the slug ``source``, or a line directly after
a comment header already has the shape of a comment-attribute line, which 0.20 would read as an
attribute and no longer as comment text. A squad clear of all three is carried unchanged. It runs
only through ``sq migrate up`` via ``_migrations._registry``.
"""

import re
from itertools import pairwise

from squads import _aio
from squads._index._store import IndexStore
from squads._itemfile import read_frontmatter
from squads._migrations._context import MigrationContext
from squads._migrations._outcome import EntriesRefused, MigrationOutcome
from squads._sections import split_lines
from squads._workflow._models import ROSTER_ROLE

SUMMARY = (
    "`source` becomes a core item key and a reserved role slug, and a line shaped like a comment "
    "attribute under a comment header is read as one. Nothing is rewritten: the run refuses a "
    "squad that holds any of the three."
)
MANUAL = (
    "Clear what `sq migrate up` refuses before running it again; it lists every case and writes "
    "nothing. "
    "(1) An item whose frontmatter has a top-level `source` key: `source` is now the item's link "
    "to an external tracker, so a key of that name cannot stay. Run these steps with the 0.19 "
    "release, before `sq migrate up`, because a newer build refuses them on a 0.19 squad. Declare "
    "an attribute under another name for the holder's type in `squads/.overrides/workflow.toml` "
    '(`[items.<type>.attributes]`, `<new> = { kind = "str" }`), then run `sq migrate '
    "rename-field source <new>`, which moves the value on every item and refuses, changing "
    "nothing, where a holder does not declare `<new>`. To drop the value instead, follow with "
    "`sq <type> <n> update --unset <new>` for each holder. "
    "(2) A role whose slug is `source`: `source` is now reserved, and a roster slug never "
    "changes, so replace the role. Run these steps with the 0.19 release, before `sq migrate "
    "up`, because a newer build refuses them on a 0.19 squad. Create its successor under a new "
    "slug the way the role was made (`sq role add <new> --file <def>` with the definition `sq "
    "role source show` prints, or `sq role activate <new> --from <template>`). Reassign its "
    "work: `sq <type> <n> update --assignee <new>` for each item assigned to `source`, and "
    "`--author <new>` for each item it authored. Re-add each of its memories with `sq memory "
    "<new> add`, from `sq memory source show <slug>`, then `sq memory source forget <slug>`. "
    "Then delete the role with `sq role source remove --purge`; archiving is not enough, "
    "because an archived role still holds its slug. What is lost: the old role's own body and "
    "discussion (git history keeps them); its inbox, since an `@source` in an existing comment "
    "reaches no one; the authorship of its comments, which keep `source` as their author and can "
    "no longer be edited or removed; and any ref to the old role's ID, which you must re-point "
    "by hand. "
    "(3) A comment whose header is directly followed by a line holding `sq:attrs` in an HTML "
    "comment: reword or remove the line, since it would be read as the comment's attributes. "
    "(4) A workflow override that declares an item type or an alias named `source`: `source` is "
    "now a reserved command, so the override no longer loads. Run these steps with the 0.19 "
    "release, before `sq migrate up`, because a newer build refuses them on a 0.19 squad. For an "
    "alias, rename or drop it in `squads/.overrides/workflow.toml`; no item file changes. For a "
    "type, declare a successor type under another name in the same file, run `sq migrate "
    "rename-type source <new>`, which moves every item of the type to the new prefix and folder, "
    "then delete the `source` type from the override. What is lost: the items' old IDs, so a "
    "reference to one in prose or outside the squad no longer resolves."
)

_SOURCE_KEY = "source"
_RESERVED_SLUG = "source"
#: A comment header line, then the line a comment attribute would occupy directly under it.
_HEADER_RE = re.compile(r"^- \[\d{4}-\d\d-\d\dT[^\]]*\] `[^`]+` .+:$")
_COMMENT_OPEN, _COMMENT_CLOSE, _ATTRIBUTES = "<!--", "-->", "sq:attrs"


def _is_attribute_line(line: str) -> bool:
    """Whether *line* is an indented HTML comment holding ``sq:attrs`` and a payload."""
    text = line.strip()
    return (
        line[:1].isspace()
        and text.startswith(_COMMENT_OPEN)
        and text.endswith(_COMMENT_CLOSE)
        and text.removeprefix(_COMMENT_OPEN).lstrip().startswith(f"{_ATTRIBUTES} ")
    )


def _attribute_lines(text: str) -> list[int]:
    """The 1-based numbers of the lines of *text* shaped like a comment attribute that sit
    directly under a comment header."""
    lines = split_lines(text)
    return [
        number + 1
        for number, (header, line) in enumerate(pairwise(lines), start=1)
        if _HEADER_RE.match(header) and _is_attribute_line(line)
    ]


async def migrate(ctx: MigrationContext) -> MigrationOutcome:
    """Scan every item file and refuse on any case; ``sq migrate up`` repairs the index and stamps
    the schema itself."""
    store = IndexStore(ctx.paths.index_path, ctx.paths.lock_path, spec=ctx.spec)
    db = await store.load(validate_vocab=False)
    problems: list[str] = []
    for item in sorted(db.items.values(), key=lambda i: i.sequence_id):
        text = (await _aio.read_bytes(ctx.paths.abspath(item.path))).decode("utf-8")
        data = read_frontmatter(text=text, source=item.path)
        if _SOURCE_KEY in data:
            problems.append(f"{item.id}: has a top-level {_SOURCE_KEY!r} key, now a core key")
        if item.type == ROSTER_ROLE and data.get("slug", item.slug) == _RESERVED_SLUG:
            problems.append(f"{item.id}: is a role with the reserved slug {_RESERVED_SLUG!r}")
        problems.extend(
            f"{item.id}: line {number} directly under a comment header has the shape of a "
            "comment attribute"
            for number in _attribute_lines(text)
        )
    if problems:
        raise EntriesRefused(
            "\n".join(
                [
                    *problems,
                    f"{len(problems)} problem(s) found; fix them by hand "
                    "(`sq migrate chlog v0.19.0..v0.20.0` lists the steps).",
                    "This step wrote nothing and the schema stamp is unchanged.",
                ]
            )
        )
    return MigrationOutcome(count=0)
