"""The GitLab connector, on REST API v4 against gitlab.com or a self-hosted base URL."""

import re
import urllib.parse
from collections.abc import Iterator, Mapping
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
from squads._sources._gitlab._probes import GitLabProbes
from squads._sources._http import HttpClient, NotFoundError, UnexpectedAnswerError
from squads._sources._probes import Expected, Family, ProbeResult
from squads._sources._records import text
from squads._sources._spec import SourceScope

#: A reference to an issue: an optional project path, then ``#`` and the project-local number.
_REFERENCE_RE = re.compile(r"(?<![\w/&#.-])((?:[\w.-]+/)*[\w.-]+)?#(\d+)\b")
_GLOBAL_ID = "gid://gitlab/Issue/"
#: GitLab's two link types that read differently from each end, each the other's inverse.
_BLOCK_LINKS = ("blocks", "is_blocked_by")
_SYMMETRIC_LINK = "relates_to"
_STATE_OPEN = "opened"
_STATE_CLOSED = "closed"


def _user(record: object) -> tuple[str, str, str]:
    """The ID, handle and display name of a GitLab user object."""
    user: Mapping[str, Any] = (
        cast("Mapping[str, Any]", record) if isinstance(record, Mapping) else {}
    )
    return text(user, "id"), text(user, "username"), text(user, "name")


def _inverse_link(kind: str) -> str:
    """The name the other end of a GitLab link of type *kind* reads it by; empty when unknown."""
    if kind == _SYMMETRIC_LINK:
        return kind
    return _BLOCK_LINKS[1 - _BLOCK_LINKS.index(kind)] if kind in _BLOCK_LINKS else ""


def _split_key(key: str) -> tuple[str, str]:
    path, _, number = key.rpartition("#")
    return path, number


