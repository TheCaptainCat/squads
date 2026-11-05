"""Schema 0.19 → 0.20 runner. The 0.20 schema makes ``source`` a core item key, reserves the role
slug ``source``, adds the comment-attribute line under a comment header and the paired view tag,
and retires the per-type skills (``sq-<type>``): the ``greeting`` and ``squads`` skills become
``sq-greeting`` and ``sq-how-to``, and ``sq-role-<slug>`` names the generated role skills. Before
anything is written the runner scans every item file and refuses the whole run, listing every case,
when an item carries a top-level ``source`` key, a role has the slug ``source``, a line directly
after a comment header already has the shape of a comment-attribute line, a per-type skill holds
prose, a comment or an inbound ref, a skill item is named ``sq-role-<slug>``, or a project skill
already holds ``sq-greeting`` or ``sq-how-to``. A clean squad then has its per-type skill items,
and their ``.claude/skills`` pointers, removed and its two skill items renamed; ``sq migrate up``
closes with the backend refresh. It runs only through ``sq migrate up`` via
``_migrations._registry``.
"""

import re
from dataclasses import dataclass, field
from itertools import pairwise
from typing import Any

from squads import _aio
from squads._backends import BackendContext, get_backend
from squads._index import IndexStore
from squads._interactions import skill_description
from squads._itemfile import read_frontmatter, write_text
from squads._migrations._context import MigrationContext
from squads._migrations._outcome import EntriesRefused, MigrationOutcome
from squads._models import Item, SquadsDB, markers, schema_tuple
from squads._sections import get_section, replace_frontmatter, split_frontmatter, split_lines
from squads._view_tags import strip_view_tags
from squads._workflow import ROSTER_ROLE, ROSTER_SKILL

SUMMARY = (
    "`source` becomes a core item key and a reserved role slug, a line shaped like a comment "
    "attribute under a comment header is read as one, and the per-type skills retire: their items "
    "and `.claude/skills` pointers are removed, `greeting` and `squads` become `sq-greeting` and "
    "`sq-how-to`, every role body gains the playbook tag and the run ends with the backend "
    "refresh. The run refuses a squad that holds a case it cannot carry."
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
    "reference to one in prose or outside the squad no longer resolves. "
    "(5) A per-type skill (`sq-<type>`, such as `sq-task`) that holds prose in its body, a "
    "discussion comment, or a ref from another item: the per-type skills are removed, because "
    "each role's skill now carries the guidance for the types it works with. Run these steps "
    "with the 0.19 release, before `sq migrate up`. Move the prose first, into the body of the "
    "role it addressed (`sq role <slug> body`), into a project skill (`sq skill add`) or into the "
    "playbook override, then re-point each ref that named the skill and clear its comments (a "
    "comment is only removed by its author). The run lists every skill it refuses and what it "
    "holds. "
    "(6) A skill item named `sq-role-<slug>`: that name now belongs to the role skill squads "
    "generates for a role. A skill's slug never changes, so create the replacement under another "
    "name (`sq skill add`), copy the body into it (`sq skill <new> body --file`), re-point the "
    "refs and link it to its roles, then run `sq skill sq-role-<slug> remove --purge`; or fold "
    "its content into the role body and remove it. "
    "(7) A project skill named `sq-greeting` or `sq-how-to`: those names now belong to the "
    "`greeting` and `squads` skills, which are renamed by this run. Replace it the same way, "
    "under another name, and remove it before the run. A stored `operator_invocable` choice on "
    "a removed skill is not carried over, and a squad's own prose that names `greeting` or "
    "`squads` is not rewritten. "
    "(8) A playbook override that sets `lifecycle` or `commands` in a `[types.<type>]` entry of "
    "`squads/.overrides/playbook.toml`: an entry no longer has either key, and the run refuses "
    "the override, naming each one, and writes nothing. Delete both keys from every entry with "
    "the 0.20 release installed, since 0.19 still requires `lifecycle` on a custom type's "
    "entry, then run `sq migrate up`. A type's lifecycle line now comes from its workflow "
    "lifecycle; move any command you want an agent to see into the `do` list of the guide whose "
    "role runs it. "
    "After the run, commit `.claude/`: it removed the pointer directories of the per-type "
    "skills and of `greeting` and `squads`, wrote the pointers of `sq-greeting`, `sq-how-to` "
    "and of each role, and rewrote every agent pointer, the managed `CLAUDE.md` section and the "
    "`settings.json` allow rules."
)

_SOURCE_KEY = "source"
_RESERVED_SLUG = "source"
#: A comment header line, then the line a comment attribute would occupy directly under it.
_HEADER_RE = re.compile(r"^- \[\d{4}-\d\d-\d\dT[^\]]*\] `[^`]+` .+:$")
_COMMENT_OPEN, _COMMENT_CLOSE, _ATTRIBUTES = "<!--", "-->", "sq:attrs"

