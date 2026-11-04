"""The GitHub connector, on REST API v3 against github.com or an Enterprise Server."""

import re
import urllib.parse
from collections.abc import Iterator, Mapping

from squads._errors import SquadsError
from squads._sources._connector import TYPE, Comment, Connector, Issue, Link, Reference
from squads._sources._github._probes import BLOCKED_BY, BLOCKING, GitHubProbes
from squads._sources._http import HttpClient, NotFoundError, UnexpectedAnswerError
from squads._sources._probes import Expected, Family, ProbeResult
from squads._sources._records import mapping, names, records, text
from squads._sources._spec import SourceScope

#: A reference to an issue: an optional ``owner/repo``, then ``#`` and the repository-local number.
_REFERENCE_RE = re.compile(r"(?<![\w/&#.-])([\w.-]+/[\w.-]+)?#(\d+)\b")
_KEY_RE = re.compile(r"([\w.-]+/[\w.-]+)#(\d+)")
_HOSTED_WEB = "https://github.com"
_HOSTED_API = "https://api.github.com"
_HOSTED_HOSTS = frozenset({"github.com", "www.github.com", "api.github.com"})
_ENTERPRISE_API_PATH = "/api/v3"
#: The domain of GitHub Enterprise Cloud with data residency, whose API host is ``api.<host>``.
_DATA_RESIDENCY = ".ghe.com"
_API_VERSION = "2022-11-28"
_STATE_OPEN = "open"
_STATE_CLOSED = "closed"


def _roots(base_url: str) -> tuple[str, str]:
    """The web address and the API address of the instance *base_url* names: github.com, an
    Enterprise API root (``…/api/v3``) or an Enterprise web root."""
    base = base_url.rstrip("/")
    parts = urllib.parse.urlsplit(base)
    if (parts.hostname or "").lower() in _HOSTED_HOSTS and not parts.path:
        return _HOSTED_WEB, _HOSTED_API
    host = (parts.hostname or "").lower()
    if host.endswith(_DATA_RESIDENCY) and not parts.path:
        web_host = host.removeprefix("api.")
        return f"{parts.scheme}://{web_host}", f"{parts.scheme}://api.{web_host}"
    if base.endswith(_ENTERPRISE_API_PATH):
        return base.removesuffix(_ENTERPRISE_API_PATH), base
    return base, f"{base}{_ENTERPRISE_API_PATH}"


def _repository(record: Mapping[str, object]) -> str:
    """The ``owner/repo`` an issue object belongs to, from its repository address."""
    address = text(record, "repository_url")
    _, found, repo = urllib.parse.urlsplit(address).path.partition("/repos/")
    return repo.strip("/") if found else ""


def _user(record: object) -> tuple[str, str]:
    """The ID and login of a GitHub user object; a deleted account has neither."""
    user = mapping(record)
    return text(user, "id"), text(user, "login")