class GitLabConnector(Connector):
    """Reads issues, notes, links and users of one GitLab instance with a personal or project
    token."""

    credential_fields = ("token",)

    def __init__(self, base_url: str, scope: SourceScope, credential: Mapping[str, str]) -> None:
        self._base = base_url.rstrip("/")
        self._scope = scope
        kind = "groups" if scope.key == "group" else "projects"
        self._listing_path = f"/api/v4/{kind}/{urllib.parse.quote(scope.value, safe='')}/issues"
        self._http = HttpClient(self._base, {"PRIVATE-TOKEN": credential.get("token", "")})

    def probes(self, family: Family, expected: Expected) -> Iterator[ProbeResult]:
        """The access, vocabulary and coverage checks of this source."""
        listed: list[Issue] | None = None

        def listing() -> list[Issue]:
            nonlocal listed
            if listed is None:
                listed = self.listing()
            return listed

        return GitLabProbes(
            self._http, self._base, self._listing_path, self._query(), self._scope, listing
        ).run(family, expected)

    def _query(self) -> dict[str, str]:
        """The one parameter of a listing: every state, no other condition."""
        return {"state": "all"}

    def _parse_issue(self, record: Mapping[str, Any]) -> Issue:
        if record.get("confidential"):
            raise RestrictedIssueError
        author_id, author_handle, _ = _user(record.get("author"))
        references = record.get("references")
        full = (
            text(cast("Mapping[str, Any]", references), "full")
            if isinstance(references, Mapping)
            else ""
        )
        labels = record.get("labels")
        state = record.get("state")
        if state not in (_STATE_OPEN, _STATE_CLOSED) or not (full and text(record, "id")):
            raise UnexpectedAnswerError("an issue without an identity or a known state")
        return Issue(
            id=f"{_GLOBAL_ID}{text(record, 'id')}",
            key=full,
            title=text(record, "title"),
            description=text(record, "description"),
            state="open" if state == _STATE_OPEN else "closed",
            updated_at=text(record, "updated_at"),
            author_id=author_id,
            author_handle=author_handle,
            sides=((TYPE, text(record, "issue_type")),),
            labels=tuple(str(label) for label in cast("list[Any]", labels))
            if isinstance(labels, list)
            else (),
            locator=(("project_id", text(record, "project_id")), ("iid", text(record, "iid"))),
        )

    def listing(self) -> list[Issue]:
        """Every issue of the project or group, closed ones included."""
        found: list[Issue] = []
        self.restricted = 0
        for record in self._http.pages(self._listing_path, self._query()):
            try:
                found.append(self._parse_issue(record))
            except RestrictedIssueError:
                self.restricted += 1
        return found

    def issue(self, issue_id: str, key: str) -> Issue | None:
        """One issue by the project path and number of its last known *key*, which any user with
        read access can fetch; ``None`` when GitLab does not return it or its ID differs."""
        path, number = _split_key(key)
        found = self._issue_by_key(path, number)
        return found if found is not None and found.id == issue_id else None

    def in_scope(self, issue: Issue) -> bool:
        """Whether the project path of *issue*'s key is the scope's project, or lies under its
        group, ignoring case."""
        path = _split_key(issue.key)[0].casefold()
        scope = self._scope.value.casefold()
        if self._scope.key == "group":
            return path.startswith(f"{scope}/")
        return path == scope

    def lookup(self, reference: str) -> Issue | None:
        """The issue named by a key (``group/project#12``), or by its global ID when the scope
        lists it; ``None`` when GitLab returns neither."""
        wanted = reference.strip()
        if "#" in wanted:
            path, number = _split_key(wanted)
            return self._issue_by_key(path, number)
        return next((i for i in self.listing() if i.id == wanted), None)

    def _issue_by_key(self, path: str, number: str) -> Issue | None:
        if not path or not number.isascii() or not number.isdigit():
            raise SquadsError(f"{path}#{number} is not an issue key (group/project#number)")
        try:
            record = self._http.get(
                f"/api/v4/projects/{urllib.parse.quote(path, safe='')}/issues/{number}"
            )
        except NotFoundError:
            return None
        try:
            return self._parse_issue(cast("Mapping[str, Any]", record))
        except RestrictedIssueError:
            return None

    def _issue_path(self, issue: Issue, tail: str) -> str:
        locator = dict(issue.locator)
        project = urllib.parse.quote(locator.get("project_id", ""), safe="")
        return f"/api/v4/projects/{project}/issues/{locator.get('iid', '')}/{tail}"

    def comments(self, issue: Issue) -> list[Comment]:
        """The human notes of *issue*, oldest first; system and internal notes are left out."""
        query = {"order_by": "created_at", "sort": "asc"}
        notes: list[Comment] = []
        for note in self._http.pages(self._issue_path(issue, "notes"), query):
            record = cast("Mapping[str, Any]", note)
            if record.get("system") or record.get("internal"):
                continue
            author_id, handle, name = _user(record.get("author"))
            notes.append(
                Comment(
                    id=text(record, "id"),
                    body=text(record, "body"),
                    author_id=author_id,
                    author_handle=handle,
                    author_name=name,
                    created_at=text(record, "created_at"),
                    updated_at=text(record, "updated_at"),
                )
            )
        return notes

    def links(self, issue: Issue) -> list[Link]:
        """The issues linked to *issue*, with GitLab's name for each link type."""
        found: list[Link] = []
        for linked in self._http.pages(self._issue_path(issue, "links")):
            record = cast("Mapping[str, Any]", linked)
            if record.get("confidential"):
                continue
            references = record.get("references")
            full = (
                text(cast("Mapping[str, Any]", references), "full")
                if isinstance(references, Mapping)
                else ""
            )
            kind = text(record, "link_type")
            found.append(Link(kind, f"{_GLOBAL_ID}{text(record, 'id')}", full, _inverse_link(kind)))
        return found

    def issue_url(self, key: str) -> str:
        """The web address of the issue named by *key* (``group/project#12``)."""
        path, number = _split_key(key)
        return f"{self._base}/{path}/-/issues/{number}"

    def user_url(self, handle: str) -> str:
        """The profile address of *handle*."""
        return f"{self._base}/{urllib.parse.quote(handle.removeprefix('@'), safe='')}"

    def resolve_handle(self, handle: str) -> str | None:
        """The user ID behind *handle*, or ``None`` when GitLab knows no such user."""
        users = self._http.get("/api/v4/users", {"username": handle.removeprefix("@")})
        if isinstance(users, list) and users:
            return text(cast("Mapping[str, Any]", users[0]), "id") or None
        return None

    def references(self, text: str, host_key: str) -> list[Reference]:
        """Each ``#12``, ``project#12`` and ``group/project#12`` in *text*, as a full key."""
        host_path, _ = _split_key(host_key)
        namespace = host_path.rpartition("/")[0]
        found: list[Reference] = []
        for match in _REFERENCE_RE.finditer(text):
            path = match.group(1)
            if path is None:
                full = host_path
            elif "/" in path:
                full = path
            else:
                full = f"{namespace}/{path}" if namespace else path
            found.append(Reference(match.start(), match.end(), f"{full}#{match.group(2)}"))
        return found
