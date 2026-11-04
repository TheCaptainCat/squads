"""The checks of ``sq source check`` for GitHub: whether the host answers, the token works and
reads the filter, whether every value a map names exists, and which tracker values nothing maps."""

import urllib.parse
from collections.abc import Callable
from typing import Any

from squads._sources._connector import TYPE, Issue
from squads._sources._http import HttpClient, MalformedAnswerError
from squads._sources._probes import Expected
from squads._sources._records import is_object, mapping, names
from squads._sources._tracker_probes import TrackerProbes

#: What the dependency endpoints of an issue are named: the link types a GitHub issue has.
BLOCKED_BY = "blocked_by"
BLOCKING = "blocking"


class GitHubProbes(TrackerProbes):
    """The probes of one GitHub source, over the connector's client and its listing."""

    tracker = "GitHub"

    def __init__(
        self,
        http: HttpClient,
        base: str,
        query: dict[str, str],
        listing: Callable[[], list[Issue]],
    ) -> None:
        super().__init__(http, base, listing)
        self._query = query

    def reach(self) -> None:
        """Ask for the instance's public metadata."""
        self._http.get("/meta")

    def identify(self) -> str:
        """Ask the instance who the token belongs to."""
        user: object = self._http.get("/user")
        if not is_object(user):
            raise MalformedAnswerError("/user")
        who = mapping(user)
        return f"authenticated as {who.get('login')} (id {who.get('id')})"

    def read(self) -> bool:
        """Whether the filter selects an issue."""
        page: Any = self._http.get("/issues", {**self._query, "per_page": "1", "page": "1"})
        if not isinstance(page, list):
            raise MalformedAnswerError("/issues")
        return page != []

    def filter_text(self) -> str:
        """The label filter, quoted."""
        return repr(self._query.get("labels", ""))

    def credential_fix(self, expected: Expected) -> str:
        """Store a valid token."""
        return (
            f"run `sq source credential set {expected.source}` with a valid personal access token"
        )

    def read_fix(self, expected: Expected) -> str:
        """Store a token that can read the repositories' issues."""
        return (
            "create a token that can read issues (the `repo` scope, or read access to Issues on "
            f"a fine-grained token), then run `sq source credential set {expected.source}`"
        )

    def known_values(self, side: str, issues: list[Issue]) -> tuple[frozenset[str], bool]:
        """The issue types in use on the in-filter issues (the full list is the organisation's,
        which is not read), or the labels of every repository that holds an in-filter issue."""
        if side == TYPE:
            return frozenset(v for i in issues for v in i.values(TYPE)), False
        repos = sorted({dict(i.locator).get("repo", "") for i in issues} - {""})
        labels: set[str] = set()
        for repo in repos:
            path = f"/repos/{urllib.parse.quote(repo, safe='/')}/labels"
            labels.update(names(list(self._http.link_pages(path))))
        return frozenset(labels), True

    def link_types(self) -> tuple[str, ...]:
        """GitHub's dependency link types."""
        return (BLOCKED_BY, BLOCKING)

    def user_exists(self, user_id: str) -> None:
        """Ask for the user by ID."""
        self._http.get(f"/user/{urllib.parse.quote(user_id, safe='')}")