# The 0.19 skill vocabulary, pinned: the per-type skills are recognised as 0.19 recorded them, so a
# type the run's spec dropped is still found.
_ALWAYS_ON = frozenset({"squads", "greeting", "sq-memory"})
_RENAMED = (("greeting", "sq-greeting"), ("squads", "sq-how-to"))
_ROLE_SKILL_PREFIX = "sq-role-"
_PER_TYPE_PREFIX = "sq-"
_PER_TYPE_VIEW = "sq:view:item_skill"
_SYSTEM_ORIGIN = "system"
# Before this schema a per-type skill stored the rendered guidance as its body, so its prose is
# generated text, not the squad's own.
_RENDERED_BODY_BEFORE = (0, 15)


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


@dataclass
class _Plan:
    """What the scan found to change, and every reason to refuse."""

    problems: list[str] = field(default_factory=list[str])
    origins: dict[int, Any] = field(default_factory=dict[int, Any])
    removed: list[Item] = field(default_factory=list[Item])
    renamed: list[tuple[Item, str, str, dict[str, Any]]] = field(
        default_factory=list[tuple[Item, str, str, dict[str, Any]]]
    )


def _is_per_type_skill(item: Item, region: str) -> bool:
    """Whether a skill item is one of the per-type skills: it carries the per-type view tag, or its
    slug is ``sq-<type>`` with the author equal to the slug, whatever its origin."""
    slug = item.slug
    if (
        slug in _ALWAYS_ON
        or slug in {new for _, new in _RENAMED}
        or slug.startswith(_ROLE_SKILL_PREFIX)
    ):
        return False
    return _PER_TYPE_VIEW in region or (slug.startswith(_PER_TYPE_PREFIX) and item.author == slug)


def _what_a_per_type_skill_holds(
    item: Item, text: str, db: SquadsDB, *, rendered_body: bool
) -> list[str]:
    """The authored content of a per-type skill, empty when it holds only its view tag; a
    *rendered_body* is generated text and never counts as prose."""
    holds: list[str] = []
    if not rendered_body and strip_view_tags(get_section(text, markers.BODY) or "").strip():
        holds.append("prose in its body")
    if (get_section(text, markers.DISCUSSION) or "").strip():
        holds.append("a discussion comment")
    if inbound := db.backrefs(item.id):
        holds.append(f"a ref from {', '.join(inbound)}")
    return holds


def _plan_skill(
    plan: _Plan, db: SquadsDB, item: Item, text: str, data: dict[str, Any], *, rendered_body: bool
) -> None:
    """Classify one skill item into *plan*: a per-type skill to remove, a legacy skill to rename,
    or a refusal."""
    slug = item.slug
    plan.origins[item.sequence_id] = data.get("origin")
    if slug.startswith(_ROLE_SKILL_PREFIX):
        plan.problems.append(
            f"{item.id}: skill {slug!r} is named like a role skill, a name 0.20 generates"
        )
    elif _is_per_type_skill(item, get_section(text, markers.BODY) or ""):
        if holds := _what_a_per_type_skill_holds(item, text, db, rendered_body=rendered_body):
            plan.problems.append(
                f"{item.id}: per-type skill {slug!r} holds {' and '.join(holds)}; move it first"
            )
        else:
            plan.removed.append(item)
    elif new := dict(_RENAMED).get(slug):
        plan.renamed.append((item, slug, new, data))


def _plan_name_holders(plan: _Plan, db: SquadsDB) -> None:
    """Refuse where a new skill name is already held by a skill the run would not replace: a
    project skill, or a system one beside the legacy skill it would replace."""
    skills = [i for i in db.items.values() if i.type == ROSTER_SKILL]
    legacy = {i.slug for i in skills if i.slug in dict(_RENAMED)}
    for item in sorted(skills, key=lambda i: i.sequence_id):
        old = next((o for o, n in _RENAMED if n == item.slug), None)
        if old is None:
            continue
        if plan.origins.get(item.sequence_id) != _SYSTEM_ORIGIN:
            plan.problems.append(
                f"{item.id}: project skill holds the name {item.slug!r}, which 0.20 gives to "
                f"the {old!r} skill"
            )
        elif old in legacy:
            plan.problems.append(
                f"{item.id}: skill {item.slug!r} exists beside the {old!r} skill it would replace"
            )


def _refusal(problems: list[str]) -> EntriesRefused:
    return EntriesRefused(
        "\n".join(
            [
                *problems,
                f"{len(problems)} problem(s) found; fix them by hand "
                "(`sq migrate chlog v0.19.0..v0.20.0` lists the steps).",
                "This step wrote nothing and the schema stamp is unchanged.",
            ]
        )
    )


