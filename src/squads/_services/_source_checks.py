"""The ``sq check`` rules for items a tracker feeds and for what names a source: duplicate holders
of one issue, a source that is undeclared, disabled or unreadable, an issue the pull lost, operator
identities, and comment attribute lines. None of them calls the network."""

from collections import defaultdict
from collections.abc import Mapping

from squads import _discussion as discussion
from squads._errors import SquadsError
from squads._models._attributes import AttributeKey, map_attribute
from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._models._participants import source_of
from squads._models._source import GONE, LOST_STATES
from squads._paths import number_for_id
from squads._services._results import CheckIssue
from squads._sources._spec import SourcesSource, SourcesSpec
from squads._workflow import ROSTER_OPERATOR


def _items_of(db: SquadsDB) -> list[Item]:
    return sorted(db.items.values(), key=lambda it: it.sequence_id)


def _holders(db: SquadsDB) -> list[CheckIssue]:
    """Every pair of items that hold one tracker issue."""
    issues: list[CheckIssue] = []
    for (name, issue_id), seqs in sorted(db.source_ids().items()):
        if len(seqs) > 1:
            held = [db.items[n] for n in sorted(seqs)]
            ids = ", ".join(it.id for it in held)
            issues.append(
                CheckIssue(
                    "error",
                    held[0].id,
                    f"{ids} all hold issue {held[0].source.key if held[0].source else issue_id} "
                    f"of source {name!r}; the pull refreshes each, so keep one and run "
                    "`source unlink` on the others",
                    "source_id_unique",
                )
            )
    return issues


def _records(db: SquadsDB, declared: SourcesSpec) -> list[CheckIssue]:
    """Items whose record names a source that is undeclared or disabled, or whose issue the pull
    lost."""
    issues: list[CheckIssue] = []
    for item in _items_of(db):
        record = item.source
        if record is None:
            continue
        source = declared.sources.get(record.name)
        if source is None:
            issues.append(
                CheckIssue(
                    "warn",
                    item.id,
                    f"source {record.name!r} is not declared in sources.toml; no pull refreshes "
                    f"{record.key}",
                    "source_declared",
                )
            )
        elif not source.enabled:
            issues.append(
                CheckIssue(
                    "warn",
                    item.id,
                    f"source {record.name!r} is disabled (enabled = false); no pull refreshes "
                    f"{record.key}",
                    "source_declared",
                )
            )
        if record.state in LOST_STATES:
            why = "no longer answers for" if record.state == GONE else "no longer lists"
            issues.append(
                CheckIssue(
                    "warn",
                    item.id,
                    f"the tracker {why} {record.key} ({record.state}); keep the item, or run "
                    f"`sq {item.type} {number_for_id(item.id)} source unlink`",
                    "source_issue_reachable",
                )
            )
    return issues


def _authors(db: SquadsDB, declared: SourcesSpec, texts: Mapping[int, str]) -> list[CheckIssue]:
    """Authors, of an item or of a comment, that name an undeclared source."""
    issues: list[CheckIssue] = []
    for item in _items_of(db):
        named = [item.author or ""]
        named += discussion.comment_authors(texts.get(item.sequence_id, ""))
        for name in dict.fromkeys(n for a in named if (n := source_of(a)) is not None):
            if name not in declared.sources:
                issues.append(
                    CheckIssue(
                        "warn",
                        item.id,
                        f"an author `source:{name}` names no source declared in sources.toml",
                        "source_author_declared",
                    )
                )
    return issues


def _identities(db: SquadsDB, declared: SourcesSpec) -> list[CheckIssue]:
    """Operator identity keys that name an undeclared source, and one tracker user held by two
    operators."""
    issues: list[CheckIssue] = []
    held: dict[tuple[str, str], list[Item]] = defaultdict(list)
    for item in _items_of(db):
        if item.type != ROSTER_OPERATOR:
            continue
        for name, user_id in sorted((map_attribute(item, AttributeKey.IDENTITIES) or {}).items()):
            if name not in declared.sources:
                issues.append(
                    CheckIssue(
                        "warn",
                        item.id,
                        f"identity {name!r} names no source declared in sources.toml",
                        "identity_source_declared",
                    )
                )
            held[(name, user_id)].append(item)
    for (name, user_id), owners in sorted(held.items()):
        if len(owners) > 1:
            slugs = ", ".join(o.slug for o in owners)
            issues.append(
                CheckIssue(
                    "error",
                    owners[0].id,
                    f"operators {slugs} all hold user {user_id!r} of source {name!r}; "
                    "a tracker user is one operator",
                    "identity_id_unique",
                )
            )
    return issues


def _attribute_lines(db: SquadsDB, texts: Mapping[int, str]) -> list[CheckIssue]:
    """Comments whose attribute line cannot be read."""
    issues: list[CheckIssue] = []
    for item in _items_of(db):
        for stamp, slug in discussion.malformed_attribute_comments(texts.get(item.sequence_id, "")):
            issues.append(
                CheckIssue(
                    "error",
                    item.id,
                    f"the comment by `{slug}` at {stamp} has an sq:attrs line that is not one "
                    "JSON object of strings; it reads as comment text",
                    "comment_attributes_valid",
                )
            )
    return issues


def source_issues(
    db: SquadsDB, sources: SourcesSource, texts: Mapping[int, str]
) -> list[CheckIssue]:
    """Every source finding of the corpus. The rules that judge a name against ``sources.toml``
    run only when it loads; when it does not, that is the one finding about it."""
    issues = _holders(db) + _attribute_lines(db, texts)
    try:
        declared = sources()
    except SquadsError as exc:
        reason = " ".join(str(exc).split())
        issues.append(
            CheckIssue("error", "sources", f"sources config invalid: {reason}", "sources_loads")
        )
        return issues
    return (
        issues + _records(db, declared) + _authors(db, declared, texts) + _identities(db, declared)
    )