class GitHubConnector(Connector):
    """Reads issues, comments, dependencies and users of one GitHub instance with a token."""

    credential_fields = ("token",)

    def __init__(self, base_url: str, scope: SourceScope, credential: Mapping[str, str]) -> None:
        self._web, self._api = _roots(base_url)
        self._scope = scope
        self._listing_path = f"/repos/{urllib.parse.quote(scope.value, safe='/')}/issues"
        self._http = HttpClient(
            self._api,
            {
                "Authorization": f"Bearer {credential.get('token', '')}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": _API_VERSION,
            },
        )

    def probes(self, family: Family, expected: Expected) -> Iterator[ProbeResult]:
        """The access, vocabulary and coverage checks of this source."""
        listed: list[Issue] | None = None

        def listing() -> list[Issue]:
            nonlocal listed
            if listed is None:
                listed = self.listing()
            return listed

        return GitHubProbes(
            self._http, self._api, self._listing_path, self._query(), self._scope, listing
        ).run(family, expected)

    def _query(self) -> dict[str, str]:
        """The one parameter of a listing: every state, no other condition."""
        return {"state": "all"}

    def _parse_issue(self, record: Mapping[str, object]) -> Issue | None:
        """The issue object as an ``Issue``; a pull request, or an object without an identity,
        is not one."""
        repo, number, node = _repository(record), text(record, "number"), text(record, "node_id")
        if "pull_request" in record:
            return None
        state = record.get("state")
        if state not in (_STATE_OPEN, _STATE_CLOSED) or not (repo and number and node):
            raise UnexpectedAnswerError("an issue without an identity or a known state")
        author_id, author_handle = _user(record.get("user"))
        return Issue(
            id=node,
            key=f"{repo}#{number}",
            title=text(record, "title"),
            description=text(record, "body"),
            state="open" if state == _STATE_OPEN else "closed",
            updated_at=text(record, "updated_at"),
            author_id=author_id,
            author_handle=author_handle,
            sides=((TYPE, text(mapping(record.get("type")), "name")),),
            labels=names(record.get("labels")),
            locator=(("repo", repo), ("number", number)),
        )

    def listing(self) -> list[Issue]:
        """Every issue of the repository, closed ones included; pull requests are left out."""
        found = (
            self._parse_issue(r)
            for r in records(list(self._http.link_pages(self._listing_path, self._query())))
        )
        return [issue for issue in found if issue is not None]

    def issue(self, issue_id: str, key: str) -> Issue | None:
        """One issue by its last known *key*, which GitHub redirects after a transfer;
        ``None`` when GitHub does not return it or its ID differs."""
        found = self._issue_by_key(key)
        return found if found is not None and found.id == issue_id else None

    def lookup(self, reference: str) -> Issue | None:
        """The issue named by a key (``owner/repo#12``), or by its node ID when the scope lists
        it; ``None`` when GitHub returns neither."""
        wanted = reference.strip()
        if "#" in wanted:
            return self._issue_by_key(wanted)
        return next((i for i in self.listing() if i.id == wanted), None)

    def _issue_by_key(self, key: str) -> Issue | None:
        matched = _KEY_RE.fullmatch(key)
        if matched is None:
            raise SquadsError(f"{key} is not an issue key (owner/repo#number)")
        repo, number = matched.groups()
        try:
            record = self._http.get(f"/repos/{urllib.parse.quote(repo, safe='/')}/issues/{number}")
        except NotFoundError:
            return None
        return self._parse_issue(mapping(record))

    def _issue_path(self, issue: Issue, tail: str) -> str:
        locator = dict(issue.locator)
        repo = urllib.parse.quote(locator.get("repo", ""), safe="/")
        return f"/repos/{repo}/issues/{locator.get('number', '')}/{tail}"

    def comments(self, issue: Issue) -> list[Comment]:
        """The comments of *issue*, oldest first."""
        found: list[Comment] = []
        for record in records(list(self._http.link_pages(self._issue_path(issue, "comments")))):
            author_id, login = _user(record.get("user"))
            found.append(
                Comment(
                    id=text(record, "id"),
                    body=text(record, "body"),
                    author_id=author_id,
                    author_handle=login,
                    author_name=login,
                    created_at=text(record, "created_at"),
                    updated_at=text(record, "updated_at"),
                )
            )
        return found

    def links(self, issue: Issue) -> list[Link]:
        """The issues *issue* is blocked by and the issues it blocks; an instance without
        dependencies has none."""
        found: list[Link] = []
        for link_type in (BLOCKED_BY, BLOCKING):
            path = self._issue_path(issue, f"dependencies/{link_type}")
            try:
                linked = list(self._http.link_pages(path))
            except NotFoundError:
                continue
            for record in records(linked):
                target = self._parse_issue(record)
                if target is not None:
                    found.append(Link(link_type, target.id, target.key))
        return found

    def issue_url(self, key: str) -> str:
        """The web address of the issue named by *key* (``owner/repo#12``)."""
        repo, _, number = key.rpartition("#")
        return f"{self._web}/{repo}/issues/{number}"

    def user_url(self, handle: str) -> str:
        """The profile address of *handle*."""
        return f"{self._web}/{urllib.parse.quote(handle.removeprefix('@'), safe='')}"

    def resolve_handle(self, handle: str) -> str | None:
        """The user ID behind *handle*, or ``None`` when GitHub knows no such user."""
        login = urllib.parse.quote(handle.removeprefix("@"), safe="")
        try:
            user = self._http.get(f"/users/{login}")
        except NotFoundError:
            return None
        return text(mapping(user), "id") or None

    def references(self, text: str, host_key: str) -> list[Reference]:
        """Each ``#12`` and ``owner/repo#12`` in *text*, as a full key."""
        host_repo = host_key.rpartition("#")[0]
        return [
            Reference(m.start(), m.end(), f"{m.group(1) or host_repo}#{m.group(2)}")
            for m in _REFERENCE_RE.finditer(text)
            if m.group(1) or host_repo
        ]
