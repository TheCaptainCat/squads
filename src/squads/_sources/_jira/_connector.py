"""The Jira connector's shared code: issues are read by their immutable ID through the JQL search,
and what differs between the cloud and the Data Center APIs is a method of the version."""

import re
import urllib.parse
from abc import abstractmethod
from collections.abc import Iterator, Mapping
from datetime import UTC, datetime
from email.message import Message
from typing import Any, cast

from squads._errors import SquadsError
from squads._sources._connector import (
    TYPE,
    Comment,
    Connector,
    Issue,
    Link,
    Reference,
    RestrictedIssueError,
)
from squads._sources._http import (
    Advance,
    HttpClient,
    NotFoundError,
    UnexpectedAnswerError,
    member_items,
)
from squads._sources._jira._probes import JiraHooks, JiraProbes
from squads._sources._probes import Expected, Family, ProbeResult
from squads._sources._records import mapping, names, records, text
from squads._sources._spec import SourceScope

#: A reference to an issue: a project key, a dash and a number.
_REFERENCE_RE = re.compile(r"(?<![\w-])([A-Z][A-Z0-9_]+-\d+)\b")
_REFERENCE_SHAPE_RE = re.compile(r"[A-Za-z0-9_-]+")
#: The fields of Jira's issue object this connector reads: tracker API names.
_ISSUE_FIELDS = (
    "summary",
    "description",
    "status",
    "issuetype",
    "priority",
    "labels",
    "reporter",
    "creator",
    "updated",
    "security",
)
(
    _SUMMARY,
    _DESCRIPTION,
    _STATUS,
    _ISSUE_TYPE,
    _PRIORITY,
    _LABELS,
    _,
    _CREATOR,
    _UPDATED,
    _SECURITY,
) = _ISSUE_FIELDS
_FIELDS = ",".join(_ISSUE_FIELDS)
_PAGE_SIZE = "100"
#: The ``statusCategory`` keys of Jira's status model: the work is finished, or it is not.
_CLOSED_CATEGORIES = frozenset({"done"})
_OPEN_CATEGORIES = frozenset({"new", "indeterminate", "undefined"})


def utc_stamp(value: str) -> str:
    """*value*, a Jira timestamp in the account's offset, as ISO UTC with its milliseconds; text
    that is not a timestamp is kept as it is."""
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return value
    if moment.tzinfo is None:
        return value
    return moment.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def offset_advance(key: str) -> Advance:
    """The next query of a Jira page that carries ``startAt`` and ``total`` and lists its
    elements under *key*."""

    def advance(
        document: Any, headers: Message, params: Mapping[str, str]
    ) -> dict[str, str] | None:
        page = mapping(document)
        found = page.get(key)
        total = page.get("total")
        start = int(params.get("startAt", "0"))
        following = start + (len(cast("list[Any]", found)) if isinstance(found, list) else 0)
        if not isinstance(total, int) or isinstance(total, bool):
            raise UnexpectedAnswerError("a page of a listing gives no numeric total")
        if following >= total:
            return None
        if following <= start:
            raise UnexpectedAnswerError("an empty page comes before the listing's total")
        return {**params, "startAt": str(following)}

    return advance