async def _scan(ctx: MigrationContext, db: SquadsDB) -> _Plan:
    """Read every item file and collect the changes the run owes and the cases it refuses."""
    plan = _Plan()
    rendered_body = schema_tuple(ctx.paths.config.schema_version) < _RENDERED_BODY_BEFORE
    for item in sorted(db.items.values(), key=lambda i: i.sequence_id):
        text = (await _aio.read_bytes(ctx.paths.abspath(item.path))).decode("utf-8")
        data = read_frontmatter(text=text, source=item.path)
        if _SOURCE_KEY in data:
            plan.problems.append(f"{item.id}: has a top-level {_SOURCE_KEY!r} key, now a core key")
        if item.type == ROSTER_ROLE and data.get("slug", item.slug) == _RESERVED_SLUG:
            plan.problems.append(f"{item.id}: is a role with the reserved slug {_RESERVED_SLUG!r}")
        plan.problems.extend(
            f"{item.id}: line {number} directly under a comment header has the shape of a "
            "comment attribute"
            for number in _attribute_lines(text)
        )
        if item.type == ROSTER_SKILL:
            _plan_skill(plan, db, item, text, data, rendered_body=rendered_body)
    _plan_name_holders(plan, db)
    return plan


def _renamed_path(path: str, old: str, new: str) -> str:
    """*path* with its trailing ``-<old>.md`` slug part replaced by *new*."""
    suffix = f"-{old}.md"
    return f"{path[: -len(suffix)]}-{new}.md" if path.endswith(suffix) else path


async def _rename_skill(ctx: MigrationContext, item: Item, old: str, new: str) -> None:
    """Give the skill file the new slug, title and author (each when it was the old slug), the new
    description and file name; the id stays."""
    path = ctx.paths.abspath(item.path)
    text = await _aio.read_text(path)
    data, _ = split_frontmatter(text, source=item.path)
    data["slug"] = new
    data["description"] = skill_description(new)
    for key in ("title", "author"):
        if data.get(key) == old:
            data[key] = new
    target = path.with_name(_renamed_path(path.name, old, new))
    await write_text(path, replace_frontmatter(text, data))
    if target != path:
        await _aio.path_rename(path, target)


async def _drop_stray_body(ctx: MigrationContext, item: Item, new: str) -> None:
    """Remove the body file ``<new>.md`` beside a renamed skill's file when it has no id: an earlier
    step of a long run writes one for each current system skill it finds no item for."""
    stray = ctx.paths.abspath(item.path).with_name(f"{new}.md")
    if await _aio.path_exists(stray):
        data, _ = split_frontmatter(await _aio.read_text(stray), source=str(stray))
        if "id" not in data:
            await _aio.path_unlink(stray)


async def _drop_pointers(ctx: MigrationContext, items: list[Item]) -> None:
    """Remove each skill's pointer from every active backend, by the slug it has now."""
    backend_ctx = BackendContext(
        paths=ctx.paths, spec=ctx.spec, playbook=ctx.playbook, catalog=ctx.catalog
    )
    for name in ctx.paths.config.active_backends:
        backend = get_backend(name)
        for item in items:
            await backend.remove_artifacts(backend_ctx, item)


async def _apply(ctx: MigrationContext, plan: _Plan) -> tuple[str, ...]:
    """Remove the per-type skills and rename the two legacy ones, files first and the index last;
    returns the report lines."""
    await _drop_pointers(ctx, [*plan.removed, *(item for item, *_ in plan.renamed)])
    for item in plan.removed:
        await _aio.path_unlink(ctx.paths.abspath(item.path))
    for item, old, new, _data in plan.renamed:
        await _drop_stray_body(ctx, item, new)
        await _rename_skill(ctx, item, old, new)
    if plan.removed:
        store = IndexStore(ctx.paths.index_path, ctx.paths.lock_path, spec=ctx.spec)
        async with store.transaction() as db:
            for item in plan.removed:
                db.items.pop(item.sequence_id, None)
    return (
        *(f"removed skill {item.id} {item.slug}" for item in plan.removed),
        *(f"renamed skill {item.id} {old} to {new}" for item, old, new, _data in plan.renamed),
    )


async def migrate(ctx: MigrationContext) -> MigrationOutcome:
    """Scan every item file and refuse on any case, else remove the per-type skills and rename the
    two legacy ones; ``sq migrate up`` repairs the index, refreshes the backends and stamps the
    schema itself."""
    store = IndexStore(ctx.paths.index_path, ctx.paths.lock_path, spec=ctx.spec)
    plan = await _scan(ctx, await store.load(validate_vocab=False))
    if plan.problems:
        raise _refusal(plan.problems)
    report = await _apply(ctx, plan)
    return MigrationOutcome(count=len(report), report=report)