class JiraConnector(Connector):
    """Reads issues, comments, links and users of one Jira instance."""

    #: The REST API root below the base URL.
    api: str

    def __init__(self, base_url: str, scope: SourceScope, credential: Mapping[str, str]) -> None:
        self._base = base_url.rstrip("/")
        self._scope = scope
        self._jql = scope.value
        self._http = HttpClient(self._base, self._headers(credential))

    @abstractmethod
    def _headers(self, credential: Mapping[str, str]) -> dict[str, str]:
        """The request headers that authenticate with *credential*."""

    @abstractmethod
    def _search(self, jql: str, fields: str, size: str) -> Iterator[Any]:
        """Every issue object *jql* selects, with *fields*, *size* to the page."""

    @abstractmethod
    def _text(self, value: object) -> str:
        """A description or comment body as the version's converter reads it."""

    @abstractmethod
    def _person(self, record: object) -> tuple[str, str, str]:
        """The ID, handle and display name of a user object."""

    @abstractmethod
    def _comment_query(self) -> dict[str, str]:
        """The extra query of the comment listing that makes the version report a comment's
        agent-only mark."""

    @abstractmethod
    def _agents_only(self, comment: Mapping[str, Any]) -> bool:
        """Whether *comment* is a service desk comment only agents may read."""

    @abstractmethod
    def user_url(self, handle: str) -> str:
        """The profile address of *handle*."""

    @abstractmethod
    def resolve_handle(self, handle: str) -> str | None:
        """The user ID behind *handle*, or ``None`` when Jira knows no such user."""

    @abstractmethod
    def _user_exists(self, user_id: str) -> None:
        """Ask for the user *user_id*; raises ``NotFoundError`` when there is none."""

    @abstractmethod
    def _describe(self, who: Mapping[str, object]) -> str:
        """The sentence the access check prints for the account the credential belongs to."""

    #: Whether the version lists every label of the instance.
    _labels_complete: bool

    @abstractmethod
    def _extra_labels(self) -> set[str]:
        """The labels the version can list beyond those on the in-scope issues."""

    def _first_page_selects(self) -> bool:
        return any(True for _ in self._search(self._filter(), _SUMMARY, "1"))

    def _filter(self) -> str:
        return self._jql

    def probes(self, family: Family, expected: Expected) -> Iterator[ProbeResult]:
        """The access, vocabulary and coverage checks of this source."""
        listed: list[Issue] | None = None

        def listing() -> list[Issue]:
            nonlocal listed
            if listed is None:
                listed = self.listing()
            return listed

        hooks = JiraHooks(
            self._first_page_selects,
            self._describe,
            self._user_exists,
            self._extra_labels,
            self._labels_complete,
        )
        return JiraProbes(self._http, self._base, self.api, self._scope, listing, hooks).run(
            family, expected
        )

    def _parse_issue(self, record: Mapping[str, Any]) -> Issue:
        issue_id, key = text(record, "id"), text(record, "key")
        if not (issue_id and key):
            raise UnexpectedAnswerError("an issue without an id and a key")
        fields = mapping(record.get("fields"))
        if fields.get(_SECURITY):
            raise RestrictedIssueError
        category = text(mapping(mapping(fields.get(_STATUS)).get("statusCategory")), "key")
        if category not in _CLOSED_CATEGORIES | _OPEN_CATEGORIES:
            raise UnexpectedAnswerError(f"issue {key} has no known status category")
        author_id, author_handle, _ = self._person(fields.get(_CREATOR))
        priority = text(mapping(fields.get(_PRIORITY)), "name")
        return Issue(
            id=issue_id,
            key=key,
            title=text(fields, _SUMMARY),
            description=self._text(fields.get(_DESCRIPTION)),
            state="closed" if category in _CLOSED_CATEGORIES else "open",
            updated_at=utc_stamp(text(fields, _UPDATED)),
            author_id=author_id,
            author_handle=author_handle,
            labels=names(fields.get(_LABELS)),
            sides=((TYPE, text(mapping(fields.get(_ISSUE_TYPE)), "name")), (_PRIORITY, priority)),
            locator=(("id", issue_id),),
        )

    def listing(self) -> list[Issue]:
        """Every issue the scope's JQL returns, closed ones included."""
        found: list[Issue] = []
        self.restricted = 0
        for record in self._search(self._filter(), _FIELDS, _PAGE_SIZE):
            try:
                found.append(self._parse_issue(mapping(record)))
            except RestrictedIssueError:
                self.restricted += 1
        return found

    def _issue_by(self, reference: str) -> Issue | None:
        """The issue named by an ID or a key; Jira answers 404 for one it will not show."""
        if not _REFERENCE_SHAPE_RE.fullmatch(reference):
            raise SquadsError(f"{reference!r} is not an issue key (PROJ-12) or an issue ID")
        try:
            record = self._http.get(
                f"{self.api}/issue/{urllib.parse.quote(reference, safe='')}", {"fields": _FIELDS}
            )
        except NotFoundError:
            return None
        try:
            return self._parse_issue(mapping(record))
        except RestrictedIssueError:
            return None

    def issue(self, issue_id: str, key: str) -> Issue | None:
        """One issue by its ID, which survives a move to another project; ``None`` when Jira does
        not return it."""
        found = self._issue_by(issue_id)
        return found if found is not None and found.id == issue_id else None

    def in_scope(self, issue: Issue) -> bool:
        """Whether one search for *issue* inside the scope's JQL finds it."""
        selected = self._search(f"id = {issue.id} AND ({self._filter()})", _SUMMARY, "1")
        return any(True for _ in selected)

    def lookup(self, reference: str) -> Issue | None:
        """The issue named by a key (``PROJ-12``) or an ID; ``None`` when Jira returns none."""
        return self._issue_by(reference.strip())

    def _issue_path(self, issue: Issue, tail: str) -> str:
        issue_id = urllib.parse.quote(dict(issue.locator).get("id", ""), safe="")
        return f"{self.api}/issue/{issue_id}{tail}"

    def comments(self, issue: Issue) -> list[Comment]:
        """The comments of *issue*, oldest first; a comment restricted to a group, a role or the
        agents of a service desk is left out."""
        pages = self._http.paged(
            self._issue_path(issue, "/comment"),
            {
                "startAt": "0",
                "maxResults": _PAGE_SIZE,
                "orderBy": "created",
                **self._comment_query(),
            },
            offset_advance("comments"),
            member_items("comments"),
        )
        found: list[Comment] = []
        for record in records(list(pages)):
            if record.get("visibility") or self._agents_only(record):
                continue
            author_id, handle, name = self._person(record.get("author"))
            found.append(
                Comment(
                    id=text(record, "id"),
                    body=self._text(record.get("body")),
                    author_id=author_id,
                    author_handle=handle,
                    author_name=name,
                    created_at=utc_stamp(text(record, "created")),
                    updated_at=utc_stamp(text(record, "updated")),
                )
            )
        return found

    def links(self, issue: Issue) -> list[Link]:
        """The issues linked to *issue*, each with the phrase for its direction."""
        record = mapping(self._http.get(self._issue_path(issue, ""), {"fields": "issuelinks"}))
        found: list[Link] = []
        for link in records(mapping(record.get("fields")).get("issuelinks")):
            kind = mapping(link.get("type"))
            for side, other, target in (
                ("outward", "inward", "outwardIssue"),
                ("inward", "outward", "inwardIssue"),
            ):
                linked = mapping(link.get(target))
                if linked:
                    found.append(
                        Link(
                            text(kind, side),
                            text(linked, "id"),
                            text(linked, "key"),
                            text(kind, other),
                        )
                    )
        return found

    def issue_url(self, key: str) -> str:
        """The web address of the issue named by *key*."""
        return f"{self._base}/browse/{urllib.parse.quote(key, safe='')}"

    def references(self, text: str, host_key: str) -> list[Reference]:
        """Each project key and number in *text*, which is already a full key."""
        return [Reference(m.start(), m.end(), m.group(1)) for m in _REFERENCE_RE.finditer(text)]
